# -*- coding: utf-8 -*-

import os
import shutil
import sys

_TOOL_PKG = "rig_anim_tool"


def _ensure_paths():
    # 启动器同目录即为工具根目录
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)


def _purge_cache():
    # 清掉 sys.modules 里的旧模块 + 物理删除 __pycache__，确保加载最新代码
    for name in list(sys.modules.keys()):
        if name == _TOOL_PKG or name.startswith(_TOOL_PKG + "."):
            try:
                del sys.modules[name]
            except Exception:
                pass

    pkg_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), _TOOL_PKG)
    for root, dirs, _files in os.walk(pkg_dir):
        if "__pycache__" in dirs:
            shutil.rmtree(os.path.join(root, "__pycache__"), ignore_errors=True)


def show():
    _ensure_paths()
    _purge_cache()
    from rig_anim_tool.ui.main_window import show_ui
    show_ui()


if __name__ == "__main__":
    show()
