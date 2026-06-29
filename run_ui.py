import importlib
import os
import shutil
import sys

d = os.environ['MAYATOUE_SCRIPT_DIR']
if d not in sys.path:
    sys.path.insert(0, d)

# ponytail: 删掉 __pycache__，避免 Maya reload 吃到旧字节码
for root, dirs, _files in os.walk(d):
    if '__pycache__' in dirs:
        shutil.rmtree(os.path.join(root, '__pycache__'), ignore_errors=True)

for _name in (
    'maya_to_ue.ui_widgets',
    'maya_to_ue.asset_validation',
    'maya_to_ue.maya_fbx',
    'maya_to_ue.ue_remote',
    'maya_to_ue.ue_scripts',
    'maya_to_ue.binding.rename',
    'maya_to_ue.binding.control_lib.controllib',
    'Auto_Rig.config',
    'Auto_Rig.joins_operate',
    'Auto_Rig.ctrls_create',
    'Auto_Rig.finish',
    'Auto_Rig.assist_tools',
    'Auto_Rig.advanced',
    'Auto_Rig.dragon',
    'Auto_Rig.UI',
    'maya_to_ue.retarget',
):
    importlib.reload(__import__(_name))

from maya_to_ue import retarget

importlib.reload(retarget)
retarget.show_ui()
