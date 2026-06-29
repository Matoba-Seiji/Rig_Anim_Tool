from maya import cmds

from Auto_Rig import config

arm = ['upperArm','elbow','wrist']
leg = ['upperLeg','knee','ankle','ball']


def handFK(side):
    
    cmds.select(clear=True)
    upperArm_jnt = cmds.joint(n=f'jnt_{side}_upperArmFK')
    elbow_jnt = cmds.joint(n=f'jnt_{side}_elbowFK')
    wrist_jnt = cmds.joint(n=f'jnt_{side}_wristFK')

    cmds.matchTransform(upperArm_jnt,f'jnt_{side}_upperArm')
    cmds.matchTransform(elbow_jnt,f'jnt_{side}_elbow')
    cmds.matchTransform(wrist_jnt,f'jnt_{side}_wrist')

    cmds.makeIdentity(f'jnt_{side}_upperArmFK',apply=True,translate=True, rotate=True, scale=True)


    for i in arm:
        cmds.file(config.ctrl_lib('circle.mb'),i=True)
        ctrl = cmds.rename('nurbsCircle1',f'ctrl_{side}_{i}FK')
        zero_ctrl = cmds.group(ctrl,n=f'zero_{side}_{i}FK')

        cmds.matchTransform(zero_ctrl,f'jnt_{side}_{i}')
        scale = cmds.getAttr('world_scale.scaleX')
        config.scale_node(f'zero_{side}_{i}FK', scale)

        cmds.parent(zero_ctrl,'ctrl_world')
        

        cmds.setAttr(f'{ctrl}.rotateZ',90)
        cmds.makeIdentity(ctrl,apply=True)

        if i == 'elbow':
            cmds.parent(zero_ctrl,f'ctrl_{side}_upperArmFK')

        if i == 'wrist':
            cmds.parent(zero_ctrl,f'ctrl_{side}_elbowFK')

        cmds.parentConstraint(ctrl,f'jnt_{side}_{i}FK')

    cmds.parent(f'jnt_{side}_upperArmFK','ctrl_world')


def footFK(side):

    cmds.select(clear=True)
    upperLeg_jnt = cmds.joint(n=f'jnt_{side}_upperLegFK')
    knee_jnt = cmds.joint(n=f'jnt_{side}_kneeFK')
    ankle_jnt = cmds.joint(n=f'jnt_{side}_ankleFK')
    ball_jnt = cmds.joint(n=f'jnt_{side}_ballFK')
    toe_jnt = cmds.joint(n=f'jnt_{side}_toeFK')

    cmds.matchTransform(upperLeg_jnt,f'jnt_{side}_upperLeg')
    cmds.matchTransform(knee_jnt,f'jnt_{side}_knee')
    cmds.matchTransform(ankle_jnt,f'jnt_{side}_ankle')
    cmds.matchTransform(ball_jnt,f'jnt_{side}_ball')
    cmds.matchTransform(toe_jnt,f'jnt_{side}_toe')

    cmds.makeIdentity(f'jnt_{side}_upperLegFK',apply=True,translate=True, rotate=True, scale=True)


    for i in leg:
        cmds.file(config.ctrl_lib('circle.mb'),i=True)
        ctrl = cmds.rename('nurbsCircle1',f'ctrl_{side}_{i}FK')
        zero_ctrl = cmds.group(ctrl,n=f'zero_{side}_{i}FK')

        cmds.matchTransform(zero_ctrl,f'jnt_{side}_{i}')

        scale = cmds.getAttr('world_scale.scaleX')
        config.scale_node(f'zero_{side}_{i}FK', scale)
        cmds.parent(zero_ctrl,'ctrl_world')
        

        cmds.setAttr(f'{ctrl}.rotateZ',90)
        cmds.makeIdentity(ctrl,apply=True)

        if i == 'knee':
            cmds.parent(zero_ctrl,f'ctrl_{side}_upperLegFK')

        if i == 'ankle':
            cmds.parent(zero_ctrl,f'ctrl_{side}_kneeFK')

        if i == 'ball':
            cmds.parent(zero_ctrl,f'ctrl_{side}_ankleFK')

        cmds.parentConstraint(ctrl,f'jnt_{side}_{i}FK')

    cmds.parent(f'jnt_{side}_upperLegFK','ctrl_world')


def handIK(side):

    cmds.select(clear=True)
    upperArm_jnt = cmds.joint(n=f'jnt_{side}_upperArmIK')
    elbow_jnt = cmds.joint(n=f'jnt_{side}_elbowIK')
    wrist_jnt = cmds.joint(n=f'jnt_{side}_wristIK')

    cmds.matchTransform(upperArm_jnt,f'jnt_{side}_upperArm')
    cmds.matchTransform(elbow_jnt,f'jnt_{side}_elbow')
    cmds.matchTransform(wrist_jnt,f'jnt_{side}_wrist')

    cmds.makeIdentity(f'jnt_{side}_upperArmIK',apply=True,translate=True, rotate=True, scale=True)

    cmds.file(config.ctrl_lib('PV.mb'),i=True)
    pv_ctrl = cmds.rename('curveControl1',f'ctrl_{side}_ArmPV')
    pv_zero_ctrl = cmds.group(pv_ctrl,n=f'zero_{side}_ArmPV')
    cmds.parent(pv_zero_ctrl,'ctrl_world')



    cmds.file(config.ctrl_lib('cube.mb'),i=True)
    IK_ctrl = cmds.rename('curve1',f'ctrl_{side}_handIK')
    cmds.setAttr(f'ctrl_{side}_handIK.scaleX',0.7)
    cmds.setAttr(f'ctrl_{side}_handIK.scaleY',0.7)
    cmds.setAttr(f'ctrl_{side}_handIK.scaleZ',0.7)
    cmds.makeIdentity(f'ctrl_{side}_handIK',apply=True)
    IK_zero_ctrl = cmds.group(IK_ctrl,n=f'zero_{side}_handIK')
    cmds.matchTransform(IK_zero_ctrl,f'jnt_{side}_wristIK')
    scale = cmds.getAttr('world_scale.scaleX')
    config.scale_node(f'zero_{side}_handIK', scale)
    cmds.parent(IK_zero_ctrl,'ctrl_world')

    cmds.setAttr(f'ctrl_{side}_handIK.rotateY',90)
    cmds.makeIdentity(f'ctrl_{side}_handIK',apply=True)
    cmds.ikHandle(sj=f'jnt_{side}_upperArmIK',ee=f'jnt_{side}_wristIK',sol='ikRPsolver',n=f'{side}_ArmikHnd')
    cmds.hide(f'{side}_ArmikHnd')
    cmds.parent(f'{side}_ArmikHnd',f'ctrl_{side}_handIK')

    cmds.matchTransform(f'zero_{side}_ArmPV',f'jnt_{side}_elbowIK',pos=True)
    cmds.parent(f'zero_{side}_ArmPV',f'jnt_{side}_elbowIK')
    if side == 'L':
        cmds.xform('zero_L_ArmPV',t=[-0.5*scale,5*scale,0])
    if side == 'R':
        cmds.xform('zero_R_ArmPV',t=[0.5*scale,-5*scale,0])
    cmds.parent(f'zero_{side}_ArmPV',world=True)
    cmds.setAttr(f'zero_{side}_ArmPV.rotateX',0)
    cmds.setAttr(f'zero_{side}_ArmPV.rotateY',0)
    cmds.setAttr(f'zero_{side}_ArmPV.rotateZ',0)
    config.scale_node(f'zero_{side}_ArmPV', scale)
    cmds.poleVectorConstraint(f'ctrl_{side}_ArmPV',f'{side}_ArmikHnd')    
    cmds.parent(f'zero_{side}_ArmPV','ctrl_world')

    cmds.annotate(f'ctrl_{side}_ArmPV',tx=' ')
    cmds.rename('annotation1',f'{side}_Arm_annotation')
    cmds.pointConstraint(f'jnt_{side}_elbowIK',f'{side}_Arm_annotation')
    cmds.setAttr(f"{side}_Arm_annotationShape.overrideEnabled",1)
    cmds.setAttr(f"{side}_Arm_annotationShape.overrideDisplayType",2)
    cmds.orientConstraint(f'ctrl_{side}_handIK',f'jnt_{side}_wristIK')

    if side == 'R':
        cmds.group('L_Arm_annotation','R_Arm_annotation',n='grp_Arm_annotation')
        cmds.parent('grp_Arm_annotation','ctrl_world')

    cmds.parent(f'jnt_{side}_upperArmIK','ctrl_world')


def hand_ikfkBlend(side):

    cmds.file(config.ctrl_lib('cross.mb'),i=True)
    cmds.rename('curve1',f'ctrl_{side}_armIKFKBlend')
    cmds.group(f'ctrl_{side}_armIKFKBlend',n=f'zero_{side}_armIKFKBlend')
    tx = cmds.xform(f'jnt_{side}_upperArm',q=True,ws=True,t=True)[0]
    ty = cmds.xform('jnt_C_head',q=True,ws=True,t=True)[1]
    tz = cmds.xform(f'jnt_{side}_upperArm',q=True,ws=True,t=True)[2]
    addBlendAttr(side,'armIKFKBlend')
    scale = cmds.getAttr('world_scale.scaleX')
    config.scale_node(f'zero_{side}_armIKFKBlend', scale)
    cmds.xform(f'zero_{side}_armIKFKBlend',t=[tx,ty,tz-5*scale])
    cmds.parent(f'zero_{side}_armIKFKBlend','ctrl_world')

    rev_node = cmds.createNode('reverse',n=f'{side}_armIKrev')
    cmds.connectAttr(f'ctrl_{side}_armIKFKBlend.ikfkBlend',f'{rev_node}.inputX')

    for i in arm:
        cmds.parentConstraint(f'jnt_{side}_{i}FK',f'jnt_{side}_{i}IK',f'jnt_{side}_{i}')

        cmds.connectAttr(f'ctrl_{side}_armIKFKBlend.ikfkBlend',f'jnt_{side}_{i}_parentConstraint1.jnt_{side}_{i}IKW1')
        cmds.connectAttr(f'{rev_node}.outputX',f'jnt_{side}_{i}_parentConstraint1.jnt_{side}_{i}FKW0')

    cmds.connectAttr(f'ctrl_{side}_armIKFKBlend.ikfkBlend',f'zero_{side}_handIK.visibility')
    cmds.connectAttr(f'ctrl_{side}_armIKFKBlend.ikfkBlend',f'zero_{side}_ArmPV.visibility')
    cmds.connectAttr(f'ctrl_{side}_armIKFKBlend.ikfkBlend',f'{side}_Arm_annotation.visibility')

    cmds.connectAttr(f'{rev_node}.outputX',f'zero_{side}_upperArmFK.visibility')

    cmds.hide(f'jnt_{side}_upperArmFK')
    cmds.hide(f'jnt_{side}_upperArmIK')

    All_fingers(side)    
    fingerFK(side,'thumb')
    fingerFK(side,'index')
    fingerFK(side,'middle')
    fingerFK(side,'ring')
    fingerFK(side,'pinky')

    cmds.group(n=f'grp_{side}_fingerFK',empty=True)
    cmds.parent(f'grp_{side}_fingerFK','ctrl_world')
    cmds.parentConstraint(f'jnt_{side}_wrist',f'grp_{side}_fingerFK')
    cmds.parent(f'zero_{side}_thumb_001',f'grp_{side}_fingerFK')
    cmds.parent(f'zero_{side}_index_001',f'grp_{side}_fingerFK')
    cmds.parent(f'zero_{side}_middle_001',f'grp_{side}_fingerFK')
    cmds.parent(f'zero_{side}_ring_001',f'grp_{side}_fingerFK')
    cmds.parent(f'zero_{side}_pinky_001',f'grp_{side}_fingerFK')

    cmds.file(config.ctrl_lib('shoulder.mb'),i=True)
    cmds.rename('curve1',f'ctrl_{side}_shoulder')
    cmds.group(f'ctrl_{side}_shoulder',n=f'zero_{side}_shoulder')
    cmds.matchTransform(f'zero_{side}_shoulder',f'ctrl_{side}_shoulder',pivots=True)
    cmds.matchTransform(f'zero_{side}_shoulder',f'jnt_{side}_shoulder')
    if side == 'L':
        cmds.setAttr(f'ctrl_{side}_shoulder.rotateX',90)
    if side == 'R':
        cmds.setAttr(f'ctrl_{side}_shoulder.rotateX',-90)
    cmds.makeIdentity(f'ctrl_{side}_shoulder',apply=True)
    scale = cmds.getAttr('world_scale.scaleX')
    config.scale_node(f'zero_{side}_shoulder', scale)
    cmds.parent(f'zero_{side}_shoulder','ctrl_world')

    cmds.parentConstraint(f'ctrl_{side}_shoulder',f'jnt_{side}_shoulder')

    cmds.parentConstraint(f'ctrl_{side}_shoulder',f'zero_{side}_upperArmFK',mo=True)
    cmds.parentConstraint(f'jnt_{side}_shoulder',f'jnt_{side}_upperArmIK',mo=True)
    

def addBlendAttr(side,name):
    config.lock_srt_vis(f'ctrl_{side}_{name}')
    cmds.addAttr(f'ctrl_{side}_{name}.',longName='ikfkBlend',attributeType='double',keyable=True,min=0,max=1)

def fingers_attrs(side):
    config.lock_srt_vis(f'ctrl_{side}_fingers')
    for finger in ('index','middle','ring','pinky','thumb'):
        cmds.addAttr(f'ctrl_{side}_fingers.',longName=finger,attributeType='double',keyable=True,min=-2,max=10)

def fingerFK(side,name):
    

    for i in range(3):
        cmds.file(config.ctrl_lib('circle.mb'),i=True)
        ctrl = cmds.rename('nurbsCircle1',f'ctrl_{side}_{name}_00{i+1}')
        zero_ctrl = cmds.group(ctrl,n=f'zero_{side}_{name}_00{i+1}')
        cmds.group(ctrl,n=f'connect_{side}_{name}_00{i+1}')

        cmds.matchTransform(zero_ctrl,f'jnt_{side}_{name}_00{i+1}')

        cmds.parent(zero_ctrl,'ctrl_world')
        
        cmds.setAttr(f'{ctrl}.rotateZ',90)
        cmds.setAttr(f'{ctrl}.scaleX',0.3)
        cmds.setAttr(f'{ctrl}.scaleY',0.3)
        cmds.setAttr(f'{ctrl}.scaleZ',0.3)
        cmds.makeIdentity(ctrl,apply=True)
        scale = cmds.getAttr('world_scale.scaleX')
        config.scale_node(f'zero_{side}_{name}_00{i+1}', scale)

        if i != 0:
            cmds.parent(zero_ctrl,f'ctrl_{side}_{name}_00{i}')

        cmds.parentConstraint(ctrl,f'jnt_{side}_{name}_00{i+1}')

    cmds.createNode('multDoubleLinear',n=f'mult_{side}_{name}')
    cmds.connectAttr(f'ctrl_{side}_fingers.{name}',f'mult_{side}_{name}.input1')
    cmds.setAttr(f'mult_{side}_{name}.input2',9)
    for i in range(3):
        if name=='thumb' and i==0:
            continue
        cmds.connectAttr(f'mult_{side}_{name}.output',f'connect_{side}_{name}_00{i+1}.rotate.rotateY')


def All_fingers(side):
    
    cmds.file(config.ctrl_lib('all_fingers.mb'),i=True)
    cmds.rename('curve1',f'ctrl_{side}_fingers')
    if side == 'R':
        cmds.setAttr(f'ctrl_{side}_fingers.scaleX',-1)
        cmds.makeIdentity(f'ctrl_{side}_fingers',apply=True)
    cmds.group(empty=True,n=f'zero_{side}_fingers')
    cmds.parent(f'ctrl_{side}_fingers',f'zero_{side}_fingers')
    cmds.matchTransform(f'zero_{side}_fingers',f'jnt_{side}_wrist')
    scale = cmds.getAttr('world_scale.scaleX')
    config.scale_node(f'zero_{side}_fingers', scale)
    cmds.parentConstraint(f'jnt_{side}_wrist',f'zero_{side}_fingers')
    cmds.parent(f'zero_{side}_fingers','ctrl_world')

    fingers_attrs(side)

def footIK(side):
    cmds.select(clear=True)
    upperLeg_jnt = cmds.joint(n=f'jnt_{side}_upperLegIK')
    knee_jnt = cmds.joint(n=f'jnt_{side}_kneeIK')
    ankle_jnt = cmds.joint(n=f'jnt_{side}_ankleIK')
    ball_jnt = cmds.joint(n=f'jnt_{side}_ballIK')
    toe_jnt = cmds.joint(n=f'jnt_{side}_toeIK')

    cmds.matchTransform(upperLeg_jnt,f'jnt_{side}_upperLeg',position=True,rotation=True,scale=True)
    cmds.matchTransform(knee_jnt,f'jnt_{side}_knee',position=True,rotation=True,scale=True)
    cmds.matchTransform(ankle_jnt,f'jnt_{side}_ankle',position=True,rotation=True,scale=True)
    cmds.matchTransform(ball_jnt,f'jnt_{side}_ball',position=True,rotation=True,scale=True)
    cmds.matchTransform(toe_jnt,f'jnt_{side}_toe',position=True,rotation=True,scale=True)

    cmds.makeIdentity(f'jnt_{side}_upperLegIK',apply=True,translate=True, rotate=True, scale=True)


    LegIK = cmds.ikHandle(sj=f'jnt_{side}_upperLegIK',ee=f'jnt_{side}_ankleIK',sol='ikRPsolver',n=f'{side}_LegikHnd')
    BallIK = cmds.ikHandle(sj=f'jnt_{side}_ankleIK',ee=f'jnt_{side}_ballIK',sol='ikSCsolver',n=f'{side}_ballikHnd')
    ToeIK = cmds.ikHandle(sj=f'jnt_{side}_ballIK',ee=f'jnt_{side}_toeIK',sol='ikSCsolver',n=f'{side}_toeikHnd')
    cmds.hide(LegIK)
    cmds.hide(BallIK)
    cmds.hide(ToeIK)

    cmds.select(clear=True)
    ctrl = cmds.joint(n=f'ctrl_{side}_footIK')
    zero_ctrl = cmds.group(ctrl,n=f'zero_{side}_footIK')
    cmds.matchTransform(zero_ctrl,f'jnt_{side}_ankleIK',position=True)

    loc_up = cmds.spaceLocator(n=f'{side}_up')
    loc_down = cmds.spaceLocator(n=f'{side}_down')
    cmds.matchTransform(loc_up,f'jnt_{side}_ankleIK',position=True)
    up_t = cmds.xform(loc_up,q=True,t=True)
    cmds.xform(loc_up,t=[up_t[0],up_t[1]+5,up_t[2]])
    cmds.matchTransform(loc_down,f'jnt_{side}_toeIK',position=True)

    cmds.aimConstraint(loc_up,ctrl,aimVector=(0,1,0),upVector=(0,0,1),worldUpType='object',worldUpObject=f'{side}_down',maintainOffset=False)
    cmds.delete(f'ctrl_{side}_footIK_aimConstraint1')
    cmds.makeIdentity(ctrl,apply=True)
    cmds.delete(loc_up)
    cmds.delete(loc_down)

    cmds.file(config.ctrl_lib('footIK.mb'),i=True)
    cmds.rename('curve1',f'crv_{side}_footIK')
    cmds.parent(f'crv_{side}_footIKShape',f'ctrl_{side}_footIK',shape=True,add=True)
    cmds.delete(f'crv_{side}_footIK')
    scale = cmds.getAttr('world_scale.scaleX')
    config.scale_node(f'zero_{side}_footIK', scale)
    cmds.setAttr(f'ctrl_{side}_footIK.drawStyle',2)
    cmds.parent(f'zero_{side}_footIK','ctrl_world')

    cmds.file(config.ctrl_lib('PV.mb'),i=True)
    pv_ctrl = cmds.rename('curveControl1',f'ctrl_{side}_LegPV')
    pv_zero_ctrl = cmds.group(pv_ctrl,n=f'zero_{side}_LegPV')
    cmds.parent(pv_zero_ctrl,'ctrl_world')

    cmds.matchTransform(f'zero_{side}_LegPV',f'jnt_{side}_kneeIK')
    cmds.parent(f'zero_{side}_LegPV',f'jnt_{side}_kneeIK')
    if side == 'L':
        cmds.xform('zero_L_LegPV',t=[-0.5*scale,5*scale,0])
    if side == 'R':
        cmds.xform('zero_R_LegPV',t=[0.5*scale,-5*scale,0])
    cmds.parent(f'zero_{side}_LegPV',world=True)
    cmds.setAttr(f'zero_{side}_LegPV.rotateX',0)
    cmds.setAttr(f'zero_{side}_LegPV.rotateY',0)
    cmds.setAttr(f'zero_{side}_LegPV.rotateZ',0)
    cmds.poleVectorConstraint(f'ctrl_{side}_LegPV',f'{side}_LegikHnd')    
    config.scale_node(f'zero_{side}_LegPV', scale)
    cmds.parent(f'zero_{side}_LegPV','ctrl_world')

    cmds.annotate(f'ctrl_{side}_LegPV',tx=' ')
    cmds.rename('annotation1',f'{side}_Leg_annotation')
    cmds.pointConstraint(f'jnt_{side}_kneeIK',f'{side}_Leg_annotation')
    cmds.setAttr(f"{side}_Leg_annotationShape.overrideEnabled",1)
    cmds.setAttr(f"{side}_Leg_annotationShape.overrideDisplayType",2)

    if side =='R':
        cmds.group('L_Leg_annotation','R_Leg_annotation',n='grp_Leg_annotation')
        cmds.parent('grp_Leg_annotation','ctrl_world')

    cmds.addAttr(f'ctrl_{side}_footIK',longName='twist',attributeType='double',keyable=True)
    cmds.connectAttr(f'ctrl_{side}_footIK.twist',f'{side}_LegikHnd.twist')

    cmds.select(clear=True)
    Rvs_toeIK1 = cmds.joint(n=f'jntRvs_{side}_toeIK_001')
    cmds.matchTransform(Rvs_toeIK1,f'jnt_{side}_ballIK',pos=True)
    Rvs_toeIK2 = cmds.joint(n=f'jntRvs_{side}_toe_002')
    cmds.matchTransform(Rvs_toeIK2,f'jnt_{side}_toeIK',pos=True)
    cmds.joint(Rvs_toeIK1,e=True,oj='xyz',sao='yup',ch=True)
    cmds.select(clear=True)
    
    Rvs_ballIK1 = cmds.joint(n=f'jntRvs_{side}_ballIK_001')
    cmds.matchTransform(Rvs_ballIK1,f'jnt_{side}_ballIK',pos=True)
    Rvs_ballIK2 = cmds.joint(n=f'jntRvs_{side}_ballIK_002')
    cmds.matchTransform(Rvs_ballIK2,f'jnt_{side}_ankleIK',pos=True)
    cmds.joint(Rvs_ballIK1,e=True,oj='xyz',sao='yup',ch=True)
    cmds.select(clear=True)

    Rvs_OutIK = cmds.joint(n=f'jntRvs_{side}_OutIK')
    cmds.matchTransform(Rvs_OutIK,f'jnt_{side}_Out',pos=True)
    Rvs_InnIK = cmds.joint(n=f'jntRvs_{side}_InnIK')
    cmds.matchTransform(Rvs_InnIK,f'jnt_{side}_Inn',pos=True)
    cmds.joint(Rvs_OutIK,e=True,oj='xyz',sao='yup',ch=True)
    cmds.parent(Rvs_InnIK,world=True)
    cmds.parent(Rvs_OutIK,Rvs_InnIK)
    cmds.joint(Rvs_InnIK,e=True,oj='xyz',sao='yup',ch=True)
    cmds.parent(Rvs_OutIK,world=True)
    cmds.select(clear=True)

    Rvs_toeIK = cmds.joint(n=f'jntRvs_{side}_toeIK')
    cmds.matchTransform(Rvs_toeIK,f'jnt_{side}_toe',pos=True)
    cmds.setAttr(f'{Rvs_toeIK}.translateY',0)
    cmds.select(clear=True)

    Rvs_heelIK = cmds.joint(n=f'jntRvs_{side}_heelIK')
    cmds.matchTransform(Rvs_heelIK,f'jnt_{side}_heel',pos=True)
    cmds.parent(Rvs_heelIK,Rvs_toeIK)
    cmds.joint(Rvs_toeIK,e=True,oj='xyz',sao='yup',ch=True)
    cmds.parent(Rvs_heelIK,world=True)
    cmds.parent(Rvs_toeIK,Rvs_heelIK)
    cmds.joint(Rvs_heelIK,e=True,oj='xyz',sao='yup',ch=True)
    cmds.parent(Rvs_toeIK,world=True)

    cmds.parent(Rvs_toeIK1,Rvs_ballIK1,Rvs_InnIK)
    cmds.parent(Rvs_InnIK,Rvs_OutIK)
    cmds.parent(Rvs_OutIK,Rvs_toeIK)
    cmds.parent(Rvs_toeIK,Rvs_heelIK)

    cmds.file(config.ctrl_lib('foot_ball.mb'),i=True)
    cmds.rename('curve1',f'ctrl_{side}_ballIK')
    cmds.group(empty=True,n=f'zero_{side}_ballIK')
    cmds.parent(f'ctrl_{side}_ballIK',f'zero_{side}_ballIK')
    cmds.matchTransform(f'zero_{side}_ballIK',f'jntRvs_{side}_ballIK_001')
    config.scale_node(f'zero_{side}_ballIK', scale)

    cmds.file(config.ctrl_lib('foot_toe.mb'),i=True)
    cmds.rename('curve1',f'ctrl_{side}_toeIK')
    cmds.group(empty=True,n=f'zero_{side}_toeIK')

    cmds.parent(f'ctrl_{side}_toeIK',f'zero_{side}_toeIK')
    cmds.matchTransform(f'zero_{side}_toeIK',f'jntRvs_{side}_toeIK_001')
    config.scale_node(f'zero_{side}_toeIK', scale)

    rvs = ['heel','toe','Out','Inn']
    for i in rvs:
        cmds.file(config.ctrl_lib('foot_rvs.mb'),i=True)
        cmds.rename('curve1',f'ctrl_{side}_{i}')
        cmds.group(empty=True,n=f'zero_{side}_{i}')
        cmds.parent(f'ctrl_{side}_{i}',f'zero_{side}_{i}')
        cmds.matchTransform(f'zero_{side}_{i}',f'jntRvs_{side}_{i}IK')
        config.scale_node(f'zero_{side}_{i}', scale)

    cmds.parent(f'zero_{side}_ballIK',f'zero_{side}_toeIK',f'ctrl_{side}_Inn')
    cmds.parent(f'zero_{side}_Inn',f'ctrl_{side}_Out')
    cmds.parent(f'zero_{side}_Out',f'ctrl_{side}_toe')
    cmds.parent(f'zero_{side}_toe',f'ctrl_{side}_heel')

    cmds.parent(f'{side}_toeikHnd',f'ctrl_{side}_toeIK')
    cmds.parent(f'{side}_ballikHnd',f'ctrl_{side}_ballIK')
    cmds.parent(f'{side}_LegikHnd',f'ctrl_{side}_ballIK')

    cmds.delete(f'jntRvs_{side}_heelIK')
    cmds.delete(f'jnt_{side}_heel')
    cmds.delete(f'jnt_{side}_Out')
    cmds.delete(f'jnt_{side}_Inn')

    cmds.parent(f'zero_{side}_heel',f'ctrl_{side}_footIK')

    cmds.addAttr(f'ctrl_{side}_footIK',longName='toeTap',attributeType='float',keyable=True)
    cmds.addAttr(f'ctrl_{side}_footIK',longName='toeSlide',attributeType='float',keyable=True)
    cmds.addAttr(f'ctrl_{side}_footIK',longName='toeRoll',attributeType='float',keyable=True)
    cmds.addAttr(f'ctrl_{side}_footIK',longName='ballRoll',attributeType='float',keyable=True,min=0)
    cmds.addAttr(f'ctrl_{side}_footIK',longName='heelRoll',attributeType='float',keyable=True)
    cmds.addAttr(f'ctrl_{side}_footIK',longName='heelSlide',attributeType='float',keyable=True)
    cmds.addAttr(f'ctrl_{side}_footIK',longName='bank',attributeType='float',keyable=True)

    cmds.group(f'ctrl_{side}_toeIK',n=f'connect_{side}_toeIK')
    cmds.matchTransform(f'connect_{side}_toeIK',f'ctrl_{side}_toeIK',pivots=True)
    cmds.connectAttr(f'ctrl_{side}_footIK.toeTap',f'connect_{side}_toeIK.rotateZ')
    cmds.group(f'ctrl_{side}_ballIK',n=f'connect_{side}_ballIK')
    cmds.matchTransform(f'connect_{side}_ballIK',f'ctrl_{side}_ballIK',pivots=True)
    cmds.connectAttr(f'ctrl_{side}_footIK.ballRoll',f'connect_{side}_ballIK.rotateZ')
    cmds.group(f'ctrl_{side}_toe',n=f'connect_{side}_toe')
    cmds.matchTransform(f'connect_{side}_toe',f'ctrl_{side}_toe',pivots=True)
    cmds.connectAttr(f'ctrl_{side}_footIK.toeRoll',f'connect_{side}_toe.rotateZ')
    cmds.connectAttr(f'ctrl_{side}_footIK.toeSlide',f'connect_{side}_toe.rotateY')
    cmds.setAttr(f'connect_{side}_toe.rotateOrder',2)
    cmds.group(f'ctrl_{side}_heel',n=f'connect_{side}_heel')
    cmds.matchTransform(f'connect_{side}_heel',f'ctrl_{side}_heel',pivots=True)
    cmds.connectAttr(f'ctrl_{side}_footIK.heelRoll',f'connect_{side}_heel.rotateZ')
    cmds.connectAttr(f'ctrl_{side}_footIK.heelSlide',f'connect_{side}_heel.rotateY')
    cmds.setAttr(f'connect_{side}_heel.rotateOrder',2)

    cmds.group(f'ctrl_{side}_Out',n=f'connect_{side}_Out')
    cmds.matchTransform(f'connect_{side}_Out',f'ctrl_{side}_Out',pivots=True)
    cmds.group(f'ctrl_{side}_Inn',n=f'connect_{side}_Inn')
    cmds.matchTransform(f'connect_{side}_Inn',f'ctrl_{side}_Inn',pivots=True)

    cmds.createNode('multDoubleLinear',n=f'muly_{side}_footInn')
    cmds.connectAttr(f'ctrl_{side}_footIK.bank',f'muly_{side}_footInn.input1')
    cmds.setAttr(f'muly_{side}_footInn.input2',-1)
    cmds.connectAttr(f'muly_{side}_footInn.output',f'connect_{side}_Inn.rotateZ')
    cmds.connectAttr(f'ctrl_{side}_footIK.bank',f'connect_{side}_Out.rotateZ')

    cmds.transformLimits(f'connect_{side}_Out',erz=(1,0),rz=(0,45))
    cmds.transformLimits(f'connect_{side}_Inn',erz=(1,0),rz=(0,45))


    locator = cmds.spaceLocator(n=f'{side}_IKToFK')
    cmds.matchTransform(locator,f'jnt_{side}_ankleFK',pos=True)
    cmds.parent(locator,f'jnt_{side}_ankleFK')

    loc_up = cmds.spaceLocator(n=f'{side}_up')
    loc_down = cmds.spaceLocator(n=f'{side}_down')
    cmds.matchTransform(loc_up,f'jnt_{side}_ankleFK',position=True)
    up_t = cmds.xform(loc_up,q=True,t=True)
    cmds.xform(loc_up,t=[up_t[0],up_t[1]+5,up_t[2]])
    cmds.matchTransform(loc_down,f'jnt_{side}_toeFK',position=True)
    cmds.aimConstraint(loc_up,locator,aimVector=(0,1,0),upVector=(0,0,1),worldUpType='object',worldUpObject=f'{side}_down',maintainOffset=False)
    cmds.delete(f'{side}_IKToFK_aimConstraint1')

    cmds.delete(loc_up)
    cmds.delete(loc_down)


def leg_ikfkBlend(side):
    cmds.file(config.ctrl_lib('cross.mb'),i=True)
    cmds.rename('curve1',f'ctrl_{side}_legIKFKBlend')
    cmds.group(f'ctrl_{side}_legIKFKBlend',n=f'zero_{side}_legIKFKBlend')
    t = cmds.xform(f'jnt_{side}_upperLeg',q=True,ws=True,t=True)
    addBlendAttr(side,'legIKFKBlend')
    scale = cmds.getAttr('world_scale.scaleX')
    config.scale_node(f'zero_{side}_legIKFKBlend', scale)
    if side == 'L':
        cmds.xform(f'zero_{side}_legIKFKBlend',t=[t[0]+3*scale,t[1]-3*scale,t[2]])
    if side == 'R':
        cmds.xform(f'zero_{side}_legIKFKBlend',t=[t[0]-3*scale,t[1]-3*scale,t[2]])
    cmds.parent(f'zero_{side}_legIKFKBlend','ctrl_world')

    rev_node = cmds.createNode('reverse',n=f'{side}_legIKrev')
    cmds.connectAttr(f'ctrl_{side}_legIKFKBlend.ikfkBlend',f'{rev_node}.inputX')

    for i in leg:
        cmds.parentConstraint(f'jnt_{side}_{i}FK',f'jnt_{side}_{i}IK',f'jnt_{side}_{i}')

        cmds.connectAttr(f'ctrl_{side}_legIKFKBlend.ikfkBlend',f'jnt_{side}_{i}_parentConstraint1.jnt_{side}_{i}FKW0')
        cmds.connectAttr(f'{rev_node}.outputX',f'jnt_{side}_{i}_parentConstraint1.jnt_{side}_{i}IKW1')

    cmds.connectAttr(f'{rev_node}.outputX',f'zero_{side}_footIK.visibility')
    cmds.connectAttr(f'{rev_node}.outputX',f'zero_{side}_LegPV.visibility')
    cmds.connectAttr(f'{rev_node}.outputX',f'{side}_Leg_annotation.visibility')

    cmds.connectAttr(f'ctrl_{side}_legIKFKBlend.ikfkBlend',f'zero_{side}_upperLegFK.visibility')

    cmds.hide(f'jnt_{side}_upperLegFK')
    cmds.hide(f'jnt_{side}_upperLegIK')

    cmds.parent(f'jnt_{side}_upperLegIK','ctrl_world')

    

def spine():
    
    cmds.file(config.ctrl_lib('cog.mb'),i=True)
    cmds.rename('curve',f'ctrl_C_cog')
    cmds.group(f'ctrl_C_cog',n='zero_C_cog')
    cmds.matchTransform('zero_C_cog','jnt_C_spine_001',pos=True)

    scale = cmds.getAttr('world_scale.scaleX')
    config.scale_node('zero_C_cog', scale)
    cmds.parent('zero_C_cog','ctrl_world')
    cmds.makeIdentity('zero_C_cog',apply=True,scale=True)

    spines = cmds.ls('*spine_*')
    spine_num = len(spines)

    points = []
    for i in range(spine_num):
        points.append(cmds.xform(f'jnt_C_spine_00{i+1}',q=True,ws=True,t=True))
    curve = cmds.curve(p=points)
    cmds.rename(curve,'crv_C_spine')

    cmds.ikHandle(sj='jnt_C_spine_001',ee=f'jnt_C_spine_{spine_num:03}',sol='ikSplineSolver',n='SpineikHnd',curve='crv_C_spine',
                  createCurve=False,parentCurve=False)

    cmds.select(clear=True)
    spine1 = cmds.joint(n='jnt_C_spineIK_001')
    cmds.select(clear=True)
    spine2 = cmds.joint(n='jnt_C_spineIK_002')
    cmds.select(clear=True)
    spine3 = cmds.joint(n='jnt_C_spineIK_003',r=False)
    cmds.matchTransform(spine1,'jnt_C_spine_001',pos=True)
    cmds.matchTransform(spine3,f'jnt_C_spine_{spine_num:03}',pos=True)

    if spine_num%2 == 0:
        spine_C1 = cmds.xform(f'jnt_C_spine_{spine_num//2:03}',q=True,t=True,ws=True)
        spine_C2 = cmds.xform(f'jnt_C_spine_{spine_num//2+1:03}',q=True,t=True,ws=True)
        cmds.xform(spine2,t=[(spine_C1[0]+spine_C2[0])/2,(spine_C1[1]+spine_C2[1])/2,(spine_C1[2]+spine_C2[2])/2],ws=True)

    else:
        cmds.matchTransform(spine2,f'jnt_C_spine_{spine_num//2+1:03}',pos=True)

    for i in range(3):
        cmds.file(config.ctrl_lib(f'circle{i+1}.mb'),i=True)
        ctrlFK = cmds.rename('nurbsCircle1',f'ctrl_C_spineFK_00{i+1}')
        cmds.setAttr(f'{ctrlFK}.scaleX',3)
        cmds.setAttr(f'{ctrlFK}.scaleY',3)
        cmds.setAttr(f'{ctrlFK}.scaleZ',3)
        cmds.makeIdentity(ctrlFK,apply=True)
        zero_ctrlFK = cmds.group(n=f'zero_C_spineFK_00{i+1}',empty=True)
        cmds.parent(ctrlFK,zero_ctrlFK)
        
        cmds.file(config.ctrl_lib(f'spineIK{i+1}.mb'),i=True)
        ctrlIK = cmds.rename('curve1',f'ctrl_C_spineIK_00{i+1}')
        zero_ctrlIK = cmds.group(ctrlIK,n=f'zero_C_spineIK_00{i+1}')

        cmds.parent(zero_ctrlIK,f'ctrl_C_spineFK_00{i+1}')

        cmds.matchTransform(zero_ctrlFK,f'jnt_C_spineIK_00{i+1}')

        if i != 0:
            cmds.parent(zero_ctrlFK,f'ctrl_C_spineFK_00{i}')

        scale = cmds.getAttr('world_scale.scaleX')
        config.scale_node(f'zero_C_spineFK_00{i+1}', scale)
        cmds.makeIdentity(f'zero_C_spineFK_00{i+1}',apply=True,scale=True)


    cmds.parent('zero_C_spineFK_001','ctrl_C_cog')

    cmds.skinCluster(['jnt_C_spineIK_001','jnt_C_spineIK_002','jnt_C_spineIK_003'],'crv_C_spine',toSelectedBones=True)
    for i in range(3):
        cmds.parent(f'jnt_C_spineIK_00{i+1}',f'ctrl_C_spineIK_00{i+1}')

    cmds.setAttr('SpineikHnd.dTwistControlEnable',1)
    cmds.setAttr('SpineikHnd.dWorldUpType',4)
    cmds.setAttr('SpineikHnd.dWorldUpVectorZ',-1)
    cmds.setAttr('SpineikHnd.dWorldUpVectorEndZ',-1)
    cmds.setAttr('SpineikHnd.dWorldUpVectorY',0)
    cmds.setAttr('SpineikHnd.dWorldUpVectorEndY',0)
    cmds.connectAttr("jnt_C_spineIK_001.worldMatrix[0]","SpineikHnd.dWorldUpMatrix")
    cmds.connectAttr("jnt_C_spineIK_003.worldMatrix[0]","SpineikHnd.dWorldUpMatrixEnd")

    cmds.createNode('curveInfo',n='crv_C_spineInfo')
    cmds.connectAttr('crv_C_spineShape.worldSpace[0]','crv_C_spineInfo.inputCurve')
    cmds.createNode('multiplyDivide',n='mult_C_spineIK')
    cmds.setAttr('mult_C_spineIK.operation',2)
    cmds.connectAttr('crv_C_spineInfo.arcLength','mult_C_spineIK.input1.input1X')
    cmds.connectAttr('ctrl_world.scaleY','mult_C_spineIK.input2.input2X')

    cmds.createNode('addDoubleLinear',n='add_C_spineIK1')
    cmds.connectAttr('mult_C_spineIK.output.outputX','add_C_spineIK1.input1')
    ArcLength = cmds.getAttr('crv_C_spineInfo.arcLength')
    cmds.setAttr('add_C_spineIK1.input2',-ArcLength)


    cmds.createNode('multDoubleLinear',n='muly_C_spineIK')
    add =1/(spine_num-1)
    cmds.setAttr('muly_C_spineIK.input2',add)
    cmds.connectAttr('add_C_spineIK1.output','muly_C_spineIK.input1')
    cmds.createNode('addDoubleLinear',n='add_C_spineIK2')
    tx = cmds.getAttr('jnt_C_spine_002.translateX')
    cmds.setAttr('add_C_spineIK2.input2',tx)
    cmds.connectAttr('muly_C_spineIK.output','add_C_spineIK2.input1')

    for i in spines[1:]:
        cmds.connectAttr('add_C_spineIK2.output',f'{i}.translateX')

    cmds.createNode('blendColors',n='blend_C_spine')
    cmds.connectAttr('ctrl_C_spineIK_001.translate','blend_C_spine.color1')
    cmds.connectAttr('ctrl_C_spineIK_003.translate','blend_C_spine.color2')
    cmds.connectAttr('blend_C_spine.output','zero_C_spineIK_002.translate')

    cmds.orientConstraint('ctrl_C_spineIK_003',f'jnt_C_spine_{spine_num:03}',maintainOffset=True)
    cmds.orientConstraint('ctrl_C_spineIK_001','jnt_C_spine_001',maintainOffset=True)

    cmds.joint(n='jnt_C_pelvisLocal')
    cmds.matchTransform('jnt_C_pelvisLocal','jnt_C_spine_001',pos=True)
    cmds.parent('jnt_C_pelvisLocal','jnt_C_spine_001')
    cmds.parent('jnt_L_upperLeg','jnt_C_pelvisLocal')
    cmds.parent('jnt_R_upperLeg','jnt_C_pelvisLocal')
    cmds.file(config.ctrl_lib('pelvisLocal.mb'),i=True)
    cmds.rename('curve1','ctrl_C_pelvisLocal')
    cmds.group('ctrl_C_pelvisLocal',n='zero_C_pelvisLocal')
    cmds.matchTransform('zero_C_pelvisLocal','jnt_C_pelvisLocal')
    config.scale_node(f'zero_C_pelvisLocal', scale)
    cmds.setAttr('zero_C_pelvisLocal.translateX',-5*scale)
    cmds.orientConstraint('ctrl_C_pelvisLocal','jnt_C_pelvisLocal',maintainOffset=True)
    cmds.parent('zero_C_pelvisLocal','ctrl_C_spineIK_001')


    cmds.parentConstraint('jnt_C_pelvisLocal','zero_L_upperLegFK',maintainOffset=True)
    cmds.parentConstraint('jnt_C_pelvisLocal','zero_R_upperLegFK',maintainOffset=True)
    cmds.parentConstraint('jnt_C_pelvisLocal','jnt_R_upperLegIK',maintainOffset=True)
    cmds.parentConstraint('jnt_C_pelvisLocal','jnt_L_upperLegIK',maintainOffset=True)
    cmds.parent('zero_L_shoulder','ctrl_C_spineIK_003')
    cmds.parent('zero_R_shoulder','ctrl_C_spineIK_003')

    cmds.parent('zero_R_legIKFKBlend','ctrl_C_cog')
    cmds.parent('zero_L_legIKFKBlend','ctrl_C_cog')
    cmds.parent('zero_L_armIKFKBlend','ctrl_C_cog')
    cmds.parent('zero_R_armIKFKBlend','ctrl_C_cog')

    cmds.hide('jnt_C_spineIK_003')
    cmds.hide('jnt_C_spineIK_002')
    cmds.hide('jnt_C_spineIK_001')
    cmds.hide('SpineikHnd')
    cmds.hide('crv_C_spine')


def head():
    cmds.file(config.ctrl_lib('circle.mb'),i=True)
    cmds.rename('nurbsCircle1','ctrl_C_neck_001')
    cmds.group('ctrl_C_neck_001',n='zero_C_neck_001')
    cmds.matchTransform('zero_C_neck_001','jnt_C_neck_001')
    cmds.setAttr('ctrl_C_neck_001.rotateZ',90)
    cmds.makeIdentity('ctrl_C_neck_001',apply=True)
    cmds.parentConstraint('ctrl_C_neck_001','jnt_C_neck_001')

    cmds.file(config.ctrl_lib('head.mb'),i=True)
    cmds.rename('nurbsCircle1','ctrl_C_head')    
    cmds.group(n='zero_C_head',empty=True)
    cmds.parent('ctrl_C_head','zero_C_head')
    cmds.matchTransform('zero_C_head','jnt_C_headEnd')
    cmds.setAttr('ctrl_C_head.rotateZ',90)
    cmds.makeIdentity('ctrl_C_head',apply=True)
    jnt_headPivot = cmds.xform('ctrl_C_head',q=True,ws=True,rotatePivot=True)
    jnt_headPos = cmds.xform('jnt_C_head',q=True,ws=True,t=True)
    cmds.xform('ctrl_C_head',ws=True,rotatePivot=jnt_headPos)
    cmds.parentConstraint('ctrl_C_head','jnt_C_head',maintainOffset=True)    

    scale = cmds.getAttr('world_scale.scaleX')
    config.scale_node('zero_C_neck_001', scale)

    config.scale_node('zero_C_head', scale)

    cmds.parent('zero_C_neck_001','ctrl_world')
    cmds.parent('zero_C_head','ctrl_world')

    cmds.parent('zero_C_neck_001','ctrl_C_spineIK_003')
    cmds.parent('zero_C_head','ctrl_C_neck_001')
    
