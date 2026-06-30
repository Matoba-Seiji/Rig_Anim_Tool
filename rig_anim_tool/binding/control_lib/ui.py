import os

from maya import cmds, mel
from PySide2 import QtWidgets, QtCore, QtGui

from rig_anim_tool.core.maya_ui import get_maya_main_window
from rig_anim_tool.core.undo import make_undo

PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
SHAPES_DIR = os.path.join(PACKAGE_DIR, 'shapes')
COLOR_LIST_HEIGHT = 130
ICON_SIZE = 56
ICON_CELL = ICON_SIZE + 8
ICON_LIST_MIN_HEIGHT = 520

BackGroundColor = [
    (0.47, 0.47, 0.47), (0, 0, 0), (0.5, 0.5, 0.5), (0.75, 0.75, 0.75),
    (0.8, 0, 0.2), (0, 0, 0.4), (0, 0, 1), (0, 0.3, 0),
    (0.2, 0, 0.3), (0.8, 0, 0.8), (0.6, 0.3, 0.2), (0.25, 0.13, 0.13),
    (0.7, 0.2, 0), (1, 0, 0), (0, 1, 0), (0, 0.3, 0.6),
    (1, 1, 1), (1, 1, 0), (0, 1, 1), (0, 1, 0.8),
    (1, 0.7, 0.7), (0.9, 0.7, 0.5), (1, 1, 0.4), (0, 0.7, 0.4),
    (0.6, 0.4, 0.2), (0.63, 0.63, 0.17), (0.4, 0.6, 0.2), (0.2, 0.63, 0.35),
    (0.18, 0.63, 0.63), (0.18, 0.4, 0.63), (0.43, 0.18, 0.63), (0.63, 0.18, 0.4),
]

_PNG_ICON_CACHE = {}


LIB_DIR = SHAPES_DIR


def _icon_from_png(png_path):
    png_path = os.path.normpath(png_path)
    if png_path in _PNG_ICON_CACHE:
        return _PNG_ICON_CACHE[png_path]

    icon = QtGui.QIcon()
    try:
        with open(png_path, 'rb') as handle:
            data = handle.read()
        image = QtGui.QImage()
        if image.loadFromData(data, 'PNG'):
            pixmap = QtGui.QPixmap.fromImage(
                image.scaled(
                    ICON_SIZE, ICON_SIZE,
                    QtCore.Qt.KeepAspectRatio,
                    QtCore.Qt.SmoothTransformation,
                ))
            if not pixmap.isNull():
                icon = QtGui.QIcon(pixmap)
    except OSError:
        pass

    if icon.isNull():
        pixmap = QtGui.QPixmap(png_path)
        if not pixmap.isNull():
            icon = QtGui.QIcon(pixmap.scaled(
                ICON_SIZE, ICON_SIZE,
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation,
            ))

    _PNG_ICON_CACHE[png_path] = icon
    return icon


class Control_libUI(QtWidgets.QWidget):

    def __init__(self, parent=None):
        if parent is None:
            parent = get_maya_main_window()
        super().__init__(parent)

        self.setWindowTitle('控制器库')

        layout = QtWidgets.QVBoxLayout(self)

        self.listWidget = QtWidgets.QListWidget()
        self.listWidget.setViewMode(QtWidgets.QListWidget.IconMode)
        self.listWidget.setResizeMode(QtWidgets.QListWidget.Adjust)
        self.listWidget.setMovement(QtWidgets.QListWidget.Static)
        self.listWidget.setIconSize(QtCore.QSize(ICON_SIZE, ICON_SIZE))
        self.listWidget.setGridSize(QtCore.QSize(ICON_CELL, ICON_CELL))
        self.listWidget.setUniformItemSizes(True)
        self.listWidget.setMinimumHeight(ICON_LIST_MIN_HEIGHT)
        self.listWidget.setSpacing(6)
        layout.addWidget(self.listWidget, 1)

        self._build_shape_buttons()
        self.listWidget.itemClicked.connect(self.logo_connect)

        self.listWidget_color = QtWidgets.QListWidget()
        self.listWidget_color.setViewMode(QtWidgets.QListWidget.IconMode)
        self.listWidget_color.setMovement(QtWidgets.QListWidget.Static)
        self.listWidget_color.setResizeMode(QtWidgets.QListWidget.Adjust)
        self.listWidget_color.setFixedHeight(COLOR_LIST_HEIGHT)
        layout.addWidget(self.listWidget_color)

        self._build_color_swatches()

        replace_button = QtWidgets.QPushButton('替换控制器')
        layout.addWidget(replace_button)
        replace_button.clicked.connect(self.replace_connect)

        mirror_button = QtWidgets.QPushButton('镜像控制器')
        layout.addWidget(mirror_button)
        mirror_button.clicked.connect(self.mirror_connect)

        radio_widget = QtWidgets.QWidget()
        radio_layout = QtWidgets.QHBoxLayout(radio_widget)
        self.radio_x = QtWidgets.QRadioButton('x')
        self.radio_y = QtWidgets.QRadioButton('y')
        self.radio_z = QtWidgets.QRadioButton('z')
        radio_layout.addWidget(self.radio_x)
        radio_layout.addWidget(self.radio_y)
        radio_layout.addWidget(self.radio_z)
        layout.addWidget(radio_widget)

        zero_button = QtWidgets.QPushButton('控制器归位')
        layout.addWidget(zero_button)
        zero_button.clicked.connect(self.zero_connect)

    def _build_shape_buttons(self):
        _PNG_ICON_CACHE.clear()
        self.listWidget.clear()
        png_files = sorted(f for f in os.listdir(LIB_DIR) if f.lower().endswith('.png'))
        for png_file in png_files:
            name = os.path.splitext(png_file)[0]
            mel_path = os.path.join(LIB_DIR, name + '.mel')
            if not os.path.isfile(mel_path):
                continue
            item = QtWidgets.QListWidgetItem()
            item.setText('')
            item.setIcon(_icon_from_png(os.path.join(LIB_DIR, png_file)))
            item.setToolTip(name)
            item.setData(QtCore.Qt.UserRole, mel_path)
            item.setSizeHint(QtCore.QSize(ICON_CELL, ICON_CELL))
            self.listWidget.addItem(item)

    def logo_connect(self, item):
        mel_path = item.data(QtCore.Qt.UserRole)
        if not mel_path:
            return
        selected = cmds.ls(sl=True, allPaths=True)
        with open(mel_path, 'r', encoding='utf-8') as f:
            ctrl = mel.eval(f.read())
        if selected and ctrl:
            cmds.matchTransform(ctrl, selected[0])
        cmds.select(ctrl, r=True)

    def _build_color_swatches(self):
        for color_rgb in BackGroundColor:
            color = QtGui.QColor(
                int(color_rgb[0] * 255), int(color_rgb[1] * 255), int(color_rgb[2] * 255))
            pixmap = QtGui.QPixmap(50, 50)
            pixmap.fill(QtGui.QColor(0, 0, 0, 0))
            painter = QtGui.QPainter(pixmap)
            painter.fillRect(pixmap.rect(), color)
            painter.end()
            item = QtWidgets.QListWidgetItem()
            item.setIcon(QtGui.QIcon(pixmap))
            item.setSizeHint(QtCore.QSize(32, 32))
            item.setData(QtCore.Qt.UserRole, color_rgb)
            self.listWidget_color.addItem(item)
        self.listWidget_color.itemClicked.connect(self.color_connect)

    def color_connect(self, item):
        color_rgb = item.data(QtCore.Qt.UserRole)
        for ctrl_name in cmds.ls(selection=1):
            shapes = cmds.listRelatives(ctrl_name, s=True)
            if not shapes:
                continue
            ctrl_shape = shapes[0]
            cmds.setAttr(f'{ctrl_shape}.overrideEnabled', 1)
            cmds.setAttr(f'{ctrl_shape}.overrideRGBColors', 1)
            cmds.setAttr(f'{ctrl_shape}.overrideColorR', color_rgb[0])
            cmds.setAttr(f'{ctrl_shape}.overrideColorG', color_rgb[1])
            cmds.setAttr(f'{ctrl_shape}.overrideColorB', color_rgb[2])

    @make_undo
    def replace_connect(self):
        ctrls = cmds.ls(sl=True, allPaths=True)
        if len(ctrls) < 2:
            return
        target_curve_sn = cmds.ls(ctrls[-1], shortNames=True)[0]
        for i in range(len(ctrls) - 1):
            copy_curve = cmds.duplicate(ctrls[-1])[0]
            curve_shape = cmds.listRelatives(copy_curve, s=True)
            cmds.delete(cmds.listRelatives(ctrls[i], s=True))
            shp = cmds.rename(curve_shape, '%sShape#' % target_curve_sn)
            cmds.parent(shp, ctrls[i], r=True, s=True)
            cmds.delete(copy_curve)
        for i in range(len(ctrls) - 1):
            cmds.select(ctrls[i], add=True)

    @make_undo
    def mirror_connect(self):
        curves = cmds.ls(sl=True)
        if len(curves) < 2:
            return
        con, con_dist = curves[0], curves[1]
        for i in range(cmds.getAttr(con + '.controlPoints', size=True)):
            p = cmds.pointPosition(con + '.controlPoints[%s]' % i)
            if self.radio_x.isChecked():
                cmds.xform(con_dist + '.controlPoints[%s]' % i, t=(-1 * p[0], p[1], p[2]), ws=True)
            elif self.radio_y.isChecked():
                cmds.xform(con_dist + '.controlPoints[%s]' % i, t=(p[0], -1 * p[1], p[2]), ws=True)
            elif self.radio_z.isChecked():
                cmds.xform(con_dist + '.controlPoints[%s]' % i, t=(p[0], p[1], -1 * p[2]), ws=True)

    @make_undo
    def zero_connect(self):
        ctrls_shape = cmds.ls(type='nurbsCurve')
        ctrls = [cmds.listRelatives(i, p=1)[0] for i in ctrls_shape]
        for i in ctrls:
            locked_attrs = cmds.listAttr(i, locked=1) or []
            if 'translateX' not in locked_attrs:
                cmds.setAttr(f'{i}.translateX', 0)
            if 'translateY' not in locked_attrs:
                cmds.setAttr(f'{i}.translateY', 0)
            if 'translateZ' not in locked_attrs:
                cmds.setAttr(f'{i}.translateZ', 0)
            if 'rotateX' not in locked_attrs:
                cmds.setAttr(f'{i}.rotateX', 0)
            if 'rotateY' not in locked_attrs:
                cmds.setAttr(f'{i}.rotateY', 0)
            if 'rotateZ' not in locked_attrs:
                cmds.setAttr(f'{i}.rotateZ', 0)
