# -*- coding: utf-8 -*-
from __future__ import division
import re

import maya.cmds as cmds
import maya.mel as mel


class FbxToHIK:
    """映射驱动的 HumanIK 控制器生成。

    骨骼来源为 picker 的 self.mapping（槽位ID→关节全路径），
    不再按硬编码 UE 骨骼名自动检测。
    """

    HIK_ID = {
        "Reference": 0, "Hips": 1,
        "LeftUpLeg": 2, "LeftLeg": 3, "LeftFoot": 4,
        "RightUpLeg": 5, "RightLeg": 6, "RightFoot": 7,
        "Spine": 8, "LeftArm": 9, "LeftForeArm": 10, "LeftHand": 11,
        "RightArm": 12, "RightForeArm": 13, "RightHand": 14,
        "Head": 15, "LeftToeBase": 16, "RightToeBase": 17,
        "LeftShoulder": 18, "RightShoulder": 19, "Neck": 20,
        "LeftFingerBase": 21, "RightFingerBase": 22,
        "Spine1": 23, "Spine2": 24, "Spine3": 25, "Spine4": 26,
        "Spine5": 27, "Spine6": 28, "Spine7": 29, "Spine8": 30, "Spine9": 31,
        "Neck1": 32, "Neck2": 33, "Neck3": 34, "Neck4": 35, "Neck5": 36,
        "Neck6": 37, "Neck7": 38, "Neck8": 39, "Neck9": 40,
        "LeftHandThumb1": 50, "LeftHandThumb2": 51, "LeftHandThumb3": 52, "LeftHandThumb4": 53,
        "LeftHandIndex1": 54, "LeftHandIndex2": 55, "LeftHandIndex3": 56, "LeftHandIndex4": 57,
        "LeftHandMiddle1": 58, "LeftHandMiddle2": 59, "LeftHandMiddle3": 60, "LeftHandMiddle4": 61,
        "LeftHandRing1": 62, "LeftHandRing2": 63, "LeftHandRing3": 64, "LeftHandRing4": 65,
        "LeftHandPinky1": 66, "LeftHandPinky2": 67, "LeftHandPinky3": 68, "LeftHandPinky4": 69,
        "RightHandThumb1": 74, "RightHandThumb2": 75, "RightHandThumb3": 76, "RightHandThumb4": 77,
        "RightHandIndex1": 78, "RightHandIndex2": 79, "RightHandIndex3": 80, "RightHandIndex4": 81,
        "RightHandMiddle1": 82, "RightHandMiddle2": 83, "RightHandMiddle3": 84, "RightHandMiddle4": 85,
        "RightHandRing1": 86, "RightHandRing2": 87, "RightHandRing3": 88, "RightHandRing4": 89,
        "RightHandPinky1": 90, "RightHandPinky2": 91, "RightHandPinky3": 92, "RightHandPinky4": 93,
        "LeftUpLegRoll": 41, "LeftLegRoll": 42, "RightUpLegRoll": 43, "RightLegRoll": 44,
        "LeftArmRoll": 45, "LeftForeArmRoll": 46, "RightArmRoll": 47, "RightForeArmRoll": 48,
    }

    # picker 槽位 → HIK 骨骼类型名
    SLOT_TO_HIK = {
        "hips": "Hips", "head": "Head", "neck": "Neck",
        "neck1": "Neck1", "neck2": "Neck2", "neck3": "Neck3",
        "neck4": "Neck4", "neck5": "Neck5",
        "spine1": "Spine", "spine2": "Spine1", "spine3": "Spine2", "spine4": "Spine3",
        "L_upleg": "LeftUpLeg", "L_leg": "LeftLeg",
        "L_foot": "LeftFoot", "L_ball": "LeftToeBase",
        "R_upleg": "RightUpLeg", "R_leg": "RightLeg",
        "R_foot": "RightFoot", "R_ball": "RightToeBase",
        "L_clavicle": "LeftShoulder", "L_shoulder": "LeftArm",
        "L_elbow": "LeftForeArm", "L_wrist": "LeftHand",
        "R_clavicle": "RightShoulder", "R_shoulder": "RightArm",
        "R_elbow": "RightForeArm", "R_wrist": "RightHand",
    }

    _FINGER_SLOT = ["thumb", "index", "middle", "ring", "pinky"]
    _FINGER_HIK = ["Thumb", "Index", "Middle", "Ring", "Pinky"]

    # 必填槽位（缺失时构建会失败）
    REQUIRED_SLOTS = [
        "hips", "head",
        "L_upleg", "L_leg", "L_foot", "R_upleg", "R_leg", "R_foot",
        "L_shoulder", "L_elbow", "L_wrist", "R_shoulder", "R_elbow", "R_wrist",
    ]

    def __init__(self, mapping, character_name="Character1"):
        self._mapping = mapping or {}
        self.character_name = character_name

    def _src(self, slot_id):
        joint = self._mapping.get(slot_id)
        if joint and cmds.objExists(joint):
            return joint
        return None

    @staticmethod
    def _joint_basename(joint_name):
        return joint_name.split("|")[-1]

    @staticmethod
    def _natural_sort_key(joint_name):
        name = joint_name.split("|")[-1].lower()
        parts = re.split(r"(\d+)", name)
        return [int(p) if p.isdigit() else p for p in parts]

    # ----------------------------------------------------------------
    # HIK 插件 / Character 管理
    # ----------------------------------------------------------------

    @staticmethod
    def _ensure_hik_loaded():
        if not cmds.pluginInfo("mayaHIK", q=True, loaded=True):
            cmds.loadPlugin("mayaHIK")
        try:
            mel.eval("HIKCharacterControlsTool;")
        except Exception:
            pass

    def _create_character(self):
        mel.eval('hikCreateCharacter("{0}")'.format(self.character_name))

    def _set_character_object(self, joint_name, hik_bone_name):
        hik_id = self.HIK_ID.get(hik_bone_name)
        if hik_id is None:
            cmds.warning("未知的 HIK 骨骼类型: {0}，跳过 {1}".format(hik_bone_name, joint_name))
            return
        if not cmds.objExists(joint_name):
            cmds.warning("Joint {0} 不存在，跳过 HIK 映射".format(joint_name))
            return
        # 优先用短名，歧义时用全路径
        short = joint_name.split("|")[-1].split(":")[-1]
        matches = cmds.ls(short, long=True) or []
        name = short if len(matches) == 1 else joint_name
        mel.eval(
            'setCharacterObject("{0}", "{1}", {2}, 0)'.format(
                name, self.character_name, hik_id)
        )

    def _lock_definition(self):
        mel.eval('hikSetCurrentCharacter("{0}")'.format(self.character_name))
        mel.eval("hikToggleLockDefinition")

    def _create_control_rig(self):
        mel.eval('hikSetCurrentCharacter("{0}")'.format(self.character_name))
        mel.eval("hikCreateControlRig")

    @staticmethod
    def _update_hik_ui():
        try:
            mel.eval("""
                if (`exists hikUpdateCharacterList`)
                {
                    hikUpdateCharacterList();
                    hikUpdateCurrentCharacterFromUI();
                    hikUpdateContextualUI();
                    hikControlRigSelectionChangedCallback;
                }
            """)
        except Exception:
            pass

    def _set_rig_look_stick(self):
        mel.eval('hikSetCurrentCharacter("{0}")'.format(self.character_name))
        try:
            mel.eval('hikSetRigLookAndFeel("{0}", 1)'.format(self.character_name))
        except Exception:
            cmds.warning("无法设置 Rig Look 为 Stick，请手动设置")
        self._update_hik_ui()

    # ----------------------------------------------------------------
    # 骨骼映射
    # ----------------------------------------------------------------

    def _map_body(self):
        for slot_id, hik_name in self.SLOT_TO_HIK.items():
            src = self._src(slot_id)
            if src:
                self._set_character_object(src, hik_name)

    def _map_fingers(self):
        for side_slot, side_hik in [("L", "Left"), ("R", "Right")]:
            for fn_slot, fn_hik in zip(self._FINGER_SLOT, self._FINGER_HIK):
                for i in (1, 2, 3):
                    slot_id = "{0}_{1}{2}".format(side_slot, fn_slot, i)
                    src = self._src(slot_id)
                    if src:
                        hik_name = "{0}Hand{1}{2}".format(side_hik, fn_hik, i)
                        self._set_character_object(src, hik_name)

    def _map_roll_bones(self):
        # twist/roll 不在 picker 中，从已映射肢体关节子级自动检测
        roll_map = [
            ("L_shoulder", "LeftArmRoll", "l"),
            ("L_elbow", "LeftForeArmRoll", "l"),
            ("L_upleg", "LeftUpLegRoll", "l"),
            ("L_leg", "LeftLegRoll", "l"),
            ("R_shoulder", "RightArmRoll", "r"),
            ("R_elbow", "RightForeArmRoll", "r"),
            ("R_upleg", "RightUpLegRoll", "r"),
            ("R_leg", "RightLegRoll", "r"),
        ]
        for slot_id, hik_name, side in roll_map:
            src = self._src(slot_id)
            if not src:
                continue
            children = cmds.listRelatives(src, c=True, type="joint") or []
            for child in children:
                child_lower = self._joint_basename(child).lower()
                if "twist" in child_lower and side in child_lower:
                    self._set_character_object(child, hik_name)
                    break

    # ----------------------------------------------------------------
    # 公开 API
    # ----------------------------------------------------------------

    def build(self):
        cmds.currentUnit(linear="cm")
        self._ensure_hik_loaded()

        if cmds.objExists(self.character_name):
            self.delete_controller()

        self._create_character()
        mel.eval('hikSetCurrentCharacter("{0}")'.format(self.character_name))
        self._update_hik_ui()

        self._map_body()
        self._map_fingers()
        self._map_roll_bones()

        self._lock_definition()
        self._update_hik_ui()

        self._create_control_rig()
        self._update_hik_ui()

        self._set_rig_look_stick()
        cmds.select(clear=True)

    def delete_controller(self):
        self._ensure_hik_loaded()
        character = self.character_name if cmds.objExists(self.character_name) else ""
        if not character:
            try:
                characters = mel.eval("hikGetSceneCharacters()") or []
            except Exception:
                characters = []
            if characters:
                character = characters[0]
        if not character:
            cmds.select(clear=True)
            return

        try:
            mel.eval('hikSetCurrentCharacter("{0}")'.format(character))
            self._update_hik_ui()
        except Exception:
            pass

        try:
            control_rig = mel.eval('hikGetControlRig("{0}")'.format(character))
        except Exception:
            control_rig = ""
        if control_rig:
            try:
                mel.eval("hikDeleteControlRig()")
            except Exception:
                if cmds.objExists(control_rig):
                    cmds.delete(control_rig)

        try:
            mel.eval('hikDeleteCharacter("{0}")'.format(character))
        except Exception:
            if cmds.objExists(character):
                cmds.delete(character)

        cmds.select(clear=True)


def build_hik_from_mapping(mapping, character_name="Character1"):
    """便捷入口：从 picker mapping 构建 HIK 控制器。"""
    builder = FbxToHIK(mapping, character_name)
    builder.build()
    return {"message": "HIK 控制器生成完成: {0}".format(character_name)}


def delete_hik_controller(character_name="Character1"):
    builder = FbxToHIK({}, character_name)
    builder.delete_controller()


if __name__ == "__main__":
    FbxToHIK({}).build()
