from maya import cmds
from PySide2 import QtWidgets, QtCore, QtGui
import os

from maya_to_ue.maya_ui import get_maya_main_window
from Auto_Rig import joins_operate, assist_tools, ctrls_create, finish, advanced, dragon, config


class UI(QtWidgets.QWidget):
    def __init__(self, parent=None):
        if parent is None:
            parent = get_maya_main_window()
        super(UI, self).__init__(parent)

        self.setWindowTitle('自动绑定')

        self.create_import()
        self.one_btn_create()
        self.higher_func()
        self.IKFK_Switch()
        self.assistive_tool()

    def create_import(self):
        self.layout = QtWidgets.QVBoxLayout(self)

        pre_jnt_group = QtWidgets.QGroupBox('导入预设骨架:')
        self.layout.addWidget(pre_jnt_group)

        gri_layout = QtWidgets.QGridLayout(pre_jnt_group)

        self.combox = QtWidgets.QComboBox()
        gri_layout.addWidget(self.combox,0,0)


        self.paths = config.PRE_JOINTS_DIR
        files = os.listdir(self.paths)
        jntsFiles = [f for f in files if f.endswith('.mb')]        
        for jntFile in jntsFiles:
            self.combox.addItem(jntFile)

        self.slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        gri_layout.addWidget(self.slider,0,2)
        self.slider.setMinimum(4)
        self.slider.setMaximum(9)
        self.slider.valueChanged.connect(self.update_label)

        self.spine_num_lable = QtWidgets.QLabel(f'脊椎骨骼数量:{self.slider.value()}')
        gri_layout.addWidget(self.spine_num_lable,0,1)
        

        import_btn = QtWidgets.QPushButton('导入')
        gri_layout.addWidget(import_btn,1,2)
        import_btn.clicked.connect(self.import_func)

        del_btn = QtWidgets.QPushButton('删除')
        gri_layout.addWidget(del_btn,1,0)
        del_btn.clicked.connect(joins_operate.delete_jnt)


    def update_label(self):
        # 更新标签显示当前的脊椎骨骼数量
        self.spine_num_lable.setText(f"脊椎骨骼数量:{self.slider.value()}")

    def import_func(self):

        if cmds.objExists('ctrl_world'):
            cmds.delete('ctrl_world')

        joins_operate.import_joint(self.combox.currentText(),self.paths)
        joins_operate.insert_joints_between('start_spine','end_spine',count=self.slider.value()-2)
        cmds.spaceLocator(n='world_scale')
        cmds.parent('world_scale','ctrl_world')
        cmds.hide('world_scale')
        joins_operate.connect_joints()

    def one_btn_create(self):
        check = QtWidgets.QCheckBox('显示骨骼坐标轴')
        self.layout.addWidget(check)
        check.stateChanged.connect(joins_operate.axes_vis)

        H_layout = QtWidgets.QHBoxLayout()
        self.layout.addLayout(H_layout)
        rebuild_btn = QtWidgets.QPushButton('重设')
        rebuild_btn.clicked.connect(joins_operate.rebuild_joints)
        H_layout.addWidget(rebuild_btn)
        rig_btn = QtWidgets.QPushButton('一键绑定')
        H_layout.addWidget(rig_btn)
        rig_btn.clicked.connect(self.oneBtnRig)
        self.jntDisplayScaleUI()
        self.get_joint_display_scale()

    def jntDisplayScaleUI(self):
        jnt_scale_layout = QtWidgets.QHBoxLayout()
        self.layout.addLayout(jnt_scale_layout)

        scale_lable = QtWidgets.QLabel('骨骼大小：')
        jnt_scale_layout.addWidget(scale_lable)

        self.scale_line = QtWidgets.QLineEdit()
        self.scale_line.setFixedWidth(50)
        self.scale_line.setAlignment(QtCore.Qt.AlignCenter)
        self.scale_line.setValidator(QtGui.QDoubleValidator(0.01,10.0,2))
        self.scale_line.returnPressed.connect(self.scale_input_update)
        jnt_scale_layout.addWidget(self.scale_line)

        self.scale_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        jnt_scale_layout.addWidget(self.scale_slider)
        self.scale_slider.setMinimum(1)
        self.scale_slider.setMaximum(1000)
        self.scale_slider.setValue(100)  
        self.scale_slider.valueChanged.connect(self.update_jntDisplayScale)

    def get_joint_display_scale(self):
        scale = cmds.jointDisplayScale(query=True)  # 获取 Joint Display Scale
        self.scale_slider.setValue(int(scale * 100))  # 乘 10 适配滑块
        self.scale_line.setText(f"{scale:.2f}")  # 设置 LineEdit 显示的值

    def scale_input_update(self):
        try:
            scale = float(self.scale_line.text())  # 获取输入值
            if 0.01 <= scale <= 10.00:  # 限制范围
                cmds.jointDisplayScale(scale)  # 更新 Joint Display Scale
                self.scale_slider.setValue(int(scale * 100))  # 更新滑块
            else:
                raise ValueError  # 超出范围则抛异常
        except ValueError:
            self.get_joint_display_scale()  # 输入无效时重置

    def update_jntDisplayScale(self):
        scale = self.scale_slider.value() / 100.0  # 还原真实值
        cmds.jointDisplayScale(scale)  # 设置 Joint Display Scale
        self.scale_line.setText(f"{scale:.2f}")  # 同步 LineEdit 的显示值
    
    def higher_func(self):
        Twist_btn = QtWidgets.QPushButton('添加Twist')
        self.layout.addWidget(Twist_btn)
        Twist_btn.clicked.connect(self.Twist_func)

    def IKFK_Switch(self):
        IKFK_group = QtWidgets.QGroupBox('IKFK无缝切换:')
        self.layout.addWidget(IKFK_group)

        h_layout = QtWidgets.QHBoxLayout(IKFK_group)

        FKToIK_btn = QtWidgets.QPushButton('无缝切换')
        h_layout.addWidget(FKToIK_btn)
        FKToIK_btn.clicked.connect(assist_tools.FKToIK)



    def assistive_tool(self):
        assist_group = QtWidgets.QGroupBox('绑定辅助工具:')
        self.layout.addWidget(assist_group)

        gridLayout = QtWidgets.QGridLayout(assist_group)

        jnt_orient_btn = QtWidgets.QPushButton('末骨骼朝向归零')
        gridLayout.addWidget(jnt_orient_btn,0,0)
        jnt_orient_btn.clicked.connect(assist_tools.zero_jnt_orient)

        chain_FK_btn = QtWidgets.QPushButton('创建FK链')
        gridLayout.addWidget(chain_FK_btn,0,1)
        chain_FK_btn.clicked.connect(assist_tools.Chain_FK)

        zero_pose_btn = QtWidgets.QPushButton('恢复默认姿势')
        gridLayout.addWidget(zero_pose_btn,1,0)
        zero_pose_btn.clicked.connect(assist_tools.zero_pose)

        global_btn = QtWidgets.QPushButton('创建Global')
        gridLayout.addWidget(global_btn,1,1)
        global_btn.clicked.connect(assist_tools.Global)

        copy_skin_btn = QtWidgets.QPushButton('复制蒙皮')
        gridLayout.addWidget(copy_skin_btn,0,2)
        copy_skin_btn.clicked.connect(assist_tools.copy_skin)

        copy_skin_btn = QtWidgets.QPushButton('创建次级FK')
        gridLayout.addWidget(copy_skin_btn,1,2)
        copy_skin_btn.clicked.connect(assist_tools.cijiFK)


        jnt_chain_layout = QtWidgets.QHBoxLayout()
        gridLayout.addLayout(jnt_chain_layout,2,0,1,3)
        jnt_chain_lable = QtWidgets.QLabel('关节数:')
        jnt_chain_layout.addWidget(jnt_chain_lable)
        self.jnt_chain_lineedit = QtWidgets.QLineEdit()
        jnt_chain_layout.addWidget(self.jnt_chain_lineedit)
        jnt_chain_btn = QtWidgets.QPushButton('创建关节链')
        jnt_chain_layout.addWidget(jnt_chain_btn)
        jnt_chain_btn.clicked.connect(self.jnt_chain_func)

        Vertical_axis_layout = QtWidgets.QHBoxLayout()
        gridLayout.addLayout(Vertical_axis_layout,3,0,1,3)
        Vertical_axis_lable = QtWidgets.QLabel('轴向:')
        Vertical_axis_layout.addWidget(Vertical_axis_lable)
        self.Y_axis_btn = QtWidgets.QRadioButton('Y')
        Vertical_axis_layout.addWidget(self.Y_axis_btn)
        self.Z_axis_btn = QtWidgets.QRadioButton('Z')
        Vertical_axis_layout.addWidget(self.Z_axis_btn)
        Vertical_axis_btn = QtWidgets.QPushButton('设置垂直轴向')
        Vertical_axis_layout.addWidget(Vertical_axis_btn)
        Vertical_axis_btn.clicked.connect(self.Verical_axis_func)

        scale_layout = QtWidgets.QHBoxLayout()
        gridLayout.addLayout(scale_layout,4,0,1,3)
        scale_lable = QtWidgets.QLabel('缩放倍数:')
        scale_layout.addWidget(scale_lable)
        self.scale_lineedit = QtWidgets.QLineEdit()
        scale_layout.addWidget(self.scale_lineedit)
        scale_btn = QtWidgets.QPushButton('缩放曲线')
        scale_layout.addWidget(scale_btn)
        scale_btn.clicked.connect(self.scale_circle_func)

    def Verical_axis_func(self):
        if self.Y_axis_btn.isChecked():
            axis = 'Y'
        elif self.Z_axis_btn.isChecked():
            axis = 'Z'
        assist_tools.Vertical_axis(axis)
    @config.make_undo
    def jnt_chain_func(self):
        count =int(self.jnt_chain_lineedit.text())
        assist_tools.jnt_chain(count)

    @config.make_undo
    def scale_circle_func(self):
        scale = float(self.scale_lineedit.text())
        assist_tools.scale_curve_cvs(scale)

    @config.make_undo
    def Twist_func(self):
        cmds.createNode('transform',n='twist',p='others')
        advanced.Twist(name='upperArm',side='L')
        advanced.Twist(name='elbow',side='L')
        advanced.Twist(name='upperLeg',side='L')
        advanced.Twist(name='knee',side='L')
        advanced.Twist(name='upperArm',side='R')
        advanced.Twist(name='elbow',side='R')
        advanced.Twist(name='upperLeg',side='R')
        advanced.Twist(name='knee',side='R')

    def oneBtnRig(self):
        if self.combox.currentText() == 'bipe.mb':
            cmds.select('ctrl_world')
            cmds.file(config.REBUILD_FILE,exportSelected=True,type='mayaBinary',force=True)

            joins_operate.re_connect_jnts()
            joins_operate.mirror_joints()
            
            ctrls_create.handFK('L')
            ctrls_create.handFK('R')

            ctrls_create.handIK('L')
            ctrls_create.handIK('R')

            ctrls_create.hand_ikfkBlend('L')
            ctrls_create.hand_ikfkBlend('R')

            ctrls_create.footFK('L')
            ctrls_create.footFK('R')

            ctrls_create.footIK('L')
            ctrls_create.footIK('R')

            ctrls_create.leg_ikfkBlend('L')
            ctrls_create.leg_ikfkBlend('R')

            ctrls_create.spine()
            ctrls_create.head()

            advanced.Stretch('L','arm')
            advanced.Stretch('L','leg')
            advanced.Stretch('R','arm')
            advanced.Stretch('R','leg')
            advanced.SpaceSwitch('L')
            advanced.SpaceSwitch('R')
            advanced.Scale('L','arm')
            advanced.Scale('R','arm')
            advanced.Scale('L','leg')
            advanced.Scale('R','leg')

            finish.Finish()
        elif self.combox.currentText() == 'dragon.mb':
            dragon.DragonRig().build()
        else:
            print(self.combox.currentIndex())


#关闭工具UI后删除重设骨架文件
    # def closeEvent(self,event):
    #     if os.path.exists(config.REBUILD_FILE):
    #         os.remove(config.REBUILD_FILE)
    #     else:
    #         pass




def show_ui():
    global auto_rig_ui
    try:
        auto_rig_ui.close()
    except:
        pass

    auto_rig_ui = UI()
    auto_rig_ui.show()


if __name__ == '__main__':
    show_ui()