from maya import cmds
from PySide2 import QtWidgets, QtCore
import maya.OpenMayaUI as omui
from shiboken2 import wrapInstance
from maya import mel
import os
import json
import tempfile
import time as _time

import ui_widgets
import asset_validation
import maya_fbx
import ue_remote
import ue_scripts

TaskProgressWidget = ui_widgets.TaskProgressWidget
DropPathLineEdit = ui_widgets.DropPathLineEdit
FbxFileListWidget = ui_widgets.FbxFileListWidget

# 加载HumanIK控制代码
MAYA_LOCATION = os.environ['MAYA_LOCATION']
mel.eval('source "'+MAYA_LOCATION+'/scripts/others/hikGlobalUtils.mel"')
mel.eval('source "'+MAYA_LOCATION+'/scripts/others/hikCharacterControlsUI.mel"')
mel.eval('source "'+MAYA_LOCATION + '/scripts/others/hikDefinitionOperations.mel"')


# ---------------- Maya UI ----------------

def get_maya_main_window():
    main_window_ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(int(main_window_ptr), QtWidgets.QWidget)


class RetargetUI(QtWidgets.QWidget):
    def __init__(self):
        parent = get_maya_main_window()
        super().__init__(parent)

        self.setWindowTitle('Maya 到 UE 工具')
        self.setWindowFlags(QtCore.Qt.Dialog)
        self.setMinimumWidth(800)

        root_layout = QtWidgets.QVBoxLayout(self)
        self.tabs = QtWidgets.QTabWidget()
        root_layout.addWidget(self.tabs)

        label_width = 72
        row_height = 28
        icon_size = 18
        app_style = QtWidgets.QApplication.style()

        def _style_path_label(text):
            label = QtWidgets.QLabel(text)
            label.setFixedWidth(label_width)
            label.setMinimumHeight(row_height)
            label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            return label

        def _style_path_icon_button(icon, tooltip, name):
            button = QtWidgets.QToolButton()
            button.setIcon(icon)
            button.setIconSize(QtCore.QSize(icon_size, icon_size))
            button.setFixedSize(row_height, row_height)
            button.setToolTip(tooltip)
            button.setObjectName(name)
            return button

        def _style_path_line(line_edit):
            line_edit.setMinimumHeight(row_height)
            return line_edit

        # ---- Tab 1: 批量重定向 ----
        tab_retarget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab_retarget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        path_grid = QtWidgets.QGridLayout()
        path_grid.setHorizontalSpacing(8)
        path_grid.setVerticalSpacing(8)
        path_grid.setColumnStretch(1, 1)

        file_icon = app_style.standardIcon(QtWidgets.QStyle.SP_FileIcon)
        folder_icon = app_style.standardIcon(QtWidgets.QStyle.SP_DirIcon)

        self.target_line = _style_path_line(DropPathLineEdit('file'))
        target_btn = _style_path_icon_button(
            file_icon, '导入目标文件', 'browse_target')
        target_btn.clicked.connect(self.open_dialog)
        path_grid.addWidget(_style_path_label('目标文件:'), 0, 0)
        path_grid.addWidget(self.target_line, 0, 1)
        path_grid.addWidget(target_btn, 0, 2)

        self.yuan_line = _style_path_line(DropPathLineEdit('file'))
        yuan_btn = _style_path_icon_button(
            file_icon, '导入源文件', 'browse_source')
        yuan_btn.clicked.connect(self.open_dialog)
        path_grid.addWidget(_style_path_label('源文件:'), 1, 0)
        path_grid.addWidget(self.yuan_line, 1, 1)
        path_grid.addWidget(yuan_btn, 1, 2)

        self.export_line = _style_path_line(DropPathLineEdit('dir'))
        export_btn = _style_path_icon_button(
            folder_icon, '设置导出路径', 'browse_export')
        export_btn.clicked.connect(self.open_dialog_files)
        path_grid.addWidget(_style_path_label('导出路径:'), 2, 0)
        path_grid.addWidget(self.export_line, 2, 1)
        path_grid.addWidget(export_btn, 2, 2)

        layout.addLayout(path_grid)

        anim_group = QtWidgets.QGroupBox('源动画文件')
        anim_group_layout = QtWidgets.QVBoxLayout(anim_group)
        anim_group_layout.setContentsMargins(8, 8, 8, 8)
        self.anim_file_list_widget = FbxFileListWidget()
        self.anim_file_list_widget.setMinimumHeight(220)
        self.anim_file_list_widget.filesChanged.connect(self.add_anim_paths)
        anim_group_layout.addWidget(self.anim_file_list_widget)
        layout.addWidget(anim_group, 1)

        start_btn = QtWidgets.QPushButton('开始')
        start_btn.setMinimumHeight(36)
        start_btn.clicked.connect(self.HumanIK_Retarget)
        layout.addWidget(start_btn)

        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.tabs.addTab(tab_retarget, '批量重定向')

        # ---- Tab 2: 绑定模块 ----
        tab_rig = QtWidgets.QWidget()
        rig_layout = QtWidgets.QVBoxLayout(tab_rig)

        rig_layout.addWidget(QtWidgets.QLabel('UE 绑定导入路径'))
        self.rig_ue_import_line = QtWidgets.QLineEdit('/Game/Maya')
        rig_layout.addWidget(self.rig_ue_import_line)

        check_rig_btn = QtWidgets.QPushButton('自动检测')
        check_rig_btn.clicked.connect(self.auto_check_rig_asset)
        rig_layout.addWidget(check_rig_btn)

        self.rig_task_widget = TaskProgressWidget()
        self.rig_task_widget.setMinimumHeight(260)
        rig_layout.addWidget(self.rig_task_widget)
        self._init_rig_task_list()

        rig_layout.addStretch(1)

        send_rig_btn = QtWidgets.QPushButton('Send To UE')
        send_rig_btn.clicked.connect(self.send_rig_to_ue)
        rig_layout.addWidget(send_rig_btn)

        self.rig_progress_bar = QtWidgets.QProgressBar()
        self.rig_progress_bar.setRange(0, 100)
        self.rig_progress_bar.setValue(0)
        rig_layout.addWidget(self.rig_progress_bar)

        self.tabs.addTab(tab_rig, '绑定导出')

        # ---- Tab 3: 动画模块 ----
        tab_anim = QtWidgets.QWidget()
        anim_layout = QtWidgets.QVBoxLayout(tab_anim)
        anim_layout.setContentsMargins(12, 12, 12, 12)
        anim_layout.setSpacing(8)

        anim_path_grid = QtWidgets.QGridLayout()
        anim_path_grid.setHorizontalSpacing(8)
        anim_path_grid.setVerticalSpacing(8)
        anim_path_grid.setColumnStretch(1, 1)

        anim_path_grid.addWidget(_style_path_label('UE 导入路径:'), 0, 0)
        self.anim_ue_import_line = QtWidgets.QLineEdit('/Game/Maya/Animations')
        self.anim_ue_import_line.setMinimumHeight(row_height)
        anim_path_grid.addWidget(self.anim_ue_import_line, 0, 1, 1, 2)

        anim_path_grid.addWidget(_style_path_label('目标骨骼:'), 1, 0)
        self.anim_ue_skel_combo = QtWidgets.QComboBox()
        self.anim_ue_skel_combo.setMinimumHeight(row_height)
        self.anim_ue_skel_combo.addItem('点击刷新 UE 骨骼列表', '')
        anim_path_grid.addWidget(self.anim_ue_skel_combo, 1, 1)
        refresh_anim_skel_btn = _style_path_icon_button(
            app_style.standardIcon(QtWidgets.QStyle.SP_BrowserReload),
            '刷新 UE 骨骼列表', 'refresh_skeleton')
        refresh_anim_skel_btn.clicked.connect(self.refresh_anim_skeletons)
        anim_path_grid.addWidget(refresh_anim_skel_btn, 1, 2)
        anim_layout.addLayout(anim_path_grid)

        anim_ue_group = QtWidgets.QGroupBox('源动画文件')
        anim_ue_group_layout = QtWidgets.QVBoxLayout(anim_ue_group)
        anim_ue_group_layout.setContentsMargins(8, 8, 8, 8)
        self.anim_ue_file_list_widget = FbxFileListWidget()
        self.anim_ue_file_list_widget.setMinimumHeight(220)
        self.anim_ue_file_list_widget.filesChanged.connect(self.add_anim_ue_paths)
        anim_ue_group_layout.addWidget(self.anim_ue_file_list_widget)
        anim_layout.addWidget(anim_ue_group, 1)

        send_anim_btn = QtWidgets.QPushButton('Send To UE')
        send_anim_btn.setMinimumHeight(36)
        send_anim_btn.clicked.connect(self.send_anim_to_ue)
        anim_layout.addWidget(send_anim_btn)

        self.anim_progress_bar = QtWidgets.QProgressBar()
        self.anim_progress_bar.setRange(0, 100)
        self.anim_progress_bar.setValue(0)
        anim_layout.addWidget(self.anim_progress_bar)

        self.tabs.addTab(tab_anim, '动画导出')

    def open_dialog(self):
        result = cmds.fileDialog2(
            dialogStyle=1, fileMode=1, okCaption="选择文件",
            fileFilter="Maya/FBX Files (*.ma *.mb *.fbx)")
        if not result:
            return
        path = result[0]
        name = self.sender().objectName()
        if name == 'browse_source':
            self.yuan_line.setText(path)
        elif name == 'browse_target':
            self.target_line.setText(path)

    def open_dialog_files(self):
        result = cmds.fileDialog2(dialogStyle=1, fileMode=3, okCaption="选择文件夹")
        if not result:
            return
        path = result[0]
        if self.sender().objectName() == 'browse_export':
            self.export_line.setText(path)

    def HumanIK_Retarget(self):
        anim_files = self.anim_file_list()
        if not anim_files:
            QtWidgets.QMessageBox.warning(
                self, '没有动画文件',
                '请拖入 .fbx 动画文件或动画文件夹')
            return
        total_files = len(anim_files)
        steps_per_file = 6
        total_steps = total_files * steps_per_file
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        def _tick(step):
            self.progress_bar.setValue(int(step * 100 / total_steps))
            QtWidgets.QApplication.processEvents()

        for idx, file in enumerate(anim_files, 1):
            base = (idx - 1) * steps_per_file
            cmds.file(new=True, force=True)
            _tick(base + 1)
            cmds.file(self.yuan_line.text(), i=True, renameAll=True,
                      mergeNamespacesOnClash=True, namespace=":")
            _tick(base + 2)
            cmds.file(file, i=True, renameAll=True, type='fbx',
                      mergeNamespacesOnClash=True, namespace=":",
                      options="fbx", importFrameRate=True,
                      importTimeRange='override')
            _tick(base + 3)
            cmds.file(self.target_line.text(), i=True, renameAll=True,
                      mergeNamespacesOnClash=False, namespace="target")
            _tick(base + 4)

            mel.eval('hikCreateCharacterControlsDockableWindow()')

            allCharacter = cmds.optionMenuGrp("hikCharacterList", query=True,
                                              itemListLong=True)
            for i, item in enumerate(allCharacter, 1):
                optMenu = "hikCharacterList|OptionMenu"
                sourceChar = cmds.menuItem(item, query=True, label=True)
                if "target" in sourceChar:
                    cmds.optionMenu(optMenu, edit=True, select=i)
                    mel.eval('hikUpdateCurrentCharacterFromUI()')
                    mel.eval('hikUpdateContextualUI()')
                    mel.eval('hikUpdateCharacterMenu()')
                    mel.eval('hikUpdateCharacterControlsUICallback()')
                    break

            allSource = cmds.optionMenuGrp("hikSourceList", query=True,
                                           itemListLong=True)
            for i, item in enumerate(allSource, 1):
                optMenu = "hikSourceList|OptionMenu"
                sourceChar = cmds.menuItem(item, query=True, label=True)
                if sourceChar.strip() == "Character1":
                    cmds.optionMenu(optMenu, edit=True, select=i)
                    mel.eval('hikUpdateCurrentSourceFromUI()')
                    mel.eval('hikUpdateContextualUI()')
                    mel.eval('hikControlRigSelectionChangedCallback()')
                    break
            _tick(base + 5)

            cmds.select('target:root')
            export_dir = self.export_line.text()
            if not os.path.exists(export_dir):
                os.makedirs(export_dir)
            file_name = os.path.basename(file)
            export_path = os.path.join(export_dir, file_name).replace("\\", "/")
            mel.eval('FBXExportBakeComplexAnimation -v true;')
            mel.eval(f'FBXExport -f "{export_path}" -s')
            _tick(base + 6)

        self.progress_bar.setValue(100)
        QtWidgets.QApplication.processEvents()

    def _collect_fbx_from_paths(self, paths):
        fbx_files = []
        for path in paths:
            if not path:
                continue
            norm_path = os.path.normpath(path)
            if os.path.isfile(norm_path) and norm_path.lower().endswith('.fbx'):
                fbx_files.append(norm_path.replace('\\', '/'))
            elif os.path.isdir(norm_path):
                for root, _dirs, files in os.walk(norm_path):
                    for name in files:
                        if name.lower().endswith('.fbx'):
                            fbx_files.append(
                                os.path.join(root, name).replace('\\', '/'))
        return fbx_files

    def _refresh_fbx_list_widget(self, list_widget, fbx_files):
        list_widget.clear()
        for path in fbx_files:
            item = QtWidgets.QListWidgetItem(path)
            item.setToolTip(path)
            list_widget.addItem(item)

    def _fbx_paths_from_widget(self, list_widget):
        paths = []
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            path = (item.toolTip() or item.text()).replace('\\', '/')
            if path and os.path.isfile(path):
                paths.append(path)
        return paths

    def add_anim_paths(self, paths):
        current = self._fbx_paths_from_widget(self.anim_file_list_widget)
        added = self._collect_fbx_from_paths(paths)
        fbx_files = list(dict.fromkeys(current + added))
        fbx_files.sort()
        self._refresh_fbx_list_widget(self.anim_file_list_widget, fbx_files)

    def add_anim_ue_paths(self, paths):
        current = self._fbx_paths_from_widget(self.anim_ue_file_list_widget)
        added = self._collect_fbx_from_paths(paths)
        fbx_files = list(dict.fromkeys(current + added))
        fbx_files.sort()
        self._refresh_fbx_list_widget(self.anim_ue_file_list_widget, fbx_files)

    def anim_file_list(self):
        return self._fbx_paths_from_widget(self.anim_file_list_widget)

    def anim_ue_file_list(self):
        return self._fbx_paths_from_widget(self.anim_ue_file_list_widget)

    def _selected_skeleton_path(self, combo):
        data = combo.currentData()
        if data:
            return str(data).strip()
        return combo.currentText().strip()

    def _parse_ue_skeleton_result(self, result):
        raw = result.get('result', '')
        if isinstance(raw, (list, tuple)):
            values = raw
        else:
            raw = '' if raw is None else str(raw)
            try:
                values = json.loads(raw)
            except Exception:
                start = raw.find('[')
                end = raw.rfind(']')
                if start == -1 or end == -1 or end <= start:
                    return []
                try:
                    values = json.loads(raw[start:end + 1])
                except Exception:
                    return []
        return [p for p in values if isinstance(p, str) and p.startswith('/Game/')]

    def _fetch_ue_skeleton_paths(self):
        nodes = ue_remote.ue_discover_nodes(timeout=1.5)
        if not nodes:
            return []
        result = ue_remote.ue_exec_command(
            nodes[0], ue_scripts.build_ue_skeleton_list_expr(),
            exec_mode='EvaluateStatement', timeout=30.0)
        if not result.get('success'):
            return []
        return self._parse_ue_skeleton_result(result)

    def _fill_skeleton_combo(self, combo, paths):
        current = self._selected_skeleton_path(combo)
        combo.clear()
        if not paths:
            combo.addItem('未找到 UE Skeleton 资产', '')
            return
        for path in paths:
            combo.addItem(path, path)
        if current in paths:
            combo.setCurrentIndex(paths.index(current))

    def _refresh_skeleton_combo(self, combo, status_label, silent=False):
        if status_label:
            status_label.setText('正在读取 UE 骨骼列表...')
        QtWidgets.QApplication.processEvents()
        try:
            paths = self._fetch_ue_skeleton_paths()
        except Exception as e:
            if status_label:
                status_label.setText('')
            if not silent:
                QtWidgets.QMessageBox.critical(self, '错误', f'读取 UE 骨骼列表失败: {e}')
            return False
        self._fill_skeleton_combo(combo, paths)
        if not paths:
            if status_label:
                status_label.setText('')
            if not silent:
                QtWidgets.QMessageBox.warning(
                    self, '未找到骨骼',
                    'UE 中没有找到 Skeleton 资产，或未发现可用的 UE 实例。')
            return False
        if status_label:
            status_label.setText(f'已读取 {len(paths)} 个 UE 骨骼')
        return True

    def refresh_anim_skeletons(self, silent=False):
        return self._refresh_skeleton_combo(self.anim_ue_skel_combo, None, silent)

    # ---------- 动画模块: 发送当前场景动画到 UE ----------
    def _set_anim_progress(self, value):
        self.anim_progress_bar.setValue(value)
        QtWidgets.QApplication.processEvents()

    def send_anim_to_ue(self):
        self._set_anim_progress(0)

        anim_files = self.anim_ue_file_list()
        if not anim_files:
            QtWidgets.QMessageBox.warning(
                self, '没有动画文件',
                '请拖入 .fbx 动画文件或动画文件夹')
            return

        dest_path = self.anim_ue_import_line.text().strip()
        skeleton_path = self._selected_skeleton_path(self.anim_ue_skel_combo)
        if not dest_path or not dest_path.startswith('/Game/'):
            QtWidgets.QMessageBox.warning(self, '提示',
                                          'UE 动画导入路径必须以 /Game/ 开头')
            return
        self._set_anim_progress(15)
        if not skeleton_path.startswith('/Game/'):
            if not self.refresh_anim_skeletons():
                return
            skeleton_path = self._selected_skeleton_path(self.anim_ue_skel_combo)
        if not skeleton_path or not skeleton_path.startswith('/Game/'):
            QtWidgets.QMessageBox.warning(self, '提示',
                                          '请先从下拉框选择 UE 目标骨骼')
            return

        self._set_anim_progress(30)
        try:
            nodes = ue_remote.ue_discover_nodes(timeout=1.5)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, '错误', f'UDP 探测失败: {e}')
            self._set_anim_progress(0)
            return

        if not nodes:
            QtWidgets.QMessageBox.warning(
                self, '未找到 UE',
                '未发现已打开并启用 Remote Execution 的 UE 实例。\n'
                '请在 UE 中确认:\n'
                '1) 启用 Python Editor Script Plugin\n'
                '2) Project Settings → Plugins → Python → '
                'Enable Remote Execution 已勾选')
            self._set_anim_progress(0)
            return

        node_id = nodes[0]
        self._set_anim_progress(45)

        py_code = ue_scripts.build_ue_import_script(
            anim_files, dest_path, skeleton_path)

        def _tick(elapsed):
            progress = min(95, 45 + int(elapsed / 300.0 * 50))
            self._set_anim_progress(progress)

        try:
            result = ue_remote.ue_exec_command(node_id, py_code, timeout=300.0,
                                               progress_callback=_tick)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, '错误', f'发送到 UE 失败: {e}')
            self._set_anim_progress(0)
            return

        if result.get('success'):
            self._set_anim_progress(100)
        else:
            msg = result.get('result', '未知错误')
            self._set_anim_progress(0)
            QtWidgets.QMessageBox.critical(self, 'UE 端报错', str(msg))

    # ---------- 绑定模块: 发送骨骼+模型到 UE ----------
    def _rig_check_task_specs(self):
        return [
            ('selection', '选择蒙皮 Mesh 和骨骼根节点'),
            ('mesh', '检测 Mesh'),
            ('root', '检测唯一 root 骨骼'),
            ('duplicate_joint', '检测重复骨骼名'),
            ('generated_joint', '检测默认生成骨骼名'),
            ('mesh_bone_name', '检测 Mesh 与骨骼重名'),
            ('mesh_scale', '检测 Mesh Scale'),
            ('skin_cluster', '检测 SkinCluster'),
            ('weights', '检测蒙皮权重'),
            ('root_origin', '检测 Root 世界原点'),
            ('export_filter', '导出内容过滤 Mesh + Joint'),
        ]

    def _init_rig_task_list(self):
        self.rig_task_items = {}
        steps = [(label, None, None) for _task_id, label in self._rig_check_task_specs()]
        self.rig_task_widget.load(steps)
        for index, (task_id, _label) in enumerate(self._rig_check_task_specs()):
            self.rig_task_items[task_id] = index

    def _set_rig_task_status(self, task_id, status, detail=''):
        index = getattr(self, 'rig_task_items', {}).get(task_id)
        if index is None:
            return
        state_map = {
            'pending': 'pending',
            'running': 'running',
            'ok': 'done',
            'warning': 'warning',
            'error': 'failed',
        }
        base_label = dict(self._rig_check_task_specs()).get(task_id, task_id)
        text = f'{base_label} - {detail}' if detail else base_label
        self.rig_task_widget.set_item_state(index, state_map.get(status, 'pending'), text)
        total = max(1, len(self._rig_check_task_specs()))
        if status in ('ok', 'warning', 'error'):
            self.rig_task_widget.set_progress(float(index + 1) / float(total))
        elif status == 'running':
            self.rig_task_widget.set_progress(float(index) / float(total))

    def _reset_rig_task_statuses(self):
        self._init_rig_task_list()
        self.rig_task_widget.set_progress(0.0)

    def _apply_rig_validation_to_tasks(self, validation):
        errors = validation.get('errors') or []
        warnings = validation.get('warnings') or []
        text_errors = '\n'.join(errors)
        text_warnings = '\n'.join(warnings)

        task_checks = {
            'root': ('Root joint', 'Root'),
            'duplicate_joint': ('重复骨骼名', ''),
            'generated_joint': ('', '默认生成骨骼名'),
            'mesh_bone_name': ('Mesh 名称与骨骼重名', ''),
            'mesh_scale': ('', 'Scale 不是 1'),
            'skin_cluster': ('没有 SkinCluster', ''),
            'weights': ('权重', '权重'),
            'root_origin': ('', 'Root 不在世界原点'),
        }
        for task_id, (error_key, warning_key) in task_checks.items():
            if error_key and error_key in text_errors:
                self._set_rig_task_status(task_id, 'error')
            elif warning_key and warning_key in text_warnings:
                self._set_rig_task_status(task_id, 'warning')
            else:
                self._set_rig_task_status(task_id, 'ok')

        self._set_rig_task_status('export_filter', 'ok')

    def _set_rig_progress(self, value):
        self.rig_progress_bar.setValue(value)
        QtWidgets.QApplication.processEvents()

    def auto_check_rig_asset(self):
        self._reset_rig_task_statuses()
        self._set_rig_progress(0)
        self._set_rig_task_status('selection', 'running')

        sel = cmds.ls(sl=True, long=True) or []
        if not sel:
            self._set_rig_task_status('selection', 'error', '未选择')
            self._set_rig_progress(0)
            return

        mesh_transforms, root_joints, export_nodes = (
            asset_validation.collect_rig_export_nodes(sel))
        self._set_rig_task_status('selection', 'ok')
        self._set_rig_task_status('mesh', 'running')
        if not mesh_transforms:
            self._set_rig_task_status('mesh', 'error', '未找到 Mesh')
            self._set_rig_progress(0)
            return
        self._set_rig_task_status('mesh', 'ok', f'{len(mesh_transforms)} 个')

        self._set_rig_task_status('root', 'running')
        if not root_joints:
            self._set_rig_task_status('root', 'error', '未找到 Root')
            self._set_rig_progress(0)
            return
        self._set_rig_task_status('root', 'ok', f'{len(root_joints)} 个')

        validation = asset_validation.validate_rig_asset(
            mesh_transforms, root_joints, export_nodes)
        self._apply_rig_validation_to_tasks(validation)
        if validation['errors']:
            self._set_rig_progress(0)
        elif validation['warnings']:
            self._set_rig_progress(100)
        else:
            self._set_rig_progress(100)

    def send_rig_to_ue(self):
        self._set_rig_progress(0)

        # 校验当前选择
        sel = cmds.ls(sl=True, long=True) or []
        if not sel:
            QtWidgets.QMessageBox.warning(self, '提示',
                                          '请先在 Maya 中选中蒙皮 Mesh 和骨骼根节点')
            return
        mesh_transforms, root_joints, export_nodes = (
            asset_validation.collect_rig_export_nodes(sel))
        if not mesh_transforms:
            QtWidgets.QMessageBox.warning(self, '提示',
                                          '当前选择中没有找到 Mesh，请选择蒙皮 Mesh 和骨骼根节点')
            return
        if not root_joints:
            QtWidgets.QMessageBox.warning(self, '提示',
                                          '当前选择中没有找到 Root joint，请选择骨骼根节点')
            return

        # 资产名 = Maya 场景文件名 (不含扩展名), 未保存场景时弹窗提示
        scene_path = cmds.file(q=True, sn=True) or ''
        if not scene_path:
            QtWidgets.QMessageBox.warning(
                self, '提示', '当前场景尚未保存, 无法确定资产名。请先保存场景。')
            return
        asset_name = os.path.splitext(os.path.basename(scene_path))[0]
        # 资产名做基本清洗
        safe_name = ''.join(c if (c.isalnum() or c in '_-') else '_'
                            for c in asset_name)
        if not safe_name:
            safe_name = 'MayaAsset'

        dest_path = self.rig_ue_import_line.text().strip()
        if not dest_path or not dest_path.startswith('/Game/'):
            QtWidgets.QMessageBox.warning(self, '提示',
                                          'UE 绑定导入路径必须以 /Game/ 开头')
            return

        version = _time.strftime('v%Y%m%d_%H%M%S')
        publish_dir = os.path.join(tempfile.gettempdir(), 'MayaToUE_publish',
                                   'Character', safe_name, version)
        os.makedirs(publish_dir, exist_ok=True)
        fbx_path = os.path.join(publish_dir, safe_name + '.fbx').replace('\\', '/')

        # 确保 fbx 插件已加载
        try:
            maya_fbx.ensure_fbx_plugin()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, '错误',
                                          f'加载 fbxmaya 插件失败: {e}')
            return

        self._set_rig_progress(15)
        try:
            maya_fbx.export_rig_fbx(fbx_path, export_nodes)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, '导出失败',
                                          f'FBX 导出失败: {e}')
            self._set_rig_progress(0)
            return

        if not os.path.isfile(fbx_path):
            QtWidgets.QMessageBox.critical(self, '导出失败',
                                          f'FBX 文件未生成: {fbx_path}')
            self._set_rig_progress(0)
            return

        self._set_rig_progress(45)
        try:
            nodes = ue_remote.ue_discover_nodes(timeout=1.5)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, '错误', f'UDP 探测失败: {e}')
            self._set_rig_progress(0)
            return

        if not nodes:
            QtWidgets.QMessageBox.warning(
                self, '未找到 UE',
                '未发现已打开并启用 Remote Execution 的 UE 实例。\n'
                '请在 UE 中确认:\n'
                '1) 启用 Python Editor Script Plugin\n'
                '2) Project Settings → Plugins → Python → '
                'Enable Remote Execution 已勾选')
            self._set_rig_progress(0)
            return

        node_id = nodes[0]
        self._set_rig_progress(60)

        py_code = ue_scripts.build_ue_skeletal_mesh_import_script(
            fbx_path, dest_path, safe_name)

        def _tick(elapsed):
            progress = min(95, 60 + int(elapsed / 300.0 * 35))
            self._set_rig_progress(progress)

        try:
            result = ue_remote.ue_exec_command(node_id, py_code, timeout=300.0,
                                               progress_callback=_tick)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, '错误', f'发送到 UE 失败: {e}')
            self._set_rig_progress(0)
            return

        if result.get('success'):
            self._set_rig_progress(100)
        else:
            msg = result.get('result', '未知错误')
            self._set_rig_progress(0)
            QtWidgets.QMessageBox.critical(self, 'UE 端报错', str(msg))


def show_ui():
    global retarget_ui
    existing = globals().get('retarget_ui')
    if existing is not None:
        try:
            existing.close()
            existing.deleteLater()
            QtWidgets.QApplication.processEvents()
        except RuntimeError:
            pass
    retarget_ui = RetargetUI()
    retarget_ui.show()
    retarget_ui.refresh_anim_skeletons(silent=True)
