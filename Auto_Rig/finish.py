from maya import cmds

from Auto_Rig import config

def Finish():

    spines = cmds.ls('jnt_C_spine_???')
    spine_num = len(spines)

    config.color_ctrls('ctrl_L_*', 6)
    config.color_ctrls('ctrl_R_*', 13)
    config.color_ctrls('ctrl_C_*', 17)
    if cmds.objExists('ctrl_C_cog'):
        cmds.setAttr('ctrl_C_cog.overrideColor', 19)

    cmds.delete('world_scale')

    cmds.createNode('transform',n='Group')
    cmds.createNode('transform',n='geometry',p='Group')
    cmds.createNode('transform',n='joints',p='Group')
    cmds.createNode('transform',n='controls',p='Group')
    cmds.createNode('transform',n='others',p='Group')
    cmds.createNode('transform',n='spine',p='others')
    cmds.createNode('transform',n='stretch',p='others')

    cmds.parent('ctrl_world','controls')
    cmds.parent('crv_C_spine','spine')
    cmds.parent('SpineikHnd','spine')
    cmds.parent('loc_L_upperArmIKPos','stretch')
    cmds.parent('loc_R_upperArmIKPos','stretch')
    cmds.parent('loc_R_upperLegIKPos','stretch')
    cmds.parent('loc_L_upperLegIKPos','stretch')

    children = cmds.listRelatives('ctrl_world',c=True)
    jnts = [i for i in children if 'jnt' in i]
    for jnt in jnts:
        cmds.parent(jnt,'joints')
    cmds.parentConstraint('ctrl_world','joints',mo=True)
    cmds.scaleConstraint('ctrl_world','joints',mo=True)
    cmds.select(clear=True)    

    translate_lock('Group')
    rotate_lock('Group')
    scale_lock('Group')
    translate_lock('ctrl_C_pelvisLocal')
    scale_lock('ctrl_C_pelvisLocal')
    rotate_lock('ctrl_C_spineIK_002')
    # scale_lock('ctrl_L_wristFK')
    # scale_lock('ctrl_R_wristFK')

    cmds.createNode('transform',n='spaceswitch')
    cmds.parent('spaceswitch','others')
    spaceList = ['World','Cog','Chest','Head','Pelvis']
    for i in spaceList:
        grp = cmds.createNode('transform',n=f'grp_C_{i}SpaceLocs')
        cmds.parent(grp,'spaceswitch')
        cmds.parent(f'loc_L_handIKSpace{i}',grp)
        cmds.parent(f'loc_R_handIKSpace{i}',grp)

    cmds.parentConstraint('ctrl_world','grp_C_WorldSpaceLocs',mo=True)
    cmds.parentConstraint('ctrl_C_cog','grp_C_CogSpaceLocs',mo=True)
    cmds.parentConstraint(f'jnt_C_spine_{spine_num:03}','grp_C_ChestSpaceLocs',mo=True)
    cmds.parentConstraint('jnt_C_head','grp_C_HeadSpaceLocs',mo=True)
    cmds.parentConstraint('jnt_C_pelvisLocal','grp_C_PelvisSpaceLocs',mo=True)
    cmds.hide('spaceswitch')

    cmds.hide('zero_L_heel')
    cmds.hide('zero_R_heel')

def translate_lock(name):
    config.lock_attrs(name, ['translateX','translateY','translateZ'])

def rotate_lock(name):
    config.lock_attrs(name, ['rotateX','rotateY','rotateZ'])

def scale_lock(name):
    config.lock_attrs(name, ['scaleX','scaleY','scaleZ'])
