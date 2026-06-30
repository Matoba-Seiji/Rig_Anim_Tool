from PySide2 import QtCore, QtGui, QtWidgets


class DropPathLineEdit(QtWidgets.QLineEdit):
    def __init__(self, path_mode='file', parent=None):
        super(DropPathLineEdit, self).__init__(parent)
        self.path_mode = path_mode
        self.setAcceptDrops(True)

    def _path_from_drop(self, event):
        if not event.mimeData().hasUrls():
            return ''
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if not path:
                continue
            if self.path_mode == 'dir' and QtCore.QFileInfo(path).isFile():
                return QtCore.QFileInfo(path).absolutePath()
            return path
        return ''

    def dragEnterEvent(self, event):
        if self._path_from_drop(event):
            event.acceptProposedAction()
        else:
            super(DropPathLineEdit, self).dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if self._path_from_drop(event):
            event.acceptProposedAction()
        else:
            super(DropPathLineEdit, self).dragMoveEvent(event)

    def dropEvent(self, event):
        path = self._path_from_drop(event)
        if path:
            self.setText(path)
            event.acceptProposedAction()
        else:
            super(DropPathLineEdit, self).dropEvent(event)


class _CheckRowWidget(QtWidgets.QWidget):
    _NAME_FONT_PX = 18
    _DETAIL_FONT_PX = 15
    _STATUS_COL_W = 26
    _EXPAND_COL_W = 24

    def __init__(self, label, parent=None):
        super(_CheckRowWidget, self).__init__(parent)
        self._label = label
        self._details = []
        self._expanded = False
        self.status = 'pending'

        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        header = QtWidgets.QWidget()
        header_layout = QtWidgets.QHBoxLayout(header)
        header_layout.setContentsMargins(4, 3, 4, 3)
        header_layout.setSpacing(6)

        self._status_label = QtWidgets.QLabel('—')
        self._status_label.setFixedWidth(self._STATUS_COL_W)
        self._status_label.setAlignment(QtCore.Qt.AlignCenter)
        self._status_label.setStyleSheet(
            'color: #888888; font-size: 18px; background: transparent;')
        header_layout.addWidget(self._status_label)

        self._name_label = QtWidgets.QLabel(label)
        self._name_label.setStyleSheet(
            'color: #CCCCCC; font-size: %dpx; background: transparent;'
            % self._NAME_FONT_PX)
        header_layout.addWidget(self._name_label, stretch=1)

        self._expand_btn = QtWidgets.QPushButton('▶')
        self._expand_btn.setFixedSize(self._EXPAND_COL_W, 26)
        self._expand_btn.setEnabled(False)
        self._expand_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #666666;
                border: none;
                font-size: 11px;
            }
            QPushButton:enabled:hover { color: #AAAAAA; }
            QPushButton:disabled { color: #333333; }
        """)
        self._expand_btn.clicked.connect(self._toggle_expanded)
        header_layout.addWidget(self._expand_btn)

        self._detail = QtWidgets.QLabel()
        self._detail.setWordWrap(True)
        self._detail.setContentsMargins(36, 0, 8, 6)
        self._detail.setStyleSheet(
            'color: #AAAAAA; font-size: %dpx; background: transparent;'
            % self._DETAIL_FONT_PX)
        self._detail.hide()

        outer.addWidget(header)
        outer.addWidget(self._detail)

    def _set_expanded(self, expanded):
        self._expanded = expanded and bool(self._details)
        self._expand_btn.setText('▼' if self._expanded else '▶')
        self._detail.setVisible(self._expanded)

    def _toggle_expanded(self):
        self._set_expanded(not self._expanded)

    def set_status(self, status, details=None):
        self.status = status
        self._details = [line for line in (details or []) if line]
        styles = {
            'pending': ('—', '#888888', 18),
            'running': ('…', '#2d7dff', 18),
            'ok': ('✓', '#2fa84f', 20),
            'warning': ('⚠', '#d6a800', 18),
            'error': ('✗', '#d9534f', 20),
        }
        text, color, size = styles.get(status, styles['pending'])
        self._status_label.setText(text)
        self._status_label.setStyleSheet(
            'color: %s; font-size: %dpx; background: transparent;'
            % (color, size))

        has_details = bool(self._details)
        self._expand_btn.setEnabled(has_details)
        if has_details:
            detail_color = color if status in ('warning', 'error') else '#888888'
            self._detail.setText('\n'.join(self._details))
            self._detail.setStyleSheet(
                'color: %s; font-size: %dpx; background: transparent;'
                % (detail_color, self._DETAIL_FONT_PX))
            self._set_expanded(status in ('warning', 'error'))
        else:
            self._detail.clear()
            self._set_expanded(False)


class CheckListWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(CheckListWidget, self).__init__(parent)
        self._scroll = QtWidgets.QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self._container = QtWidgets.QWidget()
        self._container.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Minimum)
        self._layout = QtWidgets.QVBoxLayout(self._container)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(2)
        self._layout.addStretch(1)
        self._scroll.setWidget(self._container)
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self._scroll)
        self._items = {}

    def _clear_rows(self):
        while self._layout.count() > 1:
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        self._items.clear()

    def load(self, specs):
        spec_ids = [check_id for check_id, _label in specs]
        if spec_ids and spec_ids == list(self._items.keys()):
            self.reset_all()
            return
        self._clear_rows()
        for check_id, label in specs:
            row = _CheckRowWidget(label, self._container)
            self._layout.insertWidget(self._layout.count() - 1, row)
            self._items[check_id] = row
            row.set_status('pending')
        self._container.adjustSize()

    def reset_all(self):
        for row in self._items.values():
            row.set_status('pending')

    def set_check(self, check_id, status, details=None):
        row = self._items.get(check_id)
        if row:
            row.set_status(status, details)

    def count_finished(self):
        return sum(
            1 for row in self._items.values()
            if row.status in ('ok', 'warning', 'error'))


class TaskProgressWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(TaskProgressWidget, self).__init__(parent)

        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        self.task_list = QtWidgets.QListWidget()

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.task_list)

        self.steps = []

    def load(self, steps):
        self.steps = steps
        self.task_list.clear()
        self.progress_bar.setValue(0)

        for name, _func, _cache in steps:
            item = QtWidgets.QListWidgetItem("[等待] %s" % name)
            item.setForeground(QtGui.QColor("#888888"))
            self.task_list.addItem(item)

    def set_item_state(self, index, state, text):
        item = self.task_list.item(index)
        if not item:
            return

        if state == "running":
            item.setText("[执行中] %s" % text)
            item.setForeground(QtGui.QColor("#2d7dff"))
        elif state == "done":
            item.setText("[完成] %s" % text)
            item.setForeground(QtGui.QColor("#2fa84f"))
        elif state == "warning":
            item.setText("[警告] %s" % text)
            item.setForeground(QtGui.QColor("#d6a800"))
        elif state == "failed":
            item.setText("[失败] %s" % text)
            item.setForeground(QtGui.QColor("#d9534f"))
        else:
            item.setText("[等待] %s" % text)
            item.setForeground(QtGui.QColor("#888888"))

        QtWidgets.QApplication.processEvents()

    def set_progress(self, value):
        value = max(0.0, min(1.0, value))
        self.progress_bar.setValue(int(value * 100))
        QtWidgets.QApplication.processEvents()


class FbxFileListWidget(QtWidgets.QListWidget):
    filesChanged = QtCore.Signal(list)

    def __init__(self, parent=None):
        super(FbxFileListWidget, self).__init__(parent)
        self.setAcceptDrops(True)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.setMinimumHeight(150)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def _current_files(self):
        files = []
        for index in range(self.count()):
            item = self.item(index)
            files.append(item.toolTip() or item.text())
        return files

    def _emit_files_changed(self):
        self.filesChanged.emit(self._current_files())

    def _remove_selected_items(self):
        for item in self.selectedItems():
            self.takeItem(self.row(item))
        self._emit_files_changed()

    def _clear_items(self):
        self.clear()
        self._emit_files_changed()

    def _show_context_menu(self, pos):
        menu = QtWidgets.QMenu(self)
        remove_action = menu.addAction('删除所选')
        remove_action.setEnabled(bool(self.selectedItems()))
        clear_action = menu.addAction('清空列表')
        clear_action.setEnabled(self.count() > 0)

        action = menu.exec_(self.mapToGlobal(pos))
        if action == remove_action:
            self._remove_selected_items()
        elif action == clear_action:
            self._clear_items()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super(FbxFileListWidget, self).dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super(FbxFileListWidget, self).dragMoveEvent(event)

    def dropEvent(self, event):
        paths = [url.toLocalFile() for url in event.mimeData().urls()
                 if url.toLocalFile()]
        if paths:
            self.filesChanged.emit(paths)
            event.acceptProposedAction()
        else:
            super(FbxFileListWidget, self).dropEvent(event)
