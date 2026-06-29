import json


def build_ue_import_script(fbx_files, destination_path, skeleton_path):
    files_literal = json.dumps([f.replace('\\', '/') for f in fbx_files])
    dest_literal = json.dumps(destination_path)
    skel_literal = json.dumps(skeleton_path)
    return f"""
import unreal

fbx_files = {files_literal}
destination_path = {dest_literal}
skeleton_path = {skel_literal}

def _try_set(obj, prop_name, value):
    try:
        obj.set_editor_property(prop_name, value)
    except Exception:
        pass

def _build_options(skel_path):
    options = unreal.FbxImportUI()
    skeleton = unreal.load_asset(skel_path)
    if not skeleton:
        raise RuntimeError('Skeleton asset not found: ' + skel_path)
    _try_set(options, 'automated_import_should_detect_type', False)
    _try_set(options, 'mesh_type_to_import',
             unreal.FBXImportType.FBXIT_ANIMATION)
    _try_set(options, 'import_mesh', False)
    _try_set(options, 'import_as_skeletal', False)
    _try_set(options, 'import_animations', True)
    options.skeleton = skeleton
    _try_set(options.anim_sequence_import_data,
             'import_translation', unreal.Vector(0.0, 0.0, 0.0))
    _try_set(options.anim_sequence_import_data,
             'import_rotation', unreal.Rotator(0.0, 0.0, 0.0))
    _try_set(options.anim_sequence_import_data,
             'import_uniform_scale', 1.0)
    _try_set(options.anim_sequence_import_data,
             'animation_length',
             unreal.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
    _try_set(options.anim_sequence_import_data, 'snap_to_closest_frame_boundary',
             True)
    _try_set(options.anim_sequence_import_data, 'use_default_sample_rate', True)
    _try_set(options.anim_sequence_import_data, 'remove_redundant_keys', False)
    return options

def _build_task(filename, dest, opts):
    task = unreal.AssetImportTask()
    task.set_editor_property('automated', True)
    task.set_editor_property('destination_name', '')
    task.set_editor_property('destination_path', dest)
    task.set_editor_property('filename', filename)
    task.set_editor_property('replace_existing', True)
    task.set_editor_property('save', True)
    task.set_editor_property('options', opts)
    return task

opts = _build_options(skeleton_path)
tasks = [_build_task(f, destination_path, opts) for f in fbx_files]
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
imported_paths = []
for task in tasks:
    imported_paths.extend(task.get_editor_property('imported_object_paths') or [])
if not imported_paths:
    raise RuntimeError('UE did not import any animation assets from the FBX files.')
"""


def build_ue_skeleton_list_expr():
    return (
        "(lambda u: __import__('json').dumps(sorted([str(a.package_name) "
        "for a in u.AssetRegistryHelpers.get_asset_registry().get_assets_by_class("
        "u.TopLevelAssetPath('/Script/Engine', 'Skeleton'), True)])))"
        "(__import__('unreal'))"
    )


def build_ue_skeletal_mesh_import_script(fbx_file, destination_path, asset_name):
    fbx_literal = json.dumps(fbx_file.replace('\\', '/'))
    dest_literal = json.dumps(destination_path)
    name_literal = json.dumps(asset_name)
    materials_path = destination_path.rstrip('/') + '/' + asset_name + '_Materials'
    materials_literal = json.dumps(materials_path)
    return f"""
import unreal

fbx_file = {fbx_literal}
destination_path = {dest_literal}
asset_name = {name_literal}
materials_path = {materials_literal}

def _try_set(obj, prop_name, value):
    try:
        obj.set_editor_property(prop_name, value)
    except Exception:
        pass

# ponytail: Interchange FBX 会忽略 legacy FbxImportUI 的 create_physics_asset
try:
    editor_subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    unreal.SystemLibrary.execute_console_command(
        editor_subsystem.get_editor_world(),
        'Interchange.FeatureFlags.Import.FBX false')
except Exception:
    pass

options = unreal.FbxImportUI()
_try_set(options, 'automated_import_should_detect_type', False)
_try_set(options, 'import_mesh', True)
_try_set(options, 'import_as_skeletal', True)
_try_set(options, 'import_materials', True)
_try_set(options, 'import_textures', True)
_try_set(options, 'import_animations', False)
options.set_editor_property('create_physics_asset', True)
_try_set(options, 'mesh_type_to_import',
         unreal.FBXImportType.FBXIT_SKELETAL_MESH)
sk_data = options.skeletal_mesh_import_data
_try_set(sk_data, 'import_morph_targets', True)
_try_set(sk_data, 'update_skeleton_reference_pose', False)
_try_set(sk_data, 'use_t0_as_ref_pose', False)
_try_set(sk_data, 'preserve_smoothing_groups', True)
_try_set(sk_data, 'import_meshes_in_bone_hierarchy', True)
_try_set(sk_data, 'import_translation', unreal.Vector(0.0, 0.0, 0.0))
_try_set(sk_data, 'import_rotation', unreal.Rotator(0.0, 0.0, 0.0))
_try_set(sk_data, 'import_uniform_scale', 1.0)

task = unreal.AssetImportTask()
task.set_editor_property('automated', True)
task.set_editor_property('destination_path', destination_path)
task.set_editor_property('destination_name', asset_name)
task.set_editor_property('filename', fbx_file)
task.set_editor_property('replace_existing', True)
task.set_editor_property('save', True)
task.set_editor_property('options', options)

unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

editor_asset_lib = unreal.EditorAssetLibrary
if not editor_asset_lib.does_directory_exist(materials_path):
    editor_asset_lib.make_directory(materials_path)

_material_texture_classes = frozenset([
    'Material', 'MaterialInstanceConstant', 'MaterialInstance', 'Texture2D',
])
_keep_in_root_classes = frozenset([
    'SkeletalMesh', 'Skeleton', 'PhysicsAsset',
])
for asset_path in editor_asset_lib.list_assets(destination_path, recursive=False):
    if asset_path.startswith(materials_path + '/'):
        continue
    asset = unreal.load_asset(asset_path)
    if not asset:
        continue
    class_name = asset.get_class().get_name()
    if class_name in _keep_in_root_classes:
        continue
    if class_name not in _material_texture_classes:
        continue
    new_pkg_path = materials_path + '/' + asset.get_name()
    if asset_path == new_pkg_path:
        continue
    if editor_asset_lib.does_asset_exist(new_pkg_path):
        editor_asset_lib.delete_asset(new_pkg_path)
    if not editor_asset_lib.rename_asset(asset_path, new_pkg_path):
        unreal.log_warning('Failed to move asset: ' + asset_path)

imported_paths = task.get_editor_property('imported_object_paths') or []
skel_subsystem = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
for path in imported_paths:
    asset = unreal.load_asset(path)
    if not asset or not isinstance(asset, unreal.SkeletalMesh):
        continue
    if asset.get_editor_property('physics_asset'):
        continue
    if skel_subsystem:
        skel_subsystem.create_physics_asset(asset)
"""
