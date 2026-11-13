"""Prepare measured cloth, leather and patinated steel for the two fighters' materials."""
from hashlib import sha256
import json
from pathlib import Path
from urllib.request import urlopen
import numpy as np
from PIL import Image, ImageFilter

root=Path(__file__).resolve().parents[2]
cache=root/'Saved/ArmorScans'
out=root/'Saved/SBArt'
cache.mkdir(parents=True,exist_ok=True)
out.mkdir(parents=True,exist_ok=True)
for name,info in json.loads((Path(__file__).with_name('armor_scan_sources.json')).read_text()).items():
    path=cache/name
    if path.is_file() and sha256(path.read_bytes()).hexdigest()==info['sha256']:
        continue
    with urlopen(info['url'],timeout=45) as response:
        contents=response.read()
    if sha256(contents).hexdigest()!=info['sha256']:
        raise RuntimeError(f'Unexpected source image for {name}')
    path.write_bytes(contents)

for kind,scan,strength in [('Iron','metal_plate_02',.67),('Wool','poly_wool_herringbone',.94),
                           ('Linen','rough_linen',.70),('Leather','brown_leather',.80)]:
    def load(channel,mode):
        return Image.open(cache/(scan+'_'+channel+'.jpg')).convert(mode)
    albedo=load('color','L')
    # Keep the measured variations even when the reference fabric is almost flat in value.
    lightness=np.asarray(albedo,dtype=float)
    low,high=np.percentile(lightness,[2,98])
    grain=np.clip((lightness-low)/max(10.,high-low),0,1)
    burnish=np.asarray(load('rough','L'),dtype=float)/255
    broad=np.asarray(albedo.filter(ImageFilter.GaussianBlur(13)),dtype=float)
    west,east=np.percentile(broad,[5,95])
    deposit=np.clip((east-broad)/max(2.,east-west),0,1)
    mask=np.stack([grain,burnish,.72*deposit+.28*(1-grain)],axis=2)
    Image.fromarray(np.uint8(mask*255)).save(out/f'T_Forged{kind}_M.png')
    normal=np.asarray(load('normal','RGB'),dtype=float)/127.5-1
    normal[:,:,:2]*=strength
    normal/=np.maximum(.001,np.linalg.norm(normal,axis=2,keepdims=True))
    Image.fromarray(np.uint8((normal*.5+.5).clip(0,1)*255)).save(out/f'T_Forged{kind}_N.png')
