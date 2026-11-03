"""Import generated art and sound and author L_Cathedral through Unreal Editor Python."""
import json
import math
import os
from pathlib import Path
import unreal as u
root=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
source=Path(os.getenv('SB_LEVEL_SOURCE',root/'Saved/SBLevel'))
folder='/Game/SoulBreak'
env=folder+'/Environment'
aud=folder+'/Audio'
level_path=folder+'/Maps/L_Cathedral'
assets=u.EditorAssetLibrary
tools=u.AssetToolsHelpers.get_asset_tools()
actors=u.get_editor_subsystem(u.EditorActorSubsystem)
levels=u.get_editor_subsystem(u.LevelEditorSubsystem)
for d in (env,aud,folder+'/Maps'): assets.make_directory(d)
def prop(obj,key,value):obj.set_editor_property(key,value)
def save(obj):
    if not assets.save_loaded_asset(obj,only_if_is_dirty=False):raise RuntimeError('Could not save '+obj.get_path_name())
def imported(file,d,opts=None):
    target=d+'/'+file.stem
    if '-sbreuselevelsources' in u.SystemLibrary.get_command_line().lower() and assets.does_asset_exist(target):return assets.load_asset(target)
    task=u.AssetImportTask();task.filename=str(file);task.destination_path=d;task.destination_name=file.stem;task.automated=True;task.replace_existing=True;task.save=True
    if opts is not None:task.options=opts
    tools.import_asset_tasks([task])
    asset=assets.load_asset(d+'/'+file.stem)
    if not asset:raise RuntimeError('Import failed: '+str(file))
    return asset
def sound_import():
    for wav in sorted(source.glob('S_*.wav')):
        sound=imported(wav,aud)
        if wav.stem=='S_Chapel':
            prop(sound,'looping',True);save(sound)
sound_import()
texture=imported(source/'T_Mineral.png',env)
prop(texture,'srgb',False);save(texture)
settings=u.FbxImportUI();settings.automated_import_should_detect_type=False;settings.import_mesh=True;settings.import_as_skeletal=False;settings.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
settings.import_materials=False;settings.import_textures=False
opts=settings.static_mesh_import_data
opts.combine_meshes=True;opts.auto_generate_collision=False;opts.generate_lightmap_u_vs=False
mesh=imported(source/'SM_Nave.fbx',env,settings)
bounds=mesh.get_bounds()
u.log('CHAPEL BOUNDS '+str(bounds.box_extent))
if bounds.box_extent.x<900 or bounds.box_extent.z<350:raise RuntimeError('Unexpected FBX scale')
lib=u.MaterialEditingLibrary
mat_name='M_Chapel'
mat=assets.load_asset(env+'/'+mat_name) if assets.does_asset_exist(env+'/'+mat_name) else tools.create_asset(mat_name,env,u.Material,u.MaterialFactoryNew())
prop(mat,'two_sided',True)
lib.delete_all_material_expressions(mat)
def expr(cls,x,y):return lib.create_material_expression(mat,cls,x,y)
def param(cls,name,default,x,y):
    p=expr(cls,x,y);prop(p,'parameter_name',name);prop(p,'default_value',default);return p
def conn(a,b,arg,out=''):
    if not lib.connect_material_expressions(a,out,b,arg):raise RuntimeError('Material input connection failed: '+str(b.get_name())+' '+arg)
color=param(u.MaterialExpressionVectorParameter,'Albedo',u.LinearColor(.3,.3,.3,1),-800,-160)
sample=expr(u.MaterialExpressionTextureSample,-800,80);prop(sample,'texture',texture);prop(sample,'sampler_type',u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
mul=expr(u.MaterialExpressionMultiply,-450,-100);conn(color,mul,'A');conn(sample,mul,'B','R')
lib.connect_material_property(mul,'',u.MaterialProperty.MP_BASE_COLOR)
for key,num,channel in [('Roughness',.72,u.MaterialProperty.MP_ROUGHNESS),('Metallic',0.,u.MaterialProperty.MP_METALLIC)]:
    p=param(u.MaterialExpressionScalarParameter,key,num,-800,320 if key=='Roughness' else 480);lib.connect_material_property(p,'',channel)
glow=param(u.MaterialExpressionScalarParameter,'Glow',0.,-450,630);em=expr(u.MaterialExpressionMultiply,-150,280);conn(mul,em,'A');conn(glow,em,'B')
# Only the votive flame and embers flicker; the windows remain steady.
clock=expr(u.MaterialExpressionTime,-930,815)
flame_phase=expr(u.MaterialExpressionSine,-650,815);prop(flame_phase,'period',.42);conn(clock,flame_phase,'')
flicker=param(u.MaterialExpressionScalarParameter,'Flicker',0.,-650,955)
wave=expr(u.MaterialExpressionMultiply,-400,815);conn(flame_phase,wave,'A');conn(flicker,wave,'B')
bias=expr(u.MaterialExpressionAdd,-180,815);conn(wave,bias,'A');prop(bias,'const_b',1.0)
lit=expr(u.MaterialExpressionMultiply,30,530);conn(em,lit,'A');conn(bias,lit,'B')
lib.connect_material_property(lit,'',u.MaterialProperty.MP_EMISSIVE_COLOR);lib.recompile_material(mat);save(mat)
palette=json.loads((source/'chapel_materials.json').read_text())
slots=list(mesh.get_editor_property('static_materials'))
for i,slot in enumerate(slots):
    name=str(slot.material_slot_name)
    if name not in palette:raise RuntimeError('Unknown FBX material slot '+repr(name))
    rgb,r,m,g=palette[name];inst_name='MI_Chapel_'+name
    inst=assets.load_asset(env+'/'+inst_name) if assets.does_asset_exist(env+'/'+inst_name) else tools.create_asset(inst_name,env,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    lib.set_material_instance_parent(inst,mat)
    lib.set_material_instance_vector_parameter_value(inst,'Albedo',u.LinearColor(*rgb,1))
    for key,v in [('Roughness',r),('Metallic',m),('Glow',g),('Flicker',.14 if name in ('Wick','Fire','Coal') else 0.)]:lib.set_material_instance_scalar_parameter_value(inst,key,v)
    lib.update_material_instance(inst);save(inst);mesh.set_material(i,inst)
save(mesh)
# NewLevel creates a blank, non-partitioned level. The map inherits the game's
# configured mode so it can be authored separately from the runtime C++ module.
if assets.does_asset_exist(level_path):
    if not levels.load_level(level_path):raise RuntimeError('Could not load level')
    for actor in actors.get_all_level_actors():
        if actor.actor_has_tag('ChapelAuthored'):actors.destroy_actor(actor)
elif not levels.new_level(level_path):raise RuntimeError('Could not create level')
def spawn(cls,label,loc,yaw=0,pitch=0):
    a=actors.spawn_actor_from_class(cls,u.Vector(*loc),u.Rotator(pitch=pitch,yaw=yaw,roll=0))
    if a is None:raise RuntimeError('Failed to spawn '+label)
    a.set_actor_label(label);prop(a,'tags',['ChapelAuthored']);return a
nave=spawn(u.StaticMeshActor,'Nave | Chapel of the Severed Sun',(0,0,0))
comp=nave.static_mesh_component;comp.set_static_mesh(mesh);comp.set_collision_profile_name('NoCollision');comp.set_cast_shadow(False)
cube=assets.load_asset('/Engine/BasicShapes/Cube');cylinder=assets.load_asset('/Engine/BasicShapes/Cylinder')
def blocker(label,loc,scale,m):
    a=spawn(u.StaticMeshActor,label,loc);a.static_mesh_component.set_static_mesh(m);a.set_actor_scale3d(u.Vector(*scale))
    a.static_mesh_component.set_collision_profile_name('BlockAll')
    a.set_actor_hidden_in_game(True);a.static_mesh_component.set_cast_shadow(False)
    a.static_mesh_component.set_visibility(False)
    return a
blocker('Walkable floor',(0,0,-19.8),(21,21,.4),cube)
for s in (-1,1):
    blocker('Nave boundary X '+str(s),(s*1040,0,220),(.65,21.3,4.6),cube)
    blocker('Nave boundary Y '+str(s),(0,s*1037,220),(21.4,.65,4.6),cube)
for x in (-480,480):
    for y in (-670,670):blocker('Pier collision '+str((x,y)),(x,y,264),(1.35,1.35,5.3),cylinder)
start=spawn(u.PlayerStart,'Pilgrim | Arrival',(-800,0,101))
nav=spawn(u.NavMeshBoundsVolume,'Walkable nave bounds',(0,0,150))
nav.set_actor_scale3d(u.Vector(11,11,2.8))
u.log('NAV BOUNDS '+str(nav.get_actor_bounds(False)))
# A specified sky cubemap fills the visor and armor even without hardware GI.
sky=spawn(u.SkyLight,'Blue hour | Nave fill',(0,0,790)).light_component
sky.set_mobility(u.ComponentMobility.MOVABLE)
prop(sky,'source_type',u.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
sky.set_cubemap(u.load_object(None,'/Engine/MapTemplates/Sky/DaylightAmbientCubemap.DaylightAmbientCubemap'));sky.set_intensity(.79)
key=spawn(u.DirectionalLight,'Clerestory | Silver light',(-720,-640,890),38,-47).light_component
key.set_mobility(u.ComponentMobility.MOVABLE);key.set_light_color(u.LinearColor(.758,.881,1));key.set_intensity(3.1)
prop(key,'light_source_angle',3.0)
def point(label,xyz,r,intensity,color,shadow=False):
    c=spawn(u.PointLight,label,xyz).light_component;c.set_mobility(u.ComponentMobility.MOVABLE);prop(c,'intensity_units',u.LightUnits.LUMENS);c.set_intensity(intensity);c.set_attenuation_radius(r);c.set_light_color(u.LinearColor(*color));prop(c,'cast_shadows',shadow);prop(c,'source_radius',22)
for s in (-1,1):
    for y in (-272,272):point('Ember bowl',(s*961,y,158),465,1320,(1,.393,.127))
    for x in (-680,680):point('Side chapel brazier',(x,s*943,135),500,950,(1,.40,.145))
point('Reliquary glow',(840,0,391),790,3400,(.38,.75,1))
point('Crossing gold',(90,340,403),846,2200,(1,.725,.39))
fog=spawn(u.ExponentialHeightFog,'Chapel dust',(0,0,-24)).get_component_by_class(u.ExponentialHeightFogComponent)
prop(fog,'fog_density',.016);prop(fog,'fog_height_falloff',.21);prop(fog,'fog_inscattering_luminance',u.LinearColor(.167,.211,.268,1));prop(fog,'start_distance',85)
ambient=spawn(u.AmbientSound,'Nocturne in D | Chapel ambience',(0,0,0)).audio_component
ambient.set_sound(assets.load_asset(aud+'/S_Chapel'));ambient.set_volume_multiplier(.48)
u.SystemLibrary.execute_console_command(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world(),'RebuildNavigation')
if not levels.save_current_level():raise RuntimeError('Could not save cathedral level')
u.log('SB_LEVEL_AUTHORED '+level_path)
# A scripted editor run also records the game-view composition for visual QA.
if '-executepythonscript=' in u.SystemLibrary.get_command_line().lower() and '-nullrhi' not in u.SystemLibrary.get_command_line().lower():
    import time
    cam=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    cam.set_level_viewport_camera_info(u.Vector(-814,-45,223),u.Rotator(pitch=2,yaw=2,roll=0))
    actors.set_selected_level_actors([])
    world=cam.get_editor_world()
    u.SystemLibrary.execute_console_command(world,'r.DefaultFeature.AutoExposure 0')
    u.SystemLibrary.execute_console_command(world,'r.DynamicGlobalIlluminationMethod 0')
    u.SystemLibrary.execute_console_command(world,'r.Lumen.Reflections.Allow 0')
    dest=str(root/'Saved/ChapelQA.png')
    u.AutomationLibrary.take_high_res_screenshot(1280,720,dest,delay=5.0)
    u.EditorPythonScripting.set_keep_python_script_alive(True)
    started=time.monotonic()
    def finish_preview(dt):
        if Path(dest).exists() or time.monotonic()-started>60:
            u.unregister_slate_post_tick_callback(callback)
            u.EditorPythonScripting.set_keep_python_script_alive(False)
            u.SystemLibrary.quit_editor()
    callback=u.register_slate_post_tick_callback(finish_preview)
