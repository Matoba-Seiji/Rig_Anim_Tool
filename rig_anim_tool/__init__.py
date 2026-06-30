"""绑定动画工具：Maya 内绑定、动画重定向与 UE 导出管线。"""

__all__ = ['RetargetUI', 'show_ui']


def __getattr__(name):
    if name in __all__:
        from rig_anim_tool.ui.main_window import RetargetUI, show_ui
        return {'RetargetUI': RetargetUI, 'show_ui': show_ui}[name]
    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')
