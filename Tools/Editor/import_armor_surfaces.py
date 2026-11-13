"""Bind the photographed PBR swatches to existing hero, knight and detached equipment material slots."""
from pathlib import Path
import unreal as u

base='/Game/SoulBreak/Materials/Characters'
source=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_saved_dir()))/'SBArt'
assets=u.EditorAssetLibrary
tools=u.AssetToolsHelpers.get_asset_tools()
ml=u.MaterialEditingLibrary
families=('Iron','Wool','Linen','Leather')
surfaces={}
normals={}

for family in families:
    for channel,bucket,compression in [('M',surfaces,u.TextureCompressionSettings.TC_MASKS),
                                        ('N',normals,u.TextureCompressionSettings.TC_NORMALMAP)]:
        key=f'T_Forged{family}_{channel}'
        task=u.AssetImportTask()
        task.filename=str(source/(key+'.png'))
        task.destination_path=base
        task.automated=True
        task.replace_existing=True
        task.save=True
        assert Path(task.filename).is_file(),key
        tools.import_asset_tasks([task])
        tex=assets.load_asset(base+'/'+key)
        assert tex,key
        tex.set_editor_property('compression_settings',compression)
        tex.set_editor_property('srgb',False)
        assets.save_loaded_asset(tex,False)
        bucket[family]=tex

path=base+'/M_ForgedSurfaces'
mat=assets.load_asset(path) if assets.does_asset_exist(path) else None
if not mat:
    mat=tools.create_asset('M_ForgedSurfaces',base,u.Material,u.MaterialFactoryNew())
    mat.set_editor_property('two_sided',True)
    for usage in (u.MaterialUsage.MATUSAGE_SKELETAL_MESH,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES):
        ml.set_base_material_usage(mat,usage,True)
    def node(kind,x,y,**properties):
        n=ml.create_material_expression(mat,kind,x,y)
        for k,v in properties.items():n.set_editor_property(k,v)
        return n
    def wire(src,pin,dst,slot):
        assert ml.connect_material_expressions(src,pin,dst,slot),(src.get_name(),slot)
    def output(src,pin,prop):
        assert ml.connect_material_property(src,pin,prop),str(prop)
    def scalar(name,default,x,y):
        return node(u.MaterialExpressionScalarParameter,x,y,parameter_name=name,default_value=default)
    def mul(a,b,x,y,aout='',bout=''):
        v=node(u.MaterialExpressionMultiply,x,y)
        wire(a,aout,v,'A')
        wire(b,bout,v,'B')
        return v
    def remap(sample,pin,gain,bias,x,y):
        a=node(u.MaterialExpressionMultiply,x,y,const_b=gain)
        wire(sample,pin,a,'A')
        b=node(u.MaterialExpressionAdd,x+180,y,const_b=bias)
        wire(a,'',b,'A')
        return b
    def lerp(a,apin,b,bpin,alpha,x,y):
        n=node(u.MaterialExpressionLinearInterpolate,x,y)
        wire(a,apin,n,'A')
        wire(b,bpin,n,'B')
        wire(alpha,'',n,'Alpha')
        return n

    uv=node(u.MaterialExpressionTextureCoordinate,-1720,0)
    tile=scalar('SwatchScale',1.0,-1720,140)
    coords=mul(uv,tile,-1470,0)
    scan=node(u.MaterialExpressionTextureSampleParameter2D,-1250,-220,parameter_name='SurfaceScan',
              texture=surfaces['Iron'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    wire(coords,'',scan,ml.get_material_expression_input_names(scan)[0])
    norm=node(u.MaterialExpressionTextureSampleParameter2D,-1160,850,parameter_name='MeasuredNormal',
              texture=normals['Iron'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    wire(coords,'',norm,ml.get_material_expression_input_names(norm)[0])
    output(norm,'',u.MaterialProperty.MP_NORMAL)
    dye=node(u.MaterialExpressionVectorParameter,-780,-510,parameter_name='Pigment',default_value=u.LinearColor(.2,.2,.2,1))
    albedo=mul(dye,remap(scan,'R',.74,.62,-1030,-340),-370,-420)
    # Bind-pose height keeps wear attached to the boot, hem or plate as the skeleton animates.
    bind_position=node(u.MaterialExpressionPreSkinnedPosition,-1700,430)
    z=node(u.MaterialExpressionComponentMask,-1490,450,b=True)
    wire(bind_position,'',z,'')
    hemt=node(u.MaterialExpressionVertexInterpolator,-1280,440)
    wire(z,'',hemt,'VS')
    lower=node(u.MaterialExpressionSaturate,-660,465)
    wire(remap(hemt,'',-.014,1.18,-1050,450),'',lower,'')
    grime=mul(lower,scan,-470,440,bout='B')
    dirt=mul(grime,scalar('WearAtHem',.32,-455,640),-210,435)
    soil=node(u.MaterialExpressionConstant3Vector,-120,-225,constant=u.LinearColor(.072,.055,.040,1))
    output(lerp(albedo,'',soil,'',dirt,110,-390),'',u.MaterialProperty.MP_BASE_COLOR)
    rust=remap(scan,'B',-.24,1,-785,40)
    clear=node(u.MaterialExpressionOneMinus,-15,400)
    wire(dirt,'',clear,'')
    metal=mul(scalar('Metal',.75,-460,155),rust,-210,108)
    output(mul(metal,clear,130,95),'',u.MaterialProperty.MP_METALLIC)
    # Authored base roughness preserves polished edges; the photographed map supplies local variation.
    rough=scalar('Roughness',.35,-850,235)
    r=node(u.MaterialExpressionAdd,-330,245)
    wire(rough,'',r,'A')
    wire(remap(scan,'G',.69,-.27,-824,320),'',r,'B')
    dust_rough=node(u.MaterialExpressionConstant,-56,240,r=.87)
    output(lerp(r,'',dust_rough,'',dirt,160,242),'',u.MaterialProperty.MP_ROUGHNESS)
    ml.recompile_material(mat)
    assert assets.save_loaded_asset(mat,False)

palette={
    'Iron':('Iron',.86,.31,.36), 'StormSteel':('Iron',.94,.30,.35),
    'Steel':('Iron',.83,.26,.28), 'Gilt':('Iron',1.2,.28,.28),
    'Bronze':('Iron',.95,.35,.39), 'Edge':('Iron',1.3,.18,.17),
    'Patina':('Iron',.86,.40,.34), 'Mail':('Iron',1.30,.40,.39),
    'Wine':('Wool',3.25,.77,.70),'Velvet':('Wool',3.25,.79,.76),
    'Crimson':('Wool',3.25,.71,.68), 'SeaSilk':('Wool',3.18,.73,.79),
    'DeepBlue':('Linen',3.45,.71,.72),'Azure':('Linen',3.45,.72,.66),
    'Lining':('Linen',3.6,.68,.63),'Ivory':('Linen',3.6,.68,.54),
    'Leather':('Leather',1.9,.50,.62),'Obsidian':('Leather',2.3,.47,.44)
}
for key,(family,scale,rough,wear) in palette.items():
    mi=assets.load_asset(base+'/MI_'+key)
    assert mi,key
    ml.set_material_instance_parent(mi,mat)
    ml.set_material_instance_texture_parameter_value(mi,'SurfaceScan',surfaces[family])
    micro=assets.load_asset(base+'/T_Mail_N') if key=='Mail' else normals[family]
    ml.set_material_instance_texture_parameter_value(mi,'MeasuredNormal',micro)
    for name,value in [('SwatchScale',scale),('Roughness',rough),('WearAtHem',wear)]:
        ml.set_material_instance_scalar_parameter_value(mi,name,value)
    assert assets.save_loaded_asset(mi,False)
u.log(f'SB_FORGED_SURFACES_OK {len(palette)} materials')
