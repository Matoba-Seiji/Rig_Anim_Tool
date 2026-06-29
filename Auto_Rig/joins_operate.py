from maya import cmds
import os

from Auto_Rig import config
from Auto_Rig.config import make_undo

head = ['neck_001', 'neck_002','head','headEnd']
arm = ['shoulder','upperArm','elbow','wrist']
leg = ['upperLeg','knee','ankle']
foot = ['ankle','ball','toe']
thumb = ['thumb_001','thumb_002','thumb_003','thumb_004']
index = ['index_001','index_002','index_003','index_004']
middle = ['middle_001','middle_002','middle_003','middle_004']
ring = ['ring_001','ring_002','ring_003','ring_004']
pinky = ['pinky_001','pinky_002','pinky_003','pinky_004']


def import_joint(jnt_name,path):

    jnt_path = os.path.join(path, jnt_name)
    cmds.file(jnt_path,i=True)


def insert_joints_between(start_spine, end_spine, count):
    if not cmds.objExists(start_spine) or not cmds.objExists(end_spine):
        cmds.warning("起始或终点骨骼不存在")
        return
    
    # 获取起始和终点的位置信息
    start_pos = cmds.xform(start_spine, q=True, ws=True, t=True)
    end_pos = cmds.xform(end_spine, q=True, ws=True, t=True)
    
    # 计算插值点
    joints = [start_spine]
    for i in range(1, count + 1):
        factor = i / (count + 1)
        new_pos = [
            start_pos[0] + (end_pos[0] - start_pos[0]) * factor,
            start_pos[1] + (end_pos[1] - start_pos[1]) * factor,
            start_pos[2] + (end_pos[2] - start_pos[2]) * factor,
        ]
        
        # 创建新骨骼
        new_joint = cmds.joint(p=new_pos, n=f"spine_{i+1:03}",radius=0.5)
        cmds.parent(new_joint,'ctrl_world')

        cmds.select(clear=True)
        joints.append(new_joint)
    
    joints.append(end_spine)
    cmds.rename('start_spine','spine_001')
    cmds.rename('end_spine',f'spine_{len(joints):03}')

def delete_jnt():
    if cmds.objExists('crv_C_spineInfo'):
        cmds.delete('crv_C_spineInfo')    
    if cmds.objExists('world_scale'):
        cmds.delete('world_scale')
    if cmds.objExists('Group'):        
        cmds.delete('Group')
    elif cmds.objExists('ctrl_world'):
        cmds.delete('ctrl_world')

def parent_chain(bones):
    """按顺序将骨骼列表连接为父子关系"""
    for i in range(len(bones) - 1):
        cmds.parent(bones[i + 1], bones[i])  

def joint_zero(jnt):
    cmds.setAttr(f'{jnt}.jointOrientX', 0)
    cmds.setAttr(f'{jnt}.jointOrientY', 0)
    cmds.setAttr(f'{jnt}.jointOrientZ', 0)


def connect_joints():

    spine = cmds.ls('spine_*')
    parent_chain(spine)

    cmds.parent('shoulder',world=True)
    cmds.parent('upperLeg',world=True)
    cmds.joint('spine_001',e=True,oj='xyz',secondaryAxisOrient='zdown',ch=True)
    joint_zero('headEnd')
    cmds.parent('shoulder',f'spine_{len(spine):03}')
    cmds.parent('upperLeg','spine_001')

    cmds.select(clear=True)


def mirror_joints():

    spine = cmds.ls('spine*')
    for i in spine+head:
        cmds.rename(i,f'jnt_C_{i}')

    L_arm =arm + thumb + index + middle + ring + pinky 

    for i in L_arm:
        cmds.rename(i,f'jnt_L_{i}')

    L_leg = ['upperLeg','knee','ankle','ball','toe','Out','Inn','heel']

    for i in L_leg:
        cmds.rename(i,f'jnt_L_{i}')
    
    cmds.mirrorJoint('jnt_L_shoulder',mirrorBehavior=True,mirrorYZ=True,searchReplace=('_L_','_R_'))
    cmds.mirrorJoint('jnt_L_upperLeg',mirrorBehavior=True,mirrorYZ=True,searchReplace=('_L_','_R_'))
    
    cmds.select(clear=True)

def rebuild_joints():
    delete_jnt()
    cmds.file(config.REBUILD_FILE,i=True)

@make_undo
def axes_vis(state):
    jnts = cmds.ls(type='joint')
    visibility = 1 if state == 2 else 0 
    for jnt in jnts:
        cmds.setAttr(f'{jnt}.displayLocalAxis',visibility)

def re_connect_jnts():
    cmds.makeIdentity('spine_001',apply=True)
    cmds.parent('upperLeg',world=True)
    cmds.parent('shoulder',world=True)
    cmds.parent('ball',world=True)
    cmds.parent('heel',world=True)
    cmds.parent('Out',world=True)
    cmds.parent('Inn',world=True)
    cmds.parent('thumb_001',world=True)
    cmds.parent('index_001',world=True)
    cmds.parent('middle_001',world=True)
    cmds.parent('ring_001',world=True)
    cmds.parent('pinky_001',world=True)

    cmds.makeIdentity('upperLeg',apply=True)
    cmds.makeIdentity('shoulder',apply=True)
    cmds.makeIdentity('spine_001',apply=True)
    cmds.makeIdentity('thumb_001',apply=True)
    cmds.makeIdentity('index_001',apply=True)
    cmds.makeIdentity('middle_001',apply=True)
    cmds.makeIdentity('ring_001',apply=True)
    cmds.makeIdentity('pinky_001',apply=True)

    cmds.joint('upperLeg',e=True,oj='xyz',sao='zup',ch=True)
    joint_zero('ankle')
    cmds.joint('spine_001',e=True,oj='xyz',sao='zdown',ch=True)
    joint_zero('headEnd')
    cmds.joint('shoulder',e=True,oj='xyz',sao='zdown',ch=True)
    joint_zero('wrist')
    cmds.joint('thumb_001',e=True,oj='xyz',sao='yup',ch=True)
    joint_zero('thumb_004')
    cmds.joint('index_001',e=True,oj='xyz',sao='zdown',ch=True)
    joint_zero('index_004')
    cmds.joint('middle_001',e=True,oj='xyz',sao='zdown',ch=True)
    joint_zero('middle_004')
    cmds.joint('ring_001',e=True,oj='xyz',sao='zdown',ch=True)
    joint_zero('ring_004')
    cmds.joint('pinky_001',e=True,oj='xyz',sao='zdown',ch=True)
    joint_zero('pinky_004')

    cmds.setAttr('knee.jointOrientX', 0)
    cmds.setAttr('knee.jointOrientY', 0)
    cmds.setAttr('elbow.jointOrientX', 0)
    cmds.setAttr('elbow.jointOrientY', 0)

    locator = cmds.spaceLocator()
    cmds.matchTransform(locator[0],'ankle',pos=True)
    ty = cmds.getAttr(f'{locator[0]}.translateY')
    cmds.setAttr(f'{locator[0]}.translateY',ty-1)
    cmds.aimConstraint(locator[0],'ankle',aimVector=(1,0,0),upVector=(0,1,0),worldUpType='object',worldUpObject='ball')
    cmds.delete(locator[0])
    cmds.makeIdentity('ankle',apply=True)

    cmds.parent('ball','ankle')
    cmds.joint('ball',e=True,oj='xyz',sao='yup',ch=True)
    joint_zero('toe')
    cmds.parent('Inn','ball')
    cmds.parent('Out','ball')
    cmds.parent('heel','ankle')

    cmds.setAttr('ball.jointOrientX', 0)
    cmds.setAttr('ball.jointOrientY', 0)

    cmds.parent('upperLeg','spine_001')
    spine = cmds.ls('spine_*')
    cmds.parent('shoulder',f'spine_{len(spine):03}')
    cmds.parent('thumb_001','wrist')
    cmds.parent('index_001','wrist')
    cmds.parent('middle_001','wrist')
    cmds.parent('ring_001','wrist')
    cmds.parent('pinky_001','wrist')

    if cmds.objExists('transform*'):
        cmds.delete('transform*')

    cmds.parent('world_scale',world=True)
    cmds.makeIdentity('ctrl_world',apply=True)

