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
    # Reimporting a mesh must not replace the finished measured PBR instances
    # with the simpler base used when bootstrapping the asset library.
    if asset.does_asset_exist(materials+'/M_ForgedSurfaces'):
        ready = {name: asset.load_asset(materials+'/MI_'+name) for name in palette
                 if asset.does_asset_exist(materials+'/MI_'+name)}
        if len(ready) == len(palette):
            for name, mi in ready.items():
                r,g,b,metal,roughness,emission=palette[name]
                u.MaterialEditingLibrary.set_material_instance_vector_parameter_value(mi,'Pigment',u.LinearColor(r,g,b,1))
                u.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(mi,'Metal',metal)
                if mi.get_editor_property('parent').get_name()=='M_Heraldry':
                    u.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(mi,'Roughness',roughness)
                    u.MaterialEditingLibrary.set_material_instance_vector_parameter_value(mi,'Glow',u.LinearColor(r*emission,g*emission,b*emission,1))
                asset.save_loaded_asset(mi)
            return ready
    mat = create('M_Heraldry', materials, u.Material, u.MaterialFactoryNew())
    u.MaterialEditingLibrary.delete_all_material_expressions(mat)
    setprop(mat, 'two_sided', True)
    usages=(u.MaterialUsage.MATUSAGE_SKELETAL_MESH, u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
    for usage in usages:
        u.MaterialEditingLibrary.set_base_material_usage(mat, usage, True)
    task=u.AssetImportTask()
    task.filename=str(source/'T_ArmorerMarks.tga')
    task.destination_path=materials
    task.automated=True
    task.replace_existing=True
    task.save=True
    tools.import_asset_tasks([task])
    normals={}
    for swatch in ('Burnished','Twill','Hide','Mail'):
        key='T_'+swatch+'_N'
        entry=u.AssetImportTask()
        entry.filename=str(source/(key+'.tga'))
        entry.destination_path=materials
        entry.automated=True
        entry.replace_existing=True
        entry.save=True
        tools.import_asset_tasks([entry])
        tex=asset.load_asset(materials+'/'+key)
        if not tex: raise RuntimeError(key)
        setprop(tex,'srgb',False)
        setprop(tex,'compression_settings',u.TextureCompressionSettings.TC_NORMALMAP)
        asset.save_loaded_asset(tex,False)
        normals[swatch]=tex
    marks=asset.load_asset(materials+'/T_ArmorerMarks')
    if not marks:
        raise RuntimeError('Missing baked surface marks')
    setprop(marks,'srgb',False)
    setprop(marks,'compression_settings',u.TextureCompressionSettings.TC_MASKS)
    asset.save_loaded_asset(marks,False)
    lib=u.MaterialEditingLibrary
    def node(cls,x,y):
        return lib.create_material_expression(mat,cls,x,y)
    def parameter(name,cls,x,y):
        p=node(cls,x,y)
        setprop(p,'parameter_name',name)
        return p
    def wire(a,pin,b,slot):
        if not lib.connect_material_expressions(a,pin,b,slot):
            raise RuntimeError('Material connection failed: '+slot)
    def output(a,prop):
        if not lib.connect_material_property(a,'',prop):
            raise RuntimeError('Material output connection failed')
    pigment=parameter('Pigment',u.MaterialExpressionVectorParameter,-1100,-260)
    metal=parameter('Metal',u.MaterialExpressionScalarParameter,-1100,220)
    rough=parameter('Roughness',u.MaterialExpressionScalarParameter,-640,420)
    glow=parameter('Glow',u.MaterialExpressionVectorParameter,-380,600)
    grain=node(u.MaterialExpressionTextureSample,-1100,10)
    setprop(grain,'texture',marks)
    setprop(grain,'sampler_type',u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    relief=parameter('SurfaceNormal',u.MaterialExpressionTextureSampleParameter2D,-720,-480)
    setprop(relief,'texture',normals['Burnished'])
    setprop(relief,'sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    if not lib.connect_material_property(relief,'RGB',u.MaterialProperty.MP_NORMAL):
        raise RuntimeError('Unconnected armour normal')
    variation=node(u.MaterialExpressionLinearInterpolate,-830,60)
    wire(grain,'G',variation,'A')
    wire(grain,'R',variation,'B')
    wire(metal,'',variation,'Alpha')
    remap=node(u.MaterialExpressionMultiply,-620,-70)
    setprop(remap,'const_b',.53)
    wire(variation,'',remap,'A')
    biased=node(u.MaterialExpressionAdd,-430,-60)
    setprop(biased,'const_b',.69)
    wire(remap,'',biased,'A')
    color=node(u.MaterialExpressionMultiply,-230,-99)
    wire(pigment,'',color,'A')
    wire(biased,'',color,'B')
    rough_scale=node(u.MaterialExpressionMultiply,-620,230)
    setprop(rough_scale,'const_b',.34)
    wire(variation,'',rough_scale,'A')
    rough_sum=node(u.MaterialExpressionAdd,-280,285)
    wire(rough_scale,'',rough_sum,'A')
    wire(rough,'',rough_sum,'B')
    output(color,u.MaterialProperty.MP_BASE_COLOR)
    output(metal,u.MaterialProperty.MP_METALLIC)
    output(rough_sum,u.MaterialProperty.MP_ROUGHNESS)
    output(glow,u.MaterialProperty.MP_EMISSIVE_COLOR)
    u.MaterialEditingLibrary.recompile_material(mat)
    asset.save_loaded_asset(mat)
    result = {}
    for name, (r, g, b, metal, roughness, emission) in palette.items():
        mi = create('MI_' + name, materials, u.MaterialInstanceConstant, u.MaterialInstanceConstantFactoryNew())
        u.MaterialEditingLibrary.set_material_instance_parent(mi, mat)
        for usage in usages:
            u.MaterialEditingLibrary.set_material_usage_override(mi, usage, True, True)
        for param, value in [('Pigment', u.LinearColor(r, g, b, 1)), ('Glow', u.LinearColor(r*emission, g*emission, b*emission, 1))]:
            u.MaterialEditingLibrary.set_material_instance_vector_parameter_value(mi, param, value)
        u.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(mi, 'Metal', metal)
        u.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(mi, 'Roughness', roughness)
        if name=='Mail':
            swatch='Mail'
        elif name in ('Leather','Obsidian'):
            swatch='Hide'
        elif name in ('Wine','Velvet','Crimson','Azure','DeepBlue','SeaSilk','Lining','Ivory'):
            swatch='Twill'
        else:
            swatch='Burnished'
        u.MaterialEditingLibrary.set_material_instance_texture_parameter_value(mi,'SurfaceNormal',normals[swatch])
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
    if kind != 'clip':
        mesh_opts=opts.skeletal_mesh_import_data if kind=='rig' else opts.static_mesh_import_data
        setprop(mesh_opts,'normal_import_method',u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
    if kind == 'clip':
        opts.anim_sequence_import_data.set_editor_property('use_default_sample_rate', False)
        opts.anim_sequence_import_data.set_editor_property('custom_sample_rate', 60)
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
    old_rig=characters+'/SK_Hero_Skeleton'
    existing=asset.load_asset(old_rig) if asset.does_asset_exist(old_rig) else None
    hero = import_fbx('SK_Hero', 'rig', existing)
    skeleton = hero.skeleton
    annotate(skeleton.get_path_name())
    asset.save_loaded_asset(skeleton, False)
    knight = import_fbx('SK_Knight', 'rig', skeleton)
    if knight.skeleton != skeleton: raise ValueError('Character skeletons do not match')
    assign_materials(hero, by_name, True)
    assign_materials(knight, by_name, True)
    for name in ('SM_FallenBlade','SM_FallenShield','SM_FallenKnee'):
        assign_materials(import_fbx(name,'static'),by_name,False)
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
    for b in ('Root','Pelvis','Forward','BladeBase','BladeTip','UpperArmR','ForearmR','HandR','CloakTop','CloakHem','ShieldPlate','KneePlateL'):
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
