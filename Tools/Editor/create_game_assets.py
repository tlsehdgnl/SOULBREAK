"""Generate the gameplay tuning asset and edit-ready character blueprints in Unreal."""
import unreal as u

tools = u.AssetToolsHelpers.get_asset_tools()
assets = u.EditorAssetLibrary
def blueprint(name, cls):
    folder = '/Game/SoulBreak/Characters'
    path = folder + '/' + name
    assets.make_directory(folder)
    if not assets.does_asset_exist(path):
        factory = u.BlueprintFactory()
        factory.set_editor_property('parent_class', cls)
        if not tools.create_asset(name, folder, None, factory):
            raise RuntimeError(path)
        assets.save_asset(path, only_if_is_dirty=False)
for asset, parent in [('BP_Hero',u.SBHero), ('BP_Knight',u.SBKnight)]:
    blueprint(asset,parent)
folder = '/Game/SoulBreak/Data'
assets.make_directory(folder)
if not assets.does_asset_exist(folder + '/DA_Combat'):
    factory = u.DataAssetFactory()
    factory.set_editor_property('data_asset_class', u.SBCombatData)
    data = tools.create_asset('DA_Combat', folder, u.SBCombatData, factory)
    if not data: raise RuntimeError('DA_Combat')
    assets.save_loaded_asset(data, only_if_is_dirty=False)

folder = '/Game/SoulBreak/AI'
assets.make_directory(folder)
def obtain(name,cls,factory):
    path = folder+'/'+name
    return assets.load_asset(path) if assets.does_asset_exist(path) else tools.create_asset(name,folder,cls,factory)
bb = obtain('BB_Knight', u.BlackboardData, u.BlackboardDataFactory())
tree = obtain('BT_Knight', u.BehaviorTree, u.BehaviorTreeFactory())
u.SBSelectAttackTask.configure_duel_tree(tree, bb)
assets.save_loaded_asset(bb, only_if_is_dirty=False)
assets.save_loaded_asset(tree, only_if_is_dirty=False)

data = assets.load_asset('/Game/SoulBreak/Data/DA_Combat')
for field, base, prefix in [('animations', '/Game/SoulBreak/Animations','AN_'), ('sounds','/Game/SoulBreak/Audio','S_')]:
    entries = {}
    for path in assets.list_assets(base):
        name = path.split('.')[-1]
        if name.startswith(prefix):
            entries[u.Name(name[len(prefix):])] = assets.load_asset(path)
    if not entries: raise RuntimeError('Missing resources in '+base)
    data.set_editor_property(field,entries)
assets.save_loaded_asset(data,only_if_is_dirty=False)
for asset in ['Hero','Knight']:
    bp_class=assets.load_blueprint_class('/Game/SoulBreak/Characters/BP_'+asset)
    defaults=u.get_default_object(bp_class)
    defaults.set_editor_property('combat_data',data)
    defaults.mesh.set_skeletal_mesh_asset(assets.load_asset('/Game/SoulBreak/Characters/SK_'+asset))
    assets.save_asset('/Game/SoulBreak/Characters/BP_'+asset,only_if_is_dirty=False)

folder='/Game/SoulBreak/UI'
assets.make_directory(folder)
if not assets.does_asset_exist(folder+'/WBP_Combat'):
    factory=u.WidgetBlueprintFactory()
    factory.set_editor_property('parent_class',u.SBCombatOverlay)
    widget=tools.create_asset('WBP_Combat',folder,None,factory)
    if not widget: raise RuntimeError('WBP_Combat')
    assets.save_loaded_asset(widget,only_if_is_dirty=False)

# Radial contact shadow. Its UV falloff vanishes before the quad edges.
folder='/Game/SoulBreak/Materials'
def prepare_shadow():
    mat = assets.load_asset(folder+'/M_ContactShadow') if assets.does_asset_exist(folder+'/M_ContactShadow') else tools.create_asset('M_ContactShadow',folder,u.Material,u.MaterialFactoryNew())
    u.MaterialEditingLibrary.delete_all_material_expressions(mat)
    mat.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
    ml=u.MaterialEditingLibrary
    def expr(cls,x,y):
        return ml.create_material_expression(mat,cls,x,y)
    uv=expr(u.MaterialExpressionTextureCoordinate,-800,0)
    ctr=expr(u.MaterialExpressionConstant2Vector,-800,120)
    ctr.set_editor_property('r',.5)
    ctr.set_editor_property('g',.5)
    dist=expr(u.MaterialExpressionDistance,-620,0)
    assert ml.connect_material_expressions(uv,'',dist,'A')
    assert ml.connect_material_expressions(ctr,'',dist,'B')
    scale=expr(u.MaterialExpressionMultiply,-470,0)
    scale.set_editor_property('const_b',2.0)
    assert ml.connect_material_expressions(dist,'',scale,'A')
    inv=expr(u.MaterialExpressionOneMinus,-320,0)
    assert ml.connect_material_expressions(scale,'',inv,'')
    clamp=expr(u.MaterialExpressionSaturate,-160,0)
    assert ml.connect_material_expressions(inv,'',clamp,'')
    opacity=expr(u.MaterialExpressionMultiply,0,0)
    opacity.set_editor_property('const_b',.64)
    assert ml.connect_material_expressions(clamp,'',opacity,'A')
    assert ml.connect_material_property(opacity,'',u.MaterialProperty.MP_OPACITY)
    ml.recompile_material(mat)
    assets.save_loaded_asset(mat,only_if_is_dirty=False)

prepare_shadow()
