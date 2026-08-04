# -*- coding: utf-8 -*-
from __future__ import division
import io
import os
import re

import maya.cmds as cmds
import maya.mel as mel


class FbxToADV:
    """映射驱动的 AdvancedSkeleton 控制器生成。

    骨骼来源为 picker 的 self.mapping（槽位ID→关节全路径），
    不再按硬编码 UE 骨骼名自动检测。
    """

    ADV_VERSIONS = (
        ("AdvancedSkeleton",  "AdvancedSkeleton.mel",  "AdvancedSkeletonFiles",  "as"),
        ("AdvancedSkeleton5", "AdvancedSkeleton5.mel", "AdvancedSkeleton5Files", "as"),
    )

    FIT_SKELETON_REL_PARTS = ("fitSkeletons", "biped.ma")
    SHOULDER_HEIGHT_RATIO_REF = 0.235

    # FitSkeleton 对齐：(FitSkeleton节点, picker槽位)
    _FIT_ALIGN_PHASE1 = [
        ("Root",   "hips"),
        ("Hip",    "R_upleg"),
        ("Knee",   "R_leg"),
        ("Ankle",  "R_foot"),
        ("Spine1", "spine1"),
    ]
    _FIT_ALIGN_PHASE2 = [
        ("Scapula",  "R_clavicle"),
        ("Shoulder", "R_shoulder"),
        ("Elbow",    "R_elbow"),
        ("Wrist",    "R_wrist"),
    ]

    # twist 数量检测：(FitSkeleton节点, R侧slot, L侧slot, 末端R slot, 末端L slot)
    _TWIST_DETECT = [
        ("Hip",      "R_upleg",   "L_upleg",   "R_leg",  "L_leg"),
        ("Knee",     "R_leg",     "L_leg",     "R_foot", "L_foot"),
        ("Shoulder", "R_shoulder","L_shoulder","R_elbow","L_elbow"),
        ("Elbow",    "R_elbow",   "L_elbow",   "R_wrist","L_wrist"),
    ]

    # 脊柱槽位（按从底到顶顺序）
    SPINE_SLOTS = ["spine1", "spine2", "spine3", "spine4"]
    # 颈部槽位（按从底到顶顺序，neck 是第一节）
    NECK_SLOTS = ["neck", "neck1", "neck2", "neck3", "neck4", "neck5"]

    # 约束 — 中心线：(picker槽位, ADV build后骨骼名)
    _CONSTRAIN_CENTER = [
        ("hips",   "Root_M"),
        ("spine1", "Spine1_M"),
        ("spine2", "Spine2_M"),
        ("spine3", "Spine3_M"),
        ("spine4", "Chest_M"),
        ("neck",   "Neck_M"),
        ("neck1",  "Neck1_M"),
        ("neck2",  "Neck2_M"),
        ("neck3",  "Neck3_M"),
        ("neck4",  "Neck4_M"),
        ("neck5",  "Neck5_M"),
        ("head",   "Head_M"),
    ]

    # 约束 — 侧边：(picker槽位, ADV后缀) — ADV名 = 后缀 + "_L"/"_R"
    _CONSTRAIN_SIDED = [
        ("L_upleg", "Hip"), ("R_upleg", "Hip"),
        ("L_leg",   "Knee"), ("R_leg",   "Knee"),
        ("L_foot",  "Ankle"), ("R_foot",  "Ankle"),
        ("L_clavicle", "Scapula"), ("R_clavicle", "Scapula"),
        ("L_shoulder", "Shoulder"), ("R_shoulder", "Shoulder"),
        ("L_elbow", "Elbow"), ("R_elbow", "Elbow"),
        ("L_wrist", "Wrist"), ("R_wrist", "Wrist"),
    ]

    # 约束 — 手指：(picker槽位, ADV手指骨骼名)
    _FINGER_NAMES = ["thumb", "index", "middle", "ring", "pinky"]
    _CONSTRAIN_FINGER = []
    for _side_slot, _side_adv in [("L", "_L"), ("R", "_R")]:
        for _fn_slot, _fn_adv in [("thumb", "ThumbFinger"), ("index", "IndexFinger"),
                                  ("middle", "MiddleFinger"), ("ring", "RingFinger"),
                                  ("pinky", "PinkyFinger")]:
            for _i in (1, 2, 3):
                _CONSTRAIN_FINGER.append(
                    ("{0}_{1}{2}".format(_side_slot, _fn_slot, _i),
                     "{0}{1}{2}".format(_fn_adv, _i, _side_adv)))

    # twist 约束：(ADV前缀, R侧slot, L侧slot)
    _TWIST_CONSTRAIN = [
        ("Hip",      "R_upleg",   "L_upleg"),
        ("Knee",     "R_leg",     "L_leg"),
        ("Shoulder", "R_shoulder","L_shoulder"),
        ("Elbow",    "R_elbow",   "L_elbow"),
    ]

    # FitSkeleton biped 模板节点短名（导入后不可与外部骨骼冲突）
    _ADV_RESERVED_NAMES = {
        "FitSkeleton", "CameraFocusPos", "Root", "Hip", "Knee", "Ankle",
        "Toes", "Heel", "Spine1", "Spine2", "Spine3", "Chest",
        "Neck", "Neck1", "Neck2", "Head",
        "Scapula", "Shoulder", "Elbow", "Wrist", "Cup",
        "ThumbFinger1", "ThumbFinger2", "ThumbFinger3",
        "IndexFinger1", "IndexFinger2", "IndexFinger3",
        "MiddleFinger1", "MiddleFinger2", "MiddleFinger3",
        "RingFinger1", "RingFinger2", "RingFinger3",
        "PinkyFinger1", "PinkyFinger2", "PinkyFinger3",
    }

    _ADV_STUB_WINDOW = "_adv_ui_stubs_win"
    _ADV_UI_STUB_DEFS = [
        ("checkBox",   "asBodyZUpAxisCheckBox",            {}),
        ("checkBox",   "asAdvancedSkeletonZUpAxisCheckBox", {}),
        ("checkBox",   "asBodyGameEngineCheckBox",         {"value": False}),
        ("checkBox",   "asBodyOffsetParentMatrixCheckBox", {"value": False}),
        ("checkBox",   "asBodySubControllersCheckBox",     {"value": False}),
        ("checkBox",   "asBodyExtraControllersCheckBox",   {"value": False}),
        ("checkBox",   "asBodyMirTransCheckBox",           {"value": False}),
        ("checkBox",   "asVisGeo",                         {"value": False}),
        ("checkBox",   "asRebuildConnections",             {"value": True}),
        ("checkBox",   "asLockCenterJoints",               {"value": False}),
        ("checkBox",   "asVisPoleVector",                  {"value": False}),
        ("checkBox",   "asVisJointOrient",                 {"value": False}),
        ("checkBox",   "asVisJointAxis",                   {"value": False}),
        ("button",     "asToggleFitSkeletonButton",        {}),
        ("button",     "asBuildAdvancedSkeletonButton",    {}),
        ("button",     "asToggleFitFaceButton",            {}),
        ("button",     "asBuildAdvancedFaceButton",        {}),
        ("button",     "asGoToBuildPoseFaceButton",        {}),
        ("text",       "asBodyText",                       {}),
        ("text",       "asFaceText",                       {}),
        ("rowLayout",  "asFaceRebuildKeepBSRowLayout",     {}),
        ("optionMenu", "asVisGeoType",                     {"items": ["cylinders", "boxes", "spheres"]}),
        ("floatSliderGrp", "asVisGap",                     {"value": 1.0}),
        ("floatField", "ScaleCCFloatField",                {"value": 1.0}),
    ]

    _ADV_BUILD_TOP_NODES = (
        "Group", "DeformationSystem", "MotionSystem", "Aims",
        "Geometry", "FitSkeletonVisualizers",
        "Sets", "DeformSet", "ControlSet", "AllSet",
    )

    _FINGER_DETECT_MAP = [
        ("Thumb",  "thumb"),
        ("Index",  "index"),
        ("Middle", "middle"),
        ("Ring",   "ring"),
        ("Pinky",  "pinky"),
    ]

    # ============================================================
    # 初始化
    # ============================================================

    def __init__(self, mapping=None, fit_file=None):
        base, version_info = self._find_advancedskeleton_base()
        self.advancedskeleton_base = base
        self._adv_mel_name = version_info[1]
        self._adv_files_dirname = version_info[2]
        self._adv_mel_prefix = version_info[3]

        self._is_z_up = (cmds.upAxis(q=True, ax=True) == "z")
        self._mapping = mapping or {}

        default_fit_file = os.path.join(
            self.advancedskeleton_base,
            self._adv_files_dirname,
            *self.FIT_SKELETON_REL_PARTS
        )
        self.fit_file = self._normalize_path(fit_file or default_fit_file)

    def _src(self, slot_id):
        """从 mapping 获取关节全路径，不存在返回 None。"""
        joint = self._mapping.get(slot_id)
        if joint and cmds.objExists(joint):
            return joint
        return None

    # ============================================================
    # 静态工具方法
    # ============================================================

    def _get_height(self, pos):
        return pos[2] if self._is_z_up else pos[1]

    @staticmethod
    def _zero_center_axis(pos):
        pos = list(pos)
        pos[0] = 0.0
        return pos

    @staticmethod
    def _joint_basename(joint_name):
        return joint_name.split("|")[-1]

    @staticmethod
    def _natural_sort_key(joint_name):
        name = FbxToADV._joint_basename(joint_name).lower()
        parts = re.split(r"(\d+)", name)
        return [int(p) if p.isdigit() else p for p in parts]

    @staticmethod
    def _distance(pos_a, pos_b):
        return sum((a - b) ** 2 for a, b in zip(pos_a, pos_b)) ** 0.5

    @staticmethod
    def _midpoint(pos_a, pos_b):
        return [(a + b) / 2 for a, b in zip(pos_a, pos_b)]

    @staticmethod
    def _set_uniform_scale(node, value):
        for axis in ("scaleX", "scaleY", "scaleZ"):
            cmds.setAttr("{0}.{1}".format(node, axis), value)

    @staticmethod
    def _safe_set_attr(node, attr, value):
        if cmds.attributeQuery(attr, node=node, exists=True):
            cmds.setAttr("{0}.{1}".format(node, attr), value)

    @staticmethod
    def _safe_parent(child, parent):
        current_parents = cmds.listRelatives(child, parent=True) or []
        if current_parents and current_parents[0] == parent:
            return
        cmds.parent(child, parent)

    @staticmethod
    def _normalize_path(path):
        return os.path.normpath(path).replace("\\", "/")

    @staticmethod
    def _safe_match_transform(fit_node, source_node, pos=True, rot=False):
        if not fit_node or not source_node:
            return False
        if not cmds.objExists(fit_node) or not cmds.objExists(source_node):
            return False
        try:
            cmds.matchTransform(fit_node, source_node, pos=pos, rot=rot)
            return True
        except Exception as exc:
            cmds.warning("跳过对齐 {0} <- {1}: {2}".format(fit_node, source_node, exc))
            return False

    # ============================================================
    # AdvancedSkeleton 路径查找
    # ============================================================

    @classmethod
    def _is_valid_advancedskeleton_base(cls, base_path):
        if not base_path:
            return None
        for version_info in cls.ADV_VERSIONS:
            _dirname, mel_name, files_dirname, _prefix = version_info
            mel_file = os.path.join(base_path, mel_name)
            fit_file = os.path.join(
                base_path, files_dirname, *cls.FIT_SKELETON_REL_PARTS)
            if os.path.isfile(mel_file) and os.path.isfile(fit_file):
                return version_info
        return None

    @classmethod
    def _extract_adv_paths_from_shelves(cls):
        pattern = re.compile(
            r'source\s+"([^"]+[/\\]AdvancedSkeleton5?\.mel)"', re.IGNORECASE)
        results = []
        seen = set()

        def _add_from_text(text):
            for match in pattern.finditer(text):
                mel_path = match.group(1).replace("\\", "/")
                adv_dir = "/".join(mel_path.split("/")[:-1])
                key = os.path.normpath(adv_dir).lower()
                if key not in seen:
                    seen.add(key)
                    results.append(os.path.normpath(adv_dir))

        try:
            top_shelf = mel.eval("$tmpVar=$gShelfTopLevel")
            if top_shelf and cmds.layout(top_shelf, exists=True):
                shelf_names = cmds.tabLayout(top_shelf, query=True, childArray=True) or []
                original_tab = cmds.tabLayout(top_shelf, query=True, selectTab=True) or ""
                for shelf_name in shelf_names:
                    shelf_full = "{0}|{1}".format(top_shelf, shelf_name)
                    if not cmds.shelfLayout(shelf_full, exists=True):
                        continue
                    try:
                        cmds.tabLayout(top_shelf, edit=True, selectTab=shelf_name)
                    except Exception:
                        pass
                    buttons = cmds.shelfLayout(shelf_full, query=True, childArray=True) or []
                    for btn in buttons:
                        btn_full = "{0}|{1}".format(shelf_full, btn)
                        if not cmds.shelfButton(btn_full, exists=True):
                            continue
                        try:
                            cmd_str = cmds.shelfButton(btn_full, query=True, command=True) or ""
                        except Exception:
                            continue
                        _add_from_text(cmd_str)
                if original_tab:
                    try:
                        cmds.tabLayout(top_shelf, edit=True, selectTab=original_tab)
                    except Exception:
                        pass
        except Exception:
            pass

        try:
            shelf_dirs = []
            user_app_dir = cmds.internalVar(userAppDir=True) or ""
            if user_app_dir:
                maya_version = cmds.about(version=True) or ""
                if maya_version:
                    shelf_dirs.append(os.path.join(user_app_dir, maya_version, "prefs", "shelves"))
                shelf_dirs.append(os.path.join(user_app_dir, "prefs", "shelves"))
            for shelf_dir in shelf_dirs:
                if not os.path.isdir(shelf_dir):
                    continue
                for fname in os.listdir(shelf_dir):
                    if not fname.lower().endswith(".mel"):
                        continue
                    fpath = os.path.join(shelf_dir, fname)
                    try:
                        with io.open(fpath, "r", encoding="utf-8", errors="ignore") as fh:
                            _add_from_text(fh.read())
                    except Exception:
                        continue
        except Exception:
            pass
        return results

    @classmethod
    def _find_advancedskeleton_base(cls):
        checked_paths = []
        for candidate in cls._extract_adv_paths_from_shelves():
            checked_paths.append(cls._normalize_path(candidate))
            version_info = cls._is_valid_advancedskeleton_base(candidate)
            if version_info is not None:
                return cls._normalize_path(candidate), version_info
        checked_preview = "\n".join("- {0}".format(path) for path in checked_paths)
        raise RuntimeError(
            "无法从 Shelf 按钮中找到 AdvancedSkeleton 安装目录。"
            + ("\n已检查路径：\n{0}".format(checked_preview) if checked_preview else ""))

    # ============================================================
    # MEL 辅助
    # ============================================================

    def _mel_cmd(self, proc_suffix):
        full_name = "{0}{1}".format(self._adv_mel_prefix, proc_suffix)
        mel.eval("{0};".format(full_name))

    def _mel_cmd_if_exists(self, proc_suffix):
        full_name = "{0}{1}".format(self._adv_mel_prefix, proc_suffix)
        try:
            registered = int(mel.eval('exists "{0}";'.format(full_name)))
        except Exception:
            registered = 0
        if not registered:
            cmds.warning("AdvancedSkeleton proc '{0}' not found, skipped.".format(full_name))
            return False
        mel.eval("{0};".format(full_name))
        return True

    @classmethod
    def _ensure_adv_ui_stubs(cls):
        if cmds.window(cls._ADV_STUB_WINDOW, exists=True):
            cmds.deleteUI(cls._ADV_STUB_WINDOW, window=True)
        cmds.window(cls._ADV_STUB_WINDOW, title="ADV Stubs", visible=False)
        cmds.columnLayout()
        is_z_up = cmds.upAxis(q=True, ax=True) == "z"
        for ctrl_type, ctrl_name, params in cls._ADV_UI_STUB_DEFS:
            if cmds.control(ctrl_name, exists=True):
                continue
            if ctrl_type == "checkBox":
                default_val = params.get("value", is_z_up if "ZUp" in ctrl_name else False)
                cmds.checkBox(ctrl_name, value=default_val)
            elif ctrl_type == "floatField":
                cmds.floatField(ctrl_name, **params)
            elif ctrl_type == "optionMenu":
                cmds.optionMenu(ctrl_name)
                for item_label in params.get("items", []):
                    cmds.menuItem(label=item_label, parent=ctrl_name)
            elif ctrl_type == "floatSliderGrp":
                cmds.floatSliderGrp(ctrl_name, value=params.get("value", 0.0))
            elif ctrl_type == "button":
                cmds.button(ctrl_name, label=ctrl_name)
            elif ctrl_type == "text":
                cmds.text(ctrl_name, label=ctrl_name)
            elif ctrl_type == "rowLayout":
                cmds.rowLayout(ctrl_name, numberOfColumns=1)
                cmds.setParent("..")
        cmds.setParent("..")

    # ============================================================
    # 命名冲突处理
    # ============================================================

    def _rename_conflicting_joints(self):
        """重命名与 FitSkeleton 模板节点同名的外部骨骼，避免 MEL 短名歧义。"""
        seen_paths = set()
        to_rename = []
        for slot_id, joint in self._mapping.items():
            if not joint or joint in seen_paths:
                continue
            if not cmds.objExists(joint):
                continue
            short = joint.split("|")[-1].split(":")[-1]
            if short in self._ADV_RESERVED_NAMES:
                to_rename.append((joint, short))
                seen_paths.add(joint)
        to_rename.sort(key=lambda x: x[0].count("|"))
        if not to_rename:
            return
        done = {}
        for joint, short in to_rename:
            parts = joint.split("|")
            cur_parts = [done.get(p.split(":")[-1], p) for p in parts]
            cur_path = "|".join(cur_parts)
            new_short = "{0}_src".format(short)
            try:
                cmds.rename(cur_path, new_short)
                done[short] = new_short
            except Exception as exc:
                cmds.warning("重命名 {0} -> {1} 失败: {2}".format(cur_path, new_short, exc))
        if not done:
            return
        for slot_id in list(self._mapping.keys()):
            old_path = self._mapping[slot_id]
            if not old_path:
                continue
            parts = old_path.split("|")
            new_parts = [done.get(p.split(":")[-1], p) for p in parts]
            new_path = "|".join(new_parts)
            if cmds.objExists(new_path):
                self._mapping[slot_id] = new_path
            else:
                short = new_parts[-1].split(":")[-1]
                candidates = cmds.ls(short, long=True) or []
                if len(candidates) == 1:
                    self._mapping[slot_id] = candidates[0]
                else:
                    cmds.warning("重命名后无法唯一定位槽位 {0}，保留原路径".format(slot_id))
        cmds.warning("已重命名冲突骨骼以避免 ADV 命名歧义: {0}".format(list(done.keys())))

    # ============================================================
    # 关节查询
    # ============================================================

    def _get_descendant_joints(self, root_joint, prefix):
        if not cmds.objExists(root_joint):
            raise RuntimeError("场景中没有找到对象: {0}".format(root_joint))
        descendants = cmds.listRelatives(root_joint, ad=True, type="joint", fullPath=True) or []
        matched = [j for j in descendants
                   if self._joint_basename(j).lower().startswith(prefix.lower())]
        matched.sort(key=self._natural_sort_key)
        if not matched:
            raise RuntimeError("在 {0} 的子级中没有找到以 '{1}' 开头的 joint".format(root_joint, prefix))
        return matched

    # ============================================================
    # twist 检测
    # ============================================================

    def _get_source_twist_joints(self, source_root):
        """获取 mapping 肢体关节子级的 twist 骨骼，按距离排序。"""
        if not cmds.objExists(source_root):
            return []
        matched = []
        seen = set()
        children = cmds.listRelatives(source_root, c=True, type="joint", fullPath=True) or []
        for joint in children:
            name = self._joint_basename(joint).split(":")[-1].lower()
            if "twist" not in name or "twistcor" in name:
                continue
            key = joint.lower()
            if key not in seen:
                seen.add(key)
                matched.append(joint)
        if not matched:
            return []
        parent_pos = cmds.xform(source_root, q=True, ws=True, t=True)
        distance_items = []
        for joint in matched:
            joint_pos = cmds.xform(joint, q=True, ws=True, t=True)
            distance_items.append((self._distance(parent_pos, joint_pos), joint))
        distance_items.sort(key=lambda item: (item[0], self._natural_sort_key(item[1])))
        return [item[1] for item in distance_items]

    def _get_adv_twist_joints(self, adv_prefix, side_adv):
        matched = []
        seen = set()
        part_idx = 1
        while True:
            part_name = "{0}Part{1}{2}".format(adv_prefix, part_idx, side_adv)
            if not cmds.objExists(part_name):
                break
            matched.append(part_name)
            seen.add(part_name.lower())
            part_idx += 1
        adv_root = "{0}{1}".format(adv_prefix, side_adv)
        if cmds.objExists(adv_root):
            descendants = cmds.listRelatives(adv_root, ad=True, type="joint", fullPath=True) or []
            side_lower = side_adv.lower()
            part_pattern = re.compile(
                r"^{0}part\d+{1}$".format(re.escape(adv_prefix.lower()), re.escape(side_lower)))
            for joint in descendants:
                name = self._joint_basename(joint).split(":")[-1].lower()
                if not name.endswith(side_lower):
                    continue
                if "twist" not in name and not part_pattern.match(name):
                    continue
                key = joint.lower()
                if key in seen:
                    continue
                seen.add(key)
                matched.append(joint)
        matched.sort(key=self._natural_sort_key)
        return matched

    def _set_twist_joint_count(self, fit_joint, slot_r, slot_l):
        counts = []
        for slot_id in (slot_r, slot_l):
            src = self._src(slot_id)
            if src:
                counts.append(len(self._get_source_twist_joints(src)))
        self._safe_set_attr(fit_joint, "twistJoints", max(counts) if counts else 0)

    # ============================================================
    # FitSkeleton 脊柱/颈部/手指
    # ============================================================

    def _duplicate_joint_to_fit(self, source_joint, new_name, parent_fit_node,
                                force_center=False, no_control=True):
        pos = cmds.xform(source_joint, q=True, ws=True, t=True)
        rot = cmds.xform(source_joint, q=True, ws=True, ro=True)
        if force_center:
            pos = self._zero_center_axis(pos)
        cmds.select(clear=True)
        new_joint = cmds.joint(name=new_name)
        cmds.xform(new_joint, ws=True, t=pos)
        cmds.xform(new_joint, ws=True, ro=rot)
        cmds.parent(new_joint, parent_fit_node)
        if no_control:
            cmds.addAttr(new_joint, ln="tempInbetweener", at="bool", dv=1, k=True)
            cmds.addAttr(new_joint, ln="noControl", at="bool", dv=1, k=True)
            cmds.setAttr("{0}.noControl".format(new_joint), 1)
        for attr in ("fat", "fatFront", "fatWidth"):
            parent_val = 0.0
            if cmds.attributeQuery(attr, node=parent_fit_node, exists=True):
                parent_val = cmds.getAttr("{0}.{1}".format(parent_fit_node, attr))
            cmds.addAttr(new_joint, ln=attr, at="double", dv=parent_val, k=False)
        return new_joint

    def _setup_spine(self):
        """按 mapped spine 槽位创建 ADV 脊柱分段。"""
        spine_srcs = [self._src(s) for s in self.SPINE_SLOTS]
        spine_srcs = [s for s in spine_srcs if s]
        if not spine_srcs:
            cmds.warning("未映射脊柱骨骼，跳过脊柱设置")
            return
        spine1_source = spine_srcs[0]
        chest_source = spine_srcs[-1]
        self._safe_match_transform("Spine1", spine1_source, pos=True)
        self._safe_match_transform("Chest", chest_source, pos=True)
        self._safe_set_attr("Root", "inbetweenJoints", 0)
        self._safe_set_attr("Spine1", "inbetweenJoints", 0)
        self._spine_mid_names = []
        mid_sources = spine_srcs[1:-1]
        current_parent = "Spine1"
        for i, src in enumerate(mid_sources):
            mid_name = "Spine{0}".format(i + 2)
            self._duplicate_joint_to_fit(src, mid_name, current_parent,
                                         force_center=True, no_control=False)
            self._spine_mid_names.append(mid_name)
            current_parent = mid_name
        if mid_sources:
            self._safe_parent("Chest", current_parent)

    def _setup_neck(self):
        """按 mapped neck 槽位创建 ADV 颈部分段。"""
        neck_src = self._src("neck")
        head_src = self._src("head")
        if not neck_src or not head_src:
            cmds.warning("未映射 neck/head，跳过颈部设置")
            return
        self._safe_set_attr("Neck", "inbetweenJoints", 0)
        self._safe_match_transform("Neck", neck_src, pos=True)
        self._safe_match_transform("Head", head_src, pos=True)
        neck_mids = [self._src(s) for s in self.NECK_SLOTS[1:]]
        neck_mids = [s for s in neck_mids if s]
        current_parent = "Neck"
        for i, src in enumerate(neck_mids):
            part_name = "Neck{0}".format(i + 1)
            self._duplicate_joint_to_fit(src, part_name, current_parent,
                                         force_center=True, no_control=False)
            current_parent = part_name
        if neck_mids:
            self._safe_parent("Head", current_parent)

    # ============================================================
    # 手指检测/对齐
    # ============================================================

    def _remove_fit_finger_segments(self, fit_prefix, start_index):
        for i in range(start_index, 5):
            node = "{0}Finger{1}".format(fit_prefix, i)
            if cmds.objExists(node):
                cmds.delete(node)

    def _detect_scene_finger_counts(self):
        counts = {}
        for fn in ("thumb", "index", "middle", "ring", "pinky"):
            count = 0
            for i in (1, 2, 3):
                if self._src("R_{0}{1}".format(fn, i)) or self._src("L_{0}{1}".format(fn, i)):
                    count = i
            counts[fn] = count
        return counts

    def _remove_fit_fingers_and_cup(self, finger_counts):
        for fit_prefix, fbx_prefix in self._FINGER_DETECT_MAP:
            keep_count = finger_counts.get(fbx_prefix, 0)
            start_index = 1 if keep_count <= 0 else keep_count + 1
            self._remove_fit_finger_segments(fit_prefix, start_index)
        if finger_counts.get("ring", 0) <= 0 and finger_counts.get("pinky", 0) <= 0:
            if cmds.objExists("Cup"):
                try:
                    cmds.delete("Cup")
                except Exception:
                    pass

    def _remove_extra_adv_fingers(self, finger_counts):
        for fit_prefix, fbx_prefix in self._FINGER_DETECT_MAP:
            keep_count = finger_counts.get(fbx_prefix, 0)
            patterns = []
            if keep_count <= 0:
                patterns.append("*{0}Finger*_*".format(fit_prefix))
            else:
                for i in range(keep_count + 1, 5):
                    patterns.append("*{0}Finger{1}_*".format(fit_prefix, i))
                    patterns.append("FK{0}Finger{1}_*".format(fit_prefix, i))
                    patterns.append("IK{0}Finger{1}_*".format(fit_prefix, i))
            nodes = set()
            for pattern in patterns:
                nodes.update(cmds.ls(pattern, type="transform") or [])
            for node in sorted(nodes, key=lambda x: x.count("|"), reverse=True):
                if cmds.objExists(node):
                    try:
                        cmds.delete(node)
                    except Exception:
                        pass
        if finger_counts.get("ring", 0) <= 0 and finger_counts.get("pinky", 0) <= 0:
            cup_nodes = set()
            for pattern in ("Cup_*", "FKCup_*", "IKCup_*"):
                cup_nodes.update(cmds.ls(pattern, type="transform") or [])
            for node in sorted(cup_nodes, key=lambda x: x.count("|"), reverse=True):
                if cmds.objExists(node):
                    try:
                        cmds.delete(node)
                    except Exception:
                        pass

    def _align_fingers(self):
        finger_fit = [
            ("thumb",  ["ThumbFinger1",  "ThumbFinger2",  "ThumbFinger3",  "ThumbFinger4"]),
            ("index",  ["IndexFinger1",  "IndexFinger2",  "IndexFinger3",  "IndexFinger4"]),
            ("middle", ["MiddleFinger1", "MiddleFinger2", "MiddleFinger3", "MiddleFinger4"]),
            ("ring",   ["RingFinger1",   "RingFinger2",   "RingFinger3",   "RingFinger4"]),
            ("pinky",  ["PinkyFinger1",  "PinkyFinger2",  "PinkyFinger3",  "PinkyFinger4"]),
        ]
        for fn_slot, fit_names in finger_fit:
            for i, fit_name in enumerate(fit_names, start=1):
                slot_id = "R_{0}{1}".format(fn_slot, i)
                src = self._src(slot_id)
                if src:
                    self._safe_match_transform(fit_name, src, pos=True, rot=True)

    # ============================================================
    # FitSkeleton 对齐
    # ============================================================

    @staticmethod
    def _delete_useless_bones():
        for bone in ("Eye", "Jaw"):
            if cmds.objExists(bone):
                cmds.delete(bone)

    def _align_fit_skeleton(self):
        # 1. 全局缩放（身高 + 肩宽修正）
        head_src = self._src("head")
        if head_src:
            head_height = self._get_height(cmds.xform(head_src, q=True, ws=True, t=True))
        else:
            cmds.warning("未映射 head，使用默认 ADV 缩放")
            head_height = 10.0

        sh_l = self._src("L_shoulder")
        sh_r = self._src("R_shoulder")
        if sh_l and sh_r:
            shoulder_dist = self._distance(
                cmds.xform(sh_l, q=True, ws=True, rp=True),
                cmds.xform(sh_r, q=True, ws=True, rp=True))
        else:
            shoulder_dist = head_height * self.SHOULDER_HEIGHT_RATIO_REF

        ratio = shoulder_dist / head_height if head_height else self.SHOULDER_HEIGHT_RATIO_REF
        correction = ratio / self.SHOULDER_HEIGHT_RATIO_REF
        self._correction = correction
        ctrl_correction_threshold = 0.78
        if correction >= ctrl_correction_threshold:
            self._body_correction = 1.0
        else:
            self._body_correction = correction / ctrl_correction_threshold

        base_scale = head_height / 10.0
        final_scale = base_scale * correction
        self._set_uniform_scale("FitSkeleton", final_scale)

        # 2. Phase1 对齐
        for fit_node, slot_id in self._FIT_ALIGN_PHASE1:
            src = self._src(slot_id)
            if src:
                self._safe_match_transform(fit_node, src, pos=True)

        # 3. twist joint 数量
        for fit_joint, slot_r, slot_l, _end_r, _end_l in self._TWIST_DETECT:
            self._set_twist_joint_count(fit_joint, slot_r, slot_l)

        # 4. Toes
        toes_src = self._src("R_ball")
        if toes_src:
            self._safe_match_transform("Toes", toes_src, pos=True)
        else:
            cmds.warning("未映射 R_ball，跳过 Toes 对齐")

        # 5. 脊柱分段
        self._setup_spine()

        # 6. Neck / Head
        neck_src = self._src("neck")
        if neck_src:
            self._safe_match_transform("Neck", neck_src, pos=True)
        if head_src:
            self._safe_match_transform("Head", head_src, pos=True)

        # 7. Phase2 对齐
        for fit_node, slot_id in self._FIT_ALIGN_PHASE2:
            src = self._src(slot_id)
            if src:
                self._safe_match_transform(fit_node, src, pos=True)

        # 8. 颈部分段
        self._setup_neck()

        # 9. Cup（手掌中心）
        hand_src = self._src("R_wrist")
        if hand_src and cmds.objExists("Cup"):
            hand_pos = cmds.xform(hand_src, q=True, ws=True, t=True)
            cup_ref_pos = hand_pos
            for outer_prefix in ("pinky", "ring", "middle", "index", "thumb"):
                outer_src = self._src("R_{0}1".format(outer_prefix))
                if outer_src:
                    cup_ref_pos = cmds.xform(outer_src, q=True, ws=True, t=True)
                    break
            cmds.xform("Cup", ws=True, t=self._midpoint(hand_pos, cup_ref_pos))

        # 10. 手指对齐
        self._align_fingers()

    # ============================================================
    # 控制器缩放
    # ============================================================

    def _scale_control_curve(self, ctrl_name, scale_value):
        if not cmds.objExists(ctrl_name):
            cmds.warning("控制器 {0} 不存在，跳过缩放。".format(ctrl_name))
            return
        shapes = cmds.listRelatives(ctrl_name, shapes=True, type="nurbsCurve",
                                    fullPath=True) or []
        if not shapes:
            cmds.warning("控制器 {0} 下没有 nurbsCurve shape，跳过缩放。".format(ctrl_name))
            return
        cv_list = []
        for shape in shapes:
            num_cvs = cmds.getAttr("{0}.controlPoints".format(shape), size=True)
            if num_cvs > 0:
                cv_list.append("{0}.cv[0:{1}]".format(shape, num_cvs - 1))
        if not cv_list:
            return
        pivot = cmds.xform(ctrl_name, q=True, ws=True, rp=True)
        cmds.select(cv_list, replace=True)
        cmds.scale(scale_value, scale_value, scale_value,
                   pivot=(pivot[0], pivot[1], pivot[2]), relative=True)
        cmds.select(clear=True)

    def _scale_finger_controls(self, scale_value=0.7):
        finger_prefixes = ("Thumb", "Index", "Middle", "Ring", "Pinky")
        sides = ("_L", "_R")
        for prefix in finger_prefixes:
            for side in sides:
                pattern = "FK{0}Finger*{1}".format(prefix, side)
                matches = cmds.ls(pattern, type="transform") or []
                for ctrl in matches:
                    shapes = cmds.listRelatives(ctrl, shapes=True, type="nurbsCurve") or []
                    if shapes:
                        self._scale_control_curve(ctrl, scale_value)

    # ============================================================
    # ADV → FBX 约束
    # ============================================================

    def _constrain_adv_to_fbx(self):
        constrained = [0]

        def _exists(name):
            return cmds.objExists(name)

        def _do_pos_orient_scale(adv_joint, fbx_joint):
            if not _exists(adv_joint) or not _exists(fbx_joint):
                return False
            try:
                cmds.pointConstraint(adv_joint, fbx_joint, mo=True, weight=1.0)
                cmds.orientConstraint(adv_joint, fbx_joint, mo=True, weight=1.0)
                cmds.scaleConstraint(adv_joint, fbx_joint, mo=True, weight=1.0)
                constrained[0] += 1
                return True
            except Exception as exc:
                cmds.warning("约束 {0} -> {1} 失败: {2}".format(adv_joint, fbx_joint, exc))
                return False

        def _do_pos_orient(adv_joint, fbx_joint):
            if not _exists(adv_joint) or not _exists(fbx_joint):
                return False
            try:
                cmds.pointConstraint(adv_joint, fbx_joint, mo=True, weight=1.0)
                cmds.orientConstraint(adv_joint, fbx_joint, mo=True, weight=1.0)
                constrained[0] += 1
                return True
            except Exception as exc:
                cmds.warning("约束 {0} -> {1} 失败: {2}".format(adv_joint, fbx_joint, exc))
                return False

        def _do_parent(adv_joint, fbx_joint):
            if not _exists(adv_joint) or not _exists(fbx_joint):
                return False
            try:
                cmds.parentConstraint(adv_joint, fbx_joint, mo=True, weight=1.0)
                constrained[0] += 1
                return True
            except Exception as exc:
                cmds.warning("约束 {0} -> {1} 失败: {2}".format(adv_joint, fbx_joint, exc))
                return False

        def _do_orient_only(adv_joint, fbx_joint):
            if not _exists(adv_joint) or not _exists(fbx_joint):
                return False
            try:
                cmds.orientConstraint(adv_joint, fbx_joint, mo=True, weight=1.0)
                constrained[0] += 1
                return True
            except Exception as exc:
                cmds.warning("约束 {0} -> {1} 失败: {2}".format(adv_joint, fbx_joint, exc))
                return False

        # 1. 中心线骨骼
        for slot_id, adv_name in self._CONSTRAIN_CENTER:
            src = self._src(slot_id)
            if src:
                _do_pos_orient_scale(adv_name, src)

        # 2. 左右侧骨骼
        for slot_id, adv_suffix in self._CONSTRAIN_SIDED:
            src = self._src(slot_id)
            if src:
                side = "_L" if slot_id.startswith("L_") else "_R"
                adv_name = "{0}{1}".format(adv_suffix, side)
                _do_pos_orient_scale(adv_name, src)

        # 3. Twist 骨骼
        for adv_prefix, slot_r, slot_l in self._TWIST_CONSTRAIN:
            for side_adv, slot_id in [("_R", slot_r), ("_L", slot_l)]:
                source_root = self._src(slot_id)
                if not source_root:
                    continue
                adv_twists = self._get_adv_twist_joints(adv_prefix, side_adv)
                fbx_twists = self._get_source_twist_joints(source_root)
                for adv_twist, fbx_twist in zip(adv_twists, fbx_twists):
                    _do_pos_orient(adv_twist, fbx_twist)

        # 4. correctiveRoot（按标准名检测，不在 picker 中）
        for adv_prefix, slot_r, slot_l in self._TWIST_CONSTRAIN:
            for side_adv, slot_id in [("_R", slot_r), ("_L", slot_l)]:
                side_fbx = "_r" if side_adv == "_R" else "_l"
                fbx_corrective = "{0}_correctiveRoot{1}".format(adv_prefix.lower(), side_fbx)
                if _exists(fbx_corrective):
                    adv_joint = "{0}{1}".format(adv_prefix, side_adv)
                    _do_parent(adv_joint, fbx_corrective)

        # 5. real 骨骼（orientConstraint only，按标准名检测）
        for adv_prefix, slot_r, slot_l in self._TWIST_CONSTRAIN:
            for side_adv, slot_id in [("_R", slot_r), ("_L", slot_l)]:
                side_fbx = "_r" if side_adv == "_R" else "_l"
                fbx_real = "{0}_real{1}".format(adv_prefix.lower(), side_fbx)
                if _exists(fbx_real):
                    adv_joint = "{0}{1}".format(adv_prefix, side_adv)
                    _do_orient_only(adv_joint, fbx_real)

        # 6. 手指骨骼
        for slot_id, adv_name in self._CONSTRAIN_FINGER:
            src = self._src(slot_id)
            if src:
                _do_pos_orient_scale(adv_name, src)

        # 7. metacarpal（掌骨，按标准名检测）
        finger_metacarpal_map = [
            ("IndexFinger1",  "index_metacarpal"),
            ("MiddleFinger1", "middle_metacarpal"),
            ("RingFinger1",   "ring_metacarpal"),
            ("PinkyFinger1",  "pinky_metacarpal"),
        ]
        for adv_finger_base, fbx_prefix in finger_metacarpal_map:
            for side_adv, side_fbx in [("_R", "_r"), ("_L", "_l")]:
                fbx_meta = "{0}{1}".format(fbx_prefix, side_fbx)
                if _exists(fbx_meta):
                    adv_name = "{0}{1}".format(adv_finger_base, side_adv)
                    _do_pos_orient_scale(adv_name, fbx_meta)

        # 8. Toes（脚趾）
        for slot_id in ("R_ball", "L_ball"):
            src = self._src(slot_id)
            if src:
                side = "_L" if slot_id.startswith("L_") else "_R"
                _do_pos_orient_scale("Toes{0}".format(side), src)

    # ============================================================
    # Root 骨骼
    # ============================================================

    def _add_root_vv(self):
        """在 mapped hips 骨骼上方创建 root 根骨骼。"""
        hips = self._src("hips")
        if not hips:
            cmds.warning("未映射 hips，跳过创建 root")
            return
        pelvis_parents = cmds.listRelatives(hips, parent=True, fullPath=True) or []
        cmds.select(clear=True)
        root_jnt = cmds.joint(name="root", position=[0, 0, 0])
        radius = cmds.getAttr("{0}.radius".format(hips))
        cmds.setAttr("{0}.radius".format(root_jnt), radius)
        if pelvis_parents:
            cmds.parent(root_jnt, pelvis_parents[0])
        cmds.parent(hips, root_jnt)

    @staticmethod
    def _remove_root_bone():
        all_joints = cmds.ls(type="joint", long=True) or []
        root_joints = [j for j in all_joints if j.split("|")[-1].lower() == "root"]
        if not root_joints:
            return False
        for root_jnt in root_joints:
            if not cmds.objExists(root_jnt):
                continue
            children = cmds.listRelatives(root_jnt, children=True, fullPath=True) or []
            if children:
                cmds.parent(children, world=True)
            cmds.delete(root_jnt)
        return True

    # ============================================================
    # 公开 API
    # ============================================================

    def build(self, generate_root=True):
        cmds.currentUnit(linear="cm")

        mel_path = self._normalize_path(
            os.path.join(self.advancedskeleton_base, self._adv_mel_name))
        mel.eval('source "{0}";'.format(mel_path))
        self._ensure_adv_ui_stubs()
        self._remove_root_bone()
        self._rename_conflicting_joints()

        if not cmds.objExists("FitSkeleton"):
            adv_base = mel.eval("asGetScriptLocation;")
            biped_ma = "{0}/{1}/fitSkeletons/biped.ma".format(adv_base, self._adv_files_dirname)
            mel.eval('file -import -rpr "AdvancedSkeleton" -options "v=0" "{0}";'.format(biped_ma))

        self._mel_cmd("EnsureFitSkeletonAttributes")
        self._mel_cmd_if_exists("EnsureAllFitJointAttrs")
        for attr_name in ("preRebuildScript", "postRebuildScript"):
            if not cmds.attributeQuery(attr_name, node="FitSkeleton", exists=True):
                cmds.addAttr("FitSkeleton", ln=attr_name, dt="string")

        up_axis = cmds.upAxis(q=True, ax=True)
        if up_axis == "z":
            cmds.setAttr("FitSkeleton.rotateX", -90)
            cmds.makeIdentity("FitSkeleton", apply=True, rotate=True)

        self._finger_source_counts = self._detect_scene_finger_counts()
        self._align_fit_skeleton()
        self._delete_useless_bones()
        self._remove_fit_fingers_and_cup(self._finger_source_counts)

        self._mel_cmd("FitModeManualUpdate")
        self._mel_cmd("ReBuildAdvancedSkeleton")
        self._remove_extra_adv_fingers(self._finger_source_counts)

        # 缩放控制器
        self._scale_control_curve("HipSwinger_M", 0.5)
        torso_control_groups = (
            ("FKSpine1_M", "IKSpine2_M", "IKhybridSpine2_M"),
            ("FKChest_M", "IKSpine3_M", "IKhybridSpine3_M"),
        )
        for control_group in torso_control_groups:
            for ctrl_name in control_group:
                self._scale_control_curve(ctrl_name, self._body_correction)
        for name in getattr(self, '_spine_mid_names', []):
            ctrl = "FK{0}_M".format(name)
            if cmds.objExists(ctrl):
                shapes = cmds.listRelatives(ctrl, shapes=True, type="nurbsCurve") or []
                if shapes:
                    self._scale_control_curve(ctrl, self._body_correction)
        neck_scale = (1.0 / self._correction) * 1.5
        self._scale_control_curve("FKNeck_M", neck_scale)
        self._scale_finger_controls(0.7)

        if generate_root:
            self._add_root_vv()

        self._constrain_adv_to_fbx()

        if cmds.objExists("DeformationSystem"):
            cmds.setAttr("DeformationSystem.visibility", 0)
        cmds.select(clear=True)

    def delete_controller(self):
        mel_path = self._normalize_path(
            os.path.join(self.advancedskeleton_base, self._adv_mel_name))
        mel.eval('source "{0}";'.format(mel_path))
        self._ensure_adv_ui_stubs()
        if not self._mel_cmd_if_exists("DeleteAdvanced"):
            self._fallback_delete_advanced()
        if cmds.objExists("FitSkeleton"):
            cmds.delete("FitSkeleton")
        cmds.select(clear=True)

    @classmethod
    def _fallback_delete_advanced(cls):
        if cmds.objExists("Geometry"):
            geo_children = cmds.listRelatives("Geometry", type="transform", c=True) or []
            if geo_children:
                try:
                    cmds.parent(geo_children, world=True)
                except Exception:
                    pass
        leaf_nodes = cmds.ls("IKCurveInfo*", "*MultiplyDivide*", type=("curveInfo",)) or []
        for node in leaf_nodes:
            try:
                cmds.delete(node)
            except Exception:
                pass
        for node in cls._ADV_BUILD_TOP_NODES:
            if cmds.objExists(node):
                try:
                    cmds.delete(node)
                except Exception as exc:
                    cmds.warning("Failed to delete '{0}': {1}".format(node, exc))


if __name__ == "__main__":
    FbxToADV({}).build()
