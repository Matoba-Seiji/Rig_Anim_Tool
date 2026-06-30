from maya import cmds
import maya.mel as mel
import importlib

from rig_anim_tool.rig import joints as joins_operate
from rig_anim_tool.core.undo import make_undo

importlib.reload(joins_operate)

@make_undo
def zero_jnt_orient():
    jnts = cmds.ls(selection=True)
    for jnt in jnts:
        children = cmds.listRelatives(jnt,allDescendents=True)
        joins_operate.joint_zero(children[0])

@make_undo
def Chain_FK():
    jnts = cmds.ls(selection=True)
    cmds.select(cl=True)
    for jnt in jnts:
        children = cmds.listRelatives(jnt,allDescendents=True)
        children.append(jnt)
        children = list(reversed(children))

        for i in range(len(children)):
            if i == len(children)-1:
                break
            else:
                circle = cmds.circle(n=f'{children[i]}FK',normal=[1, 0, 0])
                zero = cmds.createNode('transform',n=f'zero_{children[i]}FK')
                cmds.parent(circle[0],zero)
                cmds.matchTransform(zero,children[i])

                if i != 0:
                    cmds.parent(zero,f'{children[i-1]}FK')
                cmds.select(cl=True)

                cmds.parentConstraint(circle[0],children[i])

@make_undo
def Vertical_axis(axis):
    if axis == 'Y':
        axis_vector = (0,-1,0)
    elif axis == 'Z':
        axis_vector = (0,0,-1)
    Y_jnt = cmds.ls(selection=True)[0:-1]
    T_jnt = cmds.ls(selection=True)[-1]
    print(Y_jnt,T_jnt)
    for jnt in Y_jnt:
        locator = cmds.spaceLocator()
        cmds.matchTransform(locator,jnt)
        cmds.move(2, 0, 0, locator, relative=True, objectSpace=True)
        cmds.aimConstraint(
            "locator1",
            jnt,
            aimVector=(1, 0, 0),
            upVector=axis_vector,
            worldUpType="object",
            worldUpObject=T_jnt
        )
        cmds.delete(locator)

        cmds.makeIdentity(jnt,apply=True)
        zero_jnt_orient()

@make_undo
def zero_pose():
    ctrls_shape = cmds.ls(type='nurbsCurve')
       
    ctrls = [cmds.listRelatives(i,p=1)[0] for i in ctrls_shape]
    for i in ctrls:
        
        locked_attrs = cmds.listAttr(i,locked=1) or []
        
        if 'translateX'  not in locked_attrs:
            cmds.setAttr(f'{i}.translateX', 0)
        if 'translateY'  not in locked_attrs:
            cmds.setAttr(f'{i}.translateY', 0)
        if 'translateZ' not in locked_attrs:
            cmds.setAttr(f'{i}.translateZ', 0)
        
        # 检查是否有rotateX, rotateY, rotateZ属性
        if 'rotateX' not in locked_attrs:
            cmds.setAttr(f'{i}.rotateX', 0)
        if 'rotateY' not in locked_attrs:
            cmds.setAttr(f'{i}.rotateY', 0)
        if 'rotateZ' not in locked_attrs:
            cmds.setAttr(f'{i}.rotateZ', 0)

@make_undo
def Global():

    ctrls = cmds.ls(selection=True)
    for ctrl in ctrls:
        loc = cmds.spaceLocator(name=f'loc_{ctrl}_global')
        grp = cmds.group(loc,name=f'{ctrl}_global')
        cmds.matchTransform(grp,ctrl,pos=True,rot=True)

        orient = cmds.orientConstraint(loc,ctrl,mo=False)
        cmds.pointConstraint(ctrl,loc,mo=False)

        cmds.hide(grp)

        cmds.addAttr(ctrl,longName='global',at='double',min=0,max=10,defaultValue=0.0,keyable=True)
        cmds.setAttr(f'{ctrl}.global',10)

        attrs = cmds.listAttr(orient,keyable=True)
        _attr = [attr for attr in attrs if 'global' in attr]

        cmds.setDrivenKeyframe(f'{orient[0]}.{_attr[0]}',cd=f'{ctrl}.global')
        cmds.setAttr(f'{ctrl}.global',0)
        cmds.setAttr(f'{orient[0]}.{_attr[0]}',0)
        cmds.setDrivenKeyframe(f'{orient[0]}.{_attr[0]}',cd=f'{ctrl}.global')

@make_undo
def copy_skin():
    sel = cmds.ls(selection=True)

    source_mesh = sel[0]
    target_meshes = sel[1:]

    # get source skin cluster
    source_skin = mel.eval('findRelatedSkinCluster("' + source_mesh + '")')

    # get source skin joints
    source_joints = cmds.skinCluster(source_skin, query=True, influence=True)

    # loop in each target mesh
    for target_mesh in target_meshes:
        # bind skin with source joints
        target_skin = cmds.skinCluster(source_joints, target_mesh, toSelectedBones=True)[0]
        # copy skin weight
        cmds.copySkinWeights(sourceSkin=source_skin, destinationSkin=target_skin, noMirror=True,
                            surfaceAssociation='closestPoint', influenceAssociation=['label', 'oneToOne'])
        # remove unused influence
        cmds.select(target_mesh)
        cmds.RemoveUnusedInfluences()
        # rename skin cluster if match naming convention
        if target_mesh.startswith('mesh_'):
            cmds.rename(target_skin, target_mesh.replace('mesh_', 'skinCluster_'))

@make_undo
def jnt_chain(count):

    select_jnt = cmds.ls(selection=True)
    start_jnt = select_jnt[0]
    end_jnt = select_jnt[1]

    children_jnts = cmds.listRelatives(start_jnt,allDescendents=True)
    child_jnts=[]
    for i in list(reversed(children_jnts)):
        child_jnts.append(i)
        if i ==end_jnt:
            break
    
    for i in child_jnts:
        cmds.parent(i,world=True)
    positions = [cmds.xform(jnt, q=True, ws=True, t=True) for jnt in [start_jnt] +child_jnts]
    curve = cmds.curve(ep=positions,name='jnt_resample_curve',d=3)
    cmds.rebuildCurve(curve,s=count-1)

    child_jnts.remove(end_jnt)
    for i in child_jnts:
        cmds.delete(i)

    num_ep = cmds.getAttr(f'{curve}.spans')+1
    ep_points = [f'{curve}.ep[{i}]' for i in range(num_ep)]
    ep_positions = [cmds.xform(ep_point, q=True, ws=True, t=True) for ep_point in ep_points]

    if cmds.listRelatives(start_jnt,parent=True): 
        start_jnt_parent = cmds.listRelatives(start_jnt,parent=True)
    if cmds.listRelatives(end_jnt,children=True):
        end_jnt_children = cmds.listRelatives(end_jnt,children=True)

    cmds.select(clear=True)

    for i in range(len(ep_positions)):
        if i == 0:
            continue
        elif i == len(ep_positions)-1:
            continue
        new_jnt = cmds.joint(p=ep_positions[i])

        if i == 1:
            cmds.parent(new_jnt,start_jnt)
        elif i == len(ep_positions) - 2:
            cmds.parent(end_jnt,new_jnt)

    cmds.select(clear=True)
    cmds.delete(curve)

    if cmds.listRelatives(start_jnt,parent=True):
        cmds.joint(start_jnt_parent[0],e=True,oj='xyz',secondaryAxisOrient='yup',ch=True)
    else:
        cmds.joint(start_jnt,e=True,oj='xyz',secondaryAxisOrient='yup',ch=True)

    joins_operate.joint_zero(children_jnts[0])

@make_undo
def scale_curve_cvs(multiplier):
    selected = cmds.ls(selection=True, type="transform")
    if not selected:
        cmds.warning("请先选择一条或多条 NURBS 曲线（transform 节点）")
        return

    for curve in selected:
        shapes = cmds.listRelatives(curve, shapes=True, type='nurbsCurve', fullPath=True)
        if not shapes:
            continue
        shape = shapes[0]

        degree = cmds.getAttr(f"{shape}.degree")
        spans = cmds.getAttr(f"{shape}.spans")
        cv_count = degree + spans

        cvs = [f"{curve}.cv[{i}]" for i in range(cv_count)]

        # 获取该曲线所有 CV 的位置
        positions = [cmds.pointPosition(cv, world=True) for cv in cvs]

        # 计算该曲线 CV 的中心
        center = [sum(coord) / len(positions) for coord in zip(*positions)]

        # 缩放每个 CV
        for i, cv in enumerate(cvs):
            pos = positions[i]
            new_pos = [
                center[0] + (pos[0] - center[0]) * multiplier,
                center[1] + (pos[1] - center[1]) * multiplier,
                center[2] + (pos[2] - center[2]) * multiplier,
            ]
            cmds.move(new_pos[0], new_pos[1], new_pos[2], cv, absolute=True, worldSpace=True)


@make_undo
def cijiFK():

    jnts = cmds.ls(selection=True)

    if cmds.objExists('cijiFK'):
        pass
    else:
        cmds.group(em=True,n='cijiFK')

        cmds.group(em=True,n='A_grp')
        cmds.group(em=True,n='BC_grp')
        cmds.group(em=True,n='ctrl_grp')
        cmds.group(em=True,n='Plane_grp')
        cmds.group(em=True,n='follicle_grp')

        cmds.parent('A_grp','cijiFK')
        cmds.parent('BC_grp','cijiFK')
        cmds.parent('Plane_grp','cijiFK')
        cmds.parent('follicle_grp','cijiFK')
        cmds.hide('cijiFK')


    cmds.select(cl=True)

    jnt_pPlane = []
    for jnt in jnts:
        children = cmds.listRelatives(jnt,allDescendents=True)
        if children is None:
            children = [jnt]
        else:
            children.append(jnt)
            children = list(reversed(children))

        for i in range(len(children)):

            circle = cmds.circle(n=f'ctrl_{children[i]}FK',normal=[1, 0, 0])
            cmds.delete(circle[1])
            zero = cmds.createNode('transform',n=f'zero_{children[i]}FK')
            cmds.parent(circle[0],zero)
            cmds.matchTransform(zero,children[i])

            A_grp = cmds.spaceLocator(n=f'A_{children[i]}')[0]
            B_grp = cmds.group(em=True,n=f'B_{children[i]}')
            C_grp = cmds.group(em=True,n=f'C_{children[i]}')
            cmds.matchTransform(A_grp,children[i])
            cmds.matchTransform(B_grp,children[i])
            cmds.matchTransform(C_grp,children[i])

            cmds.parent(C_grp,f'B_{children[i]}')

            cmds.connectAttr(f'{circle[0]}.translate',f'{C_grp}.translate')
            cmds.connectAttr(f'{circle[0]}.rotate',f'{C_grp}.rotate')

            cmds.connectAttr(f'{A_grp}.translate',f'{B_grp}.translate')
            cmds.connectAttr(f'{A_grp}.rotate',f'{B_grp}.rotate')

            pPlane = cmds.polyPlane(sw=1,sh=1,n=f'{children[i]}_pPlane')

            fol_shape = cmds.createNode('follicle')
            fol_transform = cmds.listRelatives(fol_shape, p=True)[0]
            fol_transform = cmds.rename(fol_transform, f'{children[i]}_follicle')
            fol_shape = cmds.listRelatives(fol_transform)[0]

            # 连接 mesh 到 follicle
            cmds.connectAttr(pPlane[0] + '.outMesh', fol_shape + '.inputMesh', f=True)
            cmds.connectAttr(pPlane[0] + '.worldMatrix[0]', fol_shape + '.inputWorldMatrix', f=True)

            # 连接 follicle 输出到 transform
            cmds.connectAttr(fol_shape + '.outTranslate', fol_transform + '.translate', f=True)
            cmds.connectAttr(fol_shape + '.outRotate', fol_transform + '.rotate', f=True)

            # 设置 UV 位置（0~1）
            cmds.setAttr(fol_shape + '.parameterU', 0.5)
            cmds.setAttr(fol_shape + '.parameterV', 0.5)

            cmds.matchTransform(pPlane[0],children[i])
            jnt_pPlane.append(pPlane[0])

            if i != 0:
                cmds.parent(zero,f'ctrl_{children[i-1]}FK')
                cmds.parent(A_grp,f'A_{children[i-1]}')
                cmds.parent(B_grp,f'C_{children[i-1]}')


            cmds.select(cl=True)
            cmds.parentConstraint(circle[0],children[i])
            cmds.scaleConstraint(circle[0],children[i])

            cmds.parentConstraint(f'{B_grp}',f'{zero}')
            cmds.group(f'{circle[0]}',n=f'connect_{children[i]}FK')
            cmds.group(f'{circle[0]}',n=f'other_{children[i]}FK')

            cmds.parentConstraint(fol_transform,f'A_{children[i]}',mo=True)

            cmds.parent(f'{children[i]}_pPlane','Plane_grp')
            cmds.parent(f'{children[i]}_follicle','follicle_grp')

        cmds.parent(f'A_{jnt}','A_grp')
        cmds.parent(f'B_{jnt}','BC_grp')
        cmds.parent(f'zero_{jnt}FK','ctrl_grp')


    ctrls = cmds.ls('ctrl_*FK',type='transform')
    for i in ctrls:
        cmds.setAttr(f"{i}.overrideEnabled", 1)
        cmds.setAttr(f"{i}.overrideColor", 13) 

def FKToIK():
    handFK = ['upperArmFK','elbowFK','wristFK']
    handIK = ['ctrl_L_handIK','ctrl_R_handIK']
    legFK = ['upperLegFK','kneeFK','ankleFK']
    legIK = ['ctrl_L_footIK','ctrl_R_footIK']

    sel = cmds.ls(selection=True)[0]
    side = sel.split('_')[1]

    if sel in handIK:

        cmds.matchTransform(f'ctrl_{side}_upperArmFK',f'jnt_{side}_upperArmIK',pos=True,rot=True)
        cmds.matchTransform(f'ctrl_{side}_elbowFK',f'jnt_{side}_elbowIK',pos=True,rot=True)
        cmds.matchTransform(f'ctrl_{side}_wristFK',f'jnt_{side}_wristIK',pos=True,rot=True)

        cmds.setAttr(f'ctrl_{side}_armIKFKBlend.ikfkBlend',0)

    elif sel.split('_')[-1] in handFK:

        cmds.matchTransform(f'ctrl_{side}_handIK',f'jnt_{side}_wristFK',pos=True,rot=True)
        cmds.matchTransform(f'zero_{side}_ArmPV',f'jnt_{side}_elbowFK',pos=True,rot=True)
        cmds.matchTransform(f'ctrl_{side}_ArmPV',f'zero_{side}_ArmPV',pos=True,rot=True)

        if side == 'L':
            cmds.setAttr(f'ctrl_{side}_ArmPV.translateY',5)
        elif side == 'R':
            cmds.setAttr(f'ctrl_{side}_ArmPV.translateY',-5)

        cmds.setAttr(f'ctrl_{side}_armIKFKBlend.ikfkBlend',1)


    elif sel in legIK:

        cmds.matchTransform(f'ctrl_{side}_upperLegFK',f'jnt_{side}_upperLegIK',pos=True,rot=True)
        cmds.matchTransform(f'ctrl_{side}_kneeFK',f'jnt_{side}_kneeIK',pos=True,rot=True)
        cmds.matchTransform(f'ctrl_{side}_ankleFK',f'jnt_{side}_ankleIK',pos=True,rot=True)

        cmds.setAttr(f'ctrl_{side}_legIKFKBlend.ikfkBlend',1)

    elif sel.split('_')[-1] in legFK:

        cmds.matchTransform(f'ctrl_{side}_footIK',f'{side}_IKToFK',pos=True,rot=True)
        cmds.matchTransform(f'zero_{side}_LegPV',f'jnt_{side}_kneeFK',pos=True,rot=True)
        cmds.matchTransform(f'ctrl_{side}_LegPV',f'zero_{side}_LegPV',pos=True,rot=True)

        if side == 'L':
            cmds.setAttr(f'ctrl_{side}_LegPV.translateY',5)
        elif side == 'R':
            cmds.setAttr(f'ctrl_{side}_LegPV.translateY',-5)

        cmds.setAttr(f'ctrl_{side}_legIKFKBlend.ikfkBlend',0)

    cmds.select(clear=True)