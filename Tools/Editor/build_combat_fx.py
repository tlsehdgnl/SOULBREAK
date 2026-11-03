"""Build the unlit, two-sided material shared by moving blade ribbons and impact streaks."""
import unreal as u

assets = u.EditorAssetLibrary
tools = u.AssetToolsHelpers.get_asset_tools()
ml = u.MaterialEditingLibrary
folder = '/Game/SoulBreak/FX'
name = 'M_BladeLight'
assets.make_directory(folder)
path = folder+'/'+name
mat = assets.load_asset(path) if assets.does_asset_exist(path) else tools.create_asset(name,folder,u.Material,u.MaterialFactoryNew())
ml.delete_all_material_expressions(mat)
mat.set_editor_property('blend_mode', u.BlendMode.BLEND_ADDITIVE)
mat.set_editor_property('shading_model', u.MaterialShadingModel.MSM_UNLIT)
mat.set_editor_property('two_sided', True)
mat.set_editor_property('used_with_instanced_static_meshes', True)
def node(kind,x,y):
    return ml.create_material_expression(mat,kind,x,y)
vertex = node(u.MaterialExpressionVertexColor,-700,0)
tint = node(u.MaterialExpressionVectorParameter,-700,145)
tint.set_editor_property('parameter_name','Tint')
tint.set_editor_property('default_value',u.LinearColor(1,1,1,1))
energy = node(u.MaterialExpressionScalarParameter,-450,220)
energy.set_editor_property('parameter_name','Energy')
energy.set_editor_property('default_value',1.6)
pigment = node(u.MaterialExpressionMultiply,-420,0)
output = node(u.MaterialExpressionMultiply,-180,0)
assert ml.connect_material_expressions(vertex,'',pigment,'A')
assert ml.connect_material_expressions(tint,'',pigment,'B')
assert ml.connect_material_expressions(pigment,'',output,'A')
assert ml.connect_material_expressions(energy,'',output,'B')
assert ml.connect_material_property(output,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
assert ml.connect_material_property(vertex,'A',u.MaterialProperty.MP_OPACITY)
ml.recompile_material(mat)
assert assets.save_loaded_asset(mat,only_if_is_dirty=False)
