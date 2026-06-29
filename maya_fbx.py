import os

from maya import cmds, mel


def ensure_fbx_plugin():
    if not cmds.pluginInfo('fbxmaya', q=True, loaded=True):
        cmds.loadPlugin('fbxmaya')


def export_animation_fbx(fbx_path, export_joints, start_frame, end_frame):
    ensure_fbx_plugin()
    mel.eval('FBXResetExport;')
    mel.eval('FBXExportBakeComplexAnimation -v true;')
    mel.eval(f'FBXExportBakeComplexStart -v {start_frame};')
    mel.eval(f'FBXExportBakeComplexEnd -v {end_frame};')
    mel.eval('FBXExportBakeComplexStep -v 1;')
    cmds.select(export_joints, r=True)
    mel.eval(f'FBXExport -f "{fbx_path}" -s')


def export_rig_fbx(fbx_path, export_nodes):
    ensure_fbx_plugin()
    mel.eval('FBXResetExport;')
    mel.eval('FBXExportSmoothingGroups -v true;')
    mel.eval('FBXExportHardEdges -v false;')
    mel.eval('FBXExportTangents -v false;')
    mel.eval('FBXExportSmoothMesh -v true;')
    mel.eval('FBXExportTriangulate -v false;')
    mel.eval('FBXExportSkins -v true;')
    mel.eval('FBXExportShapes -v true;')
    mel.eval('FBXExportBakeComplexAnimation -v false;')
    mel.eval('FBXExportAnimationOnly -v false;')
    mel.eval('FBXExportCameras -v false;')
    mel.eval('FBXExportLights -v false;')
    try:
        mel.eval('FBXExportConstraints -v false;')
    except Exception:
        pass
    try:
        mel.eval('FBXExportInputConnections -v false;')
    except Exception:
        pass
    mel.eval('FBXExportUpAxis y;')
    mel.eval('FBXExportInAscii -v false;')
    mel.eval('FBXExportFileVersion -v FBX202000;')
    cmds.select(export_nodes, r=True)
    cmds.file(fbx_path, force=True, options='v=0;',
              type='FBX export', preserveReferences=True,
              exportSelected=True)
