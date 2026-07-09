# -*- coding: utf-8 -*-
"""
Maya 选择工具 (Picker 版) — 单文件无依赖版

由"多功能工具箱"的【选择页】单独摘出，只保留选择相关功能，
内联了全部选择算法，无需任何外部模块。

用法：把整段贴进 Maya Script Editor → Python tab，Ctrl+Enter
     或拖到 Shelf 做按钮；也可 exec(open(r"路径", encoding="utf-8").read())

功能：
  · 5 种选择算法：单链 / 多链 / 对位 / 辐射 / 一键全选
  · Picker 自定义按钮区（拖拽摆放 + 格子吸附 + 缩放 + 框选）
      - 左键单击 = 选中按钮的物体（Shift 反选 / Ctrl 加选 / Ctrl+Shift 恒加选）
      - 空地拖   = 框选（同步场景，修饰键语义同上）
      - Alt+中键 = 平移画布（仿 Maya）
      - Alt+右键 = 缩放画布（任意方向拖，仿 Maya；右/下放大、左/上缩小）
      - F 键     = 定位（有选中→居中选中按钮；无选中→恢复默认大小+居中全部）
      - 右键按钮 = 重命名 / 改色 / 隐藏·显示物体 / 增删物体 / 删除
      - 右键空地 = 新建 / 全选 / 清空 / 刷新
  · 多角色支持 + 多 rig 高亮精确（只亮场景实际选中的那个 rig 的按钮）
  · 初始视口停在画布正中

兼容：Maya 2022 / 2023 / 2024 / 2025（PySide2 / PySide6 自动适配）
依赖：仅 PySide2/6 + maya.cmds，无任何外部库
"""

import os
import re
import sys
import json
import math


# ============================================================
# 环境
# ============================================================
# 路径自适应：以本文件所在目录为基准，把 ikfk_switch_page / select_tool_window /
# corresponding_select 等同目录的兄弟模块加进 sys.path（同事拷整套到自己的 scripts
# 目录就能用，不需要改路径）
# 单文件版：无外部模块依赖，无需路径注入

# ============================================================
# PySide 兼容层（Maya 2020 PySide2 ~ Maya 2025 PySide6 全兼容）
# ============================================================
try:
    from PySide2 import QtCore, QtGui, QtWidgets
    from shiboken2 import wrapInstance
    PYSIDE_VERSION = 2
except ImportError:
    from PySide6 import QtCore, QtGui, QtWidgets
    from shiboken6 import wrapInstance
    PYSIDE_VERSION = 6

# 已知 PySide6 移除/改名的常量补丁（让 PySide2 写法在 PySide6 也能跑）
# Qt.MidButton → Qt.MiddleButton
if not hasattr(QtCore.Qt, "MidButton"):
    QtCore.Qt.MidButton = QtCore.Qt.MiddleButton

try:
    import maya.cmds as cmds
    import maya.OpenMayaUI as omui
    MAYA_RUNNING = True
except ImportError:
    MAYA_RUNNING = False


# ============================================================
# 内联算法模块（由 select_tool_window.py / corresponding_select.py 摘入）
# 注册成同名模块，保持 _run_external 调用逻辑不变。
# ============================================================
import types as _types

def _make_inline_module(mod_name, body_src):
    m = _types.ModuleType(mod_name)
    # 内联算法代码依赖的公共名字，统一注入
    m.cmds = cmds
    m.re = re
    m.os = os
    m.sys = sys
    m.json = json
    m.math = math
    exec(compile(body_src, mod_name + " (inline)", "exec"), m.__dict__)
    sys.modules[mod_name] = m
    return m

_INLINE_STW_SRC = '\n\n# ============================================================\n# 公共工具\n# ============================================================\n# 控制器命名后缀（按腾讯标准 rig 命名规范），按此顺序优先匹配\n_CTRL_SUFFIXES = ("_FKCTRL", "_IKCTRL", "_CTRL")\n\n\ndef _raw_kind_of(node):\n    """节点\'本质\'：joint / locator / nurbsCurve / mesh / ... / transform。\n    只看 nodeType / shape 类型，不看命名。一键全选用。\n    """\n    if cmds.nodeType(node) == "joint":\n        return "joint"\n    shapes = cmds.listRelatives(node, shapes=True, fullPath=True) or []\n    return cmds.nodeType(shapes[0]) if shapes else "transform"\n\n\ndef _kind_of(node):\n    """节点性质：先按命名后缀分类（FKCTRL/IKCTRL/CTRL），再 fallback 到本质类型。\n    单链/对位/扇形用，避免 FKCTRL 下挂 IKCTRL 被当成分叉。\n    """\n    base = node.split("|")[-1].split(":")[-1]\n    for suf in _CTRL_SUFFIXES:\n        if base.endswith(suf):\n            return suf.lstrip("_")\n    return _raw_kind_of(node)\n\n\ndef _notify(msg):\n    """命令行栏安静反馈（跟 Maya 自己的命令结果一样，下一次操作自动被覆盖）"""\n    print("[Notice] " + msg)\n    try:\n        import maya.mel as mel\n        safe = msg.replace(\'\\\\\', \'\\\\\\\\\').replace(\'"\', \'\\\\"\')\n        mel.eval(\'print "\' + safe + \'\\\\n";\')\n    except Exception: pass\n\n\ndef _direct_parent(node):\n    parents = cmds.listRelatives(node, parent=True, fullPath=True) or []\n    return parents[0] if parents else None\n\n\ndef _same_kind_parent(node, kind):\n    """从 node 向上穿透异性质包装层，返回第一个同性质祖先；没有返回 None。"""\n    cur = _direct_parent(node)\n    while cur is not None:\n        if _kind_of(cur) == kind:\n            return cur\n        cur = _direct_parent(cur)\n    return None\n\n\ndef _find_same_kind_children(node, kind):\n    """每个直接子树各贡献最多 1 个最近同性质后代。\n    返回候选列表（长度 >=2 即代表 node 下有分叉）。\n    """\n    direct = cmds.listRelatives(node, children=True, type="transform",\n                                fullPath=True) or []\n    out = []\n    for child in direct:\n        queue = [child]\n        while queue:\n            cur = queue.pop(0)\n            if _kind_of(cur) == kind:\n                out.append(cur)\n                break\n            queue.extend(cmds.listRelatives(cur, children=True,\n                                            type="transform",\n                                            fullPath=True) or [])\n    return out\n\n\ndef _path_same_kind(ancestor, descendant, kind):\n    """ancestor 到 descendant 之间所有同性质节点（含两端，若两端是该性质）。\n    descendant 必须是 ancestor 的后代或自己。\n    """\n    if descendant != ancestor and not descendant.startswith(ancestor + "|"):\n        return None\n    parts = descendant.split("|")\n    a_len = len(ancestor.split("|")) if ancestor else 0\n    out = []\n    for i in range(a_len, len(parts) + 1):\n        n = "|".join(parts[:i])\n        if n and _kind_of(n) == kind:\n            out.append(n)\n    return out\n\n\ndef _extend_down(start, kind):\n    """从 start 沿同性质单链向下（不含 start），遇分叉或断链停。"""\n    out = []\n    cur = start\n    while True:\n        cands = _find_same_kind_children(cur, kind)\n        if len(cands) != 1:\n            break\n        out.append(cands[0])\n        cur = cands[0]\n    return out\n\n\ndef _dedup(nodes):\n    seen = set()\n    out = []\n    for n in nodes:\n        if n not in seen:\n            seen.add(n)\n            out.append(n)\n    return out\n\n\n# ============================================================\n# 1. 单链选择\n# ============================================================\ndef select_chain():\n    sel = cmds.ls(selection=True, long=True)\n    if not sel:\n        _notify("请先选中一个或两个物体")\n        return\n\n    # 双选\n    if len(sel) >= 2:\n        a, b = sel[0], sel[-1]\n        if a == b:\n            _notify("两次选的是同一个物体")\n            return\n\n        kind_a, kind_b = _kind_of(a), _kind_of(b)\n        b_in_a = b.startswith(a + "|")\n        a_in_b = a.startswith(b + "|")\n\n        if not b_in_a and not a_in_b:\n            _notify("两个选中的物体之间没有层级关系（{} 和 {}）".format(\n                a.split("|")[-1], b.split("|")[-1]))\n            return\n\n        # 性质不同：以 a 性质为准过滤路径，忽略 b\n        if kind_a != kind_b:\n            ancestor, descendant = (a, b) if b_in_a else (b, a)\n            full = _path_same_kind(ancestor, descendant, kind_a) or []\n            chain = [n for n in full if n != b]\n            if not b_in_a:\n                chain.reverse()\n            if not chain:\n                _notify("末端 {} 性质={} 与起点性质={} 不同，且路径上没有同性质节点".format(\n                    b.split("|")[-1], kind_b, kind_a))\n                return\n            cmds.select(chain, replace=True)\n            _notify("末端 {} 性质={} 与起点性质={} 不同，已忽略末端".format(\n                b.split("|")[-1], kind_b, kind_a))\n            return\n\n        # 性质相同\n        if b_in_a:\n            chain = _path_same_kind(a, b, kind_a) or []\n            cur = b\n            while True:\n                cands = _find_same_kind_children(cur, kind_a)\n                if not cands:\n                    break\n                if len(cands) > 1:\n                    cmds.select(chain, replace=True)\n                    _notify("终点 {} 下方有 {} 条分支，已选择至当前控制器".format(\n                        cur.split("|")[-1], len(cands)))\n                    return\n                chain.append(cands[0])\n                cur = cands[0]\n        else:\n            chain = list(reversed(_path_same_kind(b, a, kind_a) or []))\n\n        if len(chain) < 2:\n            _notify("起点和终点之间没有可形成的链")\n            return\n        cmds.select(chain, replace=True)\n        return\n\n    # 单选\n    start = sel[0]\n    kind = _kind_of(start)\n    chain = [start]\n    cur = start\n    while True:\n        cands = _find_same_kind_children(cur, kind)\n        if not cands:\n            break\n        if len(cands) > 1:\n            cmds.select(chain, replace=True)\n            _notify("在 {} 下检测到 {} 条分支，请先选根再加选末端".format(\n                cur.split("|")[-1], len(cands)))\n            return\n        chain.append(cands[0])\n        cur = cands[0]\n\n    if len(chain) <= 1:\n        _notify("起点 {} 下面找不到同性质子节点".format(start.split("|")[-1]))\n        cmds.select(start, replace=True)\n        return\n    cmds.select(chain, replace=True)\n\n\n# ============================================================\n# 2. 扇形选择\n# ============================================================\ndef select_fan():\n    sel = cmds.ls(selection=True, long=True)\n    if not sel:\n        _notify("扇形选择需要先选择控制器")\n        return\n\n    kinds = {_kind_of(n) for n in sel}\n    if len(kinds) > 1:\n        _notify("扇形选择要求所选控制器性质相同")\n        return\n    kind = kinds.pop()\n\n    for i, a in enumerate(sel):\n        for b in sel[i + 1:]:\n            if b.startswith(a + "|") or a.startswith(b + "|"):\n                _notify("扇形选择不适用于有父子关系的对象")\n                return\n\n    nodes = []\n    for handle in sel:\n        nodes.append(handle)\n        queue = list(cmds.listRelatives(handle, children=True,\n                                        type="transform",\n                                        fullPath=True) or [])\n        while queue:\n            cur = queue.pop(0)\n            if _kind_of(cur) == kind:\n                nodes.append(cur)\n            queue.extend(cmds.listRelatives(cur, children=True,\n                                            type="transform",\n                                            fullPath=True) or [])\n\n    unique = _dedup(nodes)\n    last = sel[-1]  # active 末位 = 最后选中的扇柄\n    if last in unique:\n        unique.remove(last)\n        unique.append(last)\n    cmds.select(unique, replace=True)\n\n\n# ============================================================\n# 3. 对位选择\n# ============================================================\ndef _walk_up_to_chain_head(node, kind):\n    """向上穿透异性质找同性质父；父不存在或父是分叉点 即停。"""\n    cur = node\n    while True:\n        parent = _same_kind_parent(cur, kind)\n        if parent is None:\n            return cur\n        if len(_find_same_kind_children(parent, kind)) > 1:\n            return cur\n        cur = parent\n\n\ndef select_counterpart():\n    sel = cmds.ls(selection=True, long=True)\n    if not sel:\n        _notify("对位选择需要先选择控制器")\n        return\n\n    kinds = {_kind_of(n) for n in sel}\n    if len(kinds) > 1:\n        _notify("对位选择要求所选控制器性质相同")\n        return\n    kind = kinds.pop()\n\n    nodes = []\n    last_end = None\n    for i, s in enumerate(sel):\n        head = _walk_up_to_chain_head(s, kind)\n        chain = [head] + _extend_down(head, kind)\n        nodes.extend(chain)\n        if i == len(sel) - 1:\n            last_end = chain[-1]\n\n    unique = _dedup(nodes)\n    if last_end and last_end in unique:\n        unique.remove(last_end)\n        unique.append(last_end)\n    cmds.select(unique, replace=True)\n\n\n# ============================================================\n# 4. 一键全选（场景里所有同性质节点）\n# ============================================================\ndef select_all_kind():\n    sel = cmds.ls(selection=True, long=True)\n    if not sel:\n        _notify("一键全选需要先选择至少一个样本控制器")\n        return\n\n    target_kinds = {_kind_of(n) for n in sel}\n\n    matched = []\n    # 任一控制器后缀 → 把 FKCTRL/IKCTRL/CTRL 三类全收（动画师视角的"控制器"是一个大类）\n    if target_kinds & {"FKCTRL", "IKCTRL", "CTRL"}:\n        for suf in ("FKCTRL", "IKCTRL", "CTRL"):\n            matched.extend(cmds.ls("*_" + suf, long=True) or [])\n            matched.extend(cmds.ls("*:*_" + suf, long=True) or [])\n        target_kinds = target_kinds - {"FKCTRL", "IKCTRL", "CTRL"}\n\n    for k in target_kinds:\n        if k == "joint":\n            matched.extend(cmds.ls(type="joint", long=True) or [])\n        else:\n            for sh in cmds.ls(type=k, long=True) or []:\n                par = cmds.listRelatives(sh, parent=True, fullPath=True) or []\n                if par and _kind_of(par[0]) == k:\n                    matched.append(par[0])\n\n    matched = _dedup(matched)\n    if not matched:\n        _notify("场景里没找到任何同性质的节点")\n        return\n    cmds.select(matched, replace=True)\n'
_INLINE_CS_SRC = '\n\ndef _say(msg):\n    """命令行栏安静反馈（跟 Maya 自己的命令结果一样，下一次操作自动被覆盖）"""\n    print("[Notice] " + msg)\n    try:\n        import maya.mel as mel\n        safe = msg.replace(\'\\\\\', \'\\\\\\\\\').replace(\'"\', \'\\\\"\')\n        mel.eval(\'print "\' + safe + \'\\\\n";\')\n    except Exception: pass\n\n\n# ============================================================\n# 配置\n# ============================================================\n\n_CTRL_SUFFIXES = ("_FKCTRL", "_IKCTRL", "_CTRL")\n\nW_NAME, W_STRUCT, W_SHAPE, W_SPACE = 0.4, 0.3, 0.2, 0.1\nSCORE_THRESHOLD = 0.7\n\nNAME_FIELD_REGEX = re.compile(\n    r"^(?P<part>[A-Za-z][A-Za-z0-9]*?)"\n    r"_(?P<idx>\\d+)"\n    r"_(?P<side>[LRM])"\n    r"_(?P<kind>[A-Z]+)$"\n)\n\nCONSTRAINT_TYPES = ("parentConstraint", "pointConstraint", "orientConstraint")\n\n\n# ============================================================\n# 缓存\n# ============================================================\n\ndef _cache_file():\n    base = os.environ.get("LOCALAPPDATA", os.environ.get("TEMP", "."))\n    d = os.path.join(base, "Temp", "maya_select_cache")\n    if not os.path.isdir(d):\n        try:\n            os.makedirs(d)\n        except OSError:\n            pass\n    return os.path.join(d, "corresponding_select.json")\n\n\nclass _ShapeCache(object):\n    _instance = None\n\n    def __init__(self):\n        self.dirty = False\n        self.data = self._load()\n\n    @classmethod\n    def get(cls):\n        if cls._instance is None:\n            cls._instance = cls()\n        return cls._instance\n\n    def _load(self):\n        path = _cache_file()\n        if not os.path.isfile(path):\n            return {}\n        try:\n            with open(path, "r", encoding="utf-8") as f:\n                return json.load(f)\n        except Exception:\n            return {}\n\n    def save(self):\n        if not self.dirty:\n            return\n        path = _cache_file()\n        try:\n            on_disk = {}\n            if os.path.isfile(path):\n                try:\n                    with open(path, "r", encoding="utf-8") as f:\n                        on_disk = json.load(f)\n                except Exception:\n                    on_disk = {}\n            for rig_key, nodes in self.data.items():\n                if rig_key not in on_disk:\n                    on_disk[rig_key] = {}\n                on_disk[rig_key].update(nodes)\n            with open(path, "w", encoding="utf-8") as f:\n                json.dump(on_disk, f, ensure_ascii=False, indent=0)\n        except Exception:\n            pass\n        self.dirty = False\n\n    def _rig_key(self):\n        scene = cmds.file(query=True, sceneName=True) or ""\n        if scene and os.path.isfile(scene):\n            return "{}::{}".format(scene, int(os.path.getmtime(scene)))\n        return "untitled::0"\n\n    def get_node(self, key):\n        return self.data.get(self._rig_key(), {}).get(key)\n\n    def set_node(self, key, payload):\n        rig = self._rig_key()\n        if rig not in self.data:\n            self.data[rig] = {}\n        self.data[rig][key] = payload\n        self.dirty = True\n\n\n# ============================================================\n# 基础工具\n# ============================================================\n\ndef _short_name(node):\n    return node.split("|")[-1].rsplit(":", 1)[-1]\n\n\ndef _to_long(node):\n    if not node:\n        return None\n    if node.startswith("|"):\n        return node\n    matches = cmds.ls(node, long=True) or []\n    return matches[0] if matches else None\n\n\ndef _parent(node):\n    p = cmds.listRelatives(node, parent=True, fullPath=True) or []\n    return p[0] if p else None\n\n\ndef _children(node):\n    return cmds.listRelatives(node, children=True, fullPath=True, type="transform") or []\n\n\ndef _shapes(node):\n    return cmds.listRelatives(node, shapes=True, fullPath=True) or []\n\n\ndef _is_ctrl(node):\n    if not cmds.objExists(node):\n        return False\n    short = _short_name(node)\n    if any(short.endswith(suf) for suf in _CTRL_SUFFIXES):\n        return True\n    if cmds.nodeType(node) == "joint":\n        return False\n    for s in _shapes(node):\n        if cmds.nodeType(s) in ("nurbsCurve", "locator", "nurbsSurface"):\n            return True\n    return False\n\n\ndef _dag_subtree(node):\n    long_node = _to_long(node)\n    if not long_node:\n        return []\n    desc = cmds.listRelatives(long_node, allDescendents=True, fullPath=True) or []\n    return [long_node] + desc\n\n\n# ============================================================\n# 相似度: 命名 / 结构 / 形状 / 空间\n# ============================================================\n\ndef _levenshtein(a, b):\n    if a == b:\n        return 0\n    if not a:\n        return len(b)\n    if not b:\n        return len(a)\n    prev = list(range(len(b) + 1))\n    for i, ca in enumerate(a):\n        curr = [i + 1]\n        for j, cb in enumerate(b):\n            cost = 0 if ca == cb else 1\n            curr.append(min(curr[j] + 1, prev[j + 1] + 1, prev[j] + cost))\n        prev = curr\n    return prev[-1]\n\n\ndef _name_similarity(a, b):\n    sa, sb = _short_name(a), _short_name(b)\n    if not sa or not sb:\n        return 0.0\n    return 1.0 - _levenshtein(sa, sb) / float(max(len(sa), len(sb)))\n\n\ndef _structure_fingerprint(root):\n    layers = []\n    current = [root]\n    while current:\n        layers.append(len(current))\n        nxt = []\n        for n in current:\n            nxt.extend(_children(n))\n        current = nxt\n    return tuple(layers)\n\n\ndef _structure_similarity(a, b):\n    fa, fb = _structure_fingerprint(a), _structure_fingerprint(b)\n    if not fa or not fb:\n        return 0.0\n    max_len = max(len(fa), len(fb))\n    score = 0.0\n    for i in range(max_len):\n        if i >= len(fa) or i >= len(fb):\n            continue\n        x, y = fa[i], fb[i]\n        if x == 0 and y == 0:\n            score += 1\n        else:\n            score += 1 - abs(x - y) / float(max(x, y))\n    return score / max_len\n\n\ndef _shape_metrics_raw(node):\n    shapes = _shapes(node)\n    counts = {"nurbsCurve": 0, "locator": 0, "joint": 0, "nurbsSurface": 0}\n    points = []\n\n    if cmds.nodeType(node) == "joint":\n        counts["joint"] += 1\n        try:\n            r = cmds.getAttr(node + ".radius")\n        except Exception:\n            r = 1.0\n        return {"bbox_axes": (r * 2, r * 2, r * 2), "signature": _signature_str(counts)}\n\n    for s in shapes:\n        t = cmds.nodeType(s)\n        if t == "nurbsCurve":\n            counts["nurbsCurve"] += 1\n            try:\n                spans = cmds.getAttr(s + ".spans")\n                degree = cmds.getAttr(s + ".degree")\n                form = cmds.getAttr(s + ".form")\n                n_cv = spans + degree if form != 2 else spans\n            except Exception:\n                continue\n            for i in range(n_cv):\n                try:\n                    p = cmds.xform("{}.cv[{}]".format(s, i), q=True, os=True, t=True)\n                    points.append(p)\n                except Exception:\n                    pass\n        elif t == "locator":\n            counts["locator"] += 1\n            try:\n                ls = cmds.getAttr(s + ".localScale")[0]\n                lp = cmds.getAttr(s + ".localPosition")[0]\n            except Exception:\n                ls, lp = (1, 1, 1), (0, 0, 0)\n            for sx in (-1, 1):\n                for sy in (-1, 1):\n                    for sz in (-1, 1):\n                        points.append((lp[0] + sx * ls[0], lp[1] + sy * ls[1], lp[2] + sz * ls[2]))\n        elif t == "nurbsSurface":\n            counts["nurbsSurface"] += 1\n            try:\n                u_pts = cmds.getAttr(s + ".spansU") + cmds.getAttr(s + ".degreeU")\n                v_pts = cmds.getAttr(s + ".spansV") + cmds.getAttr(s + ".degreeV")\n            except Exception:\n                continue\n            for u in (0, u_pts - 1):\n                for v in range(v_pts):\n                    try:\n                        p = cmds.xform("{}.cv[{}][{}]".format(s, u, v), q=True, os=True, t=True)\n                        points.append(p)\n                    except Exception:\n                        pass\n\n    if not points:\n        return {"bbox_axes": (0, 0, 0), "signature": _signature_str(counts)}\n\n    xs = [p[0] for p in points]\n    ys = [p[1] for p in points]\n    zs = [p[2] for p in points]\n    return {"bbox_axes": (max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)),\n            "signature": _signature_str(counts)}\n\n\ndef _signature_str(counts):\n    return "nc:{},loc:{},jnt:{},ns:{}".format(\n        counts["nurbsCurve"], counts["locator"], counts["joint"], counts["nurbsSurface"])\n\n\ndef _shape_metrics(node):\n    cache = _ShapeCache.get()\n    cached = cache.get_node(node)\n    if cached is not None:\n        return cached\n    raw = _shape_metrics_raw(node)\n    payload = {"bbox_axes": list(raw["bbox_axes"]), "signature": raw["signature"]}\n    cache.set_node(node, payload)\n    return payload\n\n\ndef _cosine_axes(a, b):\n    if not a or not b:\n        return 0.0\n    dot = a[0] * b[0] + a[1] * b[1] + a[2] * b[2]\n    na = math.sqrt(a[0] ** 2 + a[1] ** 2 + a[2] ** 2)\n    nb = math.sqrt(b[0] ** 2 + b[1] ** 2 + b[2] ** 2)\n    if na < 1e-9 or nb < 1e-9:\n        return 0.0\n    return max(0.0, min(1.0, dot / (na * nb)))\n\n\ndef _shape_similarity_pair(a, b):\n    ma, mb = _shape_metrics(a), _shape_metrics(b)\n    cos = _cosine_axes(ma["bbox_axes"], mb["bbox_axes"])\n    sig_match = 1.0 if ma["signature"] == mb["signature"] else 0.0\n    return 0.6 * cos + 0.4 * sig_match\n\n\ndef _shape_similarity(a, b):\n    ca = [n for n in _dag_subtree(a) if _is_ctrl(n)]\n    cb = [n for n in _dag_subtree(b) if _is_ctrl(n)]\n    if not ca or not cb:\n        return 0.0\n    n = min(len(ca), len(cb))\n    scores = [_shape_similarity_pair(ca[i], cb[i]) for i in range(n)]\n    return sum(scores) / len(scores) if scores else 0.0\n\n\ndef _world_pos(node):\n    try:\n        return cmds.xform(node, q=True, ws=True, t=True)\n    except Exception:\n        return None\n\n\ndef _space_similarity(a, b, scale_hint=None):\n    pa, pb = _world_pos(a), _world_pos(b)\n    if not pa or not pb:\n        return 0.0\n    d = math.sqrt(sum((pa[i] - pb[i]) ** 2 for i in range(3)))\n    if scale_hint is None or scale_hint < 1e-6:\n        scale_hint = 100.0\n    return 1.0 / (1.0 + d / scale_hint)\n\n\ndef _total_similarity(a, b, scale_hint=None):\n    return (W_NAME * _name_similarity(a, b)\n            + W_STRUCT * _structure_similarity(a, b)\n            + W_SHAPE * _shape_similarity(a, b)\n            + W_SPACE * _space_similarity(a, b, scale_hint))\n\n\n# ============================================================\n# 命名短路\n# ============================================================\n\ndef _parse_name_fields(node):\n    m = NAME_FIELD_REGEX.match(_short_name(node))\n    return m.groupdict() if m else None\n\n\ndef _name_short_circuit_pass(start, candidate):\n    f_start = _parse_name_fields(start)\n    if f_start is None:\n        return True\n    f_cand = _parse_name_fields(candidate)\n    if f_cand is None:\n        return False\n    return (f_start["idx"] == f_cand["idx"]\n            and f_start["side"] == f_cand["side"]\n            and f_start["kind"] == f_cand["kind"])\n\n\n# ============================================================\n# Hub / 兄弟链\n# ============================================================\n\ndef _scene_scale_hint():\n    cache = _ShapeCache.get()\n    bucket = cache.data.get(cache._rig_key(), {})\n    if "__scene_scale__" in bucket:\n        return bucket["__scene_scale__"]\n    transforms = cmds.ls(type="transform", long=True) or []\n    if len(transforms) > 500:\n        transforms = transforms[::len(transforms) // 500]\n    xs, ys, zs = [], [], []\n    for n in transforms:\n        try:\n            p = cmds.xform(n, q=True, ws=True, t=True)\n            xs.append(p[0]); ys.append(p[1]); zs.append(p[2])\n        except Exception:\n            pass\n    if not xs:\n        scale = 100.0\n    else:\n        diag = math.sqrt((max(xs) - min(xs)) ** 2 + (max(ys) - min(ys)) ** 2 + (max(zs) - min(zs)) ** 2)\n        scale = max(diag * 0.1, 10.0)\n    cache.set_node("__scene_scale__", scale)\n    return scale\n\n\ndef _find_branch_hub(start):\n    """返回 (hub, current_branch_root, matched_siblings)。至少 2 个兄弟通过才算 hub。"""\n    scale_hint = _scene_scale_hint()\n    current = start\n    parent = _parent(current)\n    while parent:\n        siblings = [s for s in _children(parent) if s != current]\n        if siblings:\n            matched = []\n            for sib in siblings:\n                score = _total_similarity(current, sib, scale_hint)\n                if score >= SCORE_THRESHOLD:\n                    matched.append(sib)\n            if len(matched) >= 2:\n                return parent, current, matched\n        current = parent\n        parent = _parent(current)\n    return None, None, []\n\n\ndef _ctrl_chain_from_branch_root(branch_root):\n    if not branch_root:\n        return []\n    chain = []\n    queue = [branch_root]\n    while queue:\n        node = queue.pop(0)\n        if _is_ctrl(node):\n            chain.append(node)\n        queue.extend(_children(node))\n    return chain\n\n\ndef _index_in_branch(node, branch_root):\n    chain = _ctrl_chain_from_branch_root(branch_root)\n    try:\n        return chain.index(node)\n    except ValueError:\n        return -1\n\n\ndef _ctrl_at_index_in_branch(branch_root, idx):\n    chain = _ctrl_chain_from_branch_root(branch_root)\n    return chain[idx] if 0 <= idx < len(chain) else None\n\n\ndef _find_corresponding_ctrls(seed):\n    hub, cur_branch, matched = _find_branch_hub(seed)\n    if not hub or not matched:\n        return [], None\n    idx = _index_in_branch(seed, cur_branch)\n    if idx < 0:\n        return [], hub\n    siblings = []\n    for sib in matched:\n        target = _ctrl_at_index_in_branch(sib, idx)\n        if not target:\n            continue\n        if not _name_short_circuit_pass(seed, target):\n            continue\n        siblings.append(target)\n    return siblings, hub\n\n\n# ============================================================\n# 约束追溯\n# ============================================================\n\ndef _get_drivers_of(node):\n    """返回 node 被哪些 CTRL 约束驱动 (driver 节点列表)"""\n    result = []\n    long_node = _to_long(node)\n    if not long_node:\n        return result\n    for ctype in CONSTRAINT_TYPES:\n        cons_list = cmds.listRelatives(node, type=ctype, children=True, fullPath=True) or []\n        for c in cons_list:\n            inputs = cmds.listConnections(c, s=True, d=False, type="transform") or []\n            for t in set(inputs):\n                t_long = _to_long(t)\n                if not t_long or t_long == long_node:\n                    continue\n                try:\n                    if cmds.nodeType(t_long) in CONSTRAINT_TYPES:\n                        continue\n                except Exception:\n                    continue\n                result.append(t_long)\n    return result\n\n\ndef _get_driven_by(node):\n    """返回 node 作为 driver 驱动了哪些 transform"""\n    result = []\n    for ctype in CONSTRAINT_TYPES:\n        cons = cmds.listConnections(node, source=False, destination=True, type=ctype) or []\n        for c in set(cons):\n            par = cmds.listRelatives(c, parent=True, fullPath=True) or []\n            for p in par:\n                if _to_long(p) != _to_long(node):\n                    result.append(_to_long(p))\n    return result\n\n\ndef _classify_role(node):\n    """(\'plain\', None) / (\'driver_only\', driven) / (\'driven_only\', driver) / (\'error\', reason)"""\n    drivers = list(set(_get_drivers_of(node)))\n    drivens = list(set(_get_driven_by(node)))\n    nd, nv = len(drivers), len(drivens)\n    if nd > 0 and nv > 0:\n        return (\'error\', u"既被约束又驱动他人，不予处理")\n    if nv > 1:\n        return (\'error\', u"驱动了多个对象，不予处理")\n    if nd > 1:\n        return (\'error\', u"被多个约束驱动，不予处理")\n    if nv == 1:\n        return (\'driver_only\', drivens[0])\n    if nd == 1:\n        return (\'driven_only\', drivers[0])\n    return (\'plain\', None)\n\n\ndef _climb_to_top(node):\n    """沿约束链向上爬到顶 (无 driver 或有歧义时停)"""\n    visited = set()\n    current = node\n    while True:\n        if current in visited:\n            break\n        visited.add(current)\n        drivers = list(set(_get_drivers_of(current)))\n        if len(drivers) != 1:\n            break\n        current = drivers[0]\n    return current\n\n\n# ============================================================\n# 主入口\n# ============================================================\n\ndef corresponding_select():\n    sel = cmds.ls(selection=True, long=True) or []\n    if len(sel) != 1:\n        _say(u"对位选择: 请仅选中一个起点 (当前 {} 个)".format(len(sel)))\n        return\n\n    start = _to_long(sel[0])\n    if not start:\n        _say(u"对位选择: 起点不存在")\n        return\n\n    role, payload = _classify_role(start)\n    if role == \'error\':\n        _say(u"对位选择: {}".format(payload))\n        return\n\n    if role == \'driver_only\':\n        seed = payload\n        if not _is_ctrl(seed):\n            # 被驱动方非 CTRL (如 joint), 退化为用起点本身当种子\n            seed = start\n    else:\n        seed = start\n\n    if not _is_ctrl(seed):\n        _say(u"对位选择: 兄弟搜索种子不是控制器")\n        return\n\n    siblings, hub = _find_corresponding_ctrls(seed)\n    if not siblings:\n        _say(u"对位选择: 未找到结构相似的兄弟")\n        return\n\n    # 每个角色 (起点 + 兄弟) 各自爬到链顶, 去重\n    final_set = []\n    seen = set()\n    for r in [start] + siblings:\n        top = _climb_to_top(r)\n        if top not in seen:\n            seen.add(top)\n            final_set.append(top)\n\n    cmds.select(final_set, replace=True)\n    _say(u"对位选择: 共选中 {} 个".format(len(final_set)))\n    _ShapeCache.get().save()'

if MAYA_RUNNING:
    try:
        _make_inline_module("select_tool_window", _INLINE_STW_SRC)
        _make_inline_module("corresponding_select", _INLINE_CS_SRC)
    except Exception as _e:
        print("[Picker] 内联算法模块加载失败:", _e)


WIN_OBJ_NAME = "selectPickerWin"
WIN_TITLE = "选择工具 (Picker版)"


# ============================================================
# 常量
# ============================================================
PICKER_GRID_W = 120     # 单个格子宽（包含按钮 + 间距）
PICKER_GRID_H = 40      # 单个格子高
PICKER_BTN_W = 110      # 按钮本身宽
PICKER_BTN_H = 36       # 按钮本身高
PICKER_CANVAS_W = 1600  # 画布固定宽（用滚动条而不是窗口缩放）
PICKER_CANVAS_H = 1200  # 画布固定高
PICKER_COLORS = [
    ("蓝", "#4080FF"),
    ("红", "#E04040"),
    ("黄", "#E0B040"),
    ("绿", "#40C060"),
    ("灰", "#808080"),
]
DEFAULT_COLOR = "#4080FF"

# 画布缩放范围（Alt+右键缩放）
PICKER_ZOOM_MIN = 0.3
PICKER_ZOOM_MAX = 5.0
DEFAULT_ZOOM = 1.0          # 窗口刚打开时的默认缩放（定位无选中时恢复到它）
# v1.4: 仿 Maya 视口 Alt+右键缩放——按"拖动总距离"算缩放，越拖越快（指数式）
#       Maya 是右键朝任意方向拖（上下左右斜）都能缩放，用 (dx+dy) 的投影距离。
PICKER_ZOOM_DRAG_SENS = 0.006   # 每像素的缩放指数系数

def _darken_color(hex_color, factor=0.3):
    """将颜色压暗到 factor 亮度（0.0=全黑，1.0=原色）"""
    hex_color = hex_color.strip().lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join(c*2 for c in hex_color)
    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
    except Exception:
        return hex_color
    r = int(r * factor)
    g = int(g * factor)
    b = int(b * factor)
    return "#{0:02x}{1:02x}{2:02x}".format(r, g, b)


def _is_hidden_by_display_layer(obj):
    """检查物体是否因 Maya 显示层而被隐藏。返回层名或 None。"""
    if not MAYA_RUNNING:
        return None
    try:
        layers = cmds.listConnections(obj, type='displayLayer') or []
        for layer in layers:
            if layer != 'defaultLayer' and not cmds.getAttr(layer + '.visibility'):
                return layer
    except Exception:
        pass
    return None

# 右键菜单 stylesheet（仿 Maya hover 高亮整行 + 白字）
PICKER_MENU_QSS = """
QMenu {
    background-color: #3a3a3a;
    color: #d0d0d0;
    border: 1px solid #555;
    padding: 4px 0;
}
QMenu::item {
    padding: 6px 24px 6px 12px;
    background: transparent;
}
QMenu::item:selected {
    background-color: #5285a6;
    color: white;
}
QMenu::item:disabled {
    color: #666;
}
QMenu::separator {
    height: 1px;
    background-color: #555;
    margin: 4px 8px;
}
"""


# ============================================================
# 全局：会话级"不再提示"集合（Maya 重启后清零）
# ============================================================
_DISMISSED_TIPS = set()  # key 字符串集合，比如 "no_namespace_create"


class NonBlockingTipDialog(QtWidgets.QDialog):
    """非阻塞提示框：show() 不 exec_()，可以继续操作 Maya 和工具
    带【下次不再提示】勾选框（会话级，模块重载后清零）"""

    _instances = []  # 防垃圾回收，保活实例引用

    def __init__(self, title, message, dismiss_key=None, parent=None):
        super(NonBlockingTipDialog, self).__init__(parent)
        self._dismiss_key = dismiss_key
        self.setWindowTitle(title)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.Tool)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setModal(False)
        self.resize(360, 0)

        v = QtWidgets.QVBoxLayout(self)
        lbl = QtWidgets.QLabel(message)
        lbl.setWordWrap(True)
        lbl.setStyleSheet("font-size: 13px; padding: 8px;")
        v.addWidget(lbl)

        if dismiss_key:
            self.chk = QtWidgets.QCheckBox("下次不再提示（Maya 重启前不弹）")
            v.addWidget(self.chk)
        else:
            self.chk = None

        h = QtWidgets.QHBoxLayout()
        h.addStretch()
        b_ok = QtWidgets.QPushButton("确定")
        b_ok.clicked.connect(self._on_ok)
        h.addWidget(b_ok)
        v.addLayout(h)

        NonBlockingTipDialog._instances.append(self)
        self.destroyed.connect(lambda: NonBlockingTipDialog._instances.remove(self)
                                       if self in NonBlockingTipDialog._instances else None)

    def _on_ok(self):
        if self.chk and self.chk.isChecked() and self._dismiss_key:
            _DISMISSED_TIPS.add(self._dismiss_key)
        self.close()


def show_tip(title, message, dismiss_key=None, parent=None):
    """显示非阻塞提示。dismiss_key 已在 _DISMISSED_TIPS 时自动跳过。
    弹新窗前关掉所有旧窗，桌面只留最新一个。"""
    if dismiss_key and dismiss_key in _DISMISSED_TIPS:
        return None
    # 关掉所有旧的非阻塞提示，只留最新一个
    for old in list(NonBlockingTipDialog._instances):
        try: old.close()
        except Exception: pass
    dlg = NonBlockingTipDialog(title, message, dismiss_key=dismiss_key, parent=parent)
    dlg.show()
    dlg.raise_()
    return dlg


def maya_main_window():
    if not MAYA_RUNNING:
        return None
    ptr = omui.MQtUtil.mainWindow()
    if ptr is None:
        return None
    return wrapInstance(int(ptr), QtWidgets.QWidget)


# ============================================================
# Picker 按钮（自由摆放版 — 桌面图标式拖拽 + 格子吸附）
# ============================================================
class PickerButton(QtWidgets.QPushButton):
    """单个 Picker 按钮：备注名 + 一组 ctrl 短名 + 颜色 + 格子坐标。

    支持：
    - 拖动（移动到新格子）
    - 框选高亮（蓝边框）
    - "全选高亮"（绑定 ctrl 全部已选时亮蓝）
    - "部分选中"（绑定 ctrl 部分被选时淡蓝）
    """

    SEL_NONE = 0
    SEL_PARTIAL = 1
    SEL_FULL = 2

    def __init__(self, name, ctrls, color=DEFAULT_COLOR,
                 grid_x=0, grid_y=0, created_ns="", parent=None):
        super(PickerButton, self).__init__(parent)
        self._name = name
        self._ctrls = list(ctrls)
        self._color = color
        self._grid_x = grid_x
        self._grid_y = grid_y
        self._created_ns = created_ns or ""  # 创建时的 namespace（""= 无 ns）
        self._frame_selected = False  # 框选高亮
        self._sel_state = self.SEL_NONE  # 场景选区匹配状态
        self._hidden = False  # 物体隐藏状态
        self.setFixedSize(PICKER_BTN_W, PICKER_BTN_H)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self._refresh()

    def name(self):    return self._name
    def ctrls(self):   return list(self._ctrls)
    def color(self):   return self._color
    def grid_xy(self): return (self._grid_x, self._grid_y)
    def created_ns(self): return self._created_ns

    def set_name(self, n):    self._name = n;    self._refresh()
    def set_color(self, c):   self._color = c;   self._refresh()
    def set_ctrls(self, lst): self._ctrls = list(lst); self._refresh()
    def set_created_ns(self, ns): self._created_ns = ns or ""

    def set_grid(self, gx, gy, zoom=1.0):
        """v1.2: 增加 zoom 参数，按钮像素位置和尺寸跟随缩放。"""
        self._grid_x, self._grid_y = gx, gy
        margin = max(1, int(4 * zoom))
        btn_w = max(10, int(PICKER_BTN_W * zoom))
        btn_h = max(8, int(PICKER_BTN_H * zoom))
        self.setFixedSize(btn_w, btn_h)
        self.move(int(gx * PICKER_GRID_W * zoom + margin),
                  int(gy * PICKER_GRID_H * zoom + margin))

    def set_frame_selected(self, on):
        self._frame_selected = bool(on)
        self._refresh()

    def set_sel_state(self, s):
        self._sel_state = s
        self._refresh()

    def to_dict(self):
        return {"name": self._name, "ctrls": self._ctrls, "color": self._color,
                "grid_x": self._grid_x, "grid_y": self._grid_y,
                "created_ns": self._created_ns,
                "hidden": self._hidden}

    @classmethod
    def from_dict(cls, d):
        btn = cls(d.get("name", "按钮"),
                   d.get("ctrls", []),
                   d.get("color", DEFAULT_COLOR),
                   grid_x=d.get("grid_x", 0),
                   grid_y=d.get("grid_y", 0),
                   created_ns=d.get("created_ns", ""))
        btn._hidden = d.get("hidden", False)
        return btn

    def add_ctrls(self, new_shorts):
        """追加 ctrl，自动去重。返回 (added, dup) 数。"""
        existing = set(self._ctrls)
        added = []
        dup = 0
        for s in new_shorts:
            if s in existing:
                dup += 1
            else:
                added.append(s)
                existing.add(s)
        self._ctrls.extend(added)
        self._refresh()
        return len(added), dup

    def remove_ctrls(self, shorts):
        """移除 ctrl。返回实际移除数。"""
        target = set(shorts)
        before = len(self._ctrls)
        self._ctrls = [c for c in self._ctrls if c not in target]
        self._refresh()
        return before - len(self._ctrls)

    def _refresh(self):
        n = len(self._ctrls)
        text = self._name if n <= 1 else "{} ({})".format(self._name, n)
        self.setText(text)
        self.setToolTip("\n".join(self._ctrls) if self._ctrls else "(无绑定)")
        # 4 种边框（按优先级）：全选 / 部分选 / 框选 / 未选
        if self._sel_state == self.SEL_FULL:
            border = "3px solid #ffffff"   # 全选 = 白色粗实线
        elif self._sel_state == self.SEL_PARTIAL:
            border = "3px dashed #ffe040"  # 部分选 = 黄色粗虚线
        elif self._frame_selected:
            border = "2px solid #ffaa44"   # 框选 = 橙色
        else:
            border = "1px solid #000"
        # 隐藏状态：颜色压暗到 30%
        if self._hidden:
            display_color = _darken_color(self._color, 0.3)
            text_color = "#888888"
            border_style = "1px dashed #555555"
        else:
            display_color = self._color
            text_color = "white"
            border_style = border
        self.setStyleSheet("""
            QPushButton {{
                background-color: {col};
                color: {txt};
                border: {border};
                border-radius: 3px;
                font-size: 12px;
                padding: 2px;
            }}
            QPushButton:hover  {{ border: 2px solid #cccccc; }}
        """.format(col=display_color, txt=text_color, border=border_style))


# ============================================================
# Picker 画布（自由摆放，绝对坐标）
# ============================================================
class PickerCanvas(QtWidgets.QWidget):
    """Picker 按钮的自由摆放画布。
    - 固定大尺寸（PICKER_CANVAS_W x H），外层用 ScrollArea 滚动
    - 按钮使用绝对位置（move()），按格子坐标吸附
    - 支持：拖按钮 / 框选 / 框选拖动 / 空地右键菜单
    """
    rubber_finished = QtCore.Signal(list)   # list of buttons in rubber rect

    def __init__(self, owner_page):
        super(PickerCanvas, self).__init__()
        self.page = owner_page
        self.buttons = []
        self.setFixedSize(PICKER_CANVAS_W, PICKER_CANVAS_H)
        self.setMouseTracking(True)
        self._show_grid = False  # 拖动时显示网格

        # 框选 rubberband
        self._rubber = QtWidgets.QRubberBand(QtWidgets.QRubberBand.Rectangle, self)
        self._rubber_origin = None
        self._rubber_modifiers = QtCore.Qt.NoModifier  # v1.3: 框选按下时的修饰键

        # 拖动状态
        self._drag_btn = None        # 当前被拖动的按钮（按下时记录）
        self._drag_group = []        # 整组拖动的所有按钮
        self._drag_start_pos = None  # 鼠标按下时的画布坐标
        self._drag_btn_origins = {}  # {btn: (orig_grid_x, orig_grid_y)}

        # Alt+中键平移画布（仿 Maya 视口 panning）
        self._pan_active = False
        self._pan_start_global = None  # 鼠标按下瞬间的全局坐标
        self._pan_start_scroll = None  # 那一刻 ScrollArea 的滚动值 (h, v)

        # Alt+右键缩放画布（v1.4 仿 Maya：以鼠标位置为锚点，越拖越快）
        self._zoom = DEFAULT_ZOOM
        self._zoom_active = False
        self._zoom_start_global = None    # 按下时鼠标全局坐标
        self._zoom_start_value = DEFAULT_ZOOM
        self._zoom_anchor_doc = None      # 锚点：按下时鼠标对应的"文档归一化坐标"(fx, fy)
                                          # fx,fy ∈ [0,1]，缩放时让该文档点始终停在鼠标下方

        # v1.2: Ctrl 键定位需要焦点
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

    # ===== 按钮管理 =====
    def add_button(self, name, ctrls, color=DEFAULT_COLOR,
                   grid_x=None, grid_y=None, created_ns="", at_grid=None):
        """at_grid: 可选 (gx, gy)，从该格子起螺旋找最近空格子；
        优先级：明确给 grid_x/y > at_grid 螺旋搜索 > 默认左上扫描"""
        if grid_x is not None and grid_y is not None:
            pass  # 完全指定，原样用
        elif at_grid is not None:
            grid_x, grid_y = self._nearest_free_cell(at_grid[0], at_grid[1])
        else:
            grid_x, grid_y = self._next_free_cell()
        btn = PickerButton(name, ctrls, color, grid_x, grid_y,
                           created_ns=created_ns, parent=self)
        btn.set_grid(grid_x, grid_y, self._zoom)
        btn.show()
        self._wire_button(btn)
        self.buttons.append(btn)
        return btn

    def _next_free_cell(self):
        z = max(0.01, self._zoom)
        cols = max(1, int(self.width() // (PICKER_GRID_W * z)) - 1)
        used = {(b._grid_x, b._grid_y) for b in self.buttons}
        for y in range(0, 100):
            for x in range(0, cols):
                if (x, y) not in used:
                    return (x, y)
        return (0, 0)

    def _nearest_free_cell(self, gx, gy):
        """从 (gx, gy) 起螺旋扩散搜索最近的空格子。
        如果 (gx, gy) 没被占就直接返回；否则按曼哈顿距离逐圈扩。"""
        used = {(b._grid_x, b._grid_y) for b in self.buttons}
        gx = max(0, gx)
        gy = max(0, gy)
        if (gx, gy) not in used:
            return (gx, gy)
        # 螺旋扩散搜索（曼哈顿距离逐圈，最大 30 圈足够）
        for r in range(1, 30):
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    if abs(dx) + abs(dy) != r:
                        continue
                    nx, ny = gx + dx, gy + dy
                    if nx < 0 or ny < 0:
                        continue
                    if (nx, ny) not in used:
                        return (nx, ny)
        # 兜底：用普通策略
        return self._next_free_cell()

    def pos_to_grid(self, canvas_pos):
        """画布局部坐标 → 最近格子 (gx, gy)，已考虑当前缩放"""
        z = max(0.01, self._zoom)
        gx = max(0, int((canvas_pos.x() - 4 * z) // (PICKER_GRID_W * z)))
        gy = max(0, int((canvas_pos.y() - 4 * z) // (PICKER_GRID_H * z)))
        return (gx, gy)

    def remove_button(self, btn):
        if btn in self.buttons:
            self.buttons.remove(btn)
            btn.setParent(None)
            btn.deleteLater()

    def clear_all(self):
        for b in list(self.buttons):
            b.setParent(None)
            b.deleteLater()
        self.buttons = []

    def selected_buttons(self):
        return [b for b in self.buttons if b._frame_selected]

    def clear_frame_selection(self):
        for b in self.buttons:
            b.set_frame_selected(False)

    def to_data(self):
        return {"version": "2.1",
                "zoom": round(self._zoom, 4),     # v1.2
                "buttons": [b.to_dict() for b in self.buttons]}

    def load_data(self, data):
        self.clear_all()
        # v1.2: 先恢复缩放，再排按钮
        self._set_zoom_internal(data.get("zoom", 1.0))
        for d in data.get("buttons", []):
            btn = PickerButton.from_dict(d)
            btn.setParent(self)
            btn.set_grid(btn._grid_x, btn._grid_y, self._zoom)
            btn.show()
            self._wire_button(btn)
            self.buttons.append(btn)
        # v1.2: 恢复隐藏状态到 Maya 场景
        self._restore_hidden_to_scene()

    def _restore_hidden_to_scene(self):
        """v1.2: 加载 json 后，把标记为 hidden 的按钮的物体在场景里隐藏掉。"""
        if not MAYA_RUNNING:
            return
        to_hide = []
        for b in self.buttons:
            if getattr(b, "_hidden", False):
                for short in b.ctrls():
                    full = self.page._resolve_short(short, btn=b)
                    if full:
                        to_hide.append(full)
        if to_hide:
            try:
                cmds.hide(to_hide)
            except Exception:
                pass

    # ===== v1.2: 缩放核心 =====
    def _set_zoom_internal(self, new_zoom):
        """更新缩放值，重排所有按钮和画布尺寸（不调整 scroll）。"""
        old = self._zoom
        self._zoom = max(PICKER_ZOOM_MIN, min(PICKER_ZOOM_MAX, float(new_zoom)))
        if abs(self._zoom - old) < 0.001:
            return
        new_w = max(1, int(PICKER_CANVAS_W * self._zoom))
        new_h = max(1, int(PICKER_CANVAS_H * self._zoom))
        self.setFixedSize(new_w, new_h)
        for b in self.buttons:
            b.set_grid(b._grid_x, b._grid_y, self._zoom)
        self.update()

    def set_zoom(self, new_zoom, anchor_doc=None, anchor_viewport_pos=None):
        """缩放并保持锚点不动（仿 Maya 视口缩放：鼠标下的内容停在原地，视口不跳）。

        anchor_doc:           (fx, fy) 文档归一化坐标 [0,1]，缩放后让它停在 anchor_viewport_pos。
        anchor_viewport_pos:  该锚点要停在视口里的像素位置（QPoint，相对 viewport 左上）。
        """
        sa = self._scroll_area()
        self._set_zoom_internal(new_zoom)
        if anchor_doc is None or sa is None or anchor_viewport_pos is None:
            return
        z = self._zoom
        # 缩放后，锚点文档坐标对应的画布像素位置
        canvas_w = max(1, int(PICKER_CANVAS_W * z))
        canvas_h = max(1, int(PICKER_CANVAS_H * z))
        target_canvas_x = anchor_doc[0] * canvas_w
        target_canvas_y = anchor_doc[1] * canvas_h
        # 想让 target_canvas 停在 viewport 的 anchor_viewport_pos 处
        # → 滚动条 = 画布坐标 - 视口内目标像素
        new_h = int(target_canvas_x - anchor_viewport_pos.x())
        new_v = int(target_canvas_y - anchor_viewport_pos.y())
        bar_h = sa.horizontalScrollBar()
        bar_v = sa.verticalScrollBar()
        bar_h.setValue(max(bar_h.minimum(), min(new_h, bar_h.maximum())))
        bar_v.setValue(max(bar_v.minimum(), min(new_v, bar_v.maximum())))

    def _doc_coord_at_canvas(self, canvas_pos):
        """画布像素坐标 → 文档归一化坐标 (fx, fy) ∈ [0,1]（与缩放无关）。"""
        w = max(1, self.width())
        h = max(1, self.height())
        fx = min(1.0, max(0.0, canvas_pos.x() / float(w)))
        fy = min(1.0, max(0.0, canvas_pos.y() / float(h)))
        return (fx, fy)

    # ===== v1.4: Alt+右键缩放（仿 Maya：任意方向拖、以鼠标为锚点、视口不跳） =====
    def _begin_zoom(self, global_pos, canvas_pos):
        """开始缩放。记录锚点的文档归一化坐标 + 锚点此刻在视口里的像素位置，
        缩放过程中始终让这个文档点停在视口同一像素位置（视口不会跳）。"""
        sa = self._scroll_area()
        if sa is None:
            return
        self._zoom_active = True
        self._zoom_start_global = global_pos
        self._zoom_start_value = self._zoom
        # 锚点文档坐标（与缩放无关，缩放后用它反算新的画布像素）
        self._zoom_anchor_doc = self._doc_coord_at_canvas(canvas_pos)
        # 锚点此刻在 viewport 里的像素位置（缩放后让文档点停在这里 → 鼠标下内容不动）
        self._zoom_anchor_vp = sa.viewport().mapFromGlobal(global_pos)
        self.setCursor(QtGui.QCursor(QtCore.Qt.SizeAllCursor))

    def _update_zoom_drag(self, global_pos):
        """拖动中更新缩放。完全照 Maya 视口：右键朝任意方向拖都能缩放。
        Maya 习惯：往右(+dx) = 放大、往左 = 缩小；往下(+dy) = 放大、往上 = 缩小。
        所以 drive = dx + dy（右、下都使其变大），指数式越拖越快。"""
        if self._zoom_start_global is None:
            return
        dx = global_pos.x() - self._zoom_start_global.x()
        dy = global_pos.y() - self._zoom_start_global.y()
        drive = dx + dy
        factor = math.exp(drive * PICKER_ZOOM_DRAG_SENS)
        new_zoom = self._zoom_start_value * factor
        self.set_zoom(new_zoom,
                      anchor_doc=self._zoom_anchor_doc,
                      anchor_viewport_pos=self._zoom_anchor_vp)

    def _end_zoom(self):
        self._zoom_active = False
        self._zoom_start_global = None
        self._zoom_anchor_doc = None
        self._zoom_anchor_vp = None
        self.unsetCursor()
        self.page._status("缩放: {:.0f}%".format(self._zoom * 100))

    # ===== v1.4: 定位按钮（F 快捷键） =====
    def locate_buttons(self):
        """定位逻辑（v1.4，仿 Maya 的 F 聚焦）：

        - 当前在画布上选中了按钮 → 保持缩放不变，居中显示这几个选中的按钮。
        - 当前没有选中任何按钮     → 恢复初始默认缩放(DEFAULT_ZOOM)，并居中显示全部按钮。
        """
        sel_btns = self.selected_buttons()
        if sel_btns:
            # 有选中：保持缩放，居中这些按钮
            self.center_on_buttons(sel_btns)
            self.page._status("定位：居中 {} 个选中按钮".format(len(sel_btns)))
        else:
            # 无选中：恢复默认缩放 + 居中所有按钮
            self._set_zoom_internal(DEFAULT_ZOOM)
            if self.buttons:
                self.center_on_buttons(self.buttons)
                self.page._status("定位：恢复默认大小，居中全部 {} 个按钮".format(len(self.buttons)))
            else:
                # 没有任何按钮 → 滚动条归零
                sa = self._scroll_area()
                if sa is not None:
                    sa.horizontalScrollBar().setValue(0)
                    sa.verticalScrollBar().setValue(0)
                self.page._status("定位：恢复默认大小（画布为空）")

    def center_on_buttons(self, btns):
        """把给定一组按钮的几何中心，滚动到视口正中央（不改变缩放）。"""
        sa = self._scroll_area()
        if sa is None or not btns:
            return
        rects = [b.geometry() for b in btns]
        left = min(r.left() for r in rects)
        right = max(r.right() for r in rects)
        top = min(r.top() for r in rects)
        bottom = max(r.bottom() for r in rects)
        cx = (left + right) // 2
        cy = (top + bottom) // 2
        vp = sa.viewport().rect()
        bar_h = sa.horizontalScrollBar()
        bar_v = sa.verticalScrollBar()
        bar_h.setValue(max(bar_h.minimum(), min(cx - vp.width() // 2, bar_h.maximum())))
        bar_v.setValue(max(bar_v.minimum(), min(cy - vp.height() // 2, bar_v.maximum())))

    def _wire_button(self, btn):
        # 单击 = 选 ctrl，但因为我们要在 mousePress 里做拖拽 + 修饰键，
        # 不直接绑 clicked 信号；改在自定义 mouse 事件里处理
        btn.customContextMenuRequested.connect(
            lambda pos, b=btn: self.page.on_picker_right_click(b, pos))
        btn.installEventFilter(self)

    # ===== 事件处理 =====
    def eventFilter(self, obj, ev):
        """拦截子按钮的鼠标事件——实现拖拽 + 修饰键选择"""
        if not isinstance(obj, PickerButton):
            return False
        # v1.4: 按钮拿到焦点时按 F 也能定位（转发给画布）
        if ev.type() == QtCore.QEvent.KeyPress and ev.key() == QtCore.Qt.Key_F \
                and not (ev.modifiers() & (QtCore.Qt.ControlModifier
                                           | QtCore.Qt.AltModifier
                                           | QtCore.Qt.MetaModifier)):
            self.locate_buttons()
            return True
        if ev.type() == QtCore.QEvent.MouseButtonPress:
            # Alt+中键即使点在按钮上也走平移画布（仿 Maya panning）
            if ev.button() == QtCore.Qt.MidButton and (ev.modifiers() & QtCore.Qt.AltModifier):
                sa = self._scroll_area()
                if sa is not None:
                    self._pan_active = True
                    self._pan_start_global = ev.globalPos()
                    self._pan_start_scroll = (
                        sa.horizontalScrollBar().value(),
                        sa.verticalScrollBar().value())
                    self.setCursor(QtCore.Qt.ClosedHandCursor)
                return True  # 消费事件，按钮不响应
            # Alt+右键 → 缩放画布（即使点在按钮上）
            if ev.button() == QtCore.Qt.RightButton and (ev.modifiers() & QtCore.Qt.AltModifier):
                sa = self._scroll_area()
                if sa is not None:
                    self._begin_zoom(ev.globalPos(), obj.mapToParent(ev.pos()))
                return True  # 消费事件，不让按钮弹菜单
            if ev.button() == QtCore.Qt.LeftButton:
                self._on_btn_press(obj, ev)
                return False  # 不消费，让按钮继续处理（hover 等）
        elif ev.type() == QtCore.QEvent.MouseMove:
            if self._pan_active:
                # 平移期间所有 move 走画布逻辑
                sa = self._scroll_area()
                if sa is not None and self._pan_start_global is not None:
                    dx = ev.globalPos().x() - self._pan_start_global.x()
                    dy = ev.globalPos().y() - self._pan_start_global.y()
                    sa.horizontalScrollBar().setValue(self._pan_start_scroll[0] - dx)
                    sa.verticalScrollBar().setValue(self._pan_start_scroll[1] - dy)
                return True
            # 缩放期间所有 move 走画布逻辑（v1.4 仿 Maya 任意方向拖动）
            if self._zoom_active and self._zoom_start_global is not None:
                self._update_zoom_drag(ev.globalPos())
                return True
            if self._drag_btn is not None and (ev.buttons() & QtCore.Qt.LeftButton):
                self._on_btn_drag(ev)
                return True
        elif ev.type() == QtCore.QEvent.MouseButtonRelease:
            if self._pan_active and ev.button() == QtCore.Qt.MidButton:
                self._pan_active = False
                self._pan_start_global = None
                self._pan_start_scroll = None
                self.unsetCursor()
                return True
            # 按钮上松开 Alt+右键 = 结束缩放
            if self._zoom_active and ev.button() == QtCore.Qt.RightButton:
                self._end_zoom()
                return True
            if ev.button() == QtCore.Qt.LeftButton and self._drag_btn is not None:
                self._on_btn_release(obj, ev)
                return True
        return False

    def _on_btn_press(self, btn, ev):
        # 鼠标按下：记录起始位置 + 准备拖动
        self._drag_btn = btn
        # 把鼠标按钮坐标转成画布坐标
        self._drag_start_pos = btn.mapToParent(ev.pos())
        self._drag_moved = False
        # 整组拖动：如果按下的按钮在框选组里，整组一起动
        if btn._frame_selected:
            self._drag_group = self.selected_buttons()
        else:
            self._drag_group = [btn]
        self._drag_btn_origins = {b: (b._grid_x, b._grid_y) for b in self._drag_group}

    def _on_btn_drag(self, ev):
        if self._drag_btn is None: return
        # 当前画布坐标
        cur = self._drag_btn.mapToParent(ev.pos())
        delta = cur - self._drag_start_pos
        # 阈值过滤：移动超过 4px 才算拖动
        if not self._drag_moved and abs(delta.x()) + abs(delta.y()) < 4:
            return
        self._drag_moved = True
        self._show_grid = True
        # 实时跟随：按 px 移动整组（v1.2: 考虑 zoom）
        z = self._zoom
        for b in self._drag_group:
            ox, oy = self._drag_btn_origins[b]
            new_x = ox * PICKER_GRID_W * z + 4 * z + delta.x()
            new_y = oy * PICKER_GRID_H * z + 4 * z + delta.y()
            b.move(int(new_x), int(new_y))
        self.update()

    def _on_btn_release(self, btn, ev):
        was_drag = self._drag_moved
        self._drag_moved = False
        self._show_grid = False

        if not was_drag:
            # 没真拖动 → 当点击处理（带修饰键）
            self._click_button(btn, ev.modifiers())
        else:
            # 真拖动 → 吸附到最近格子 + 检查冲突
            self._snap_drag_group_or_revert()

        # 清掉所有被拖按钮的 down 状态（防止 stylesheet 卡 pressed）
        for b in (self._drag_group or [btn]):
            try: b.setDown(False)
            except Exception: pass

        self._drag_btn = None
        self._drag_group = []
        self._drag_btn_origins = {}
        self.update()

    def _snap_drag_group_or_revert(self):
        """松开后整组吸附到最近格子。如果有非选中按钮被冲突 → 整组弹回原位"""
        # 拿"被拖动主按钮"的当前像素位置反推 delta_grid
        main = self._drag_btn
        cur_x = main.x()
        cur_y = main.y()
        z = self._zoom
        new_main_gx = max(0, round((cur_x - 4 * z) / (PICKER_GRID_W * z))) if z > 0 else 0
        new_main_gy = max(0, round((cur_y - 4 * z) / (PICKER_GRID_H * z))) if z > 0 else 0
        orig_gx, orig_gy = self._drag_btn_origins[main]
        delta_gx = new_main_gx - orig_gx
        delta_gy = new_main_gy - orig_gy

        if delta_gx == 0 and delta_gy == 0:
            # 没真移动 → 复位
            for b in self._drag_group:
                ox, oy = self._drag_btn_origins[b]
                b.set_grid(ox, oy, z)
            return

        # 计算每个被拖按钮的目标格子
        new_pos = {}  # btn → (gx, gy)
        for b in self._drag_group:
            ox, oy = self._drag_btn_origins[b]
            new_pos[b] = (ox + delta_gx, oy + delta_gy)

        # 检查冲突：目标格子是否被"非组内按钮"占用
        non_group = [b for b in self.buttons if b not in self._drag_group]
        non_group_pos = {(b._grid_x, b._grid_y): b for b in non_group}

        # 如果是单个按钮拖动 → 走 B 规则交换
        if len(self._drag_group) == 1:
            target = list(new_pos.values())[0]
            if target in non_group_pos:
                # 交换：被占按钮搬到主按钮的原位置
                other = non_group_pos[target]
                other.set_grid(orig_gx, orig_gy, z)
            main.set_grid(target[0], target[1], z)
        else:
            # 组拖动：任何冲突都弹回原位
            conflict = any(p in non_group_pos for p in new_pos.values())
            if conflict:
                # 整组弹回
                for b in self._drag_group:
                    ox, oy = self._drag_btn_origins[b]
                    b.set_grid(ox, oy, z)
            else:
                # 整组吸附到新位置
                for b, (gx, gy) in new_pos.items():
                    b.set_grid(gx, gy, z)

    def _click_button(self, btn, modifiers):
        """单击按钮（带修饰键）→ 选 ctrl。仿 Maya 选择语义：
            无修饰      = 替换（只选这个）
            Shift       = 反选/toggle（已选则减、未选则加）
            Ctrl        = 加选（始终加进选区）
            Ctrl+Shift  = 加选（不管当前选没选，都加上）
        按钮高亮(frame_selected) 与 Maya 场景选区严格同步。"""
        shift = bool(modifiers & QtCore.Qt.ShiftModifier)
        ctrl = bool(modifiers & QtCore.Qt.ControlModifier)
        if ctrl and shift:
            # Ctrl+Shift = 恒加选
            mode = "add"
            btn.set_frame_selected(True)
        elif ctrl:
            # Ctrl = 加选
            mode = "add"
            btn.set_frame_selected(True)
        elif shift:
            # Shift = 反选：已选则减，未选则加，高亮同步切换
            if btn._frame_selected:
                mode = "remove"
                btn.set_frame_selected(False)
            else:
                mode = "add"
                btn.set_frame_selected(True)
        else:
            # 普通单击 = 替换：清除其它框选高亮，只亮当前
            mode = "replace"
            self.clear_frame_selection()
            btn.set_frame_selected(True)
        self.page.select_btn_ctrls(btn, mode)

    # ===== 画布鼠标事件（空地右键 + 框选） =====
    def _scroll_area(self):
        """拿到外层 ScrollArea（PickerArea.scroll）"""
        try:
            return self.page.picker_area.scroll
        except Exception:
            return None

    def mousePressEvent(self, ev):
        # Alt+中键 → 平移画布（仿 Maya 视口 panning）
        if ev.button() == QtCore.Qt.MidButton and (ev.modifiers() & QtCore.Qt.AltModifier):
            sa = self._scroll_area()
            if sa is not None:
                self._pan_active = True
                self._pan_start_global = ev.globalPos()
                self._pan_start_scroll = (
                    sa.horizontalScrollBar().value(),
                    sa.verticalScrollBar().value())
                self.setCursor(QtCore.Qt.ClosedHandCursor)
                ev.accept()
                return
        # Alt+右键 → 缩放画布
        if ev.button() == QtCore.Qt.RightButton and (ev.modifiers() & QtCore.Qt.AltModifier):
            sa = self._scroll_area()
            if sa is not None:
                self._begin_zoom(ev.globalPos(), ev.pos())
                ev.accept()
                return
        if ev.button() == QtCore.Qt.LeftButton:
            # 空地左键 → 框选
            self._rubber_origin = ev.pos()
            # v1.3: 记录框选按下时的修饰键，决定加选/减选/替换
            self._rubber_modifiers = ev.modifiers()
            self._rubber.setGeometry(QtCore.QRect(self._rubber_origin, QtCore.QSize()))
            self._rubber.show()
            # v1.3: 不带修饰键 → 框选前清空已有框选高亮（替换模式）
            #       带 Shift/Ctrl → 保留现有框选（在其基础上加选/减选）
            if not (ev.modifiers() & (QtCore.Qt.ShiftModifier | QtCore.Qt.ControlModifier)):
                self.clear_frame_selection()
        super(PickerCanvas, self).mousePressEvent(ev)

    def mouseMoveEvent(self, ev):
        if self._pan_active:
            sa = self._scroll_area()
            if sa is not None and self._pan_start_global is not None:
                dx = ev.globalPos().x() - self._pan_start_global.x()
                dy = ev.globalPos().y() - self._pan_start_global.y()
                # 反向滚动（鼠标向右拖 = 画布向右移 = 滚动条向左走）
                sa.horizontalScrollBar().setValue(self._pan_start_scroll[0] - dx)
                sa.verticalScrollBar().setValue(self._pan_start_scroll[1] - dy)
            ev.accept()
            return
        # 缩放拖动（v1.4 仿 Maya 任意方向）
        if self._zoom_active and self._zoom_start_global is not None:
            self._update_zoom_drag(ev.globalPos())
            ev.accept()
            return
        if self._rubber_origin is not None:
            rect = QtCore.QRect(self._rubber_origin, ev.pos()).normalized()
            self._rubber.setGeometry(rect)
        super(PickerCanvas, self).mouseMoveEvent(ev)

    def mouseReleaseEvent(self, ev):
        if self._pan_active and ev.button() == QtCore.Qt.MidButton:
            self._pan_active = False
            self._pan_start_global = None
            self._pan_start_scroll = None
            self.unsetCursor()
            ev.accept()
            return
        # 缩放释放
        if self._zoom_active and ev.button() == QtCore.Qt.RightButton:
            self._end_zoom()
            ev.accept()
            return
        if ev.button() == QtCore.Qt.LeftButton and self._rubber_origin is not None:
            rect = self._rubber.geometry()
            # 真正画了框（不是单击）才算框选
            is_real_drag = rect.width() > 4 and rect.height() > 4
            mods = getattr(self, "_rubber_modifiers", QtCore.Qt.NoModifier)
            shift = bool(mods & QtCore.Qt.ShiftModifier)
            ctrl = bool(mods & QtCore.Qt.ControlModifier)
            self._rubber.hide()
            self._rubber_origin = None
            self._rubber_modifiers = QtCore.Qt.NoModifier
            if is_real_drag:
                # 框内命中的按钮
                hit_btns = [b for b in self.buttons
                            if rect.intersects(b.geometry())]
                # v1.4: 框选修饰键语义与单击一致（仿 Maya）
                #   无修饰     = 替换
                #   Shift      = 反选（框内已选的减掉，未选的加上）
                #   Ctrl       = 加选
                #   Ctrl+Shift = 加选
                #   按钮高亮 与 Maya 场景选区 严格同步。
                if ctrl:
                    # Ctrl / Ctrl+Shift = 加选
                    add_btns = [b for b in hit_btns if not b._frame_selected]
                    for b in add_btns:
                        b.set_frame_selected(True)
                    if add_btns:
                        self._sync_scene_to_frame_selection(
                            action="add", changed=add_btns)
                elif shift:
                    # Shift = 反选：框内分两拨——已选的减、未选的加
                    to_add = [b for b in hit_btns if not b._frame_selected]
                    to_remove = [b for b in hit_btns if b._frame_selected]
                    for b in to_add:
                        b.set_frame_selected(True)
                    for b in to_remove:
                        b.set_frame_selected(False)
                    if to_add:
                        self._sync_scene_to_frame_selection(
                            action="add", changed=to_add)
                    if to_remove:
                        self._sync_scene_to_frame_selection(
                            action="remove", changed=to_remove)
                else:
                    # 无修饰 = 替换：仅保留框内按钮
                    self.clear_frame_selection()
                    for b in hit_btns:
                        b.set_frame_selected(True)
                    self._sync_scene_to_frame_selection(action="replace")
            else:
                # 单击空地：取消所有选择（清按钮框选 + 清场景选区）
                self.clear_frame_selection()
                if MAYA_RUNNING:
                    try:
                        cmds.select(clear=True)
                        self.page._status("已取消选择")
                    except Exception: pass
        super(PickerCanvas, self).mouseReleaseEvent(ev)

    def _sync_scene_to_frame_selection(self, action="replace", changed=None):
        """v1.3: 让 Maya 场景选区与画布按钮高亮状态保持同步。

        action:
            "replace" → 场景选区 = 当前所有高亮按钮的物体（全量重选）
            "add"     → 把 changed 这些按钮的物体追加到场景选区
            "remove"  → 把 changed 这些按钮的物体从场景选区里剔除
        """
        if action == "add" and changed:
            self.page.select_buttons_objects(changed, mode="add")
        elif action == "remove" and changed:
            self.page.select_buttons_objects(changed, mode="remove")
        else:
            # replace：用当前全部高亮按钮重选，保证按钮态与场景态完全一致
            sel_btns = self.selected_buttons()
            if sel_btns:
                self.page.select_buttons_objects(sel_btns, mode="replace")
            elif MAYA_RUNNING:
                try:
                    cmds.select(clear=True)
                except Exception:
                    pass

    def contextMenuEvent(self, ev):
        # 空地右键 → 弹菜单
        # 如果右键点的是按钮，按钮自己的 customContextMenuRequested 会处理
        # 这里只处理空地
        child = self.childAt(ev.pos())
        if child is not None:
            return  # 让按钮自己处理
        # Alt 修饰下不弹菜单（让 Alt+右键拖动用于缩放）
        if ev.modifiers() & QtCore.Qt.AltModifier:
            return
        # 把右键的画布局部坐标对应的 grid 也传过去（用于在原位置创建新按钮）
        canvas_grid = self.pos_to_grid(ev.pos())
        self.page.on_canvas_right_click(ev.globalPos(), canvas_grid=canvas_grid)

    # v1.4: F 键定位（取代旧的 Ctrl 定位）
    def keyPressEvent(self, ev):
        if ev.key() == QtCore.Qt.Key_F and not (
                ev.modifiers() & (QtCore.Qt.ControlModifier
                                  | QtCore.Qt.AltModifier
                                  | QtCore.Qt.MetaModifier)):
            self.locate_buttons()
            ev.accept()
            return
        super(PickerCanvas, self).keyPressEvent(ev)

    def paintEvent(self, ev):
        super(PickerCanvas, self).paintEvent(ev)
        if self._show_grid:
            painter = QtGui.QPainter(self)
            painter.setPen(QtGui.QPen(QtGui.QColor(120, 120, 120, 80), 1, QtCore.Qt.DashLine))
            z = self._zoom
            zx = PICKER_GRID_W * z
            zy = PICKER_GRID_H * z
            if zx <= 0 or zy <= 0: return
            for gx in range(0, int(self.width() / zx) + 2):
                x = int(gx * zx)
                painter.drawLine(x, 0, x, self.height())
            for gy in range(0, int(self.height() / zy) + 2):
                y = int(gy * zy)
                painter.drawLine(0, y, self.width(), y)


class PickerArea(QtWidgets.QWidget):
    """ScrollArea 包裹 PickerCanvas（兼容老接口）"""

    def __init__(self, owner_page):
        super(PickerArea, self).__init__()
        self.page = owner_page

        v = QtWidgets.QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(False)  # 关键：不让 ScrollArea 拉伸 canvas
        v.addWidget(self.scroll)

        self.canvas = PickerCanvas(owner_page)
        self.scroll.setWidget(self.canvas)

        # v1.5: 窗口首次显示时，初始视口停在画布正中间
        self._centered_once = False

    def showEvent(self, ev):
        super(PickerArea, self).showEvent(ev)
        if not self._centered_once:
            self._centered_once = True
            # 延后到布局完成后再居中，确保 viewport 尺寸已就绪
            QtCore.QTimer.singleShot(0, self.center_canvas)

    def center_canvas(self):
        """把滚动条滚到画布正中央（初始视口居中）。"""
        sa = self.scroll
        if sa is None:
            return
        bar_h = sa.horizontalScrollBar()
        bar_v = sa.verticalScrollBar()
        # 画布中心像素 - 视口一半 = 让画布中心对齐视口中心
        cx = self.canvas.width() // 2 - sa.viewport().width() // 2
        cy = self.canvas.height() // 2 - sa.viewport().height() // 2
        bar_h.setValue(max(bar_h.minimum(), min(cx, bar_h.maximum())))
        bar_v.setValue(max(bar_v.minimum(), min(cy, bar_v.maximum())))

    # 兼容老接口
    @property
    def buttons(self):
        return self.canvas.buttons

    def add_button(self, name, ctrls, color=DEFAULT_COLOR, created_ns="", at_grid=None):
        return self.canvas.add_button(name, ctrls, color,
                                      created_ns=created_ns, at_grid=at_grid)

    def remove_button(self, btn):
        self.canvas.remove_button(btn)

    def clear_all(self):
        self.canvas.clear_all()

    def to_data(self):
        return self.canvas.to_data()

    def load_data(self, data):
        self.canvas.load_data(data)




# ============================================================
# 选择页
# ============================================================
class SelectionPage(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super(SelectionPage, self).__init__(parent)
        self._sel_job_id = None
        self._build_ui()
        self._register_selection_job()
        self._update_sel_state()

    # -------- UI --------
    def _build_ui(self):
        v = QtWidgets.QVBoxLayout(self)
        v.setContentsMargins(6, 6, 6, 6)
        v.setSpacing(6)

        # namespace 行
        ns_row = QtWidgets.QHBoxLayout()
        # 勾选框：☑ 启用 = 跟 ns_combo 走，☐ 不启用 = 锁死按钮自己 created_ns
        self.chk_ns_lock = QtWidgets.QCheckBox("启用空间名")
        self.chk_ns_lock.setChecked(False)  # 默认不启用
        self.chk_ns_lock.setToolTip(
            "☑ 启用：按钮跟随下方空间名切换（多角色复用同一套按钮）\n"
            "☐ 不启用：按钮锁死创建时所在的角色（单角色精准）")
        self.chk_ns_lock.toggled.connect(self._on_ns_lock_toggled)
        ns_row.addWidget(self.chk_ns_lock)
        self.lbl_ns = QtWidgets.QLabel("空间名:")
        ns_row.addWidget(self.lbl_ns)
        self.ns_combo = QtWidgets.QComboBox()
        self.ns_combo.setMinimumWidth(260)
        ns_row.addWidget(self.ns_combo)
        ns_row.addStretch()
        btn_refresh = QtWidgets.QPushButton("刷新")
        btn_refresh.setFixedWidth(60)
        btn_refresh.clicked.connect(self._cb_refresh_namespaces)
        ns_row.addWidget(btn_refresh)
        v.addLayout(ns_row)

        # 5 工具按钮
        tool_row = QtWidgets.QHBoxLayout()
        for label, cb in (
            ("单链选择",  self._cb_chain),
            ("多链选择",  self._cb_multi_chain),
            ("对位选择",  self._cb_counterpart),
            ("辐射选择",  self._cb_radiate),
            ("一键全选",  self._cb_all_kind),
        ):
            b = QtWidgets.QPushButton(label)
            b.setMinimumHeight(28)
            b.clicked.connect(cb)
            tool_row.addWidget(b)
        v.addLayout(tool_row)

        # 文件操作（删除"进入编辑模式"按钮，全程可编辑）
        edit_row = QtWidgets.QHBoxLayout()
        edit_row.addStretch()
        self.btn_open = QtWidgets.QPushButton("打开 Picker")
        self.btn_save = QtWidgets.QPushButton("保存 Picker")
        self.btn_clear = QtWidgets.QPushButton("清空")
        self.btn_open.clicked.connect(self._cb_open)
        self.btn_save.clicked.connect(self._cb_save)
        self.btn_clear.clicked.connect(self._cb_clear)
        edit_row.addWidget(self.btn_open)
        edit_row.addWidget(self.btn_save)
        edit_row.addWidget(self.btn_clear)
        v.addLayout(edit_row)

        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        v.addWidget(line)

        # Picker 主区
        self.picker_area = PickerArea(self)
        v.addWidget(self.picker_area, 1)

        # 底部"+ 新建按钮"——常驻，根据场景选区灰显
        bottom_row = QtWidgets.QHBoxLayout()
        self.btn_new = QtWidgets.QPushButton("+ 新建按钮")
        self.btn_new.setMinimumHeight(28)
        self.btn_new.clicked.connect(self._cb_new_picker_btn)
        self.btn_new.setToolTip("先在 Maya 里选中物体（ctrl/相机/灯光/mesh 都行），再点这里新建按钮")
        bottom_row.addWidget(self.btn_new)
        # v1.4: 定位按钮（快捷键 F）
        self.btn_locate = QtWidgets.QPushButton("定位按钮 (F)")
        self.btn_locate.setMinimumHeight(28)
        self.btn_locate.setToolTip(
            "快捷键 F：\n"
            "  · 选中了按钮 → 保持缩放，居中显示选中的按钮\n"
            "  · 没选中按钮 → 恢复默认大小，居中显示全部按钮")
        self.btn_locate.clicked.connect(self._cb_locate_selection)
        bottom_row.addWidget(self.btn_locate)
        bottom_row.addStretch()
        # 提示文字
        tip = QtWidgets.QLabel("拖按钮=移动 | 左键=选物(Shift反选/Ctrl加选) | 空地拖=框选 | Alt+中键=平移 | Alt+右键=缩放 | F=定位")
        tip.setStyleSheet("color: #aaa; font-size: 11px;")
        bottom_row.addWidget(tip)
        v.addLayout(bottom_row)

        self._cb_refresh_namespaces()
        self._on_ns_lock_toggled(self.chk_ns_lock.isChecked())  # 应用初始灰显

    # v1.4: 定位按钮回调（F 键 / 点击按钮）
    def _cb_locate_selection(self):
        if hasattr(self.picker_area, "canvas"):
            self.picker_area.canvas.locate_buttons()

    # -------- 5 工具按钮回调 --------
    def _cb_chain(self):       self._run_external("select_tool_window", "select_chain",       "单链选择")
    def _cb_multi_chain(self): self._run_external("select_tool_window", "select_counterpart", "多链选择")
    def _cb_radiate(self):     self._run_external("select_tool_window", "select_fan",         "辐射选择")
    def _cb_all_kind(self):    self._run_external("select_tool_window", "select_all_kind",    "一键全选")
    def _cb_counterpart(self): self._run_external("corresponding_select", "corresponding_select", "对位选择")

    def _run_external(self, module_name, fn_name, label):
        """从外部模块调函数，每次 import 后 reload，方便算法迭代。"""
        try:
            mod = __import__(module_name)
            fn = getattr(mod, fn_name, None)
            if fn is None:
                self._status("[{}] {}.{} 不存在".format(label, module_name, fn_name))
                return
            fn()
            self._status("[{}] 已执行".format(label))
        except Exception as e:
            self._status("{} 失败：{}".format(label, e))

    # -------- Picker 按钮操作 --------
    def _cb_new_picker_btn(self, at_grid=None):
        """at_grid: 可选 (gx, gy)，从该格子起螺旋找最近空格子（画布右键 → 新建用）"""
        if not MAYA_RUNNING:
            self._status("Maya 未运行，无法采集选中物体")
            return
        sel = cmds.ls(selection=True, long=True) or []
        if not sel:
            show_tip("提示", "请先在 Maya 里选中至少一个物体（ctrl/相机/灯光/mesh 等）",
                     parent=self)
            return

        # 推出选中物体的 namespace（取第一个能拿到 ns 的），无论是否启用 ns_combo
        # 都把它存进按钮的 created_ns 里（不启用时锁死用，启用时也保留作为切换默认）
        sel_ns = self._infer_namespace(sel)

        # 启用空间名 ☑ 时，跳 ns_combo 到选中物体的 ns（方便用户后续切换）
        # 不启用时不动 ns_combo（它本来也灰显着）
        if sel_ns and self.chk_ns_lock.isChecked():
            self._set_combo_namespace(sel_ns)

        # 如果推出来是裸名（场景物体没 namespace）→ 弱提示一次
        if not sel_ns:
            show_tip("提示", "无空间名（namespace），但已正常选择 {} 个物体".format(len(sel)),
                     dismiss_key="no_namespace_create", parent=self)

        shorts = [self._strip_ns(s.split("|")[-1]) for s in sel]
        default_name = shorts[0]
        self.picker_area.add_button(default_name, shorts,
                                    created_ns=sel_ns, at_grid=at_grid)
        self._status("已新建按钮: {} 绑定 {} 个物体（创建空间名: {}）".format(
            default_name, len(shorts), sel_ns or "（无）"))

    @staticmethod
    def _infer_namespace(full_names):
        """从一组完整路径里推出 namespace（取第一个有 ns 的）"""
        for f in full_names:
            short_with_ns = f.split("|")[-1]
            if ":" in short_with_ns:
                return short_with_ns.rsplit(":", 1)[0]
        return ""

    def _set_combo_namespace(self, ns):
        """把 ns_combo 设到指定 namespace（找不到匹配项就不动）"""
        if not hasattr(self, "ns_combo"): return
        for i in range(self.ns_combo.count()):
            if self.ns_combo.itemText(i) == ns:
                self.ns_combo.setCurrentIndex(i)
                self._status("空间名自动跳转 → {}".format(ns))
                return

    def _on_ns_lock_toggled(self, on):
        """启用空间名 ☑ → 空间名 label/combo 正常；
        不启用 ☐ → label/combo 明显灰下去（暗背景+深灰文字+暗边框）"""
        self.lbl_ns.setEnabled(on)
        self.ns_combo.setEnabled(on)
        if on:
            # 启用：清空 stylesheet，恢复默认样式
            self.lbl_ns.setStyleSheet("")
            self.ns_combo.setStyleSheet("")
            self.ns_combo.setCursor(QtCore.Qt.ArrowCursor)
        else:
            # 不启用：明显灰下去
            self.lbl_ns.setStyleSheet("color: #666;")
            self.ns_combo.setStyleSheet(
                "QComboBox { background-color: #2a2a2a; color: #555; "
                "border: 1px solid #3a3a3a; }"
                "QComboBox::drop-down { border: none; }"
                "QComboBox::down-arrow { image: none; }")
            self.ns_combo.setCursor(QtCore.Qt.ForbiddenCursor)

    def _resolve_short(self, short, btn=None, scope=None):
        """把短名解析成场景里实际存在的完整路径。
        策略由勾选框决定：
        - chk_ns_lock 启用 → 用 ns_combo 当前选中的 ns 拼接（精确到一个角色）
        - chk_ns_lock 不启用 → 用 btn.created_ns 锁死创建时角色；找不到才 fallback *:short
        """
        if not short: return None
        if self.chk_ns_lock.isChecked():
            # 启用：跟 ns_combo 走
            ns = self._current_namespace()
            if ns:
                full = ns + ":" + short
                if cmds.objExists(full): return full
                return None
            # ns_combo 是"无" → 短名直接命中 / 全场景兜底
            if cmds.objExists(short): return short
            try:
                hits = cmds.ls("*:" + short, long=False) or []
                if hits: return hits[0]
            except Exception: pass
            return None

        # 不启用：锁死按钮自己 created_ns
        if btn is not None:
            cns = btn.created_ns()
            if cns:
                full = cns + ":" + short
                if cmds.objExists(full): return full
                # created_ns 失效（角色被删了） → fallback 到全场景兜底
        # 老存档没 created_ns / 创建时无 ns → 全场景找
        if cmds.objExists(short): return short
        try:
            hits = cmds.ls("*:" + short, long=False) or []
            if hits: return hits[0]
        except Exception: pass
        return None

    def _decide_scope(self, btns):
        """保留接口签名兼容，但行为已由 chk_ns_lock 勾选框完全决定。
        永远返回 'auto'——_resolve_short 不再依赖 scope 参数。"""
        return "auto"

    def select_btn_ctrls(self, btn, mode="replace"):
        """根据修饰键模式选 ctrl
        mode: "replace" / "add" / "toggle" / "remove"
        """
        if not MAYA_RUNNING:
            return

        # D 修复：按钮还没绑物体（add/remove 操作把 ctrl 全清空了）
        if not btn.ctrls():
            show_tip("提示", "[{}] 这个按钮还没绑定任何物体。\n\n"
                            "在 Maya 里选中物体 → 右键此按钮 → 添加物体".format(btn.name()),
                     parent=self)
            return

        full_names = []
        missing = []
        for short in btn.ctrls():
            full = self._resolve_short(short, btn=btn)
            if full:
                full_names.append(full)
            else:
                missing.append(short)
        if not full_names:
            cns = btn.created_ns()
            ns = self._current_namespace()
            tip = "[{}] 没找到 {} 个物体。\n\n".format(btn.name(), len(missing))
            if self.chk_ns_lock.isChecked():
                if ns:
                    tip += "已启用空间名，当前: {}\n请检查空间名是否正确，或切换到其他空间名".format(ns)
                else:
                    tip += "已启用空间名，但当前选中是「无」\n场景里没有匹配的同名物体"
            else:
                if cns:
                    tip += "未启用空间名，按钮锁定到创建角色: {}\n该角色可能已不在场景中".format(cns)
                else:
                    tip += "未启用空间名，按钮无创建角色记录\n场景里没有匹配的同名物体"
            show_tip("找不到物体", tip, parent=self)
            return
        try:
            if mode == "replace":
                cmds.select(full_names, replace=True)
            elif mode == "add":
                cmds.select(full_names, add=True)
            elif mode == "toggle":
                cmds.select(full_names, toggle=True)
            elif mode == "remove":
                cmds.select(full_names, deselect=True)
        except Exception as e:
            self._status("选中失败: {}".format(e))
            return
        msg = "[{}] {} {} 个".format(
            btn.name(), {"replace": "选中", "add": "追加",
                          "toggle": "切换", "remove": "剔除"}[mode],
            len(full_names))
        if missing:
            # 部分找到：正常选 + Maya 命令行黄条爆出缺失短名（左下角警告条）
            preview = ", ".join(missing[:8])
            if len(missing) > 8:
                preview += " 等 {} 个".format(len(missing))
            try:
                cmds.warning("[{}] 缺少 {} 个物体: {}".format(
                    btn.name(), len(missing), preview))
            except Exception: pass
        self._status(msg, ms=8000)

    def select_buttons_objects(self, btns, mode="replace"):
        """多个按钮的物体并集 → 一次 select"""
        if not MAYA_RUNNING or not btns: return
        all_full = []
        seen = set()
        miss_shorts = []  # 收集缺失的短名（带按钮归属）
        for b in btns:
            for short in b.ctrls():
                full = self._resolve_short(short, btn=b)
                if not full:
                    miss_shorts.append(short)
                    continue
                if full in seen: continue
                seen.add(full)
                all_full.append(full)
        if not all_full:
            tip = "操作了 {} 个按钮，但没找到任何物体。\n\n".format(len(btns))
            if self.chk_ns_lock.isChecked():
                ns = self._current_namespace()
                if ns:
                    tip += "已启用空间名，当前: {}\n请检查空间名是否正确".format(ns)
                else:
                    tip += "已启用空间名，但当前选中是「无」\n场景里没有匹配的同名物体"
            else:
                tip += "未启用空间名，按钮锁定各自创建角色\n这些角色可能都不在场景里"
            show_tip("找不到物体", tip, parent=self)
            return
        try:
            if mode == "replace":
                cmds.select(all_full, replace=True)
            elif mode == "add":
                cmds.select(all_full, add=True)
            elif mode == "toggle":
                cmds.select(all_full, toggle=True)
            elif mode == "remove":
                cmds.select(all_full, deselect=True)
        except Exception as e:
            self._status("选中失败: {}".format(e))
            return
        msg = "框选 {} 个按钮 → 选中 {} 个物体".format(len(btns), len(all_full))
        if miss_shorts:
            preview = ", ".join(miss_shorts[:8])
            if len(miss_shorts) > 8:
                preview += " 等 {} 个".format(len(miss_shorts))
            try:
                cmds.warning("框选缺少 {} 个物体: {}".format(
                    len(miss_shorts), preview))
            except Exception: pass
        self._status(msg, ms=8000)

    def on_picker_right_click(self, btn, pos):
        """按钮右键菜单（仿 Maya displayLayer）。
        如果右键的按钮在框选组里（≥ 2 个），所有动作整组批量；
        否则按单个处理 + 取消之前的框选高亮（用户右键点框外按钮 = 重新指向）。"""
        # 决定是否走批量
        group = self.picker_area.canvas.selected_buttons() \
            if hasattr(self.picker_area, "canvas") else []
        if btn in group and len(group) >= 2:
            target_btns = list(group)
            is_batch = True
        else:
            target_btns = [btn]
            is_batch = False
            # 右键点的按钮不在框选组 → 取消之前的框选高亮
            if group:
                self.picker_area.canvas.clear_frame_selection()

        sel_in_scene = []
        if MAYA_RUNNING:
            sel_in_scene = cmds.ls(selection=True, long=True) or []
        has_sel = bool(sel_in_scene)

        menu = QtWidgets.QMenu(self)
        menu.setStyleSheet(PICKER_MENU_QSS)
        if is_batch:
            a_select = menu.addAction("选中这 {} 个按钮的所有物体".format(len(target_btns)))
        else:
            a_select = menu.addAction("选中此按钮的所有物体")
        menu.addSeparator()
        # 隐藏/显示物体（仿 Maya displayLayer）
        any_hidden = any(b._hidden for b in target_btns)
        if any_hidden:
            a_hide = menu.addAction("显示物体")
            a_hide.setToolTip("恢复按钮绑定的所有物体的显示")
        else:
            a_hide = menu.addAction("隐藏物体")
            a_hide.setToolTip("隐藏按钮绑定的所有物体")
        menu.addSeparator()
        a_add = menu.addAction("添加物体（场景当前选中）")
        a_add.setEnabled(has_sel)
        a_remove = menu.addAction("移除物体（场景当前选中）")
        a_remove.setEnabled(has_sel)
        menu.addSeparator()
        a_rename = menu.addAction("重命名")
        if is_batch:
            a_rename.setEnabled(False)
            a_rename.setToolTip("框选多个时不支持批量重命名")
        color_menu = menu.addMenu("改色")
        for label, col in PICKER_COLORS:
            ca = color_menu.addAction("{}  ●".format(label))
            ca.setData(col)
        menu.addSeparator()
        if is_batch:
            a_del = menu.addAction("删除这 {} 个按钮".format(len(target_btns)))
        else:
            a_del = menu.addAction("删除按钮")

        action = menu.exec_(btn.mapToGlobal(pos))
        if action is None: return

        if action == a_select:
            if is_batch:
                self.select_buttons_objects(target_btns, mode="replace")
            else:
                self.select_btn_ctrls(btn, "replace")
        elif action == a_add:
            # 启用空间名时，跳 combo 到当前选中物体的 ns（不启用时不动 combo）
            sel_ns = self._infer_namespace(sel_in_scene)
            if self.chk_ns_lock.isChecked() and not self._current_namespace() and sel_ns:
                self._set_combo_namespace(sel_ns)
            shorts = [self._strip_ns(s.split("|")[-1]) for s in sel_in_scene]
            total_added = 0
            total_dup = 0
            for b in target_btns:
                a, d = b.add_ctrls(shorts)
                total_added += a
                total_dup += d
            if is_batch:
                self._status("批量给 {} 个按钮添加 {} 个物体（去重 {}）".format(
                    len(target_btns), total_added, total_dup))
            else:
                self._status("[{}] 添加 {} 个物体，{} 个已存在".format(
                    btn.name(), total_added, total_dup))
        elif action == a_remove:
            shorts = [self._strip_ns(s.split("|")[-1]) for s in sel_in_scene]
            total_removed = 0
            for b in target_btns:
                total_removed += b.remove_ctrls(shorts)
            if is_batch:
                self._status("批量从 {} 个按钮移除 {} 个物体".format(
                    len(target_btns), total_removed))
            else:
                self._status("[{}] 移除 {} 个物体".format(btn.name(), total_removed))
        elif action == a_rename:
            # 已通过 setEnabled(False) 在批量模式下灰显，这里只处理单按钮
            text, ok = QtWidgets.QInputDialog.getText(
                self, "重命名", "新名字：", text=btn.name())
            if ok and text.strip():
                btn.set_name(text.strip())
        elif action == a_del:
            if is_batch:
                ret = QtWidgets.QMessageBox.question(
                    self, "删除按钮",
                    "确定删除选中的 {} 个按钮吗？".format(len(target_btns)),
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
                if ret == QtWidgets.QMessageBox.Yes:
                    for b in target_btns:
                        self.picker_area.remove_button(b)
                    self._status("已删除 {} 个按钮".format(len(target_btns)))
            else:
                ret = QtWidgets.QMessageBox.question(
                    self, "删除按钮",
                    "确定删除按钮 [{}] 吗？".format(btn.name()),
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
                if ret == QtWidgets.QMessageBox.Yes:
                    self.picker_area.remove_button(btn)
        elif action == a_hide:
            # 每个按钮独立判断自己的 _hidden 状态
            skipped = 0
            for b in target_btns:
                if b._hidden:
                    # 按钮当前是隐藏的 → 执行显示
                    for obj_short in b.ctrls():
                        full = self._resolve_short(obj_short, b)
                        if full and cmds.objExists(full):
                            layer = _is_hidden_by_display_layer(full)
                            if layer:
                                skipped += 1
                                continue
                            try: cmds.showHidden(full)
                            except Exception: pass
                    b._hidden = False
                else:
                    # 按钮当前是显示的 → 执行隐藏
                    for obj_short in b.ctrls():
                        full = self._resolve_short(obj_short, b)
                        if full and cmds.objExists(full):
                            try: cmds.hide(full)
                            except Exception: pass
                    b._hidden = True
                b._refresh()
            if skipped:
                cmds.warning("选择工具：{} 个物体因显示层隐藏而跳过（显示层优先级更高）".format(skipped))
            self._status("已{} {} 个按钮的物体".format(
                "显示" if all(not b._hidden for b in target_btns) else "隐藏",
                len(target_btns)))
        elif action.parent() is color_menu:
            for b in target_btns:
                b.set_color(action.data())
            if is_batch:
                self._status("已批量改色 {} 个按钮".format(len(target_btns)))

    def on_canvas_right_click(self, global_pos, canvas_grid=None):
        """空地右键菜单：新建 / 刷新 / 全选 / 清空。
        canvas_grid: (gx, gy) 右键位置对应的画布格子，新建按钮时在此位置创建。"""
        sel_in_scene = []
        if MAYA_RUNNING:
            sel_in_scene = cmds.ls(selection=True, long=True) or []
        has_sel = bool(sel_in_scene)

        menu = QtWidgets.QMenu(self)
        menu.setStyleSheet(PICKER_MENU_QSS)
        a_new = menu.addAction("新建按钮")
        a_new.setEnabled(has_sel)
        if not has_sel:
            a_new.setToolTip("请先在 Maya 里选中物体")
        a_refresh = menu.addAction("刷新面板")
        menu.addSeparator()
        a_select_all = menu.addAction("选中全部按钮的物体")
        a_clear = menu.addAction("清空 Picker")

        action = menu.exec_(global_pos)
        if action is None: return

        if action == a_new:
            self._cb_new_picker_btn(at_grid=canvas_grid)
        elif action == a_refresh:
            for b in self.picker_area.buttons:
                b._refresh()
            self._status("已刷新")
        elif action == a_select_all:
            self._cb_select_all_ctrls()
        elif action == a_clear:
            self._cb_clear()

    def _cb_select_all_ctrls(self):
        """选中所有 Picker 按钮绑定 ctrl 的并集"""
        if not MAYA_RUNNING:
            return
        btns = list(self.picker_area.buttons)
        if not btns:
            self._status("画布为空")
            return
        all_full = []
        seen = set()
        for b in btns:
            for short in b.ctrls():
                full = self._resolve_short(short, btn=b)
                if not full or full in seen: continue
                seen.add(full)
                all_full.append(full)
        if not all_full:
            self._status("没有可选的物体")
            return
        cmds.select(all_full, replace=True)
        self._status("已选中 {} 个物体".format(len(all_full)))

    # -------- 文件操作 --------
    def _cb_save(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "保存 Picker", "", "Picker (*.json)")
        if not path:
            return
        if not path.endswith(".json"):
            path += ".json"
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.picker_area.to_data(), f,
                          ensure_ascii=False, indent=2)
            self._status("已保存：" + path)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "保存失败", str(e))

    def _cb_open(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "打开 Picker", "", "Picker (*.json)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.picker_area.load_data(data)
            self._status("已加载：{}（{} 个按钮）".format(
                path, len(self.picker_area.buttons)))
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "打开失败", str(e))

    def _cb_clear(self):
        if not self.picker_area.buttons:
            self._status("Picker 已经是空的")
            return
        ret = QtWidgets.QMessageBox.question(
            self, "清空 Picker",
            "确定要清空所有 {} 个按钮吗？".format(len(self.picker_area.buttons)),
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if ret == QtWidgets.QMessageBox.Yes:
            self.picker_area.clear_all()
            self._status("已清空 Picker")

    # -------- namespace --------
    def _cb_refresh_namespaces(self):
        self.ns_combo.clear()
        if MAYA_RUNNING:
            ns_list = cmds.namespaceInfo(listOnlyNamespaces=True, recurse=True) or []
            ns_list = [n for n in ns_list if n not in ("UI", "shared")]
            self.ns_combo.addItem("（无 namespace）")
            for n in ns_list:
                self.ns_combo.addItem(n)
        else:
            self.ns_combo.addItem("（offline mode — Maya 未运行）")

    def _current_namespace(self):
        txt = self.ns_combo.currentText()
        if txt.startswith("（"):
            return ""
        return txt

    @staticmethod
    def _strip_ns(short_with_ns):
        return short_with_ns.rsplit(":", 1)[-1]

    # -------- 状态栏 --------
    def _status(self, msg, ms=3000):
        # picker 版：仅更新窗口状态栏(如有)，不再往脚本编辑器打印提示
        win = self.window()
        if hasattr(win, "statusBar"):
            try:
                win.statusBar().showMessage(msg, ms)
            except Exception:
                pass

    # -------- 场景选区监听（更新 + 新建按钮灰显 / 按钮 sel_state） --------
    def _register_selection_job(self):
        if not MAYA_RUNNING: return
        if self._sel_job_id is not None:
            try: cmds.scriptJob(kill=self._sel_job_id, force=True)
            except Exception: pass
        try:
            self._sel_job_id = cmds.scriptJob(
                event=["SelectionChanged", self._update_sel_state],
                killWithScene=False, protected=False)
        except Exception as e:
            print("[ToolBox] selectionPage scriptJob 注册失败:", e)

    def _update_sel_state(self):
        """更新 + 新建按钮灰显 + 每个 Picker 按钮的 sel_state（三态）。
        被 scriptJob 调用——如果 self 已经被销毁（reload / 工具关闭但 job 没 kill），
        Qt 对象访问会抛 RuntimeError，这里捕获后主动 kill 自己的 scriptJob，避免持续报错。"""
        try:
            self._do_update_sel_state()
        except RuntimeError:
            # Qt 对象已销毁（工具被关/reload）→ 自杀式清理 scriptJob
            try:
                if self._sel_job_id is not None and MAYA_RUNNING:
                    cmds.scriptJob(kill=self._sel_job_id, force=True)
            except Exception: pass
            self._sel_job_id = None
        except Exception as e:
            # 其他异常不影响 Maya 主循环，吞掉 + 打日志
            print("[ToolBox] _update_sel_state 异常:", e)

    def _do_update_sel_state(self):
        if not MAYA_RUNNING:
            self.btn_new.setEnabled(False)
            return
        try:
            sel = cmds.ls(selection=True, long=True) or []
        except Exception:
            sel = []
        # + 新建按钮灰显
        self.btn_new.setEnabled(bool(sel))

        # 按钮三态高亮判定（v1.5.1 修复"对应按钮不亮"）：
        #   先用"完整长路径"精确比对（区分多 rig：A、B 同名控制器只亮被选那个）；
        #   长路径对不上时，再无条件回退到"短名"比对，兜住：
        #     · 无 namespace 物体（截图里的情况）
        #     · _resolve_short 返回值与场景长路径前缀/大小写不一致
        #     · 老存档没 created_ns
        #   这样既保留多 rig 精确，又不会因为路径对不上而整个不亮。
        try:
            # 场景选区：完整长路径集合 + 长路径集合各物体的短名集合
            sel_full = set(cmds.ls(sel, long=True) or sel)
            sel_short = {self._strip_ns(s.split("|")[-1]) for s in sel}
        except Exception:
            sel_full = set(sel)
            sel_short = set()

        # 是否处于"可能多 rig"场景：场景里出现了带 namespace 的选中物体，
        # 或启用了空间名锁定——这时才需要严格用长路径区分，避免误亮同名按钮。
        try:
            multi_rig = self.chk_ns_lock.isChecked() or any(":" in s.split("|")[-1] for s in sel)
        except Exception:
            multi_rig = False

        for b in self.picker_area.buttons:
            try:
                bound_shorts = b.ctrls()
                if not bound_shorts:
                    b.set_sel_state(b.SEL_NONE)
                    continue
                hit = 0
                for short in bound_shorts:
                    matched = False
                    full = self._resolve_short(short, btn=b)
                    # 1) 完整长路径精确比对（多 rig 区分）
                    if full:
                        for long_path in (cmds.ls(full, long=True) or [full]):
                            if long_path in sel_full:
                                matched = True
                                break
                    # 2) 回退短名比对：
                    #    - 非多 rig 场景：直接按短名比对（最稳，按钮一定亮）
                    #    - 多 rig 场景：仅当上面长路径解析失败(full 为空)时才用短名兜底，
                    #      避免把另一个 rig 的同名按钮也点亮。
                    if not matched:
                        if not multi_rig or not full:
                            if self._strip_ns(short) in sel_short:
                                matched = True
                    if matched:
                        hit += 1
                total = len(bound_shorts)
                if hit == 0:
                    b.set_sel_state(b.SEL_NONE)
                    # v1.5.2: 场景里这个按钮的物体一个都没被选中，
                    # 就把它残留的"框选橙边"也清掉——否则会从白色掉成橙黄色边，
                    # 让三态高亮(_sel_state) 成为唯一真实来源，避免残留亮显。
                    if b._frame_selected:
                        b.set_frame_selected(False)
                elif hit >= total:
                    b.set_sel_state(b.SEL_FULL)
                else:
                    b.set_sel_state(b.SEL_PARTIAL)
            except RuntimeError:
                pass

    def closeEvent(self, ev):
        if MAYA_RUNNING and self._sel_job_id is not None:
            try: cmds.scriptJob(kill=self._sel_job_id, force=True)
            except Exception: pass
            self._sel_job_id = None
        super(SelectionPage, self).closeEvent(ev)


# ============================================================
# 主窗口（picker 版：只有选择页，无导航栏/镜像/IKFK）
# ============================================================
class PickerWindow(QtWidgets.QMainWindow):

    def __init__(self, parent=None):
        super(PickerWindow, self).__init__(parent)
        self.setObjectName(WIN_OBJ_NAME)
        self.setWindowTitle(WIN_TITLE)
        self.resize(680, 540)
        self.setStyleSheet("QMainWindow { background-color: #383838; } "
                           "QWidget { background-color: #383838; color: #d0d0d0; }")
        self.setUpdatesEnabled(False)
        try:
            self.setCentralWidget(SelectionPage(self))
            self.statusBar().showMessage("\u5c31\u7eea")
        finally:
            self.setUpdatesEnabled(True)


# ============================================================
# 入口
# ============================================================
def _kill_orphan_scriptjobs():
    if not MAYA_RUNNING:
        return
    try:
        info = cmds.scriptJob(listJobs=True) or []
    except Exception:
        return
    for line in info:
        if "_update_sel_state" in line:
            try:
                jid = int(line.split(":", 1)[0].strip())
                cmds.scriptJob(kill=jid, force=True)
            except Exception:
                pass


def show():
    parent = maya_main_window()
    if parent is not None:
        for old in parent.findChildren(QtWidgets.QWidget, WIN_OBJ_NAME):
            try:
                old.close()
                old.setParent(None)
                old.deleteLater()
            except Exception:
                pass
    _kill_orphan_scriptjobs()
    win = PickerWindow(parent)
    try:
        QtWidgets.QApplication.processEvents()
    except Exception:
        pass
    win.show()
    return win


if __name__ == "__main__":
    try:
        _picker_win = show()
    except Exception as e:
        print("[Picker] \u542f\u52a8\u5931\u8d25:", e)
        raise
