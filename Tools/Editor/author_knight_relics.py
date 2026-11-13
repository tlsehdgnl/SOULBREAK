"""Bake the Warden's rigid armor pieces and its second-phase sounds."""
import math
import random
import struct
import wave
from pathlib import Path
import unreal as u

audio = '/Game/SoulBreak/Audio'
characters = '/Game/SoulBreak/Characters'
rate = 22050
rng = random.Random(13)
for name, seconds in [('PhaseChoir', 3.6), ('StoneScrape', .84)]:
    pcm = bytearray()
    noise = 0.
    for i in range(int(rate * seconds)):
        t = i / rate
        if name == 'PhaseChoir':
            value = 0.
            for voice, fundamental in enumerate([73.42, 109.8, 146.4]):
                phase = 2*math.pi*fundamental*t + .12*math.sin(t*(17+voice))
                for h in range(1, 17):
                    f = h*fundamental
                    formant = .15 + math.exp(-((f-480)/140)**2) + .7*math.exp(-((f-860)/205)**2)
                    value += math.sin(h*phase)*formant/(h*2)
            envelope = min(1,t/.5)*min(1,(seconds-t)/1.3)
        else:
            noise = .6*noise + .4*rng.uniform(-1,1)
            value = noise + .16*math.sin(2*math.pi*(1810*t-330*t*t)+4*noise)
            envelope = min(1,t/.09)*min(1,(seconds-t)/.25)*(.67+.33*math.sin(t*54)**2)
        pcm.extend(struct.pack('<h', round(28500*envelope*math.tanh(value))))
    path = Path(u.Paths.convert_relative_path_to_full(u.Paths.project_saved_dir()))/(name+'.wav')
    with wave.open(str(path),'wb') as wav:
        wav.setparams((1,2,rate,0,'NONE','none'))
        wav.writeframes(pcm)
    task = u.AssetImportTask()
    task.filename, task.destination_path, task.destination_name = str(path), audio, 'S_'+name
    task.automated = task.save = task.replace_existing = True
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    assert task.imported_object_paths

rig = u.load_asset(characters+'/SK_Knight')
for name, pivot, bones in [('FallenLeg','ShinL',['ShinL','FootL','KneePlateL']),
                           ('RackArm','UpperArmR',['UpperArmR','ForearmR'])]:
    mesh = u.DynamicMesh()
    u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(rig,mesh,u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    indices = {mesh.get_bone_index(b)[2] for b in bones}
    _, valid, info = mesh.get_bone_info(pivot)
    assert valid
    count = mesh.get_triangle_count()
    remove = []
    for tri in range(count):
        vertices, valid = mesh.get_triangle_indices(tri)
        if valid and mesh.get_largest_vertex_bone_weight(vertices.x)[1].bone_index not in indices:
            remove.append(tri)
    assert 0 < len(remove) < count
    mesh.delete_triangles_from_mesh(u.GeometryScript_List.convert_array_to_index_list(remove))
    mesh.translate_mesh(info.world_transform.translation * -1.)
    options = u.GeometryScriptCreateNewStaticMeshAssetOptions()
    options.enable_collision = False
    result, outcome = u.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(mesh,characters+'/SM_'+name,options)
    assert result
    slots = []
    for slot in rig.materials:
        material = u.StaticMaterial()
        material.material_slot_name = slot.material_slot_name
        material.material_interface = slot.material_interface
        slots.append(material)
    result.set_editor_property('static_materials', slots)
    u.EditorAssetLibrary.save_loaded_asset(result)
    u.log('Armor mesh '+name+' '+str(result.get_bounding_box()))

