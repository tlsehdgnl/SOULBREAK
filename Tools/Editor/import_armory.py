"""Import the pell's scanned materials and mesh sections, and the knight's new audio cues."""
from pathlib import Path
import unreal as u

source=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_saved_dir()))/'SBArmory'
folder='/Game/SoulBreak/Armory'
audio='/Game/SoulBreak/Audio'
assets=u.EditorAssetLibrary
tools=u.AssetToolsHelpers.get_asset_tools()
lib=u.MaterialEditingLibrary
assets.make_directory(folder)

def imported(path, destination, options=None):
    if not path.is_file():
        raise FileNotFoundError(path)
    task=u.AssetImportTask()
    task.filename=str(path)
    task.destination_path=destination
    task.destination_name=path.stem
    task.automated=True
    task.replace_existing=True
    task.save=True
    if options:
        task.options=options
        task.factory=u.FbxFactory()
    tools.import_asset_tasks([task])
    if not task.imported_object_paths:
        raise RuntimeError(f'Import failed for {path}')
    return assets.load_asset(task.imported_object_paths[0])

for cue in ('Charge','Wave','ShieldBreak','KneeBreak'):
    imported(source/f'S_{cue}.wav', audio)

materials={}
for surface in ('Ash','Hide'):
    name='M_Pell'+surface
    if assets.does_asset_exist(folder+'/'+name):
        materials[surface]=assets.load_asset(folder+'/'+name)
        continue
    mat=tools.create_asset(name,folder,u.Material,u.MaterialFactoryNew())
    for i,(key,property_name,sampler) in enumerate([
        ('Color',u.MaterialProperty.MP_BASE_COLOR,u.MaterialSamplerType.SAMPLERTYPE_COLOR),
        ('Normal',u.MaterialProperty.MP_NORMAL,u.MaterialSamplerType.SAMPLERTYPE_NORMAL),
        ('Rough',u.MaterialProperty.MP_ROUGHNESS,u.MaterialSamplerType.SAMPLERTYPE_MASKS)]):
        tex=imported(source/f'T_Pell{surface}{key}.jpg',folder)
        if key!='Color':
            tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if key=='Normal' else u.TextureCompressionSettings.TC_MASKS)
            tex.set_editor_property('srgb',False)
            assets.save_loaded_asset(tex,False)
        sample=lib.create_material_expression(mat,u.MaterialExpressionTextureSample,-480,220*i)
        sample.set_editor_property('texture',tex)
        sample.set_editor_property('sampler_type',sampler)
        if not lib.connect_material_property(sample,'R' if key=='Rough' else '',property_name):
            raise RuntimeError(f'Could not wire {surface} {key}')
    lib.recompile_material(mat)
    assets.save_loaded_asset(mat,False)
    materials[surface]=mat

for name in ('Iron','Bronze','Leather','Ivory'):
    materials[name]=assets.load_asset('/Game/SoulBreak/Materials/Characters/MI_'+name)
options=u.FbxImportUI()
options.automated_import_should_detect_type=False
options.import_as_skeletal=False
options.import_mesh=True
options.import_materials=False
options.import_textures=False
options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
options.static_mesh_import_data.set_editor_property('auto_generate_collision',False)
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
flag='Interchange.FeatureFlags.Import.FBX'
old=u.SystemLibrary.get_console_variable_bool_value(flag)
u.SystemLibrary.execute_console_command(world,flag+' 0')
try:
    for name in ('SM_PellStand','SM_LeatherTarge'):
        mesh=imported(source/(name+'.fbx'),folder,options)
        slots=list(mesh.static_materials)
        for slot in slots:
            slot.material_interface=materials[str(slot.material_slot_name)]
            assert slot.material_interface
        mesh.static_materials=slots
        if not assets.save_loaded_asset(mesh,False):raise RuntimeError(mesh.get_name())
finally:
    u.SystemLibrary.execute_console_command(world,flag+(' 1' if old else ' 0'))
u.log('SB_ARMORY_OK')

dust_path='/Game/SoulBreak/FX'
mask=imported(source/'T_StoneDust.png',dust_path)
mask.set_editor_property('srgb',False)
mask.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS)
assets.save_loaded_asset(mask,False)
name='M_StoneDust'
if not assets.does_asset_exist(dust_path+'/'+name):
    dust=tools.create_asset(name,dust_path,u.Material,u.MaterialFactoryNew())
    dust.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
    dust.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
    dust.set_editor_property('two_sided',True)
    lib.set_base_material_usage(dust,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES,True)
    def dust_node(kind,x,y):
        return lib.create_material_expression(dust,kind,x,y)
    t=dust_node(u.MaterialExpressionTextureSample,-700,240)
    t.set_editor_property('texture',mask)
    t.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    opacity=dust_node(u.MaterialExpressionPerInstanceCustomData,-720,420)
    opacity.set_editor_property('data_index',0)
    fade=dust_node(u.MaterialExpressionMultiply,-410,310)
    assert lib.connect_material_expressions(t,'R',fade,'A')
    assert lib.connect_material_expressions(opacity,'',fade,'B')
    depth=dust_node(u.MaterialExpressionDepthFade,-200,300)
    depth.set_editor_property('fade_distance_default',16.)
    assert lib.connect_material_expressions(fade,'',depth,'Opacity')
    assert lib.connect_material_property(depth,'',u.MaterialProperty.MP_OPACITY)
    color=dust_node(u.MaterialExpressionConstant3Vector,-420,-30)
    color.set_editor_property('constant',u.LinearColor(.25,.224,.193,1))
    assert lib.connect_material_property(color,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
    lib.recompile_material(dust)
    assert assets.save_loaded_asset(dust,False)
u.log('SB_DUST_OK')
