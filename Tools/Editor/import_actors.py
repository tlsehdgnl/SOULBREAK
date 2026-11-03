"""After build_art.py, use UnrealEditor-Cmd <project> -EnablePlugins=PythonScriptPlugin -ExecutePythonScript=<this_file> -unattended -RenderOffscreen."""
from pathlib import Path
import json
import unreal as u

source = Path(u.Paths.convert_relative_path_to_full(u.Paths.project_saved_dir())) / 'SBArt'
art = '/Game/SoulBreak'
characters = art + '/Characters'
animations = art + '/Animations'
materials = art + '/Materials/Characters'
asset = u.EditorAssetLibrary
tools = u.AssetToolsHelpers.get_asset_tools()

def annotate(message):
    u.log('SoulBreakArt: ' + str(message))

def create(name, folder, cls, factory):
    existing = asset.load_asset(folder + '/' + name) if asset.does_asset_exist(folder + '/' + name) else None
    return existing or tools.create_asset(name, folder, cls, factory)

def setprop(obj, key, value):
    obj.set_editor_property(key, value)

def palette_materials():
    palette = json.loads((source / 'palette.json').read_text())
    mat = create('M_Heraldry', materials, u.Material, u.MaterialFactoryNew())
    u.MaterialEditingLibrary.delete_all_material_expressions(mat)
    setprop(mat, 'two_sided', True)
    u.MaterialEditingLibrary.set_base_material_usage(mat, u.MaterialUsage.MATUSAGE_SKELETAL_MESH, True)
    def parameter(name, prop, expression, x, y):
        node = u.MaterialEditingLibrary.create_material_expression(mat, expression, x, y)
        setprop(node, 'parameter_name', name)
        u.MaterialEditingLibrary.connect_material_property(node, '', prop)
    parameter('Pigment', u.MaterialProperty.MP_BASE_COLOR, u.MaterialExpressionVectorParameter, -440, 0)
    parameter('Metal', u.MaterialProperty.MP_METALLIC, u.MaterialExpressionScalarParameter, -440, 140)
    parameter('Roughness', u.MaterialProperty.MP_ROUGHNESS, u.MaterialExpressionScalarParameter, -440, 280)
    parameter('Glow', u.MaterialProperty.MP_EMISSIVE_COLOR, u.MaterialExpressionVectorParameter, -440, 420)
    u.MaterialEditingLibrary.recompile_material(mat)
    asset.save_loaded_asset(mat)
    result = {}
    for name, (r, g, b, metal, roughness, emission) in palette.items():
        mi = create('MI_' + name, materials, u.MaterialInstanceConstant, u.MaterialInstanceConstantFactoryNew())
        u.MaterialEditingLibrary.set_material_instance_parent(mi, mat)
        u.MaterialEditingLibrary.set_material_usage_override(mi, u.MaterialUsage.MATUSAGE_SKELETAL_MESH, True, True)
        for param, value in [('Pigment', u.LinearColor(r, g, b, 1)), ('Glow', u.LinearColor(r*emission, g*emission, b*emission, 1))]:
            u.MaterialEditingLibrary.set_material_instance_vector_parameter_value(mi, param, value)
        u.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(mi, 'Metal', metal)
        u.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(mi, 'Roughness', roughness)
        asset.save_loaded_asset(mi)
        result[name] = mi
    return result

def import_fbx(name, kind, skeleton=None):
    opts = u.FbxImportUI()
    for key, value in [('automated_import_should_detect_type', False), ('import_as_skeletal', kind != 'static'),
                       ('import_mesh', kind != 'clip'), ('import_animations', kind == 'clip'), ('create_physics_asset', False),
                       ('import_materials', False), ('import_textures', False)]:
        setprop(opts, key, value)
    kinds={'static': u.FBXImportType.FBXIT_STATIC_MESH, 'rig': u.FBXImportType.FBXIT_SKELETAL_MESH,
           'clip': u.FBXImportType.FBXIT_ANIMATION}
    setprop(opts, 'mesh_type_to_import', kinds[kind])
    if skeleton:
        setprop(opts, 'skeleton', skeleton)
    if kind == 'clip':
        opts.anim_sequence_import_data.set_editor_property('use_default_sample_rate', True)
        opts.anim_sequence_import_data.set_editor_property('animation_length', u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
    task = u.AssetImportTask()
    folder = animations if kind == 'clip' else characters
    for key, value in [('filename', str(source / (name + '.fbx'))), ('destination_path', folder), ('destination_name', name),
                       ('options', opts), ('factory', u.FbxFactory()), ('replace_existing', True),
                       ('automated', True), ('save', True)]:
        setprop(task, key, value)
    tools.import_asset_tasks([task])
    annotate(str(task.imported_object_paths))
    ob = asset.load_asset(folder + '/' + name)
    if not ob:
        raise ValueError('FBX import failed for ' + name)
    return ob

def assign_materials(mesh, by_name, skeletal):
    prop = 'materials' if skeletal else 'static_materials'
    slots = list(mesh.get_editor_property(prop))
    for slot in slots:
        name = str(slot.get_editor_property('material_slot_name'))
        if name not in by_name:
            raise KeyError('Unknown material slot '+name)
        slot.set_editor_property('material_interface', by_name[name])
    setprop(mesh, prop, slots)
    asset.save_loaded_asset(mesh)

def run():
    by_name = palette_materials()
    hero = import_fbx('SK_Hero', 'rig')
    skeleton = hero.skeleton
    annotate(skeleton.get_path_name())
    asset.save_loaded_asset(skeleton, False)
    knight = import_fbx('SK_Knight', 'rig', skeleton)
    if knight.skeleton != skeleton: raise ValueError('Character skeletons do not match')
    assign_materials(hero, by_name, True)
    assign_materials(knight, by_name, True)
    assign_materials(import_fbx('SM_FallenBlade', 'static'), by_name, False)
    report={}
    for f in sorted(source.glob('AN_*.fbx')):
        clip = import_fbx(f.stem, 'clip', skeleton)
        if clip.get_editor_property("skeleton") != skeleton or clip.get_play_length()<.4:
            raise ValueError('Unusable clip: ' + f.stem)
        report[f.stem] = clip.get_play_length()
    actor = u.get_editor_subsystem(u.EditorActorSubsystem).spawn_actor_from_class(u.SkeletalMeshActor,u.Vector(),u.Rotator())
    comp=actor.skeletal_mesh_component
    comp.set_skeletal_mesh_asset(hero)
    names = [str(comp.get_bone_name(i)) for i in range(comp.get_num_bones())]
    for b in ('Root','Pelvis','Forward','BladeBase','BladeTip','UpperArmR','ForearmR','HandR'):
        if b not in names: raise ValueError('Missing bone '+b)
    for b in ['Root','Pelvis','Forward','BladeTip','HandR','Head']:
        report[b] = str(comp.get_socket_location(b))
    report['Skeleton'] = skeleton.get_path_name()
    report['Bones']=names
    (source/'import_report.json').write_text(json.dumps(report,indent=2))
    annotate(report)
    u.get_editor_subsystem(u.EditorActorSubsystem).destroy_actor(actor)
world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
fbx_import_flag = 'Interchange.FeatureFlags.Import.FBX'
previous_import_mode = u.SystemLibrary.get_console_variable_bool_value(fbx_import_flag)
u.SystemLibrary.execute_console_command(world, fbx_import_flag + ' 0')
try:
    run()
finally:
    u.SystemLibrary.execute_console_command(world, fbx_import_flag + (' 1' if previous_import_mode else ' 0'))
