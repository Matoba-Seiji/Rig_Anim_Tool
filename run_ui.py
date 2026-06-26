import importlib
import os
import sys

d = os.environ['MAYATOUE_SCRIPT_DIR']
if d not in sys.path:
    sys.path.insert(0, d)

for _name in ('ui_widgets', 'asset_validation', 'maya_fbx',
              'ue_remote', 'ue_scripts'):
    importlib.reload(__import__(_name))

import HumanIK_Retarget

importlib.reload(HumanIK_Retarget)
HumanIK_Retarget.show_ui()
