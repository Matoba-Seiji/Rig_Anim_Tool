from maya import cmds

from rig_anim_tool.rig import config

def Twist(name,side):
    cmds.joint(n=f'jnt_{side}_{name}TwistDriven_001')
    cmds.select(clear=True)
    cmds.joint(n=f'jnt_{side}_{name}TwistDriven_002')

    cmds.matchTransform(f'jnt_{side}_{name}TwistDriven_001',f'jnt_{side}_{name}')
    cmds.matchTransform(f'jnt_{side}_{name}TwistDriven_002',cmds.listRelatives(f'jnt_{side}_{name}',children=True)[0],pos=True)
    cmds.makeIdentity(f'jnt_{side}_{name}TwistDriven_001',apply=True)
    cmds.makeIdentity(f'jnt_{side}_{name}TwistDriven_002',apply=True)
    cmds.parent(f'jnt_{side}_{name}TwistDriven_002',f'jnt_{side}_{name}TwistDriven_001')
    cmds.parent(f'jnt_{side}_{name}TwistDriven_001',f'jnt_{side}_{name}')

    cmds.ikHandle(sj=f'jnt_{side}_{name}TwistDriven_001',ee=f'jnt_{side}_{name}TwistDriven_002',sol='ikSCsolver',n=f'{side}_{name}twistikHnd')
    
    if name == 'upperArm' or name == 'upperLeg':
        cmds.pointConstraint(cmds.listRelatives(f'jnt_{side}_{name}',children=True)[0],f'{side}_{name}twistikHnd')
        cmds.parent(f'{side}_{name}twistikHnd','twist')
    else:
        cmds.parent(f'{side}_{name}twistikHnd','twist')

    cmds.hide(f'{side}_{name}twistikHnd')

    cmds.joint(n=f'jnt_{side}_{name}Twist_001')
    cmds.select(clear=True)
    cmds.joint(n=f'jnt_{side}_{name}Twist_002')
    cmds.select(clear=True)
    cmds.joint(n=f'jnt_{side}_{name}Twist_003')

    cmds.matchTransform(f'jnt_{side}_{name}Twist_001',f'jnt_{side}_{name}')
    cmds.matchTransform(f'jnt_{side}_{name}Twist_002',f'jnt_{side}_{name}')
    cmds.matchTransform(f'jnt_{side}_{name}Twist_003',f'jnt_{side}_{name}')

    cmds.makeIdentity(f'jnt_{side}_{name}Twist_001',apply=True)
    cmds.makeIdentity(f'jnt_{side}_{name}Twist_002',apply=True)
    cmds.makeIdentity(f'jnt_{side}_{name}Twist_003',apply=True)

    cmds.matchTransform(f'jnt_{side}_{name}Twist_003',cmds.listRelatives(f'jnt_{side}_{name}',children=True)[0],pos=True)
    pointConstraint = cmds.pointConstraint(f'jnt_{side}_{name}Twist_001',f'jnt_{side}_{name}Twist_003',f'jnt_{side}_{name}Twist_002')
    cmds.delete(pointConstraint)

    cmds.parent(f'jnt_{side}_{name}Twist_001',f'jnt_{side}_{name}')
    cmds.parent(f'jnt_{side}_{name}Twist_002',f'jnt_{side}_{name}')
    cmds.parent(f'jnt_{side}_{name}Twist_003',f'jnt_{side}_{name}')

    if name == 'upperArm' or name == 'upperLeg':
        cmds.connectAttr(f'jnt_{side}_{name}TwistDriven_001.rotate.rotateX',f'jnt_{side}_{name}Twist_001.rotate.rotateX')
        cmds.createNode('multDoubleLinear',n=f'mult_{side}_{name}Twist_001')
        cmds.connectAttr(f'jnt_{side}_{name}TwistDriven_001.rotate.rotateX',f'mult_{side}_{name}Twist_001.input1')
        cmds.connectAttr(f'mult_{side}_{name}Twist_001.output',f'jnt_{side}_{name}Twist_002.rotate.rotateX')
        cmds.setAttr(f'mult_{side}_{name}Twist_001.input2',0.5)

    else:
        cmds.connectAttr(f'jnt_{side}_{name}TwistDriven_001.rotate.rotateX',f'jnt_{side}_{name}Twist_003.rotate.rotateX')
        cmds.createNode('multDoubleLinear',n=f'mult_{side}_{name}Twist_001')
        cmds.connectAttr(f'jnt_{side}_{name}TwistDriven_001.rotate.rotateX',f'mult_{side}_{name}Twist_001.input1')
        cmds.connectAttr(f'mult_{side}_{name}Twist_001.output',f'jnt_{side}_{name}Twist_002.rotate.rotateX')
        cmds.setAttr(f'mult_{side}_{name}Twist_001.input2',0.5)

    cmds.hide('*Driven*')
    if name =='upperArm':
        cmds.pointConstraint(f'jnt_{side}_elbow',f'jnt_{side}_{name}Twist_003',mo=True)
        cmds.pointConstraint(f'jnt_{side}_upperArm',f'jnt_{side}_elbow',f'jnt_{side}_{name}Twist_002',mo=True)
    elif name =='elbow':
        cmds.pointConstraint(f'jnt_{side}_wrist',f'jnt_{side}_{name}Twist_003',mo=True)
        cmds.pointConstraint(f'jnt_{side}_elbow',f'jnt_{side}_wrist',f'jnt_{side}_{name}Twist_002',mo=True)
    elif name == 'upperLeg':
        cmds.pointConstraint(f'jnt_{side}_knee',f'jnt_{side}_{name}Twist_003',mo=True)
        cmds.pointConstraint(f'jnt_{side}_upperLeg',f'jnt_{side}_knee',f'jnt_{side}_{name}Twist_002',mo=True)
    elif name == 'knee':
        cmds.pointConstraint(f'jnt_{side}_ankle',f'jnt_{side}_{name}Twist_003',mo=True)
        cmds.pointConstraint(f'jnt_{side}_knee',f'jnt_{side}_ankle',f'jnt_{side}_{name}Twist_002',mo=True)


    for i in range(1,4):
        if side =='L':
            cmds.setAttr(f'jnt_{side}_{name}Twist_00{i}.side',1)
        else:
            cmds.setAttr(f'jnt_{side}_{name}Twist_00{i}.side',2)
        cmds.setAttr(f'jnt_{side}_{name}Twist_00{i}.type',18)
        cmds.setAttr(f'jnt_{side}_{name}Twist_00{i}.otherType',f'{name}{i}',type='string')


def Stretch(side,part):
    if part =='arm':
        up_name = 'upperArm'
        middle_name = 'elbow'
        down_name = 'wrist'
        ctrl_name = 'hand'
        stretch_list = ['upperArm','elbow','wrist']
    elif part =='leg':
        up_name = 'upperLeg'
        middle_name = 'knee'
        down_name = 'ankle'
        ctrl_name = 'foot'
        stretch_list = ['upperLeg','knee','ankle']

    up_loc = cmds.spaceLocator(n=f'loc_{side}_{up_name}IKPos')
    down_loc = cmds.spaceLocator(n=f'loc_{side}_{ctrl_name}IKPos')
    cmds.hide(up_loc,down_loc)
    cmds.matchTransform(up_loc,f'jnt_{side}_{up_name}',pos=True)
    cmds.matchTransform(down_loc,f'ctrl_{side}_{ctrl_name}IK',pos=True)
    cmds.pointConstraint(f'jnt_{side}_{up_name}IK',up_loc,)
    cmds.parent(down_loc,f'ctrl_{side}_{ctrl_name}IK')

    cmds.createNode('distanceBetween',n=f'dis_{side}_{part}StretchIK')
    cmds.connectAttr(f'loc_{side}_{up_name}IKPosShape.worldPosition[0]',f'dis_{side}_{part}StretchIK.point1')
    cmds.connectAttr(f'loc_{side}_{ctrl_name}IKPosShape.worldPosition[0]',f'dis_{side}_{part}StretchIK.point2')

    cmds.createNode('addDoubleLinear',n=f'add_{side}_{part}StretchIKLength')
    length1 = cmds.xform(f'jnt_{side}_{middle_name}IK',q=True,t=True)[0]
    length2 = cmds.xform(f'jnt_{side}_{down_name}IK',q=True,t=True)[0]
    length = length1+length2
    if side == "L":
        cmds.setAttr(f'add_{side}_{part}StretchIKLength.input2',-length)
    else:
        cmds.setAttr(f'add_{side}_{part}StretchIKLength.input2',length)
    
    cmds.createNode('condition',n=f'cond_{side}_{part}StretchIK')
    cmds.connectAttr(f'add_{side}_{part}StretchIKLength.output',f'cond_{side}_{part}StretchIK.firstTerm')
    cmds.setAttr(f"cond_{side}_{part}StretchIK.operation",2)
    cmds.setAttr(f"cond_{side}_{part}StretchIK.colorIfFalseR",length1)
    cmds.setAttr(f"cond_{side}_{part}StretchIK.colorIfFalseG",length2)

    cmds.createNode('addDoubleLinear',n=f'add_{side}_{part}StretchIK')
    cmds.createNode('multDoubleLinear',n=f'mult_{side}_{part}StretchIKLength')
    cmds.connectAttr(f'add_{side}_{part}StretchIKLength.output',f'mult_{side}_{part}StretchIKLength.input1')
    cmds.setAttr(f'mult_{side}_{part}StretchIKLength.input2',0.5)
    cmds.setAttr(f'add_{side}_{part}StretchIK.input2',length1)
    cmds.createNode('addDoubleLinear',n=f'add_{side}_{down_name}StretchIK')
    cmds.setAttr(f'add_{side}_{down_name}StretchIK.input2',length2)
    if side == 'L':
        cmds.connectAttr(f'mult_{side}_{part}StretchIKLength.output',f'add_{side}_{part}StretchIK.input1')
        cmds.connectAttr(f'mult_{side}_{part}StretchIKLength.output',f'add_{side}_{down_name}StretchIK.input1')
    else:
        cmds.createNode('multDoubleLinear',n=f'mult_R_{part}reverse')
        cmds.connectAttr(f'mult_{side}_{part}StretchIKLength.output',f'mult_R_{part}reverse.input1')
        cmds.setAttr(f'mult_R_{part}reverse.input2',-1)
        cmds.connectAttr(f'mult_R_{part}reverse.output',f'add_{side}_{part}StretchIK.input1')
        cmds.connectAttr(f'mult_R_{part}reverse.output',f'add_{side}_{down_name}StretchIK.input1')
    cmds.connectAttr(f'add_{side}_{part}StretchIK.output',f'cond_{side}_{part}StretchIK.colorIfTrueR')
    cmds.connectAttr(f'add_{side}_{down_name}StretchIK.output',f'cond_{side}_{part}StretchIK.colorIfTrueG')

    cmds.addAttr(f'ctrl_{side}_{ctrl_name}IK.',longName='stretch',attributeType='double',keyable=True,min=0,max=1)    
    cmds.createNode('blendColors',n=f'blend_{side}_{part}StretchIK')
    cmds.connectAttr(f'ctrl_{side}_{ctrl_name}IK.stretch',f'blend_{side}_{part}StretchIK.blender')
    cmds.setAttr(f'blend_{side}_{part}StretchIK.color2R',length1)
    cmds.setAttr(f'blend_{side}_{part}StretchIK.color2G',length2)
    cmds.connectAttr(f'cond_{side}_{part}StretchIK.outColor.outColorR',f'blend_{side}_{part}StretchIK.color1R')
    cmds.connectAttr(f'cond_{side}_{part}StretchIK.outColor.outColorG',f'blend_{side}_{part}StretchIK.color1G')
    cmds.connectAttr(f'blend_{side}_{part}StretchIK.outputR',f'jnt_{side}_{middle_name}IK.translate.translateX')
    cmds.connectAttr(f'blend_{side}_{part}StretchIK.outputG',f'jnt_{side}_{down_name}IK.translate.translateX')
    cmds.createNode('multiplyDivide',n=f'div_{side}_{part}StretchIKLength')
    cmds.connectAttr(f'dis_{side}_{part}StretchIK.distance',f'div_{side}_{part}StretchIKLength.input1X')
    cmds.connectAttr('ctrl_world.scaleX',f'div_{side}_{part}StretchIKLength.input2X')
    cmds.setAttr(f'div_{side}_{part}StretchIKLength.operation',2)
    cmds.connectAttr(f'div_{side}_{part}StretchIKLength.outputX',f'add_{side}_{part}StretchIKLength.input1')
    
    for i in stretch_list:
        cmds.createNode('blendColors',n=f'blend_{side}_{i}IKFKBlend')
        cmds.connectAttr(f'ctrl_{side}_{part}IKFKBlend.ikfkBlend',f'blend_{side}_{i}IKFKBlend.blender')
        cmds.connectAttr(f'jnt_{side}_{i}IK.translate',f'blend_{side}_{i}IKFKBlend.color1')
        cmds.connectAttr(f'jnt_{side}_{i}FK.translate',f'blend_{side}_{i}IKFKBlend.color2')
        cmds.connectAttr(f'blend_{side}_{i}IKFKBlend.output',f'jnt_{side}_{i}.translate')

def SpaceSwitch(side):

    cmds.addAttr(f'ctrl_{side}_handIK',longName='space',attributeType='enum',keyable=True,enumName='World:Cog:Chest:Head:Pelvis')
    cmds.group(f'ctrl_{side}_handIK',n=f'space_{side}_handIK')

    spaceList = ['World','Cog','Chest','Head','Pelvis']

    for i in spaceList:
        loc = cmds.spaceLocator(n=f'loc_{side}_handIKSpace{i}')
        cmds.matchTransform(loc,f'space_{side}_handIK')
        cmds.parentConstraint(loc,f'space_{side}_handIK',mo=False)
        cmds.setAttr(f'space_{side}_handIK_parentConstraint1.interpType',2)

        cmds.createNode('condition',n=f'cond_{side}_handIKSpace{i}')
        cmds.connectAttr(f'ctrl_{side}_handIK.space',f'cond_{side}_handIKSpace{i}.firstTerm')
        cmds.setAttr(f'cond_{side}_handIKSpace{i}.colorIfTrueR',1)
        cmds.setAttr(f'cond_{side}_handIKSpace{i}.colorIfFalseR',0)
        cmds.connectAttr(f'cond_{side}_handIKSpace{i}.outColor.outColorR',f'space_{side}_handIK_parentConstraint1.loc_{side}_handIKSpace{i}W{spaceList.index(i)}')

        cmds.setAttr(f'cond_{side}_handIKSpace{i}.secondTerm',spaceList.index(i))

def Scale(side,part):
    if part == 'arm':
        FK_name = 'wrist'
        IK_name = 'hand'
    elif part == 'leg':
        FK_name = 'ankle'
        IK_name = 'foot'

    cmds.addAttr(f'ctrl_{side}_{FK_name}FK',longName='size',attributeType='double',keyable=True,min=0,defaultValue=1)
    cmds.connectAttr(f'ctrl_{side}_{FK_name}FK.size',f'jnt_{side}_{FK_name}FK.scaleX')
    cmds.connectAttr(f'ctrl_{side}_{FK_name}FK.size',f'jnt_{side}_{FK_name}FK.scaleY')
    cmds.connectAttr(f'ctrl_{side}_{FK_name}FK.size',f'jnt_{side}_{FK_name}FK.scaleZ')

    cmds.connectAttr(f'ctrl_{side}_{FK_name}FK.size',f'ctrl_{side}_{FK_name}FK.scaleX')
    cmds.connectAttr(f'ctrl_{side}_{FK_name}FK.size',f'ctrl_{side}_{FK_name}FK.scaleY')
    cmds.connectAttr(f'ctrl_{side}_{FK_name}FK.size',f'ctrl_{side}_{FK_name}FK.scaleZ')
    if part == 'arm':
        cmds.disconnectAttr(f'jnt_{side}_wrist.scale',f'jnt_{side}_pinky_001.inverseScale')
        cmds.disconnectAttr(f'jnt_{side}_wrist.scale',f'jnt_{side}_ring_001.inverseScale')
        cmds.disconnectAttr(f'jnt_{side}_wrist.scale',f'jnt_{side}_middle_001.inverseScale')
        cmds.disconnectAttr(f'jnt_{side}_wrist.scale',f'jnt_{side}_index_001.inverseScale')
        cmds.disconnectAttr(f'jnt_{side}_wrist.scale',f'jnt_{side}_thumb_001.inverseScale')
    elif part == 'leg':
        cmds.disconnectAttr(f'jnt_{side}_ankleFK.scale',f'jnt_{side}_ballFK.inverseScale')
        cmds.disconnectAttr(f'jnt_{side}_ankleIK.scale',f'jnt_{side}_ballIK.inverseScale')
        cmds.disconnectAttr(f'jnt_{side}_ankle.scale',f'jnt_{side}_ball.inverseScale')


    cmds.addAttr(f'ctrl_{side}_{IK_name}IK',longName='size',attributeType='double',keyable=True,min=0,defaultValue=1)
    cmds.connectAttr(f'ctrl_{side}_{IK_name}IK.size',f'jnt_{side}_{FK_name}IK.scaleX')
    cmds.connectAttr(f'ctrl_{side}_{IK_name}IK.size',f'jnt_{side}_{FK_name}IK.scaleY')
    cmds.connectAttr(f'ctrl_{side}_{IK_name}IK.size',f'jnt_{side}_{FK_name}IK.scaleZ')

    cmds.connectAttr(f'ctrl_{side}_{IK_name}IK.size',f'ctrl_{side}_{IK_name}IK.scaleX')
    cmds.connectAttr(f'ctrl_{side}_{IK_name}IK.size',f'ctrl_{side}_{IK_name}IK.scaleY')
    cmds.connectAttr(f'ctrl_{side}_{IK_name}IK.size',f'ctrl_{side}_{IK_name}IK.scaleZ')

    cmds.createNode('blendColors',n=f'blend_{side}_{IK_name}Scale')
    cmds.connectAttr(f'ctrl_{side}_{part}IKFKBlend.ikfkBlend',f'blend_{side}_{IK_name}Scale.blender')
    if part == 'arm':
        cmds.connectAttr(f'jnt_{side}_{FK_name}IK.scale',f'blend_{side}_{IK_name}Scale.color1')
        cmds.connectAttr(f'jnt_{side}_{FK_name}FK.scale',f'blend_{side}_{IK_name}Scale.color2')
    elif part =='leg':
        cmds.connectAttr(f'jnt_{side}_{FK_name}IK.scale',f'blend_{side}_{IK_name}Scale.color2')
        cmds.connectAttr(f'jnt_{side}_{FK_name}FK.scale',f'blend_{side}_{IK_name}Scale.color1')
    cmds.connectAttr(f'blend_{side}_{IK_name}Scale.output',f'jnt_{side}_{FK_name}.scale')
    if part == 'leg':
        cmds.scaleConstraint(f'jnt_{side}_wrist',f'grp_{side}_fingerFK')
        cmds.scaleConstraint(f'jnt_{side}_wrist',f'zero_{side}_fingers')

    config.lock_attrs(f'ctrl_{side}_{IK_name}IK', ['scaleX','scaleY','scaleZ'])
    config.lock_attrs(f'ctrl_{side}_{FK_name}FK', ['scaleX','scaleY','scaleZ'])
