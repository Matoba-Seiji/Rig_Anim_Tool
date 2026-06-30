import os

from maya import cmds

PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(PACKAGE_DIR, 'assets')
CTRLS_LIB_DIR = os.path.join(ASSETS_DIR, 'ctrls_lib')
PRE_JOINTS_DIR = os.path.join(ASSETS_DIR, 'pre_joints')
REBUILD_FILE = os.path.join(ASSETS_DIR, 'jnt_rebuild', 'bipe.mb')


def ctrl_lib(name):
    """返回 ctrls_lib 下控制器文件的完整路径。"""
    return os.path.join(CTRLS_LIB_DIR, name)


def scale_node(node, factor):
    """在 node 现有 scale 基础上整体乘以 factor。"""
    sx, sy, sz = cmds.getAttr(f'{node}.scale')[0]
    cmds.setAttr(f'{node}.scaleX', sx * factor)
    cmds.setAttr(f'{node}.scaleY', sy * factor)
    cmds.setAttr(f'{node}.scaleZ', sz * factor)


def lock_attrs(node, attrs):
    """锁定并隐藏 node 上的指定属性。"""
    for attr in attrs:
        cmds.setAttr(f'{node}.{attr}', lock=True, keyable=False, channelBox=False)


def lock_srt_vis(node):
    """锁定 node 的 translate/rotate/scale 各轴及 visibility。"""
    attrs = [f'{c}{a}' for c in ('translate', 'rotate', 'scale') for a in 'XYZ']
    lock_attrs(node, attrs + ['visibility'])


def color_ctrls(pattern, color):
    """给匹配 pattern 的所有 transform 控制器设置覆盖颜色。"""
    for node in cmds.ls(pattern, type='transform'):
        cmds.setAttr(f'{node}.overrideEnabled', 1)
        cmds.setAttr(f'{node}.overrideColor', color)
