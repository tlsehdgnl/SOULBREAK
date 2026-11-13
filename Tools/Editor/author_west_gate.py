"""Cut a real west entrance in the nave, split the map blocker and relocate PlayerStart."""
import unreal as u
levels=u.get_editor_subsystem(u.LevelEditorSubsystem)
actors=u.get_editor_subsystem(u.EditorActorSubsystem)
assets=u.get_editor_subsystem(u.EditorAssetSubsystem)
assert levels.load_level('/Game/SoulBreak/Maps/L_Cathedral')
source='/Game/SoulBreak/Environment/SM_Nave'
destination=source+'WestGate'
mesh=assets.load_asset(destination) if assets.does_asset_exist(destination) else assets.duplicate_asset(source,destination)
if not assets.get_metadata_tag(mesh,'WestDoorwayV3'):
    dyn=u.DynamicMesh()
    result=u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(assets.load_asset(source),dyn,u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    assert result[-1]==u.GeometryScriptOutcomePins.SUCCESS, result
    # Legacy sources include two rows of raised tesserae at the old combat trigger.
    for x in (-558,-545):
        bounds=u.Box(min=u.Vector(x-1.6,-760,.06),max=u.Vector(x+1.6,760,.44))
        _,selection=u.GeometryScript_MeshSelection.select_mesh_elements_in_box(dyn,bounds)
        _,removed=u.GeometryScript_MeshEdits.delete_selected_triangles_from_mesh(dyn,selection)
        print("Former combat marker triangles removed",x,removed)
    cutter=u.DynamicMesh()
    u.GeometryScript_Primitives.append_box(cutter,u.GeometryScriptPrimitiveOptions(),u.Transform(),600,368,372)
    where=u.Transform(location=[-1110,0,-3])
    opts=u.GeometryScriptMeshBooleanOptions()
    opts.fill_holes=False
    u.GeometryScript_MeshBooleans.apply_mesh_boolean(dyn,u.Transform(),cutter,where,u.GeometryScriptBooleanOperation.TRIM_INSIDE,opts)
    result=u.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(dyn,mesh,u.GeometryScriptCopyMeshToAssetOptions(),u.GeometryScriptMeshWriteLOD())
    assert result[-1]==u.GeometryScriptOutcomePins.SUCCESS, result
    assets.set_metadata_tag(mesh,'WestDoorwayV3','1')
    assert assets.save_loaded_asset(mesh)
world=actors.get_all_level_actors()
nave=next(a for a in world if a.get_actor_label().startswith('Nave |'))
nave.static_mesh_component.set_static_mesh(mesh)
west=next(a for a in world if a.get_actor_label()=='Nave boundary X -1')
west.set_actor_location(u.Vector(-1040,-625,220),False,True)
west.set_actor_scale3d(u.Vector(.65,8.8,4.6))
north=next((a for a in world if a.get_actor_label()=='West gate north return'),None)
if not north:
    north=actors.spawn_actor_from_class(u.StaticMeshActor,u.Vector(-1040,625,220))
    north.static_mesh_component.set_static_mesh(west.static_mesh_component.static_mesh)
    north.static_mesh_component.set_collision_profile_name('BlockAll')
    north.set_actor_hidden_in_game(True)
    north.static_mesh_component.set_visibility(False)
    north.set_actor_scale3d(u.Vector(.65,8.8,4.6))
    north.set_actor_label('West gate north return')
north.set_actor_location(u.Vector(-1040,625,220),False,True)
start=next(a for a in world if isinstance(a,u.PlayerStart))
start.set_actor_location(u.Vector(-1730,0,101),False,True)
world_asset=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
assert u.EditorLoadingAndSavingUtils.save_map(world_asset,'/Game/SoulBreak/Maps/L_CathedralGate')




