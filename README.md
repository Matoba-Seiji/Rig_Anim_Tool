# MayaToUE

Maya 内绑定与动画管线工具，支持自动绑定、HumanIK 批量重定向、FBX 导出，以及通过 UE Remote Execution 一键导入。

## 目录结构

```
MayaToUE/
├── run_ui.py              # Maya 启动入口
├── maya_to_ue/            # 主功能包
│   ├── retarget.py        # 主界面（绑定 / 动画 Tab）
│   ├── ui_widgets.py      # 通用 Qt 控件
│   ├── asset_validation.py
│   ├── maya_fbx.py
│   ├── ue_remote.py
│   ├── ue_scripts.py
│   └── maya_ui.py         # Maya 主窗口辅助
└── Auto_Rig/              # 自动绑定子系统
    ├── UI.py
    ├── joins_operate.py   # 骨架操作
    ├── ctrls_create.py    # 控制器创建
    ├── finish.py / advanced.py / assist_tools.py / dragon.py
    ├── pre_joints/        # 预设骨架 .mb
    ├── jnt_rebuild/       # 骨架重建缓存
    └── ctrls_lib/         # 控制器模板 .mb
```

## 启动

1. 设置环境变量 `MAYATOUE_SCRIPT_DIR` 为本仓库根目录。
2. 在 Maya 中执行 `run_ui.py`（Shelf 按钮或 `exec(open(...).read())`）。

## 功能

| Tab | 功能 |
|-----|------|
| 绑定 → 自动绑定 | 导入预设骨架、一键创建 FK/IK 控制器 |
| 绑定 → 绑定导出 | 资产检测、FBX 导出、Send To UE |
| 动画 → 批量重定向 | HumanIK 动画重定向批量处理 |
| 动画 → 动画导出 | FBX 动画导入 UE |

## UE 前置条件

- 启用 **Python Editor Script Plugin**
- **Project Settings → Plugins → Python → Enable Remote Execution** 已勾选
