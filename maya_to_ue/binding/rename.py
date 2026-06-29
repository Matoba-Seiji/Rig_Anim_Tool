from functools import wraps

from maya import cmds
from PySide2 import QtWidgets, QtCore

from maya_to_ue.maya_ui import get_maya_main_window


class Rename_functions:

    def Add(self, mode=None, prefix='', suffix=''):
        if mode == '选中':
            selections = cmds.ls(selection=True, uuid=1)
            for i in selections:
                name = cmds.ls(i)
                cmds.rename(name, prefix + name[0].split('|')[-1] + suffix)

        if mode == '层级':
            selections = cmds.ls(selection=True, long=1)
            children = cmds.listRelatives(selections, ad=1, fullPath=1) or []
            for child in children:
                selections.append(child)
            uuid_list = []
            for i in selections:
                uuid = cmds.ls(i, uuid=1)
                uuid_list.append(uuid)
            for i in uuid_list:
                name = cmds.ls(i)
                cmds.rename(name, prefix + name[0].split('|')[-1] + suffix)

        if mode == '全选':
            cmds.select(allDagObjects=True)
            selections = cmds.ls(selection=True, long=1)
            children = cmds.listRelatives(selections, ad=1, fullPath=1) or []
            for child in children:
                selections.append(child)
            uuid_list = []
            for i in selections:
                uuid = cmds.ls(i, uuid=1)
                uuid_list.append(uuid)
            for i in uuid_list:
                name = cmds.ls(i)
                cmds.rename(name, prefix + name[0].split('|')[-1] + suffix)

    def Replace(self, mode=None, search='', replace=''):
        if mode == '选中':
            selections = cmds.ls(selection=True, uuid=1)
            for i in selections:
                old_name = cmds.ls(i)
                name = old_name[0].split('|')[-1]
                new_name = name.replace(search, replace)
                cmds.rename(old_name, new_name)

        if mode == '层级':
            selections = cmds.ls(selection=True, long=1)
            children = cmds.listRelatives(selections, ad=1, fullPath=1) or []
            for child in children:
                selections.append(child)
            uuid_list = []
            for i in selections:
                uuid = cmds.ls(i, uuid=1)
                uuid_list.append(uuid)
            for i in uuid_list:
                old_name = cmds.ls(i)
                name = old_name[0].split('|')[-1]
                new_name = name.replace(search, replace)
                cmds.rename(old_name, new_name)

        if mode == '全选':
            cmds.select(allDagObjects=True)
            selections = cmds.ls(selection=True, long=1)
            children = cmds.listRelatives(selections, ad=1, fullPath=1) or []
            for child in children:
                selections.append(child)
            uuid_list = []
            for i in selections:
                uuid = cmds.ls(i, uuid=1)
                uuid_list.append(uuid)
            for i in uuid_list:
                old_name = cmds.ls(i)
                name = old_name[0].split('|')[-1]
                new_name = name.replace(search, replace)
                cmds.rename(old_name, new_name)

    def Rename(self, mode=None, new_name='', first_num=''):
        if mode == '选中':
            selections = cmds.ls(selection=True, uuid=True)
            for i in selections:
                name = cmds.ls(i)
                cmds.rename(name, new_name + f'_{first_num:03}')
                first_num += 1

        if mode == '层级':
            selections = cmds.ls(selection=True, long=1)
            children = cmds.listRelatives(selections, ad=1, fullPath=1) or []
            children.reverse()
            for child in children:
                selections.append(child)
            uuid_list = []
            for i in selections:
                uuid = cmds.ls(i, uuid=1)
                uuid_list.append(uuid)
            for i in uuid_list:
                name = cmds.ls(i)
                cmds.rename(name, new_name + f'_{first_num:03}')
                first_num += 1


def make_undo(func):
    @wraps(func)
    def wrap(*args, **kwargs):
        cmds.undoInfo(openChunk=True)
        try:
            return func(*args, **kwargs)
        finally:
            cmds.undoInfo(closeChunk=True)
    return wrap


class RenameUI(QtWidgets.QWidget):
    def __init__(self, parent=None):
        if parent is None:
            parent = get_maya_main_window()
        super().__init__(parent)

        self.rename_functions = Rename_functions()
        self.setWindowTitle('重命名工具')

        layout = QtWidgets.QVBoxLayout(self)

        samename = QtWidgets.QPushButton('修改全部相同物体名')
        samename.clicked.connect(self.Clear_same_name)
        layout.addWidget(samename)

        addWidget = QtWidgets.QGroupBox('添加前后缀')
        layout.addWidget(addWidget)
        addLayout = QtWidgets.QVBoxLayout(addWidget)

        lineWidget = QtWidgets.QWidget()
        addLayout.addWidget(lineWidget)
        lineLayout = QtWidgets.QGridLayout(lineWidget)
        lineLayout.addWidget(QtWidgets.QLabel('前缀:'), 0, 0)
        self.pre_line = QtWidgets.QLineEdit()
        lineLayout.addWidget(self.pre_line, 0, 1)
        lineLayout.addWidget(QtWidgets.QLabel('后缀:'), 1, 0)
        self.suf_line = QtWidgets.QLineEdit()
        lineLayout.addWidget(self.suf_line, 1, 1)

        radioWidget = QtWidgets.QWidget()
        addLayout.addWidget(radioWidget)
        radioLayout = QtWidgets.QHBoxLayout(radioWidget)
        self.s_radio = QtWidgets.QRadioButton('选中')
        radioLayout.addWidget(self.s_radio)
        self.h_radio = QtWidgets.QRadioButton('层级')
        radioLayout.addWidget(self.h_radio)
        self.a_radio = QtWidgets.QRadioButton('全选')
        radioLayout.addWidget(self.a_radio)

        addButton = QtWidgets.QPushButton('添加')
        addButton.clicked.connect(self.AddClick)
        addLayout.addWidget(addButton)

        replaceWidget = QtWidgets.QGroupBox('替换字符串')
        layout.addWidget(replaceWidget)
        replaceLayout = QtWidgets.QVBoxLayout(replaceWidget)

        lineWidget1 = QtWidgets.QWidget()
        replaceLayout.addWidget(lineWidget1)
        lineLayout1 = QtWidgets.QGridLayout(lineWidget1)
        lineLayout1.addWidget(QtWidgets.QLabel('寻找:'), 0, 0)
        self.search_line = QtWidgets.QLineEdit()
        lineLayout1.addWidget(self.search_line, 0, 1)
        lineLayout1.addWidget(QtWidgets.QLabel('替换:'), 1, 0)
        self.replace_line = QtWidgets.QLineEdit()
        lineLayout1.addWidget(self.replace_line, 1, 1)

        radioWidget1 = QtWidgets.QWidget()
        replaceLayout.addWidget(radioWidget1)
        radioLayout1 = QtWidgets.QHBoxLayout(radioWidget1)
        self.s_radio1 = QtWidgets.QRadioButton('选中')
        radioLayout1.addWidget(self.s_radio1)
        self.h_radio1 = QtWidgets.QRadioButton('层级')
        radioLayout1.addWidget(self.h_radio1)
        self.a_radio1 = QtWidgets.QRadioButton('全选')
        radioLayout1.addWidget(self.a_radio1)

        replaceButton = QtWidgets.QPushButton('替换')
        replaceButton.clicked.connect(self.ReplaceClick)
        replaceLayout.addWidget(replaceButton)

        renameWidget = QtWidgets.QGroupBox('重命名')
        layout.addWidget(renameWidget)
        renameLayout = QtWidgets.QVBoxLayout(renameWidget)

        lineWidget2 = QtWidgets.QWidget()
        renameLayout.addWidget(lineWidget2)
        lineLayout2 = QtWidgets.QGridLayout(lineWidget2)
        lineLayout2.addWidget(QtWidgets.QLabel('新名字:'), 0, 0)
        self.rename_line = QtWidgets.QLineEdit()
        lineLayout2.addWidget(self.rename_line, 0, 1)
        lineLayout2.addWidget(QtWidgets.QLabel('开头编号:'), 1, 0)
        self.start_line = QtWidgets.QLineEdit()
        lineLayout2.addWidget(self.start_line, 1, 1)

        radioWidget2 = QtWidgets.QWidget()
        renameLayout.addWidget(radioWidget2)
        radioLayout2 = QtWidgets.QHBoxLayout(radioWidget2)
        self.s_radio2 = QtWidgets.QRadioButton('选中')
        radioLayout2.addWidget(self.s_radio2)
        self.h_radio2 = QtWidgets.QRadioButton('层级')
        radioLayout2.addWidget(self.h_radio2)

        renameButton = QtWidgets.QPushButton('重命名')
        renameButton.clicked.connect(self.RenameClick)
        renameLayout.addWidget(renameButton)

        layout.addStretch(1)

    @make_undo
    def AddClick(self):
        prefix = self.pre_line.text()
        suffix = self.suf_line.text()
        if self.s_radio.isChecked():
            mode = '选中'
        elif self.h_radio.isChecked():
            mode = '层级'
        elif self.a_radio.isChecked():
            mode = '全选'
        else:
            return
        self.rename_functions.Add(mode, prefix, suffix)

    @make_undo
    def ReplaceClick(self):
        search = self.search_line.text()
        replace = self.replace_line.text()
        if self.s_radio1.isChecked():
            mode = '选中'
        elif self.h_radio1.isChecked():
            mode = '层级'
        elif self.a_radio1.isChecked():
            mode = '全选'
        else:
            return
        self.rename_functions.Replace(mode, search, replace)

    @make_undo
    def RenameClick(self):
        new_name = self.rename_line.text()
        if not self.start_line.text().strip():
            return
        first_num = int(self.start_line.text())
        if self.s_radio2.isChecked():
            mode = '选中'
        elif self.h_radio2.isChecked():
            mode = '层级'
        else:
            return
        self.rename_functions.Rename(mode, new_name, first_num)

    @make_undo
    def Clear_same_name(self):
        cmds.select(allDagObjects=True)
        selections = cmds.ls(selection=True, long=True)

        for obj in selections:
            children = cmds.listRelatives(obj, children=True, fullPath=True) or []
            shapes = cmds.listRelatives(obj, shapes=True, fullPath=True)
            if shapes is not None:
                for shape in shapes:
                    children.remove(shape)
            for child in children:
                selections.append(child)

        selections.sort(reverse=True)
        count = len(selections)

        for i in range(0, len(selections) - 1):
            num = 1
            for j in range(i + 1, count):
                if selections[j].split('|')[-1] == selections[i].split('|')[-1]:
                    uuid = cmds.ls(selections[j], uuid=True)
                    if uuid:
                        uuid = uuid[0]
                        obj_name = cmds.ls(uuid)[0]
                        cmds.rename(obj_name, selections[j].split('|')[-1] + f'_{num}')
                        num += 1
