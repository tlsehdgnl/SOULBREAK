"""Generate a voiced, helmet-muffled battle cry and import it into the project."""
import math
import os
import random
import struct
import wave
import unreal

rate = 44100
rng = random.Random(917)
phase = 0
pcm = bytearray()
resonators = [[0., 0.] for _ in range(3)]
for i in range(int(rate * 1.55)):
    t = i / rate
    pitch = 87 + 54 * math.sin(math.pi * t / 1.55) + 2 * math.sin(43*t)
    phase = (phase + pitch / rate) % 1.
    voice = math.sin(math.pi * phase / .48)**2 if phase < .48 else 0.
    drive = (voice - .24) * (.85 + .15 * math.sin(2*math.pi*51*t)) + .055*rng.uniform(-1, 1)
    out = 0.
    for j,(freq,bw,gain) in enumerate(((690,125,.8),(1130,150,.55),(2470,220,.21))):
        r = math.exp(-math.pi*bw/rate)
        y1,y2 = resonators[j]
        v = 2*r*math.cos(2*math.pi*(freq+50*math.sin(2.6*t))/rate)*y1-r*r*y2+drive
        resonators[j] = [v,y1]
        out += gain*v*(1-r)*2*math.sin(2*math.pi*freq/rate)
    env = min(1,t/.13)*min(1,(1.55-t)/.42)
    pcm.extend(struct.pack('<h',round(28500*env*math.tanh(4*out))))
path = os.path.abspath(os.path.join(unreal.Paths.project_saved_dir(),'KnightRoar.wav'))
with wave.open(path,'wb') as wav:
    wav.setparams((1,2,rate,0,'NONE','not compressed'))
    wav.writeframes(pcm)
task=unreal.AssetImportTask()
task.filename=path
task.destination_path='/Game/SoulBreak/Audio'
task.destination_name='S_KnightRoar'
task.automated=True
task.replace_existing=True
task.save=True
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
assert task.imported_object_paths, 'Roar import failed'
