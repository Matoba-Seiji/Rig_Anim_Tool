from maya import cmds


def short_node_name(node):
    return node.split('|')[-1].split(':')[-1]


def mesh_transform_from_node(node):
    node_type = cmds.nodeType(node)
    if node_type == 'mesh':
        parent = cmds.listRelatives(node, parent=True, fullPath=True) or []
        return parent[0] if parent else None
    shapes = cmds.listRelatives(node, shapes=True, fullPath=True,
                                noIntermediate=True, type='mesh') or []
    return node if shapes else None


def collect_mesh_transforms(selection):
    nodes = set(selection)
    for node in selection:
        children = cmds.listRelatives(node, allDescendents=True,
                                      fullPath=True) or []
        nodes.update(children)
    meshes = []
    for node in nodes:
        mesh_transform = mesh_transform_from_node(node)
        if mesh_transform:
            meshes.append(mesh_transform)
    return list(dict.fromkeys(meshes))


def collect_selected_root_joints(selection):
    roots = []
    for node in selection:
        if cmds.nodeType(node) == 'joint':
            roots.append(node)
            continue
        children = cmds.listRelatives(node, allDescendents=True,
                                      fullPath=True, type='joint') or []
        child_set = set(children)
        for child in children:
            parent = cmds.listRelatives(child, parent=True, fullPath=True) or []
            if not parent or parent[0] not in child_set:
                roots.append(child)
    return list(dict.fromkeys(roots))


def expand_joint_hierarchy(roots):
    joints = []
    for root in roots:
        joints.append(root)
        children = cmds.listRelatives(root, allDescendents=True,
                                      fullPath=True, type='joint') or []
        joints.extend(children)
    return list(dict.fromkeys(joints))


def collect_skin_influence_joints(mesh_transforms):
    joints = []
    for mesh in mesh_transforms:
        history = cmds.listHistory(mesh, pruneDagObjects=True) or []
        skin_clusters = cmds.ls(history, type='skinCluster') or []
        for skin_cluster in skin_clusters:
            influences = cmds.skinCluster(skin_cluster, q=True, inf=True) or []
            joints.extend(cmds.ls(influences, long=True) or influences)
    return list(dict.fromkeys(joints))


def top_joint_roots(joints):
    roots = []
    for joint in joints:
        current = joint
        while True:
            parent = cmds.listRelatives(current, parent=True, fullPath=True) or []
            if not parent or cmds.nodeType(parent[0]) != 'joint':
                break
            current = parent[0]
        roots.append(current)
    return list(dict.fromkeys(roots))


def collect_rig_export_nodes(selection):
    mesh_transforms = collect_mesh_transforms(selection)
    root_joints = collect_selected_root_joints(selection)
    influence_joints = collect_skin_influence_joints(mesh_transforms)
    joint_roots = root_joints or top_joint_roots(influence_joints)
    joint_hierarchy = expand_joint_hierarchy(joint_roots)
    export_nodes = list(dict.fromkeys(mesh_transforms + joint_hierarchy))
    return mesh_transforms, joint_roots, export_nodes


def has_generated_joint_name(name):
    lower_name = name.lower()
    if lower_name.startswith('joint') and lower_name[5:].isdigit():
        return True
    if lower_name.startswith('bone') and lower_name[4:].isdigit():
        return True
    return False


def skin_clusters_for_mesh(mesh):
    history = cmds.listHistory(mesh, pruneDagObjects=True) or []
    return cmds.ls(history, type='skinCluster') or []


def validate_skin_weights(mesh, skin_cluster, max_influences=4):
    warnings = []
    errors = []
    vertex_count = cmds.polyEvaluate(mesh, vertex=True) or 0
    too_many_count = 0
    unweighted_count = 0
    sample_too_many = []
    sample_unweighted = []
    for idx in range(vertex_count):
        component = f'{mesh}.vtx[{idx}]'
        try:
            weights = cmds.skinPercent(skin_cluster, component,
                                       q=True, value=True) or []
        except Exception as e:
            warnings.append(f'{short_node_name(mesh)} 权重读取失败: {e}')
            break
        active_weights = [w for w in weights if w > 0.0001]
        if len(active_weights) > max_influences:
            too_many_count += 1
            if len(sample_too_many) < 5:
                sample_too_many.append(idx)
        if not active_weights:
            unweighted_count += 1
            if len(sample_unweighted) < 5:
                sample_unweighted.append(idx)
    if too_many_count:
        errors.append(
            f'{short_node_name(mesh)} 有 {too_many_count} 个点影响骨骼数超过 '
            f'{max_influences}，示例点: {sample_too_many}')
    if unweighted_count:
        errors.append(
            f'{short_node_name(mesh)} 有 {unweighted_count} 个点没有有效权重，'
            f'示例点: {sample_unweighted}')
    return errors, warnings


def validate_rig_asset(mesh_transforms, root_joints, export_nodes):
    errors = []
    warnings = []
    info = []

    if len(root_joints) != 1:
        errors.append('必须存在唯一 Root joint')
    elif short_node_name(root_joints[0]).lower() != 'root':
        errors.append(
            f'Root joint 必须命名为 root，当前为 {short_node_name(root_joints[0])}')

    joints = cmds.ls(export_nodes, type='joint', long=True) or []
    short_joint_names = [short_node_name(j) for j in joints]
    duplicate_joint_names = sorted(
        name for name in set(short_joint_names) if short_joint_names.count(name) > 1)
    if duplicate_joint_names:
        errors.append(f'存在重复骨骼名: {", ".join(duplicate_joint_names)}')

    generated_names = [n for n in short_joint_names if has_generated_joint_name(n)]
    if generated_names:
        warnings.append(f'存在默认生成骨骼名，建议规范命名: {", ".join(generated_names[:10])}')

    joint_name_set = set(short_joint_names)
    for mesh in mesh_transforms:
        mesh_name = short_node_name(mesh)
        if mesh_name in joint_name_set:
            errors.append(f'Mesh 名称与骨骼重名: {mesh_name}')
        scale = cmds.xform(mesh, q=True, relative=True, scale=True)
        if any(abs(v - 1.0) > 0.001 for v in scale):
            warnings.append(f'{mesh_name} Scale 不是 1: {[round(v, 4) for v in scale]}')

        skin_clusters = skin_clusters_for_mesh(mesh)
        if not skin_clusters:
            errors.append(f'{mesh_name} 没有 SkinCluster')
            continue
        skin_errors, skin_warnings = validate_skin_weights(mesh, skin_clusters[0])
        errors.extend(skin_errors)
        warnings.extend(skin_warnings)

    if root_joints:
        root_pos = cmds.xform(root_joints[0], q=True, ws=True, t=True)
        if any(abs(v) > 0.001 for v in root_pos):
            warnings.append(f'Root 不在世界原点: {[round(v, 4) for v in root_pos]}')

    info.append(f'Mesh: {len(mesh_transforms)}')
    info.append(f'Joint: {len(joints)}')
    return {'errors': errors, 'warnings': warnings, 'info': info}


def format_validation_log(metadata, validation):
    lines = [
        f"资产: {metadata.get('asset')}",
        f"版本: {metadata.get('version')}",
        f"UE路径: {metadata.get('ue_destination')}",
        f"FBX: {metadata.get('fbx')}",
        '',
        '[Info]',
    ]
    lines.extend(validation.get('info') or ['None'])
    lines.append('')
    lines.append('[Errors]')
    lines.extend(validation.get('errors') or ['None'])
    lines.append('')
    lines.append('[Warnings]')
    lines.extend(validation.get('warnings') or ['None'])
    return '\n'.join(lines)
