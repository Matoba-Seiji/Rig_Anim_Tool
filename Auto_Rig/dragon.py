from maya import cmds

from Auto_Rig import config


class DragonRig:
    def __init__(self, name="dragon"):
        self.name = name
        self.hand_jnts = ['HipFront','KneeFront','ToesFront1','ToesFront','ToesEndFront']
        self.leg_jnts = ['Hip','Knee','Toes1','Toes2','ToesEnd']
        self.footFront_jnts = ['OutFront','InnFront','HeelFront','ToesEndFront']
        self.foot_jnts = ['Out','Inn','Heel','ToesEnd']
        self.spine_jnts = ['Root_M','Spine1_M','Spine2_M','Chest_M']
        self.neck_jnts = ['Neck1_M','Neck2_M','Neck3_M','Head_M']
        self.tail_jnts = ['Tail0','Tail0Part1','Tail1','Tail1Part1','Tail2','Tail2Part1',
                          'Tail3','Tail3Part1','Tail4','Tail4Part1','Tail5']
        self.wingFirstFK_jnts = ['Shoulder','Elbow','Wrist']
        self.wingSecondFK_jnts_1 = ['ElbowFinger1','ElbowFinger2','ElbowFinger3']
        self.wingSecondFK_jnts_2 = ['PinkyFinger1','PinkyFinger2','PinkyFinger3','PinkyFinger4']
        self.wingSecondFK_jnts_3 = ['ThumbFinger1','ThumbFinger2','ThumbFinger3','ThumbFinger4']
        

    def Jnts_mirror(self):

        cmds.mirrorJoint('FrontLegScapular_L',mirrorBehavior=True,mirrorYZ=True,searchReplace=('_L','_R'))
        cmds.mirrorJoint('Scapula_L',mirrorBehavior=True,mirrorYZ=True,searchReplace=('_L','_R'))
        cmds.mirrorJoint('Hip_L',mirrorBehavior=True,mirrorYZ=True,searchReplace=('_L','_R'))

        cmds.parent(f'FrontLegScapular_R',world=True)
        cmds.parent(f'Scapula_R',world=True)
        cmds.parent(f'Hip_R',world=True)
        cmds.parent(f'FrontLegScapular_L',world=True)
        cmds.parent(f'Scapula_L',world=True)
        cmds.parent(f'Hip_L',world=True)
        cmds.parent(f'Tail0_M',world=True)
        cmds.parent(f'Neck1_M',world=True)
    def FK_create(self,side,jnts):

        cmds.select(clear=True)
        for i in jnts:
            if i == jnts[-1]:
                break
            IK_jnt = cmds.joint(n=f'{i}_{side}_FK')
            cmds.matchTransform(IK_jnt,f'{i}_{side}') 

        cmds.makeIdentity(f'{jnts[0]}_{side}_FK',apply=True,translate=True, rotate=True, scale=True)
        for i in jnts:
            if i == f'{jnts[-1]}':
                break

            cmds.file(config.ctrl_lib('circle.mb'),i=True)
            ctrl = cmds.rename('nurbsCircle1',f'ctrl_{side}_{i}FK')
            zero_ctrl = cmds.group(ctrl,n=f'zero_{side}_{i}FK')

            cmds.matchTransform(zero_ctrl,f'{i}_{side}')
            # scale = cmds.getAttr('world_scale.scaleX')
            config.scale_node(f'zero_{side}_{i}FK', 0.3)

            cmds.parent(zero_ctrl,'ctrl_world')
            

            cmds.setAttr(f'{ctrl}.rotateZ',90)
            cmds.makeIdentity(ctrl,apply=True)

            if i >= f'{jnts[1]}':
                cmds.parent(zero_ctrl,f'ctrl_{side}_{jnts[jnts.index(i)-1]}FK')

            cmds.parentConstraint(ctrl,f'{i}_{side}_FK')

        cmds.parent(f'{jnts[0]}_{side}_FK','ctrl_world')

    def IK_create(self,side,jnts,foot_jnts):

        cmds.select(clear=True)
        upperLeg_jnt = cmds.joint(n=f'{jnts[0]}_{side}_IK')
        knee_jnt = cmds.joint(n=f'{jnts[1]}_{side}_IK')
        ankle_jnt = cmds.joint(n=f'{jnts[2]}_{side}_IK')
        ball_jnt = cmds.joint(n=f'{jnts[3]}_{side}_IK')
        toe_jnt = cmds.joint(n=f'{jnts[4]}_{side}_IK')

        cmds.matchTransform(upperLeg_jnt,f'{jnts[0]}_{side}',position=True,rotation=True,scale=True)
        cmds.matchTransform(knee_jnt,f'{jnts[1]}_{side}',position=True,rotation=True,scale=True)
        cmds.matchTransform(ankle_jnt,f'{jnts[2]}_{side}',position=True,rotation=True,scale=True)
        cmds.matchTransform(ball_jnt,f'{jnts[3]}_{side}',position=True,rotation=True,scale=True)
        cmds.matchTransform(toe_jnt,f'{jnts[4]}_{side}',position=True,rotation=True,scale=True)

        cmds.makeIdentity(f'{jnts[0]}_{side}_IK',apply=True,translate=True, rotate=True, scale=True)


        LegIK = cmds.ikHandle(sj=f'{jnts[0]}_{side}_IK',ee=f'{jnts[2]}_{side}_IK',sol='ikRPsolver',n=f'{side}_{jnts[2]}ikHnd')
        BallIK = cmds.ikHandle(sj=f'{jnts[2]}_{side}_IK',ee=f'{jnts[3]}_{side}_IK',sol='ikSCsolver',n=f'{side}_{jnts[3]}ikHnd')
        ToeIK = cmds.ikHandle(sj=f'{jnts[3]}_{side}_IK',ee=f'{jnts[4]}_{side}_IK',sol='ikSCsolver',n=f'{side}_{jnts[4]}ikHnd')
        cmds.hide(LegIK)
        cmds.hide(BallIK)
        cmds.hide(ToeIK)

        cmds.select(clear=True)
        ctrl = cmds.joint(n=f'ctrl_{side}_{jnts[2]}IK')
        zero_ctrl = cmds.group(ctrl,n=f'zero_{side}_{jnts[2]}IK')
        cmds.matchTransform(zero_ctrl,ankle_jnt,position=True)

        loc_up = cmds.spaceLocator(n=f'{side}_{jnts[2]}_up')
        loc_down = cmds.spaceLocator(n=f'{side}_{jnts[2]}_down')
        cmds.matchTransform(loc_up,f'{jnts[2]}_{side}_IK',position=True)
        up_t = cmds.xform(loc_up,q=True,t=True)
        cmds.xform(loc_up,t=[up_t[0],up_t[1]+5,up_t[2]])
        cmds.matchTransform(loc_down,f'{jnts[4]}_{side}_IK',position=True)

        cmds.aimConstraint(loc_up,ctrl,aimVector=(0,1,0),upVector=(0,0,1),worldUpType='object',worldUpObject=f'{side}_{jnts[2]}_down',maintainOffset=False)
        cmds.delete(f'ctrl_{side}_{jnts[2]}IK_aimConstraint1')
        cmds.makeIdentity(ctrl,apply=True)
        cmds.delete(loc_up)
        cmds.delete(loc_down)

        cmds.file(config.ctrl_lib('footIK.mb'),i=True)
        cmds.rename('curve1',f'crv_{side}_{jnts[2]}IK')
        cmds.parent(f'crv_{side}_{jnts[2]}IKShape',f'ctrl_{side}_{jnts[2]}IK',shape=True,add=True)
        cmds.delete(f'crv_{side}_{jnts[2]}IK')
        # scale = cmds.getAttr('world_scale.scaleX')
        config.scale_node(f'zero_{side}_{jnts[2]}IK', 0.2)
        cmds.setAttr(f'ctrl_{side}_{jnts[2]}IK.drawStyle',2)
        cmds.parent(f'zero_{side}_{jnts[2]}IK','ctrl_world')

        cmds.file(config.ctrl_lib('PV.mb'),i=True)
        pv_ctrl = cmds.rename('curveControl1',f'ctrl_{side}_{jnts[1]}PV')
        pv_zero_ctrl = cmds.group(pv_ctrl,n=f'zero_{side}_{jnts[1]}PV')
        cmds.parent(pv_zero_ctrl,'ctrl_world')

        cmds.matchTransform(f'zero_{side}_{jnts[1]}PV',knee_jnt)
        cmds.parent(f'zero_{side}_{jnts[1]}PV',knee_jnt)
        if side == 'L':
            cmds.xform(f'zero_L_{jnts[1]}PV',t=[0.2,-0.4,0])
            cmds.xform(f'zero_L_{jnts[1]}PV',t=[0.2,0.4,0]) if jnts == self.hand_jnts else None
        if side == 'R':
            cmds.xform(f'zero_R_{jnts[1]}PV',t=[-0.2,0.4,0])
            cmds.xform(f'zero_R_{jnts[1]}PV',t=[-0.2,-0.4,0]) if jnts == self.hand_jnts else None

        cmds.parent(f'zero_{side}_{jnts[1]}PV',world=True)
        cmds.setAttr(f'zero_{side}_{jnts[1]}PV.rotateX',0)
        cmds.setAttr(f'zero_{side}_{jnts[1]}PV.rotateY',0)
        cmds.setAttr(f'zero_{side}_{jnts[1]}PV.rotateZ',0)
        cmds.poleVectorConstraint(f'ctrl_{side}_{jnts[1]}PV',f'{side}_{jnts[2]}ikHnd')    
        config.scale_node(f'zero_{side}_{jnts[1]}PV', 0.3)
        cmds.parent(f'zero_{side}_{jnts[1]}PV','ctrl_world')

        cmds.annotate(f'ctrl_{side}_{jnts[1]}PV',tx=' ')
        cmds.rename('annotation1',f'{side}_{jnts[1]}_annotation')
        cmds.pointConstraint(knee_jnt,f'{side}_{jnts[1]}_annotation')
        cmds.setAttr(f"{side}_{jnts[1]}_annotationShape.overrideEnabled",1)
        cmds.setAttr(f"{side}_{jnts[1]}_annotationShape.overrideDisplayType",2)

        if side =='R':
            cmds.group(f'L_{jnts[1]}_annotation',f'R_{jnts[1]}_annotation',n=f'grp_{jnts[1]}_annotation')
            cmds.parent(f'grp_{jnts[1]}_annotation','ctrl_world')

        cmds.addAttr(f'ctrl_{side}_{jnts[2]}IK',longName='twist',attributeType='double',keyable=True)
        cmds.connectAttr(f'ctrl_{side}_{jnts[2]}IK.twist',f'{side}_{jnts[2]}ikHnd.twist')



        cmds.select(clear=True)
        Rvs_toeIK1 = cmds.joint(n=f'jntRvs_{side}_{jnts[4]}IK_001')
        cmds.matchTransform(Rvs_toeIK1,ball_jnt,pos=True)
        Rvs_toeIK2 = cmds.joint(n=f'jntRvs_{side}_{jnts[4]}IK_002')
        cmds.matchTransform(Rvs_toeIK2,toe_jnt,pos=True)
        cmds.joint(Rvs_toeIK1,e=True,oj='xyz',sao='yup',ch=True)
        cmds.select(clear=True)

        Rvs_ballIK1 = cmds.joint(n=f'jntRvs_{side}_{jnts[3]}IK_001')
        cmds.matchTransform(Rvs_ballIK1,ball_jnt,pos=True)
        Rvs_ballIK2 = cmds.joint(n=f'jntRvs_{side}_{jnts[3]}IK_002')
        cmds.matchTransform(Rvs_ballIK2,ankle_jnt,pos=True)
        cmds.joint(Rvs_ballIK1,e=True,oj='xyz',sao='yup',ch=True)
        cmds.select(clear=True)

        Rvs_OutIK = cmds.joint(n=f'jntRvs_{side}_{foot_jnts[0]}IK')
        cmds.matchTransform(Rvs_OutIK,f'{foot_jnts[0]}_{side}',pos=True)
        Rvs_InnIK = cmds.joint(n=f'jntRvs_{side}_{foot_jnts[1]}IK')
        cmds.matchTransform(Rvs_InnIK,f'{foot_jnts[1]}_{side}',pos=True)
        cmds.joint(Rvs_OutIK,e=True,oj='xyz',sao='yup',ch=True)
        cmds.parent(Rvs_InnIK,world=True)
        cmds.parent(Rvs_OutIK,Rvs_InnIK)
        cmds.joint(Rvs_InnIK,e=True,oj='xyz',sao='yup',ch=True)
        cmds.parent(Rvs_OutIK,world=True)
        cmds.select(clear=True)

        Rvs_toeIK = cmds.joint(n=f'jntRvs_{side}_{jnts[4]}IK')
        cmds.matchTransform(Rvs_toeIK,f'{jnts[4]}_{side}',pos=True)
        cmds.setAttr(f'{Rvs_toeIK}.translateY',0)
        cmds.select(clear=True)

        Rvs_heelIK = cmds.joint(n=f'jntRvs_{side}_{foot_jnts[2]}IK')
        cmds.matchTransform(Rvs_heelIK,f'{foot_jnts[2]}_{side}',pos=True)
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
        cmds.rename('curve1',f'ctrl_{side}_{jnts[3]}IK')
        cmds.group(empty=True,n=f'zero_{side}_{jnts[3]}IK')
        cmds.parent(f'ctrl_{side}_{jnts[3]}IK',f'zero_{side}_{jnts[3]}IK')
        cmds.matchTransform(f'zero_{side}_{jnts[3]}IK',f'jntRvs_{side}_{jnts[3]}IK_001')
        # sca = cmds.getAttr(f'zero_{side}_{jnts[3]}IK.scale')[0]
        # cmds.setAttr(f'zero_{side}_{jnts[3]}IK.scaleX',sca[0]*scale)
        # cmds.setAttr(f'zero_{side}_{jnts[3]}IK.scaleY',sca[1]*scale)
        # cmds.setAttr(f'zero_{side}_{jnts[3]}IK.scaleZ',sca[2]*scale)    

        cmds.file(config.ctrl_lib('foot_toe.mb'),i=True)
        cmds.rename('curve1',f'ctrl_{side}_{jnts[4]}IK')
        cmds.group(empty=True,n=f'zero_{side}_{jnts[4]}IK')

        cmds.parent(f'ctrl_{side}_{jnts[4]}IK',f'zero_{side}_{jnts[4]}IK')
        cmds.matchTransform(f'zero_{side}_{jnts[4]}IK',f'jntRvs_{side}_{jnts[4]}IK_001')
        # sca = cmds.getAttr(f'zero_{side}_{jnts[4]}IK.scale')[0]
        # cmds.setAttr(f'zero_{side}_{jnts[4]}IK.scaleX',sca[0]*scale)
        # cmds.setAttr(f'zero_{side}_{jnts[4]}IK.scaleY',sca[1]*scale)
        # cmds.setAttr(f'zero_{side}_{jnts[4]}IK.scaleZ',sca[2]*scale)


        for i in foot_jnts:
            cmds.file(config.ctrl_lib('foot_rvs.mb'),i=True)
            cmds.rename('curve1',f'ctrl_{side}_{i}')
            zero = cmds.group(empty=True,n=f'zero_{side}_{i}')
            cmds.parent(f'ctrl_{side}_{i}',f'zero_{side}_{i}')
            cmds.matchTransform(f'zero_{side}_{i}',f'jntRvs_{side}_{i}IK')
            cmds.hide(zero)
            # sca_rvs = cmds.getAttr(f'zero_{side}_{i}.scale')[0]
            # cmds.setAttr(f'zero_{side}_{i}.scaleX',sca_rvs[0]*scale)
            # cmds.setAttr(f'zero_{side}_{i}.scaleY',sca_rvs[1]*scale)
            # cmds.setAttr(f'zero_{side}_{i}.scaleZ',sca_rvs[2]*scale)

        cmds.parent(f'zero_{side}_{jnts[3]}IK',f'zero_{side}_{jnts[4]}IK',f'ctrl_{side}_{foot_jnts[1]}')
        cmds.parent(f'zero_{side}_{foot_jnts[1]}',f'ctrl_{side}_{foot_jnts[0]}')
        cmds.parent(f'zero_{side}_{foot_jnts[0]}',f'ctrl_{side}_{jnts[4]}')
        cmds.parent(f'zero_{side}_{jnts[4]}',f'ctrl_{side}_{foot_jnts[2]}')

        cmds.parent(f'{side}_{jnts[4]}ikHnd',f'ctrl_{side}_{jnts[4]}IK')
        cmds.parent(f'{side}_{jnts[3]}ikHnd',f'ctrl_{side}_{jnts[3]}IK')
        cmds.parent(f'{side}_{jnts[2]}ikHnd',f'ctrl_{side}_{jnts[3]}IK')

        cmds.delete(f'jntRvs_{side}_{foot_jnts[2]}IK')
        cmds.delete(foot_jnts[3] + f'_{side}')
        cmds.delete(foot_jnts[0] + f'_{side}')
        cmds.delete(foot_jnts[1] + f'_{side}')
        cmds.delete(foot_jnts[2] + f'_{side}')

        cmds.parent(f'zero_{side}_{foot_jnts[2]}',f'ctrl_{side}_{jnts[2]}IK')

        cmds.addAttr(f'ctrl_{side}_{jnts[2]}IK',longName='toeTap',attributeType='float',keyable=True)
        cmds.addAttr(f'ctrl_{side}_{jnts[2]}IK',longName='toeSlide',attributeType='float',keyable=True)
        cmds.addAttr(f'ctrl_{side}_{jnts[2]}IK',longName='toeRoll',attributeType='float',keyable=True)
        cmds.addAttr(f'ctrl_{side}_{jnts[2]}IK',longName='ballRoll',attributeType='float',keyable=True,min=0)
        cmds.addAttr(f'ctrl_{side}_{jnts[2]}IK',longName='heelRoll',attributeType='float',keyable=True)
        cmds.addAttr(f'ctrl_{side}_{jnts[2]}IK',longName='heelSlide',attributeType='float',keyable=True)
        cmds.addAttr(f'ctrl_{side}_{jnts[2]}IK',longName='bank',attributeType='float',keyable=True)

        cmds.group(f'ctrl_{side}_{jnts[4]}IK',n=f'connect_{side}_{jnts[4]}IK')
        cmds.matchTransform(f'connect_{side}_{jnts[4]}IK',f'ctrl_{side}_{jnts[4]}IK',pivots=True)
        cmds.connectAttr(f'ctrl_{side}_{jnts[2]}IK.toeTap',f'connect_{side}_{jnts[4]}IK.rotateZ')
        cmds.group(f'ctrl_{side}_{jnts[3]}IK',n=f'connect_{side}_{jnts[3]}IK')
        cmds.matchTransform(f'connect_{side}_{jnts[3]}IK',f'ctrl_{side}_{jnts[3]}IK',pivots=True)
        cmds.connectAttr(f'ctrl_{side}_{jnts[2]}IK.ballRoll',f'connect_{side}_{jnts[3]}IK.rotateZ')
        cmds.group(f'ctrl_{side}_{jnts[4]}',n=f'connect_{side}_{jnts[4]}')
        cmds.matchTransform(f'connect_{side}_{jnts[4]}',f'ctrl_{side}_{jnts[4]}',pivots=True)
        cmds.connectAttr(f'ctrl_{side}_{jnts[2]}IK.toeRoll',f'connect_{side}_{jnts[4]}.rotateZ')
        cmds.connectAttr(f'ctrl_{side}_{jnts[2]}IK.toeSlide',f'connect_{side}_{jnts[4]}.rotateY')
        cmds.setAttr(f'connect_{side}_{jnts[4]}.rotateOrder',2)
        cmds.group(f'ctrl_{side}_{foot_jnts[2]}',n=f'connect_{side}_{foot_jnts[2]}')
        cmds.matchTransform(f'connect_{side}_{foot_jnts[2]}',f'ctrl_{side}_{foot_jnts[2]}',pivots=True)
        cmds.connectAttr(f'ctrl_{side}_{jnts[2]}IK.heelRoll',f'connect_{side}_{foot_jnts[2]}.rotateZ')
        cmds.connectAttr(f'ctrl_{side}_{jnts[2]}IK.heelSlide',f'connect_{side}_{foot_jnts[2]}.rotateY')
        cmds.setAttr(f'connect_{side}_{foot_jnts[2]}.rotateOrder',2)

        cmds.group(f'ctrl_{side}_{foot_jnts[0]}',n=f'connect_{side}_{foot_jnts[0]}')
        cmds.matchTransform(f'connect_{side}_{foot_jnts[0]}',f'ctrl_{side}_{foot_jnts[0]}',pivots=True)
        cmds.group(f'ctrl_{side}_{foot_jnts[1]}',n=f'connect_{side}_{foot_jnts[1]}')
        cmds.matchTransform(f'connect_{side}_{foot_jnts[1]}',f'ctrl_{side}_{foot_jnts[1]}',pivots=True)

        cmds.createNode('multDoubleLinear',n=f'muly_{side}_{jnts[2]}{foot_jnts[1]}')
        cmds.connectAttr(f'ctrl_{side}_{jnts[2]}IK.bank',f'muly_{side}_{jnts[2]}{foot_jnts[1]}.input1')
        cmds.setAttr(f'muly_{side}_{jnts[2]}{foot_jnts[1]}.input2',-1)
        cmds.connectAttr(f'muly_{side}_{jnts[2]}{foot_jnts[1]}.output',f'connect_{side}_{foot_jnts[1]}.rotateZ')
        cmds.connectAttr(f'ctrl_{side}_{jnts[2]}IK.bank',f'connect_{side}_{foot_jnts[0]}.rotateZ')

        cmds.transformLimits(f'connect_{side}_{foot_jnts[0]}',erz=(1,0),rz=(0,45))
        cmds.transformLimits(f'connect_{side}_{foot_jnts[1]}',erz=(1,0),rz=(0,45))


        # locator = cmds.spaceLocator(n=f'{side}_IKToFK')
        # cmds.matchTransform(locator,f'jnt_{side}_ankleFK',pos=True)
        # cmds.parent(locator,f'jnt_{side}_ankleFK')

        # loc_up = cmds.spaceLocator(n=f'{side}_up')
        # loc_down = cmds.spaceLocator(n=f'{side}_down')
        # cmds.matchTransform(loc_up,f'jnt_{side}_ankleFK',position=True)
        # up_t = cmds.xform(loc_up,q=True,t=True)
        # cmds.xform(loc_up,t=[up_t[0],up_t[1]+5,up_t[2]])
        # cmds.matchTransform(loc_down,f'jnt_{side}_{jnts[4]}FK',position=True)
        # cmds.aimConstraint(loc_up,locator,aimVector=(0,1,0),upVector=(0,0,1),worldUpType='object',worldUpObject=f'{side}_down',maintainOffset=False)
        # cmds.delete(f'{side}_IKToFK_aimConstraint1')

        # cmds.delete(loc_up)
        # cmds.delete(loc_down)
  
    def IKFKBlend(self,side,jnts,foot_jnts):
        cmds.file(config.ctrl_lib('cross.mb'),i=True)
        cmds.rename('curve1',f'ctrl_{side}_{jnts[2]}IKFKBlend')
        cmds.group(f'ctrl_{side}_{jnts[2]}IKFKBlend',n=f'zero_{side}_{jnts[2]}IKFKBlend')
        t = cmds.xform(f'{jnts[0]}_{side}',q=True,ws=True,t=True)
        self.BlendLock(side,jnts[2]+'IKFKBlend')
        # scale = cmds.getAttr('world_scale.scaleX')
        config.scale_node(f'zero_{side}_{jnts[2]}IKFKBlend', 0.2)
        if side == 'L':
            cmds.xform(f'zero_{side}_{jnts[2]}IKFKBlend',t=[t[0]+3*0.2,t[1]-3*0.2,t[2]])
        if side == 'R':
            cmds.xform(f'zero_{side}_{jnts[2]}IKFKBlend',t=[t[0]-3*0.2,t[1]-3*0.2,t[2]])
        cmds.parent(f'zero_{side}_{jnts[2]}IKFKBlend','ctrl_world')

        rev_node = cmds.createNode('reverse',n=f'{side}_{jnts[2]}IKrev')
        cmds.connectAttr(f'ctrl_{side}_{jnts[2]}IKFKBlend.ikfkBlend',f'{rev_node}.inputX')

        for i in jnts:
            if i == f'{jnts[4]}':
                break
            cmds.parentConstraint(f'{i}_{side}_FK',f'{i}_{side}_IK',f'{i}_{side}')

            cmds.connectAttr(f'ctrl_{side}_{jnts[2]}IKFKBlend.ikfkBlend',f'{i}_{side}_parentConstraint1.{i}_{side}_FKW0')
            cmds.connectAttr(f'{rev_node}.outputX',f'{i}_{side}_parentConstraint1.{i}_{side}_IKW1')

        cmds.connectAttr(f'{rev_node}.outputX',f'zero_{side}_{jnts[2]}IK.visibility')
        cmds.connectAttr(f'{rev_node}.outputX',f'zero_{side}_{jnts[1]}PV.visibility')
        cmds.connectAttr(f'{rev_node}.outputX',f'{side}_{jnts[1]}_annotation.visibility')

        cmds.connectAttr(f'ctrl_{side}_{jnts[2]}IKFKBlend.ikfkBlend',f'zero_{side}_{jnts[0]}FK.visibility')
        cmds.hide(f'{jnts[0]}_{side}_FK')
        cmds.hide(f'{jnts[0]}_{side}_IK')

        cmds.parent(f'{jnts[0]}_{side}_IK','ctrl_world')

    def BlendLock(self,side,name):
        config.lock_srt_vis(f'ctrl_{side}_{name}')
        cmds.addAttr(f'ctrl_{side}_{name}.',longName='ikfkBlend',attributeType='double',keyable=True,min=0,max=1)

    def Spine_create(self,jnts):
        
        cmds.file(config.ctrl_lib('cog.mb'),i=True)
        cmds.rename('curve',f'ctrl_C_cog')
        cmds.group(n='zero_C_cog',empty=True)
        cmds.parent('ctrl_C_cog','zero_C_cog')
        cmds.matchTransform('zero_C_cog',f'{jnts[0]}',pos=True)

        # scale = cmds.getAttr('world_scale.scaleX')
        config.scale_node('zero_C_cog', 0.2)
        cmds.parent('zero_C_cog','ctrl_world')
        cmds.makeIdentity('zero_C_cog',apply=True,scale=True)


        points = []
        for i in jnts:
            points.append(cmds.xform(f'{i}',q=True,ws=True,t=True))
        curve = cmds.curve(p=points)
        cmds.rename(curve,'crv_C_spine')

        cmds.ikHandle(sj=f'{jnts[0]}',ee=f'{jnts[-1]}',sol='ikSplineSolver',n='SpineikHnd',curve='crv_C_spine',
                    createCurve=False,parentCurve=False)

        cmds.select(clear=True)
        spine1 = cmds.joint(n=f'{jnts[0]}_IK')
        cmds.select(clear=True)
        spine2 = cmds.joint(n=f'{jnts[1]}_IK')
        cmds.select(clear=True)
        spine3 = cmds.joint(n=f'{jnts[2]}_IK',r=False)
        cmds.matchTransform(spine1,f'{jnts[0]}',pos=True)
        cmds.matchTransform(spine3,f'{jnts[-1]}',pos=True)

        # if spine_num%2 == 0:
        #     spine_C1 = cmds.xform(f'jnt_C_spine_{spine_num//2:03}',q=True,t=True,ws=True)
        #     spine_C2 = cmds.xform(f'jnt_C_spine_{spine_num//2+1:03}',q=True,t=True,ws=True)
        #     cmds.xform(spine2,t=[(spine_C1[0]+spine_C2[0])/2,(spine_C1[1]+spine_C2[1])/2,(spine_C1[2]+spine_C2[2])/2],ws=True)

        # else:
        #     cmds.matchTransform(spine2,f'jnt_C_spine_{spine_num//2+1:03}',pos=True)

        spine_C1 = cmds.xform(f'{jnts[1]}',q=True,t=True,ws=True)
        spine_C2 = cmds.xform(f'{jnts[2]}',q=True,t=True,ws=True)
        cmds.xform(spine2,t=[(spine_C1[0]+spine_C2[0])/2,(spine_C1[1]+spine_C2[1])/2,(spine_C1[2]+spine_C2[2])/2],ws=True)

        for i in range(3):
            cmds.file(config.ctrl_lib(f'circle{i+1}.mb'),i=True)
            ctrlFK = cmds.rename('nurbsCircle1',f'ctrl_C_{jnts[i]}_FK')
            cmds.setAttr(f'{ctrlFK}.scaleX',3)
            cmds.setAttr(f'{ctrlFK}.scaleY',3)
            cmds.setAttr(f'{ctrlFK}.scaleZ',3)
            cmds.setAttr(f'{ctrlFK}.rotateX',90)
            cmds.makeIdentity(ctrlFK,apply=True)
            zero_ctrlFK = cmds.group(n=f'zero_C_{jnts[i]}_FK',empty=True)
            cmds.parent(ctrlFK,zero_ctrlFK)
            
            cmds.file(config.ctrl_lib(f'spineIK{i+1}.mb'),i=True)
            ctrlIK = cmds.rename('curve1',f'ctrl_C_spineIK_00{i+1}')
            cmds.setAttr(f'{ctrlIK}.rotateX',90)
            cmds.makeIdentity(ctrlIK,apply=True)
            zero_ctrlIK = cmds.group(ctrlIK,n=f'zero_C_spineIK_00{i+1}')

            cmds.parent(zero_ctrlIK,f'ctrl_C_{jnts[i]}_FK')

            cmds.matchTransform(zero_ctrlFK,f'{jnts[i]}_IK')

            if i != 0:
                cmds.parent(zero_ctrlFK,f'ctrl_C_{jnts[i-1]}_FK')

            # scale = cmds.getAttr('world_scale.scaleX')
            config.scale_node(f'zero_C_{jnts[i]}_FK', 0.2)

            cmds.makeIdentity(f'zero_C_{jnts[i]}_FK',apply=True,scale=True)


        cmds.parent(f'zero_C_{jnts[0]}_FK','ctrl_C_cog')

        cmds.skinCluster([spine1,spine2,spine3],'crv_C_spine',toSelectedBones=True)
        for i in range(3):
            cmds.parent(f'{jnts[i]}_IK',f'ctrl_C_spineIK_00{i+1}')

        cmds.setAttr('SpineikHnd.dTwistControlEnable',1)
        cmds.setAttr('SpineikHnd.dWorldUpType',4)
        cmds.setAttr('SpineikHnd.dWorldUpVectorY',1)
        cmds.setAttr('SpineikHnd.dWorldUpVectorEndY',1)
        cmds.connectAttr(f"{spine1}.worldMatrix[0]","SpineikHnd.dWorldUpMatrix")
        cmds.connectAttr(f"{spine3}.worldMatrix[0]","SpineikHnd.dWorldUpMatrixEnd")

        cmds.createNode('curveInfo',n='crv_C_spineInfo')
        cmds.connectAttr('crv_C_spineShape.worldSpace[0]','crv_C_spineInfo.inputCurve')
        cmds.createNode('multiplyDivide',n='mult_C_spineIK')
        cmds.setAttr('mult_C_spineIK.operation',2)
        cmds.connectAttr('crv_C_spineInfo.arcLength','mult_C_spineIK.input1.input1X')
        # cmds.connectAttr('ctrl_world.scaleY','mult_C_spineIK.input2.input2X')

        ArcLength = cmds.getAttr('crv_C_spineInfo.arcLength')
        cmds.setAttr('mult_C_spineIK.input2X',ArcLength)

        for i in jnts:
            cmds.connectAttr('mult_C_spineIK.output.outputX',f'{i}.scaleX')


        cmds.orientConstraint('ctrl_C_spineIK_003',f'{jnts[-1]}',maintainOffset=True)
        cmds.orientConstraint('ctrl_C_spineIK_001',f'{jnts[0]}',maintainOffset=True)

        cmds.hide(f'{self.spine_jnts[0]}_IK')
        cmds.hide(f'{self.spine_jnts[1]}_IK')
        cmds.hide(f'{self.spine_jnts[2]}_IK')
        cmds.hide('SpineikHnd')
        cmds.hide('crv_C_spine')

        cmds.parent('SpineikHnd','ctrl_C_spineIK_003')

    def Neck_create(self,jnts):

        for i in range(4):
            if i == 3:
                break
            cmds.file(config.ctrl_lib('circle.mb'),i=True)
            cmds.rename('nurbsCircle1',f'ctrl_C_{jnts[i]}')
            cmds.group(f'ctrl_C_{jnts[i]}',n=f'zero_C_{jnts[i]}')
            cmds.matchTransform(f'zero_C_{jnts[i]}',f'{jnts[i]}')
            config.scale_node(f'zero_C_{jnts[i]}', 0.6)
            cmds.setAttr(f'ctrl_C_{jnts[i]}.rotateZ',90)
            cmds.makeIdentity(f'ctrl_C_{jnts[i]}',apply=True)
            cmds.parentConstraint(f'ctrl_C_{jnts[i]}',f'{jnts[i]}')

            if i == 1:
                cmds.parent(f'zero_C_{jnts[i]}',f'ctrl_C_{jnts[0]}')

            if i == 2:
                cmds.parent(f'zero_C_{jnts[i]}',f'ctrl_C_{jnts[1]}')

        cmds.file(config.ctrl_lib('dragon_head.mb'),i=True)
        cmds.rename('nurbsCircle1','ctrl_C_head')    
        cmds.group(n='zero_C_head',empty=True)
        cmds.parent('ctrl_C_head','zero_C_head')
        cmds.matchTransform('zero_C_head',f'{jnts[3]}')
        cmds.makeIdentity('ctrl_C_head',apply=True)

        cmds.parentConstraint('ctrl_C_head',f'{jnts[3]}',maintainOffset=True)    

        # scale = cmds.getAttr('world_scale.scaleX')
        # sca = cmds.getAttr('zero_C_neck_001.scale')[0]
        # cmds.setAttr('zero_C_neck_001.scaleX',sca[0]*scale)
        # cmds.setAttr('zero_C_neck_001.scaleY',sca[1]*scale)
        # cmds.setAttr('zero_C_neck_001.scaleZ',sca[2]*scale)

        cmds.parent('zero_C_head',f'ctrl_C_{jnts[2]}')
        cmds.parent(f'zero_C_{jnts[0]}','ctrl_world')

        cmds.parentConstraint('ctrl_C_spineIK_003',f'zero_C_{jnts[0]}',maintainOffset=True)

    def Shoulder_create(self,side,jnts):
        cmds.file(config.ctrl_lib('shoulder.mb'),i=True)
        cmds.rename('curve1',f'ctrl_{side}_{jnts}_shoulder')
        cmds.group(f'ctrl_{side}_{jnts}_shoulder',n=f'zero_{side}_{jnts}_shoulder')
        cmds.matchTransform(f'zero_{side}_{jnts}_shoulder',f'ctrl_{side}_{jnts}_shoulder',pivots=True)
        cmds.matchTransform(f'zero_{side}_{jnts}_shoulder',f'{jnts}_{side}')
        if side == 'L':
            cmds.setAttr(f'ctrl_{side}_{jnts}_shoulder.rotateX',90)
        if side == 'R':
            cmds.setAttr(f'ctrl_{side}_{jnts}_shoulder.rotateX',-90)
        cmds.makeIdentity(f'ctrl_{side}_{jnts}_shoulder',apply=True)
        # scale = cmds.getAttr('world_scale.scaleX')
        config.scale_node(f'zero_{side}_{jnts}_shoulder', 0.3)
        cmds.parent(f'zero_{side}_{jnts}_shoulder','ctrl_world')

        cmds.parentConstraint(f'ctrl_{side}_{jnts}_shoulder',f'{jnts}_{side}')

        cmds.parentConstraint(f'ctrl_{side}_{jnts}_shoulder',f'zero_{side}_{self.hand_jnts[0]}FK',mo=True)
        cmds.parentConstraint(f'{jnts}_{side}',f'{self.hand_jnts[0]}_{side}_IK',mo=True)

    def Tail_create(self,side,jnts):

        cmds.select(clear=True)

        for idx, jnt in enumerate(jnts):

            # 最后一节骨骼一般不做 FK
            if jnt == jnts[-1]:
                break

            # 1. 导入控制器
            cmds.file(
                config.ctrl_lib('circle.mb'),
                i=True
            )

            ctrl = cmds.rename('nurbsCircle1', f'ctrl_{side}_{jnt}FK')

            # 2. zero 组
            zero = cmds.group(ctrl, n=f'zero_{side}_{jnt}FK')

            # 3. 对齐到骨骼
            cmds.matchTransform(zero, f'{jnt}_{side}')

            # 4. 缩放 zero（不冻结 scale）
            config.scale_node(zero, 0.3)

            # 5. 放到世界控制器下（可选）
            if cmds.objExists('ctrl_world'):
                cmds.parent(zero, 'ctrl_world')

            # 6. 调整 ctrl 朝向 + 冻结 rotate
            cmds.setAttr(f'{ctrl}.rotateZ', 90)
            cmds.makeIdentity(ctrl, apply=True, r=True, s=False, t=False)

            # 7. FK 层级（用 index，不用字符串比较）
            if idx > 0:
                parent_ctrl = f'ctrl_{side}_{jnts[idx - 1]}FK'
                cmds.parent(zero, parent_ctrl)

            # 8. 约束骨骼（一定要 mo=True）
            cmds.parentConstraint(ctrl, f'{jnt}_{side}', mo=True)

    cmds.select(clear=True)

    cmds.select(clear=True)
    def Wing_create(self,side):
        cmds.file(config.ctrl_lib('shoulder.mb'),i=True)
        cmds.rename('curve1',f'ctrl_{side}_shoulder')
        cmds.group(f'ctrl_{side}_shoulder',n=f'zero_{side}_shoulder')
        cmds.matchTransform(f'zero_{side}_shoulder',f'ctrl_{side}_shoulder',pivots=True)
        cmds.matchTransform(f'zero_{side}_shoulder',f'Scapula_{side}')
        if side == 'L':
            cmds.setAttr(f'ctrl_{side}_shoulder.rotateX',-90)
        if side == 'R':
            cmds.setAttr(f'ctrl_{side}_shoulder.rotateX',90)
        cmds.makeIdentity(f'ctrl_{side}_shoulder',apply=True)
        # scale = cmds.getAttr('world_scale.scaleX')
        config.scale_node(f'zero_{side}_shoulder', 0.3)
        cmds.parent(f'zero_{side}_shoulder','ctrl_world')

        cmds.parentConstraint(f'ctrl_{side}_shoulder',f'Scapula_{side}')

        cmds.select(clear=True)
        for idx, i in enumerate(self.wingFirstFK_jnts):

            cmds.file(config.ctrl_lib('circle.mb'), i=True)
            ctrl = cmds.rename('nurbsCircle1', f'ctrl_{side}_{i}FK')
            zero_ctrl = cmds.group(ctrl, n=f'zero_{side}_{i}FK')

            cmds.matchTransform(zero_ctrl, f'{i}_{side}')

            config.scale_node(zero_ctrl, 0.3)

            cmds.parent(zero_ctrl, 'ctrl_world')

            cmds.setAttr(f'{ctrl}.rotateZ', 90)
            cmds.makeIdentity(ctrl, apply=True)

            if idx > 0:
                prev_jnt = self.wingFirstFK_jnts[idx - 1]
                cmds.parent(zero_ctrl,f'ctrl_{side}_{prev_jnt}FK')

            cmds.parentConstraint(ctrl, f'{i}_{side}', mo=True)


    def connect(self):
        
        cmds.select(clear=True)
        cmds.joint(n='jnt_C_pelvisLocal')
        cmds.matchTransform('jnt_C_pelvisLocal',f'{self.spine_jnts[0]}',pos=True)
        cmds.file(config.ctrl_lib('pelvisLocal.mb'),i=True)
        cmds.rename('curve1','ctrl_C_pelvisLocal')
        cmds.group('ctrl_C_pelvisLocal',n='zero_C_pelvisLocal')
        cmds.matchTransform('zero_C_pelvisLocal','jnt_C_pelvisLocal')
        config.scale_node(f'zero_C_pelvisLocal', 0.2)
        cmds.setAttr('zero_C_pelvisLocal.translateX',-5*0.2)
        cmds.parentConstraint('ctrl_C_pelvisLocal','jnt_C_pelvisLocal',maintainOffset=True)
        cmds.parent('zero_C_pelvisLocal','ctrl_C_spineIK_001')


        cmds.parent(f'{self.leg_jnts[0]}_L','jnt_C_pelvisLocal')
        cmds.parent(f'{self.leg_jnts[0]}_R','jnt_C_pelvisLocal')

        cmds.parentConstraint('jnt_C_pelvisLocal',f'zero_L_{self.leg_jnts[0]}FK',maintainOffset=True)
        cmds.parentConstraint('jnt_C_pelvisLocal',f'zero_R_{self.leg_jnts[0]}FK',maintainOffset=True)
        cmds.parentConstraint('jnt_C_pelvisLocal',f'{self.leg_jnts[0]}_R_IK',maintainOffset=True)
        cmds.parentConstraint('jnt_C_pelvisLocal',f'{self.leg_jnts[0]}_L_IK',maintainOffset=True)

        cmds.parentConstraint('ctrl_C_spineIK_003','zero_L_FrontLegScapular_shoulder',maintainOffset=True)
        cmds.parentConstraint('ctrl_C_spineIK_003','zero_R_FrontLegScapular_shoulder',maintainOffset=True)

        cmds.parent(f'zero_R_{self.leg_jnts[2]}IKFKBlend','ctrl_C_cog')
        cmds.parent(f'zero_L_{self.leg_jnts[2]}IKFKBlend','ctrl_C_cog')
        cmds.parent(f'zero_L_{self.hand_jnts[2]}IKFKBlend','ctrl_C_cog')
        cmds.parent(f'zero_R_{self.hand_jnts[2]}IKFKBlend','ctrl_C_cog')


        cmds.parent(self.neck_jnts[0],self.spine_jnts[-1])

        cmds.parent('FrontLegScapular_L',self.spine_jnts[-1])
        cmds.parent('FrontLegScapular_R',self.spine_jnts[-1])

        cmds.parent('Tail0_M','jnt_C_pelvisLocal')

        cmds.parent('Scapula_L',self.spine_jnts[-1])
        cmds.parent('Scapula_R',self.spine_jnts[-1])

        empty_group = cmds.group(n='Group',empty=True)
        jnts_group = cmds.group(n='joints',empty=True)
        model_group = cmds.group(n='Model',empty=True)
        other_group = cmds.group(n='Other',empty=True)

        cmds.parent([jnts_group,other_group,model_group],empty_group)
        cmds.parent(['Root_M','jnt_C_pelvisLocal'],empty_group)
        cmds.parent('ctrl_world',empty_group)

        cmds.parent('crv_C_spine',other_group)

        cmds.parent('Root_M',jnts_group)
        cmds.parent('jnt_C_pelvisLocal',jnts_group)

        cmds.parentConstraint('jnt_C_pelvisLocal',f'zero_M_Tail0FK',maintainOffset=True)


        cmds.parentConstraint('ctrl_L_WristFK','zero_L_ThumbFinger1FK',mo=True)
        cmds.parentConstraint('ctrl_L_WristFK','zero_L_PinkyFinger1FK',mo=True)
        cmds.parentConstraint('ctrl_L_ElbowFK','zero_L_ElbowFinger1FK',mo=True)

        cmds.parentConstraint('ctrl_R_WristFK','zero_R_ThumbFinger1FK',mo=True)
        cmds.parentConstraint('ctrl_R_WristFK','zero_R_PinkyFinger1FK',mo=True)
        cmds.parentConstraint('ctrl_R_ElbowFK','zero_R_ElbowFinger1FK',mo=True)

        cmds.parentConstraint('ctrl_L_shoulder','zero_L_ShoulderFK',mo=True)
        cmds.parentConstraint('ctrl_R_shoulder','zero_R_ShoulderFK',mo=True)

        cmds.parentConstraint('ctrl_C_spineIK_003','zero_L_shoulder',mo=True)
        cmds.parentConstraint('ctrl_C_spineIK_003','zero_R_shoulder',mo=True)
    def Color(self):
        config.color_ctrls('ctrl_L_*', 6)
        config.color_ctrls('ctrl_R_*', 13)
        config.color_ctrls('ctrl_M_*', 20)
        config.color_ctrls('ctrl_C_*', 17)
        if cmds.objExists('ctrl_C_cog'):
            cmds.setAttr('ctrl_C_cog.overrideColor', 19)


    def build(self):
        self.Jnts_mirror()

        self.FK_create(side='L',jnts=self.hand_jnts)
        self.FK_create(side='R',jnts=self.hand_jnts)

        self.FK_create(side='L',jnts=self.leg_jnts)
        self.FK_create(side='R',jnts=self.leg_jnts)

        self.Tail_create(side='M',jnts=self.tail_jnts)

        self.IK_create(side='L',jnts=self.leg_jnts,foot_jnts=self.foot_jnts)
        self.IK_create(side='R',jnts=self.leg_jnts,foot_jnts=self.foot_jnts)
        self.IK_create(side='L',jnts=self.hand_jnts,foot_jnts=self.footFront_jnts)
        self.IK_create(side='R',jnts=self.hand_jnts,foot_jnts=self.footFront_jnts)

        self.IKFKBlend(side='L',jnts=self.leg_jnts,foot_jnts=self.foot_jnts)
        self.IKFKBlend(side='R',jnts=self.leg_jnts,foot_jnts=self.foot_jnts)
        self.IKFKBlend(side='L',jnts=self.hand_jnts,foot_jnts=self.footFront_jnts)
        self.IKFKBlend(side='R',jnts=self.hand_jnts,foot_jnts=self.footFront_jnts)

        self.Spine_create(jnts=self.spine_jnts)

        self.Neck_create(jnts=self.neck_jnts)

        self.Shoulder_create(side='L',jnts='FrontLegScapular')
        self.Shoulder_create(side='R',jnts='FrontLegScapular')

        self.Wing_create(side='L')
        self.Wing_create(side='R')

        self.Tail_create(side='L',jnts=self.wingSecondFK_jnts_1)
        self.Tail_create(side='L',jnts=self.wingSecondFK_jnts_2)
        self.Tail_create(side='L',jnts=self.wingSecondFK_jnts_3)
        self.Tail_create(side='R',jnts=self.wingSecondFK_jnts_1)
        self.Tail_create(side='R',jnts=self.wingSecondFK_jnts_2)
        self.Tail_create(side='R',jnts=self.wingSecondFK_jnts_3)

        self.connect()
        self.Color()

        cmds.select(clear=True)

if __name__ == "__main__":
    DragonRig().build()