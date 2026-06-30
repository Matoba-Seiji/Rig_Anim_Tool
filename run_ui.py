import os
import shutil
import sys

d = os.environ.get('RIG_ANIM_TOOL_DIR')
if not d:
    raise EnvironmentError('请设置环境变量 RIG_ANIM_TOOL_DIR 为本仓库根目录')
if d in sys.path:
    sys.path.remove(d)
sys.path.insert(0, d)

for root, dirs, _files in os.walk(d):
    if '__pycache__' in dirs:
        shutil.rmtree(os.path.join(root, '__pycache__'), ignore_errors=True)


def _purge_modules(prefix):
    for name in list(sys.modules):
        if name == prefix or name.startswith(prefix + '.'):
            del sys.modules[name]


_purge_modules('rig_anim_tool')

from rig_anim_tool.ui.main_window import show_ui

show_ui()
