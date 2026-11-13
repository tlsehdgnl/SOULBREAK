"""Shape the playable nave's specular light with the two visible banks of windows."""
import unreal as u
levels=u.get_editor_subsystem(u.LevelEditorSubsystem)
actors=u.get_editor_subsystem(u.EditorActorSubsystem)
assert levels.load_level('/Game/SoulBreak/Maps/L_CathedralGate')
by_label={a.get_actor_label():a for a in actors.get_all_level_actors()}
for label,where,target,width,height,power,tint in [
    ('North clerestory reflection',(120,-830,430),(180,55,110),320,240,420,(.72,.83,1.)),
    ('South chapel reflection',(475,770,325),(130,30,145),185,260,180,(1.,.74,.48))]:
    location,focus=u.Vector(*where),u.Vector(*target)
    rotation=u.MathLibrary.find_look_at_rotation(location,focus)
    actor=by_label.get(label) or actors.spawn_actor_from_class(u.RectLight,location,rotation)
    actor.set_actor_label(label)
    actor.set_actor_location_and_rotation(location,rotation,False,True)
    c=actor.get_component_by_class(u.RectLightComponent)
    c.set_mobility(u.ComponentMobility.MOVABLE)
    c.set_editor_property('intensity_units',u.LightUnits.LUMENS)
    c.set_source_width(width)
    c.set_source_height(height)
    c.set_light_color(u.LinearColor(*tint))
    c.set_attenuation_radius(1750)
    c.set_intensity(power)
    c.set_cast_shadows(True)
# Keep the windows readable on curved steel and avoid washing out the dark fabric.
for label,intensity in [('Pilgrim fill',360),('Nave moon rim',350),('Crossing reflected candlelight',285)]:
    by_label[label].light_component.set_intensity(intensity)
assert levels.save_current_level()

base='/Game/SoulBreak/Materials/Characters/MI_'
ml=u.MaterialEditingLibrary
assets=u.EditorAssetLibrary
master=u.load_asset('/Game/SoulBreak/Materials/Characters/M_ForgedSurfaces')
if not assets.get_metadata_tag(master,'ClothNapV1'):
    prop=u.MaterialProperty.MP_BASE_COLOR
    previous=ml.get_material_property_input_node(master,prop)
    previous_pin=ml.get_material_property_input_node_output_name(master,prop)
    def node(cls,x,y,**params):
        n=ml.create_material_expression(master,cls,x,y)
        for key,value in params.items(): n.set_editor_property(key,value)
        return n
    def wire(src,pin,dst,slot):
        assert ml.connect_material_expressions(src,pin,dst,slot)
    # Back-scattering from short fibres lifts the grazing edge of wool.
    fresnel=node(u.MaterialExpressionFresnel,-340,-750,exponent=3.6,base_reflect_fraction=0.)
    nap=node(u.MaterialExpressionScalarParameter,-340,-900,parameter_name='ClothNap',default_value=0.)
    weight=node(u.MaterialExpressionMultiply,-110,-720)
    wire(fresnel,'',weight,'A')
    wire(nap,'',weight,'B')
    rim=node(u.MaterialExpressionLinearInterpolate,360,-420,const_b=.32)
    wire(previous,previous_pin,rim,'A')
    wire(weight,'',rim,'Alpha')
    assert ml.connect_material_property(rim,'',prop)
    ml.recompile_material(master)
    assets.set_metadata_tag(master,'ClothNapV1','1')
    assert assets.save_loaded_asset(master,False)
for slot,rough,scale in [('Iron',.34,1.3),('StormSteel',.32,1.45),('Steel',.28,1.55),('Edge',.21,1.65),
                         ('Leather',.57,2.2),('SeaSilk',.85,4.5),('Wine',.84,4.5),('Velvet',.86,4.5)]:
    mi=u.load_asset(base+slot)
    ml.set_material_instance_scalar_parameter_value(mi,'Roughness',rough)
    ml.set_material_instance_scalar_parameter_value(mi,'SwatchScale',scale)
    if slot in ('SeaSilk','Wine','Velvet'):
        ml.set_material_instance_scalar_parameter_value(mi,'Metal',0.)
        ml.set_material_instance_scalar_parameter_value(mi,'ClothNap',.24)
    assert u.EditorAssetLibrary.save_loaded_asset(mi,False)
u.log('CHAPEL_LIGHTING_SAVED')

