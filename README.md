# 绑定动画工具（RigAnimTool）

Maya 内绑定与动画管线工具，支持自动绑定、HumanIK 批量重定向、FBX 导出，以及通过 UE Remote Execution 一键导入。

## 目录结构

```
仓库根目录/
├── run_ui.py                    # Maya 启动入口
└── rig_anim_tool/               # Python 主包
    ├── __init__.py              # 公开 API: show_ui, RetargetUI
    ├── core/                    # 共享基础
    │   ├── maya_ui.py           # Maya 主窗口 Qt 父控件
    │   └── undo.py              # 撤销块装饰器
    ├── ui/
    │   ├── widgets.py           # 通用 Qt 控件
    │   └── main_window.py       # 主界面（绑定 / 动画 Tab）
    ├── pipeline/
    │   ├── rig_validation.py    # 绑定资产检测
    │   └── fbx_export.py        # Maya FBX 导出
    ├── ue/
    │   ├── remote.py            # UE Remote Execution 客户端
    │   └── import_scripts.py    # UE 端导入脚本生成
    ├── binding/                 # 绑定辅助工具
    │   ├── rename.py            # 批量重命名
    │   └── control_lib/
    │       ├── ui.py            # 控制器库界面
    │       └── shapes/          # 曲线控制器 mel + png
    └── rig/                     # 自动绑定
        ├── ui.py
        ├── config.py
        ├── joints.py
        ├── controllers.py
        ├── advanced.py
        ├── tools.py
        ├── finish.py
        ├── dragon.py
        └── assets/
            ├── pre_joints/
            ├── jnt_rebuild/
            └── ctrls_lib/
```

## 启动

1. 设置环境变量 **`RIG_ANIM_TOOL_DIR`** 为本仓库根目录。
   - Maya：在 `Documents/maya/2024/Maya.env` 写入  
     `RIG_ANIM_TOOL_DIR=C:\Users\yanchaofeng\Documents\GitHub\Rig_Anim_Tool`  
     改完**重启 Maya**。
2. 在 Maya 中执行 `run_ui.py`（脚本编辑器打开文件点执行，或 Shelf）。

## 功能

| Tab | 功能 |
|-----|------|
| 绑定 → 自动绑定 | 导入预设骨架、一键创建 FK/IK 控制器 |
| 绑定 → 重命名 | 批量添加前后缀、替换字符串、重命名 |
| 绑定 → 控制器库 | 曲线控制器创建、上色、替换与镜像 |
| 绑定 → 绑定导出 | 资产检测、FBX 导出、Send To UE |
| 动画 → 批量重定向 | HumanIK 动画重定向批量处理 |
| 动画 → 动画导出 | FBX 动画导入 UE |

## UE 前置条件

- 启用 **Python Editor Script Plugin**
- **Project Settings → Plugins → Python → Enable Remote Execution** 已勾选
