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
if '-sbskipunchangedsound' not in u.SystemLibrary.get_command_line().lower():sound_import()
skills={'Argillite','Tufa','Chasing','Damask','PotGlass'}
packed={};normals={}
def texfile(name,setting=None,linear=False):
    t=imported(source/(name+'.png'),env)
    if setting is not None:prop(t,'compression_settings',setting)
    if linear:prop(t,'srgb',False)
    save(t);return t
for family in sorted(skills):
    packed[family]=texfile('T_'+family+'_M',u.TextureCompressionSettings.TC_MASKS,True)
    normals[family]=texfile('T_'+family+'_N',u.TextureCompressionSettings.TC_NORMALMAP,True)
projected=texfile('T_ClerestoryLight',u.TextureCompressionSettings.TC_MASKS,True)
incense=texfile('T_IncenseRay',u.TextureCompressionSettings.TC_MASKS,True)
icon_texture=texfile('T_SeveredOath')
settings=u.FbxImportUI();settings.automated_import_should_detect_type=False;settings.import_mesh=True;settings.import_as_skeletal=False;settings.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
settings.import_materials=False;settings.import_textures=False
opts=settings.static_mesh_import_data
opts.combine_meshes=True;opts.auto_generate_collision=False;opts.generate_lightmap_u_vs=False
mesh=imported(source/'SM_Nave.fbx',env,settings)
bounds=mesh.get_bounds()
if bounds.box_extent.x<900 or bounds.box_extent.z<350:raise RuntimeError('Unexpected FBX scale')
lib=u.MaterialEditingLibrary
def master(name,translucent=False):
    m=assets.load_asset(env+'/'+name) if assets.does_asset_exist(env+'/'+name) else tools.create_asset(name,env,u.Material,u.MaterialFactoryNew())
    prop(m,'two_sided',True)
    if translucent:
        prop(m,'blend_mode',u.BlendMode.BLEND_ADDITIVE)
        prop(m,'shading_model',u.MaterialShadingModel.MSM_UNLIT)
    lib.delete_all_material_expressions(m);return m
def node(cls,x,y):return lib.create_material_expression(mat,cls,x,y)
def param(cls,name,v,x,y):
    a=node(cls,x,y);prop(a,'parameter_name',name);prop(a,'default_value',v);return a
def conn(a,b,k,out=''):
    if not lib.connect_material_expressions(a,out,b,k):raise RuntimeError('Material connection failed: '+b.get_name()+' / '+k)
def output(a,p,o=''):
    if not lib.connect_material_property(a,o,p):raise RuntimeError('Material output failed: '+str(p))
def sample(texture,typ,x,y,name=None):
    cls=u.MaterialExpressionTextureSampleParameter2D if name else u.MaterialExpressionTextureSample
    a=node(cls,x,y)
    if name:prop(a,'parameter_name',name)
    prop(a,'texture',texture);prop(a,'sampler_type',typ);return a
def binary(cls,a,b,x,y,oa='',ob=''):
    n=node(cls,x,y);conn(a,n,'A',oa);conn(b,n,'B',ob);return n
def factor(a,value,x,y,output=''):
    n=node(u.MaterialExpressionMultiply,x,y);conn(a,n,'A',output);prop(n,'const_b',value);return n
M=u.MaterialProperty;S=u.MaterialSamplerType
mat=master('M_Chapel')
color=param(u.MaterialExpressionVectorParameter,'Albedo',u.LinearColor(.2,.2,.2,1),-1200,-360)
surface=sample(packed['Tufa'],S.SAMPLERTYPE_MASKS,-1200,-160,'Surface')
relief=sample(normals['Tufa'],S.SAMPLERTYPE_NORMAL,-1200,110,'Relief')
output(relief,M.MP_NORMAL)
albedo=binary(u.MaterialExpressionMultiply,color,surface,-880,-340,ob='R')
rough=param(u.MaterialExpressionScalarParameter,'Roughness',.72,-920,140)
output(binary(u.MaterialExpressionMultiply,rough,surface,-560,120,ob='G'),M.MP_ROUGHNESS)
output(surface,M.MP_AMBIENT_OCCLUSION,'B')
metal=param(u.MaterialExpressionScalarParameter,'Metallic',0.,-900,320)
output(metal,M.MP_METALLIC)
worldpos=node(u.MaterialExpressionWorldPosition,-1450,580)
xy=node(u.MaterialExpressionComponentMask,-1210,580);prop(xy,'r',True);prop(xy,'g',True);conn(worldpos,xy,'')
local=factor(xy,1/2240.,-965,580);uv=node(u.MaterialExpressionAdd,-750,580);conn(local,uv,'A');prop(uv,'const_b',.5)
projection=sample(projected,S.SAMPLERTYPE_MASKS,-525,580);conn(uv,projection,'UVs')
floor=param(u.MaterialExpressionScalarParameter,'Floor',0.,-510,810)
shade=node(u.MaterialExpressionLinearInterpolate,-225,350);prop(shade,'const_a',1.);conn(projection,shade,'B','A');conn(floor,shade,'Alpha')
base=binary(u.MaterialExpressionMultiply,albedo,shade,0,-340)
output(base,M.MP_BASE_COLOR)
glow=param(u.MaterialExpressionScalarParameter,'Glow',0.,-900,1050)
clock=node(u.MaterialExpressionTime,-1400,1280)
sin=node(u.MaterialExpressionSine,-1180,1280);prop(sin,'period',.42);conn(clock,sin,'')
flicker=param(u.MaterialExpressionScalarParameter,'Flicker',0.,-1180,1450)
wave=binary(u.MaterialExpressionMultiply,sin,flicker,-900,1290)
bias=node(u.MaterialExpressionAdd,-640,1270);conn(wave,bias,'A');prop(bias,'const_b',1.)
em=binary(u.MaterialExpressionMultiply,binary(u.MaterialExpressionMultiply,base,glow,-570,1000),bias,-340,1000)
transmitted=binary(u.MaterialExpressionMultiply,projection,floor,-210,665)
scatter=binary(u.MaterialExpressionMultiply,transmitted,albedo,20,660)
output(binary(u.MaterialExpressionAdd,em,factor(scatter,1.7,210,660),415,880),M.MP_EMISSIVE_COLOR)
lib.recompile_material(mat);save(mat)
stone_master=mat

mat=master('M_Icon')
icon=sample(icon_texture,S.SAMPLERTYPE_COLOR,-560,-190);output(icon,M.MP_BASE_COLOR)
output(factor(icon,.34,-235,25),M.MP_EMISSIVE_COLOR)
r=node(u.MaterialExpressionConstant,-245,150);prop(r,'r',.52);output(r,M.MP_ROUGHNESS)
lib.recompile_material(mat);save(mat)
icon_material=mat

mat=master('M_Incense',True)
mask=sample(incense,S.SAMPLERTYPE_MASKS,-550,90)
opacity=factor(mask,.063,-230,100,'R');output(opacity,M.MP_OPACITY)
tint=param(u.MaterialExpressionVectorParameter,'Airlight',u.LinearColor(.14,.31,.49,1),-555,-170);output(tint,M.MP_EMISSIVE_COLOR)
lib.recompile_material(mat);save(mat)
beam_material=mat

palette=json.loads((source/'chapel_materials.json').read_text())
slots=list(mesh.get_editor_property('static_materials'))
def material_family(name):
    if name.startswith('Slab') or name in ('Deep','Mortar'):return 'Argillite'
    if name.endswith('Glass') or name in ('Flame','Fire','Wick','Coal','Rune'):return 'PotGlass'
    if name in ('Oxblood','Velvet','ClothGold'):return 'Damask'
    if name in ('Gold','Burnished','Iron','Oxide','Tracery'):return 'Chasing'
    return 'Tufa'
for slot in slots:
    name=str(slot.material_slot_name)
    if name not in palette:raise RuntimeError('Unknown FBX material slot '+repr(name))
    if name in ('Icon','Incense'):
        slot.material_interface=icon_material if name=='Icon' else beam_material;continue
    rgb,r,m,g=palette[name];inst_name='MI_Chapel_'+name
    inst=assets.load_asset(env+'/'+inst_name) if assets.does_asset_exist(env+'/'+inst_name) else tools.create_asset(inst_name,env,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    lib.set_material_instance_parent(inst,stone_master)
    lib.set_material_instance_vector_parameter_value(inst,'Albedo',u.LinearColor(*rgb,1))
    for k,v in [('Roughness',r),('Metallic',m),('Glow',g),('Flicker',.14 if name in ('Wick','Fire','Coal') else 0.),('Floor',1. if name.startswith('Slab') else 0.)]:
        lib.set_material_instance_scalar_parameter_value(inst,k,v)
    family=material_family(name)
    lib.set_material_instance_texture_parameter_value(inst,'Surface',packed[family])
    lib.set_material_instance_texture_parameter_value(inst,'Relief',normals[family])
    lib.update_material_instance(inst);save(inst);slot.material_interface=inst
prop(mesh,'static_materials',slots);save(mesh)

# NewLevel creates a blank, non-partitioned level. The map inherits the game's
# configured mode so it can be authored separately from the runtime C++ module.
if assets.does_asset_exist(level_path):
    current=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    if current is None or level_path not in current.get_path_name():
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
    if label.startswith('Pier collision'):
        a.static_mesh_component.set_cast_shadow(True);prop(a.static_mesh_component,'cast_hidden_shadow',True)
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
sky.set_cubemap(u.load_object(None,'/Engine/MapTemplates/Sky/DaylightAmbientCubemap.DaylightAmbientCubemap'));sky.set_intensity(.22)
key=spawn(u.DirectionalLight,'Clerestory | Silver light',(-250,-840,890),68,-43).light_component
key.set_mobility(u.ComponentMobility.MOVABLE);key.set_light_color(u.LinearColor(.53,.69,1));key.set_intensity(1.45)
prop(key,'light_source_angle',2.8)
def point(label,xyz,r,intensity,color,shadow=False):
    c=spawn(u.PointLight,label,xyz).light_component;c.set_mobility(u.ComponentMobility.MOVABLE);prop(c,'intensity_units',u.LightUnits.LUMENS);c.set_intensity(intensity);c.set_attenuation_radius(r);c.set_light_color(u.LinearColor(*color));prop(c,'cast_shadows',shadow);prop(c,'source_radius',22)
for s in (-1,1):
    for y in (-272,272):point('Ember bowl',(s*961,y,158),450,315,(1,.32,.080))
    for x in (-680,680):point('Side chapel brazier',(x,s*943,135),460,270,(1,.34,.093))
point('Reliquary cyan rim',(911,-84,420),415,232,(.18,.39,1))
point('Reliquary enamel',(945,35,203),345,195,(1,.62,.20))
point('Crossing gold',(112,385,318),730,620,(1,.61,.26))
# A cold arcing window source separates the dark steel breastplate from the far masonry.
point('Nave moon rim',(432,-430,480),710,800,(.34,.64,1))
point('Pilgrim fill',(-555,290,303),664,386,(.52,.69,.96))
fog=spawn(u.ExponentialHeightFog,'Chapel dust',(0,0,-24)).get_component_by_class(u.ExponentialHeightFogComponent)
prop(fog,'fog_density',.028);prop(fog,'fog_height_falloff',.26);prop(fog,'fog_inscattering_luminance',u.LinearColor(.037,.065,.103,1));prop(fog,'start_distance',125)
grade=spawn(u.PostProcessVolume,'Nave | candle and moon tonemapping',(0,0,32))
prop(grade,'unbound',True)
pp=grade.get_editor_property('settings')
for key,value in [('bloom_intensity',.12),('bloom_threshold',1.8),('vignette_intensity',.26)]:
    prop(pp,'override_'+key,True);prop(pp,key,value)
prop(grade,'settings',pp)
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
    dest=str(root/'Saved/ChapelMaterialQA.png')
    u.AutomationLibrary.take_high_res_screenshot(1280,720,dest,delay=5.0)
    u.EditorPythonScripting.set_keep_python_script_alive(True)
    started=time.monotonic()
    def finish_preview(dt):
        if Path(dest).exists() or time.monotonic()-started>60:
            u.unregister_slate_post_tick_callback(callback)
            u.EditorPythonScripting.set_keep_python_script_alive(False)
            u.SystemLibrary.quit_editor()
    callback=u.register_slate_post_tick_callback(finish_preview)
