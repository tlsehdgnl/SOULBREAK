"""Import chapel art and author L_Cathedral through Unreal Editor Python.

Bake source with Blender build_cathedral.py and Python build_chapel_surfaces.py.
Run UnrealEditor-Cmd with the Python/EditorScriptingUtilities plugins, legacy FBX
(Interchange.FeatureFlags.Import.FBX=False) and -ExecutePythonScript=<this file>.
Pass -ini:Engine:[/Script/NavigationSystem.NavigationSystemV1]:bWaitForAsyncLoadingBeforeBuildingNavigationAutomatically=False
when regenerating headlessly so static Recast tiles are built before the map is saved.
-SBSkipUnchangedSound and -SBReuseLevelTextures can shorten geometry-only passes.
"""
import json
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
scan_families=('Paving','Choir','Masonry','Dressed')
families={'Argillite','Tufa','Chasing','Damask','PotGlass',*scan_families}
packed={};normals={}
def texfile(name,setting=None,linear=False):
    if '-sbreuseleveltextures' in u.SystemLibrary.get_command_line().lower() and assets.does_asset_exist(env+'/'+name):
        return assets.load_asset(env+'/'+name)
    t=imported(source/(name+'.png'),env)
    if setting is not None:prop(t,'compression_settings',setting)
    if linear:prop(t,'srgb',False)
    save(t);return t
for family in sorted(families):
    packed[family]=texfile('T_'+family+'_M',u.TextureCompressionSettings.TC_MASKS,True)
    normals[family]=texfile('T_'+family+'_N',u.TextureCompressionSettings.TC_NORMALMAP,True)
colors={family:texfile('T_'+family+'_C') for family in scan_families}
neutral=texfile('T_Neutral_C')
projected=texfile('T_ClerestoryLight',u.TextureCompressionSettings.TC_MASKS,True)
incense=texfile('T_IncenseRay',u.TextureCompressionSettings.TC_MASKS,True)
icon_texture=texfile('T_SeveredOath')
saints_texture=texfile('T_Votaries')
fire_texture=texfile('T_CenserFire')
settings=u.FbxImportUI();settings.automated_import_should_detect_type=False;settings.import_mesh=True;settings.import_as_skeletal=False;settings.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
settings.reset_to_fbx_on_material_conflict=True
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
stone_color=sample(neutral,S.SAMPLERTYPE_COLOR,-1200,-620,'StoneColor')
relief=sample(normals['Tufa'],S.SAMPLERTYPE_NORMAL,-1200,110,'Relief')
output(relief,M.MP_NORMAL)
stone_tint=binary(u.MaterialExpressionMultiply,color,stone_color,-930,-440)
albedo=binary(u.MaterialExpressionMultiply,stone_tint,surface,-680,-340,ob='R')
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
output(binary(u.MaterialExpressionAdd,em,factor(scatter,.63,210,660),415,880),M.MP_EMISSIVE_COLOR)
lib.recompile_material(mat);save(mat)
stone_master=mat

mat=master('M_Icon')
icon=sample(icon_texture,S.SAMPLERTYPE_COLOR,-560,-190);output(icon,M.MP_BASE_COLOR)
output(factor(icon,.03,-235,25),M.MP_EMISSIVE_COLOR)
r=node(u.MaterialExpressionConstant,-245,150);prop(r,'r',.78);output(r,M.MP_ROUGHNESS)
lib.recompile_material(mat);save(mat)
icon_material=mat

mat=master('M_Incense',True)
mask=sample(incense,S.SAMPLERTYPE_MASKS,-550,90)
opacity=factor(mask,.070,-230,100,'R');output(opacity,M.MP_OPACITY)
tint=param(u.MaterialExpressionVectorParameter,'Airlight',u.LinearColor(.29,.34,.40,1),-555,-170);output(tint,M.MP_EMISSIVE_COLOR)
lib.recompile_material(mat);save(mat)
beam_material=mat

mat=master('M_VotaryGlass')
panel=sample(saints_texture,S.SAMPLERTYPE_COLOR,-520,-120)
output(factor(panel,.33,-265,-140),M.MP_BASE_COLOR)
output(factor(panel,.76,-265,55),M.MP_EMISSIVE_COLOR)
r=node(u.MaterialExpressionConstant,-250,200);prop(r,'r',.59);output(r,M.MP_ROUGHNESS)
lib.recompile_material(mat);save(mat);pane_material=mat

mat=master('M_CenserFlame',True)
uv=node(u.MaterialExpressionTextureCoordinate,-800,-240)
clock=node(u.MaterialExpressionTime,-800,40)
atlas=node(u.MaterialExpressionCustom,-465,-215)
prop(atlas,'description','Censer flame atlas, independent candle phases')
prop(atlas,'output_type',u.CustomMaterialOutputType.CMOT_FLOAT2)
inputs=[]
for label in ('UV','Seconds'):
    entry=u.CustomInput();prop(entry,'input_name',label);inputs.append(entry)
prop(atlas,'inputs',inputs)
# Mesh UVs store an integer phase followed by the local quad coordinate.
prop(atlas,'code',"float frame=floor(frac(Seconds*.91+floor(UV.x)/16.)*16.); return (float2(fmod(frame,4.),floor(frame/4.))+frac(UV))/4.;")
conn(uv,atlas,'UV');conn(clock,atlas,'Seconds')
fire=sample(fire_texture,S.SAMPLERTYPE_COLOR,-190,-180);conn(atlas,fire,'UVs')
output(factor(fire,1.75,20,-120),M.MP_EMISSIVE_COLOR)
lib.recompile_material(mat);save(mat);flame_material=mat

palette=json.loads((source/'chapel_materials.json').read_text())
slots=list(mesh.get_editor_property('static_materials'))
def material_family(name):
    if name=='Pavement':return 'Paving'
    if name=='ChoirPaving':return 'Choir'
    if name in ('Ashlar','Sootstone','VaultWeb'):return 'Masonry'
    if name in ('Chalk','Carving','Parchment','Purbeck','Sculpture','Tracery'):return 'Dressed'
    if name=='Memorial':return 'Chasing'
    if name=='Oak':return 'Damask'

    if name.startswith('Slab') or name in ('Deep','Mortar'):return 'Argillite'
    if name.endswith('Glass') or name in ('Flame','Fire','Wick','Coal','Rune'):return 'PotGlass'
    if name in ('Oxblood','Velvet','ClothGold'):return 'Damask'
    if name in ('Gold','Burnished','Iron','Oxide','Tracery'):return 'Chasing'
    return 'Tufa'
special={'Icon':icon_material,'Incense':beam_material,'SaintGlass':pane_material,'FlameSheet':flame_material}
actual_names={str(slot.material_slot_name) for slot in slots}
if not special.keys() <= actual_names:
    raise RuntimeError('FBX failed to supply chapel art slots: '+str(special.keys()-actual_names))
for slot in slots:
    name=str(slot.material_slot_name)
    if name not in palette:raise RuntimeError('Unknown FBX material slot '+repr(name))
    if name in special:
        slot.material_interface=special[name];continue
    rgb,r,m,g=palette[name];inst_name='MI_Chapel_'+name
    inst=assets.load_asset(env+'/'+inst_name) if assets.does_asset_exist(env+'/'+inst_name) else tools.create_asset(inst_name,env,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    lib.set_material_instance_parent(inst,stone_master)
    lib.set_material_instance_vector_parameter_value(inst,'Albedo',u.LinearColor(*rgb,1))
    for k,v in [('Roughness',r),('Metallic',m),('Glow',g),('Flicker',.14 if name in ('Wick','Fire','Coal') else 0.),('Floor',1. if name in ('Pavement','ChoirPaving','Memorial') else 0.)]:
        lib.set_material_instance_scalar_parameter_value(inst,k,v)
    family=material_family(name)
    lib.set_material_instance_texture_parameter_value(inst,'StoneColor',colors.get(family,neutral))
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
# Clerestory piers cast bands of soft window shadow. These six simple forms
# have no collision and cost considerably less than shadowing the entire nave.
for pier_x in (-1060,-657,-221,221,657,1060):
    a=spawn(u.StaticMeshActor,'Clerestory shadow pier', (pier_x,-1047,456))
    c=a.static_mesh_component;c.set_static_mesh(cube);c.set_collision_profile_name('NoCollision')
    a.set_actor_scale3d(u.Vector(.93,.27,8.92))
    c.set_cast_shadow(True);prop(c,'cast_hidden_shadow',True);a.set_actor_hidden_in_game(True)
start=spawn(u.PlayerStart,'Pilgrim | Arrival',(-740,0,101))
nav=spawn(u.NavMeshBoundsVolume,'Walkable nave bounds',(0,0,150))
nav.set_actor_scale3d(u.Vector(11,11,2.8))
u.log('NAV BOUNDS '+str(nav.get_actor_bounds(False)))
# A specified sky cubemap fills the visor and armor even without hardware GI.
sky=spawn(u.SkyLight,'Blue hour | Nave fill',(0,0,790)).light_component
sky.set_mobility(u.ComponentMobility.MOVABLE)
prop(sky,'source_type',u.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
sky.set_cubemap(u.load_object(None,'/Engine/MapTemplates/Sky/DaylightAmbientCubemap.DaylightAmbientCubemap'));sky.set_intensity(.225)
key=spawn(u.DirectionalLight,'Clerestory | Silver light',(-250,-840,890),67,-38).light_component
key.set_mobility(u.ComponentMobility.MOVABLE);key.set_light_color(u.LinearColor(.66,.77,.93));key.set_intensity(1.14)
prop(key,'light_source_angle',4.2)
def point(label,xyz,r,intensity,color,shadow=False):
    c=spawn(u.PointLight,label,xyz).light_component;c.set_mobility(u.ComponentMobility.MOVABLE);prop(c,'intensity_units',u.LightUnits.LUMENS);c.set_intensity(intensity);c.set_attenuation_radius(r);c.set_light_color(u.LinearColor(*color));prop(c,'cast_shadows',shadow);prop(c,'source_radius',22)
for s in (-1,1):
    for y in (-272,272):point('Ember bowl',(s*(1116 if s>0 else 961),y,150),470,175,(1,.33,.10))
    for x in (-680,680):point('Side chapel brazier',(x,s*943,135),430,155,(1,.34,.093))
point('Apse clerestory',(1100,-68,480),395,135,(.42,.57,.72))
point('Altar votives',(943,48,165),326,33,(1,.61,.36))
point('Crossing reflected candlelight',(135,413,306),708,432,(1,.68,.44))
# A cold arcing window source separates the dark steel breastplate from the far masonry.
point('Nave moon rim',(399,-427,471),735,670,(.46,.70,.95))
point('Pilgrim fill',(-468,217,279),790,642,(.83,.81,.77))
fog=spawn(u.ExponentialHeightFog,'Chapel dust',(0,0,-24)).get_component_by_class(u.ExponentialHeightFogComponent)
prop(fog,'fog_density',.028);prop(fog,'fog_height_falloff',.26);prop(fog,'fog_inscattering_luminance',u.LinearColor(.037,.065,.103,1));prop(fog,'start_distance',125)
grade=spawn(u.PostProcessVolume,'Nave | candle and moon tonemapping',(0,0,32))
prop(grade,'unbound',True)
pp=grade.get_editor_property('settings')
for key,value in [('bloom_intensity',.12),('bloom_threshold',1.8),('vignette_intensity',.245),('ambient_occlusion_intensity',.82),('ambient_occlusion_radius',95.)]:
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
