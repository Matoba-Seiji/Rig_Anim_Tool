import os
import shutil
import sys

d = os.environ.get('RIG_ANIM_TOOL_DIR') or os.environ.get('MAYATOUE_SCRIPT_DIR')
if not d:
    raise EnvironmentError('请设置环境变量 RIG_ANIM_TOOL_DIR 为本仓库根目录')
if d in sys.path:
    sys.path.remove(d)
sys.path.insert(0, d)

# ponytail: 删掉 __pycache__，避免 Maya 吃到旧字节码
for root, dirs, _files in os.walk(d):
    if '__pycache__' in dirs:
        shutil.rmtree(os.path.join(root, '__pycache__'), ignore_errors=True)


def _purge_modules(prefix):
    for name in list(sys.modules):
        if name == prefix or name.startswith(prefix + '.'):
            del sys.modules[name]


# ponytail: reload 只重跑旧 __file__，不会换路径；先踢出缓存再全新 import
_purge_modules('rig_anim_tool')
_purge_modules('maya_to_ue')
_purge_modules('Auto_Rig')

from rig_anim_tool.ui.main_window import show_ui

show_ui()
