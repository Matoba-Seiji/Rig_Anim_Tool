# -*- coding: utf-8 -*-
"""Transpose bone mapping UI: A-pose block picker with neck/fingers sub-views."""

import os
import json
import time

from maya import cmds
from PySide2 import QtCore, QtGui, QtWidgets

from rig_anim_tool.core.maya_ui import get_maya_main_window


# ============================================================
# Slot definitions (HumanIK-style, A-pose layout)
# ============================================================
BTN_W = 100
BTN_H = 40
CANVAS_W = 440
CANVAS_H = 700
CX = 220

# (id, label, cx, cy, required, side, group, in_main)
# in_main=False means only shown in sub-view
_SLOTS_DEF = [
    # Center column (spine numbered from hips upward)
    ('head',   'head',   220,  30, True,  'M', 'spine', True),
    ('neck',   'neck >', 220,  80, False, 'M', 'spine', True),
    ('spine4', 'spine4', 220, 130, True,  'M', 'spine', True),
    ('spine3', 'spine3', 220, 180, True,  'M', 'spine', True),
    ('spine2', 'spine2', 220, 230, True,  'M', 'spine', True),
    ('spine1', 'spine1', 220, 280, True,  'M', 'spine', True),
    ('hips',   'hips',   220, 330, True,  'M', 'spine', True),

    # Arms: clavicle near spine, shoulder/elbow/wrist/hand shifted outward half a button
    ('L_clavicle', 'clavicle', 110, 130, True, 'L', 'arm', True),
    ('L_shoulder', 'shoulder',  60, 180, True, 'L', 'arm', True),
    ('L_elbow',    'elbow',     60, 230, True, 'L', 'arm', True),
    ('L_wrist',    'wrist',     60, 280, True, 'L', 'arm', True),
    ('L_hand',     'hand >',    60, 330, False, 'L', 'arm', True),
    ('R_clavicle', 'clavicle', 330, 130, True, 'R', 'arm', True),
    ('R_shoulder', 'shoulder', 380, 180, True, 'R', 'arm', True),
    ('R_elbow',    'elbow',    380, 230, True, 'R', 'arm', True),
    ('R_wrist',    'wrist',    380, 280, True, 'R', 'arm', True),
    ('R_hand',     'hand >',   380, 330, False, 'R', 'arm', True),

    # Legs
    ('L_upleg', 'upleg', 110, 380, True,  'L', 'leg', True),
    ('R_upleg', 'upleg', 330, 380, True,  'R', 'leg', True),
    ('L_leg',   'leg',   110, 430, True,  'L', 'leg', True),
    ('R_leg',   'leg',   330, 430, True,  'R', 'leg', True),
    ('L_foot',  'foot',  110, 480, True,  'L', 'leg', True),
    ('R_foot',  'foot',  330, 480, True,  'R', 'leg', True),
    ('L_ball',  'ball',  110, 530, True,  'L', 'leg', True),
    ('R_ball',  'ball',  330, 530, True,  'R', 'leg', True),

    # Neck sub-slots (only shown in neck sub-view)
    ('neck1', 'neck1', 0, 0, False, 'M', 'neck', False),
    ('neck2', 'neck2', 0, 0, False, 'M', 'neck', False),
    ('neck3', 'neck3', 0, 0, False, 'M', 'neck', False),
    ('neck4', 'neck4', 0, 0, False, 'M', 'neck', False),
    ('neck5', 'neck5', 0, 0, False, 'M', 'neck', False),
]

# Finger sub-slots: 5 fingers x 3 joints x 2 sides
_FINGER_NAMES = ['thumb', 'index', 'middle', 'ring', 'pinky']
for _side in ('L', 'R'):
    for _fn in _FINGER_NAMES:
        for _i in (1, 2, 3):
            _SLOTS_DEF.append(
                ('%s_%s%d' % (_side, _fn, _i),
                 '%s%d' % (_fn, _i),
                 0, 0, False, _side, 'finger', False))


def _build_slots():
    slots = []
    for sid, label, cx, cy, req, side, grp, in_main in _SLOTS_DEF:
        slots.append({'id': sid, 'label': label, 'cx': cx, 'cy': cy,
                      'required': req, 'side': side, 'group': grp,
                      'in_main': in_main})
    return slots


SLOTS = _build_slots()
SLOT_IDS = {s['id'] for s in SLOTS}
SLOT_BY_ID = {s['id']: s for s in SLOTS}
MAIN_SLOTS = [s for s in SLOTS if s['in_main']]
NECK_SUB_SLOTS = [s for s in SLOTS if s['group'] == 'neck']


def finger_slots(side):
    return [s for s in SLOTS if s['group'] == 'finger' and s['side'] == side]


# ============================================================
# Stylesheet
# ============================================================
_TRANSPOSE_QSS = """
QWidget#TransposeRoot {
    background: #2B2B2B;
}
QLabel#TitleLabel {
    font-family: 'Microsoft YaHei';
    font-size: 15px;
    font-weight: 600;
    color: #E6E6E6;
    padding: 2px 0px;
}
QPushButton#ToolBtn {
    font-family: 'Microsoft YaHei';
    font-size: 14px;
    color: #E6E6E6;
    background: #3A3A3A;
    border: 1px solid #555;
    border-radius: 3px;
    padding: 8px 16px;
}
QPushButton#ToolBtn:hover { border: 1px solid #64A6FF; background: #444; }
QPushButton#ToolBtn:pressed { background: #2A2A2A; }
QPushButton#AccentBtn {
    font-family: 'Microsoft YaHei';
    font-size: 12px;
    color: #FFFFFF;
    background: #2F6FCC;
    border: 1px solid #2F6FCC;
    border-radius: 3px;
    padding: 5px 10px;
}
QPushButton#AccentBtn:hover { background: #3F8CFF; }
QPushButton#AccentBtn:disabled { color: #808080; background: #353535; border: 1px solid #444; }
QLabel#DetailLabel {
    font-family: 'Microsoft YaHei';
    font-size: 12px;
    color: #BDBDBD;
}
QLabel#StatusLabel {
    font-family: 'Microsoft YaHei';
    font-size: 12px;
    padding: 4px 8px;
}
QScrollArea#PickerScroll {
    background: #1F1F22;
    border: 1px solid #3a3a3a;
    border-radius: 4px;
}
QWidget#NeckView, QWidget#FingersView {
    background: #1F1F22;
    border: 1px solid #3a3a3a;
    border-radius: 4px;
}
QMenu {
    background-color: #3A3A3A;
    color: #D0D0D0;
    border: 1px solid #555;
    padding: 4px 0;
}
QMenu::item {
    padding: 6px 24px 6px 14px;
    font-family: 'Microsoft YaHei';
    font-size: 12px;
}
QMenu::item:selected { background-color: #2F6FCC; color: white; }
QMenu::item:disabled { color: #666; }
"""


# ============================================================
# Bone slot button (QPushButton + setStyleSheet)
# ============================================================
class BoneButton(QtWidgets.QPushButton):

    def __init__(self, slot, parent=None, use_pos=True):
        super().__init__(parent)
        self.slot = slot
        self.slot_id = slot['id']
        self.setFixedSize(BTN_W, BTN_H)
        if use_pos and slot.get('cx', 0) and slot.get('cy', 0):
            self.move(slot['cx'] - BTN_W // 2, slot['cy'] - BTN_H // 2)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setCheckable(True)
        self._joint = ''
        self._valid = True
        self._update_text()
        self._apply_style()

    def set_joint(self, name, valid=True):
        self._joint = name or ''
        self._valid = valid
        self._update_text()
        self._apply_style()

    def clear(self):
        self._joint = ''
        self._valid = True
        self._update_text()
        self._apply_style()

    def _update_text(self):
        if self._joint:
            short = self._joint.split('|')[-1].split(':')[-1]
            if len(short) > 8:
                short = short[:8] + '..'
            self.setText(short)
            self.setToolTip('%s -> %s' % (self.slot['label'], self._joint))
        else:
            self.setText(self.slot['label'])
            tip = self.slot['label']
            if self.slot['required']:
                tip += ' (required)'
            self.setToolTip(tip)

    def _apply_style(self):
        if not self._joint:
            bg = '#3A3A3A'
            txt = '#E0E0E0'
            border = '1px solid #E08A3E' if self.slot['required'] else '1px solid #000000'
        elif not self._valid:
            bg = '#A03232'
            txt = '#FFFFFF'
            border = '1px solid #FF5050'
        else:
            bg = '#2F6FCC'
            txt = '#FFFFFF'
            border = '1px solid #000000'
        self.setStyleSheet("""
            QPushButton {{
                background-color: {bg};
                color: {txt};
                border: {border};
                border-radius: 3px;
                font-family: 'Consolas';
                font-size: 14px;
                padding: 2px;
            }}
            QPushButton:hover {{ border: 2px solid #CCCCCC; }}
            QPushButton:checked {{ border: 3px solid #FFFFFF; }}
        """.format(bg=bg, txt=txt, border=border))


# ============================================================
# A-pose picker canvas
# ============================================================
class BodyPicker(QtWidgets.QWidget):

    def __init__(self, parent_ui):
        super().__init__()
        self.parent_ui = parent_ui
        self.setFixedSize(CANVAS_W, CANVAS_H)
        self.buttons = {}
        self._build()

    def _build(self):
        for slot in MAIN_SLOTS:
            btn = BoneButton(slot, self, use_pos=True)
            sid = slot['id']
            if sid == 'neck':
                btn.setCheckable(False)
                btn.clicked.connect(lambda *args: self.parent_ui._show_neck_view())
            elif sid in ('L_hand', 'R_hand'):
                btn.setCheckable(False)
                side = slot['side']
                btn.clicked.connect(
                    lambda *args, s=side: self.parent_ui._show_fingers_view(s))
            else:
                btn.clicked.connect(
                    lambda *args, b=btn: self.parent_ui.select_slot(b.slot_id))
                btn.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
                btn.customContextMenuRequested.connect(
                    lambda pos, b=btn: self.parent_ui.show_slot_menu(b, pos))
            self.buttons[sid] = btn


# ============================================================
# Neck sub-view: vertical stack of neck1..neck5 (bottom-up)
# ============================================================
class NeckSlotsView(QtWidgets.QWidget):

    back_requested = QtCore.Signal()

    def __init__(self, parent_ui):
        super().__init__()
        self.setObjectName('NeckView')
        self.parent_ui = parent_ui
        self.buttons = {}
        self._build()

    def _build(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        header = QtWidgets.QHBoxLayout()
        btn_back = QtWidgets.QPushButton('< 返回')
        btn_back.setObjectName('ToolBtn')
        btn_back.clicked.connect(self.back_requested.emit)
        header.addWidget(btn_back)
        header.addStretch()
        title = QtWidgets.QLabel('颈椎槽位')
        title.setObjectName('TitleLabel')
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        # Display top-down as neck5..neck1 (neck1 at bottom)
        for slot in reversed(NECK_SUB_SLOTS):
            btn = BoneButton(slot, self, use_pos=False)
            btn.clicked.connect(
                lambda *args, b=btn: self.parent_ui.select_slot(b.slot_id))
            btn.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
            btn.customContextMenuRequested.connect(
                lambda pos, b=btn: self.parent_ui.show_slot_menu(b, pos))
            self.buttons[slot['id']] = btn
            layout.addWidget(btn, alignment=QtCore.Qt.AlignCenter)

        layout.addStretch()

    def refresh(self):
        for sid, btn in self.buttons.items():
            joint = self.parent_ui.mapping.get(sid, '')
            if joint:
                valid = cmds.objExists(joint)
                btn.set_joint(joint, valid=valid)
            else:
                btn.clear()


# ============================================================
# Fingers sub-view: 5 columns x 3 rows per side
# ============================================================
class FingersView(QtWidgets.QWidget):

    back_requested = QtCore.Signal()

    def __init__(self, parent_ui, side):
        super().__init__()
        self.setObjectName('FingersView')
        self.parent_ui = parent_ui
        self.side = side
        self.buttons = {}
        self._build()

    def _build(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        header = QtWidgets.QHBoxLayout()
        btn_back = QtWidgets.QPushButton('< 返回')
        btn_back.setObjectName('ToolBtn')
        btn_back.clicked.connect(self.back_requested.emit)
        header.addWidget(btn_back)
        header.addStretch()
        title = QtWidgets.QLabel('%s 手指' % self.side)
        title.setObjectName('TitleLabel')
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        # Grid: 5 columns (thumb/index/middle/ring/pinky) x 3 rows (1/2/3)
        grid = QtWidgets.QGridLayout()
        grid.setSpacing(6)
        slots = finger_slots(self.side)
        # slots are ordered by finger name then joint index; rearrange into grid
        for col, fname in enumerate(_FINGER_NAMES):
            for row in range(3):
                sid = '%s_%s%d' % (self.side, fname, row + 1)
                slot = SLOT_BY_ID.get(sid)
                if not slot:
                    continue
                btn = BoneButton(slot, self, use_pos=False)
                btn.clicked.connect(
                    lambda *args, b=btn: self.parent_ui.select_slot(b.slot_id))
                btn.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
                btn.customContextMenuRequested.connect(
                    lambda pos, b=btn: self.parent_ui.show_slot_menu(b, pos))
                self.buttons[sid] = btn
                grid.addWidget(btn, row, col)

        layout.addLayout(grid)
        layout.addStretch()

    def refresh(self):
        for sid, btn in self.buttons.items():
            joint = self.parent_ui.mapping.get(sid, '')
            if joint:
                valid = cmds.objExists(joint)
                btn.set_joint(joint, valid=valid)
            else:
                btn.clear()


# ============================================================
# Transpose main panel
# ============================================================
class TransposeUI(QtWidgets.QWidget):

    def __init__(self, parent=None):
        if parent is None:
            parent = get_maya_main_window()
        super().__init__(parent)
        self.setObjectName('TransposeRoot')
        self.setWindowTitle('Transpose')
        self.setStyleSheet(_TRANSPOSE_QSS)

        self.mapping = {}
        self.current_slot = None

        self._build_ui()
        self._sync_buttons()
        self._refresh_status()

    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        title = QtWidgets.QLabel('转置骨骼映射')
        title.setObjectName('TitleLabel')
        root.addWidget(title)

        toolbar = QtWidgets.QHBoxLayout()
        toolbar.setSpacing(6)
        self.btn_import = self._tool_btn('导入', self.import_preset)
        self.btn_export = self._tool_btn('导出', self.export_preset)
        self.btn_clear = self._tool_btn('清空', self.clear_all)
        toolbar.addWidget(self.btn_import)
        toolbar.addWidget(self.btn_export)
        toolbar.addStretch()
        toolbar.addWidget(self.btn_clear)
        root.addLayout(toolbar)

        # Stacked widget: 0=main, 1=neck, 2=fingers L, 3=fingers R
        self.stack = QtWidgets.QStackedWidget()
        self.stack.setObjectName('PickerStack')

        # Page 0: main picker
        page_main = QtWidgets.QWidget()
        main_layout = QtWidgets.QVBoxLayout(page_main)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setAlignment(QtCore.Qt.AlignCenter)
        self.picker = BodyPicker(self)
        main_layout.addWidget(self.picker)
        self.stack.addWidget(page_main)

        # Page 1: neck sub-view
        self.neck_view = NeckSlotsView(self)
        self.neck_view.back_requested.connect(self._show_main_picker)
        self.stack.addWidget(self.neck_view)

        # Page 2: fingers L
        self.fingers_view_L = FingersView(self, 'L')
        self.fingers_view_L.back_requested.connect(self._show_main_picker)
        self.stack.addWidget(self.fingers_view_L)

        # Page 3: fingers R
        self.fingers_view_R = FingersView(self, 'R')
        self.fingers_view_R.back_requested.connect(self._show_main_picker)
        self.stack.addWidget(self.fingers_view_R)

        root.addWidget(self.stack, 1)

        # Detail + action bar
        detail = QtWidgets.QHBoxLayout()
        detail.setSpacing(8)
        self.detail_label = QtWidgets.QLabel('请选择一个骨骼槽位')
        self.detail_label.setObjectName('DetailLabel')
        detail.addWidget(self.detail_label)
        detail.addStretch()
        root.addLayout(detail)

        self.status_label = QtWidgets.QLabel()
        self.status_label.setObjectName('StatusLabel')
        root.addWidget(self.status_label)

    def _tool_btn(self, text, slot):
        btn = QtWidgets.QPushButton(text)
        btn.setObjectName('ToolBtn')
        btn.clicked.connect(slot)
        return btn

    # ---------- View switching ----------
    def _show_neck_view(self):
        self.neck_view.refresh()
        self.stack.setCurrentIndex(1)

    def _show_fingers_view(self, side):
        if side == 'L':
            self.fingers_view_L.refresh()
            self.stack.setCurrentIndex(2)
        else:
            self.fingers_view_R.refresh()
            self.stack.setCurrentIndex(3)

    def _show_main_picker(self):
        self.stack.setCurrentIndex(0)

    # ---------- Slot selection ----------
    def select_slot(self, slot_id):
        self.current_slot = slot_id
        for sid, btn in self.picker.buttons.items():
            btn.setChecked(sid == slot_id)
        for sid, btn in self.neck_view.buttons.items():
            btn.setChecked(sid == slot_id)
        for sid, btn in self.fingers_view_L.buttons.items():
            btn.setChecked(sid == slot_id)
        for sid, btn in self.fingers_view_R.buttons.items():
            btn.setChecked(sid == slot_id)
        slot = SLOT_BY_ID[slot_id]
        joint = self.mapping.get(slot_id, '')
        side_txt = {'L': 'L', 'R': 'R', 'M': 'M'}.get(slot['side'], '')
        if joint:
            short = joint.split('|')[-1].split(':')[-1]
            self.detail_label.setText(
                '当前: %s %s  骨骼: %s' % (side_txt, slot['label'], short))
            if cmds.objExists(joint):
                cmds.select(joint, replace=True)
        else:
            self.detail_label.setText(
                '当前: %s %s  骨骼: 未指定' % (side_txt, slot['label']))

    # ---------- Write mapping ----------
    def assign_current(self):
        if not self.current_slot:
            return
        sel = cmds.ls(selection=True, long=True) or []
        if not sel:
            QtWidgets.QMessageBox.warning(self, '提示', '请先在 Maya 中选择一个骨骼')
            return
        node = sel[0]
        if cmds.nodeType(node) != 'joint':
            QtWidgets.QMessageBox.warning(
                self, '提示', '所选节点 %s 不是 joint' % node.split('|')[-1])
            return
        self.mapping[self.current_slot] = node
        self._update_button(self.current_slot, node)
        self._auto_mirror(self.current_slot, node)
        self.select_slot(self.current_slot)
        self._refresh_status()

    def _mirror_joint_name(self, name):
        """Find mirrored joint by negating X world position."""
        try:
            pos = cmds.xform(name, q=True, ws=True, t=True)
        except Exception:
            return None
        mirror_pos = [-pos[0], pos[1], pos[2]]
        all_joints = cmds.ls(type='joint', long=True) or []
        best = None
        best_dist = float('inf')
        for j in all_joints:
            if j == name:
                continue
            try:
                jpos = cmds.xform(j, q=True, ws=True, t=True)
            except Exception:
                continue
            dist = ((jpos[0] - mirror_pos[0]) ** 2 +
                    (jpos[1] - mirror_pos[1]) ** 2 +
                    (jpos[2] - mirror_pos[2]) ** 2) ** 0.5
            if dist < best_dist:
                best_dist = dist
                best = j
        if best and best_dist < 1.0:
            return best
        return None

    def _auto_mirror(self, slot_id, joint):
        """Auto-map mirrored joint to the opposite side if found."""
        slot = SLOT_BY_ID.get(slot_id)
        if not slot or slot['side'] == 'M':
            return
        if slot_id.startswith('L_'):
            other_id = 'R_' + slot_id[2:]
        elif slot_id.startswith('R_'):
            other_id = 'L_' + slot_id[2:]
        else:
            return
        if other_id not in SLOT_BY_ID:
            return
        if other_id in self.mapping:
            return
        mirror_name = self._mirror_joint_name(joint)
        if mirror_name and cmds.objExists(mirror_name):
            self.mapping[other_id] = mirror_name
            self._update_button(other_id, mirror_name)

    def clear_slot(self, slot_id):
        if slot_id not in self.mapping:
            return
        del self.mapping[slot_id]
        self._update_button(slot_id, '')
        if self.current_slot == slot_id:
            self.select_slot(slot_id)
        self._refresh_status()

    def clear_current(self):
        if self.current_slot:
            self.clear_slot(self.current_slot)

    def clear_all(self):
        if not self.mapping:
            return
        r = QtWidgets.QMessageBox.question(
            self, '确认', '清空所有骨骼映射？',
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if r != QtWidgets.QMessageBox.Yes:
            return
        self.mapping.clear()
        for btn in self.picker.buttons.values():
            btn.clear()
        for btn in self.neck_view.buttons.values():
            btn.clear()
        for btn in self.fingers_view_L.buttons.values():
            btn.clear()
        for btn in self.fingers_view_R.buttons.values():
            btn.clear()
        if self.current_slot:
            self.select_slot(self.current_slot)
        self._refresh_status()

    def _update_button(self, slot_id, joint):
        btn = (self.picker.buttons.get(slot_id)
               or self.neck_view.buttons.get(slot_id)
               or self.fingers_view_L.buttons.get(slot_id)
               or self.fingers_view_R.buttons.get(slot_id))
        if not btn:
            return
        if joint:
            valid = cmds.objExists(joint)
            btn.set_joint(joint, valid=valid)
        else:
            btn.clear()

    # ---------- Context menu ----------
    def show_slot_menu(self, btn, pos):
        menu = QtWidgets.QMenu(self)
        a_map = menu.addAction('映射')
        a_unmap = menu.addAction('取消映射')
        a_unmap.setEnabled(bool(btn._joint))
        action = menu.exec_(btn.mapToGlobal(pos))
        if action == a_map:
            self.select_slot(btn.slot_id)
            self.assign_current()
        elif action == a_unmap:
            self.clear_slot(btn.slot_id)

    def _sync_buttons(self):
        for sid, btn in self.picker.buttons.items():
            joint = self.mapping.get(sid, '')
            if joint:
                valid = cmds.objExists(joint)
                btn.set_joint(joint, valid=valid)
            else:
                btn.clear()
        self.neck_view.refresh()
        self.fingers_view_L.refresh()
        self.fingers_view_R.refresh()

    def _refresh_status(self):
        required = [s for s in SLOTS if s['required']]
        req_filled = sum(1 for s in required if self.mapping.get(s['id']))
        req_missing = len(required) - req_filled
        invalid = sum(1 for sid, j in self.mapping.items()
                      if j and not cmds.objExists(j))
        if req_missing == 0 and invalid == 0:
            self.status_label.setStyleSheet('color: #4CAF50;')
            self.status_label.setText(
                '映射完成: 必填 %d/%d  已映射 %d/%d' % (
                    req_filled, len(required), len(self.mapping), len(SLOTS)))
        else:
            self.status_label.setStyleSheet('color: #E0A83E;')
            self.status_label.setText(
                '必填: %d/%d   缺失: %d   无效: %d   总计: %d/%d' % (
                    req_filled, len(required), req_missing, invalid,
                    len(self.mapping), len(SLOTS)))

    # ---------- Preset IO ----------
    def export_preset(self):
        default_dir = os.path.join(
            os.environ.get('USERPROFILE', os.path.expanduser('~')), 'Desktop')
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, '导出骨骼映射预设', default_dir, 'JSON (*.json)')
        if not path:
            return
        if not path.lower().endswith('.json'):
            path += '.json'
        data = {
            'version': 1,
            'created': time.strftime('%Y-%m-%d %H:%M:%S'),
            'mapping': self.mapping,
        }
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, '错误', '写入预设失败: %s' % e)
            return
        self.status_label.setStyleSheet('color: #4CAF50;')
        self.status_label.setText('已导出到: %s' % path)

    def import_preset(self):
        default_dir = os.path.join(
            os.environ.get('USERPROFILE', os.path.expanduser('~')), 'Desktop')
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, '导入骨骼映射预设', default_dir, 'JSON (*.json)')
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, '错误', '读取预设失败: %s' % e)
            return
        mapping = data.get('mapping', {}) if isinstance(data, dict) else {}
        if not isinstance(mapping, dict):
            QtWidgets.QMessageBox.warning(self, '提示', '预设文件格式不正确')
            return
        self.mapping = {k: v for k, v in mapping.items() if k in SLOT_IDS}
        self._sync_buttons()
        if self.current_slot:
            self.select_slot(self.current_slot)
        self._refresh_status()

    # ---------- Public API ----------
    def get_mapping(self):
        return dict(self.mapping)

    def get_slot_def(self, slot_id):
        return SLOT_BY_ID.get(slot_id)
