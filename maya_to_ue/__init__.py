"""Maya → UE 管线：主界面、FBX 导出、资产校验、UE 远程导入。"""

__all__ = ['RetargetUI', 'show_ui']


def __getattr__(name):
    if name in __all__:
        from maya_to_ue.retarget import RetargetUI, show_ui
        return {'RetargetUI': RetargetUI, 'show_ui': show_ui}[name]
    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')
