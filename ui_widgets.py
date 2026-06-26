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
