"""Author the cathedral's relief, microsurface, projected glass and triptych textures."""
from pathlib import Path
from shutil import copyfile
import struct,sys,zlib
import numpy as np

out=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[2]/'Saved/SBLevel'
out.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(9618)
N=512
Y,X=np.mgrid[:N,:N]
frequency=np.hypot(np.fft.fftfreq(N)[:,None]*N,np.fft.fftfreq(N)[None,:]*N)

def png(name,v):
    a=np.uint8(np.clip(v,0,1)*255+.5)
    color={1:0,3:2,4:6}[1 if a.ndim==2 else a.shape[-1]]
    def chunk(tag,b):return struct.pack('>I',len(b))+tag+b+struct.pack('>I',zlib.crc32(tag+b)&0xffffffff)
    scan=b''.join(b'\0'+row.tobytes() for row in a)
    (out/(name+'.png')).write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',a.shape[1],a.shape[0],8,color,0,0,0))+chunk(b'IDAT',zlib.compress(scan,8))+chunk(b'IEND',b''))
def noise(band):
    v=np.fft.ifft2(np.fft.fft2(rng.normal(size=(N,N)))*np.exp(-(frequency/band)**2)).real
    return v/v.std()
def maps(name,relief,albedo,rough,occlusion,steepness):
    dx=(np.roll(relief,-1,1)-np.roll(relief,1,1))*steepness*.60
    dy=(np.roll(relief,1,0)-np.roll(relief,-1,0))*steepness*.60
    n=np.stack([-dx,-dy,np.ones_like(dx)],-1);n/=np.linalg.norm(n,axis=-1)[:,:,None]
    png('T_'+name+'_N',n*.5+.5);png('T_'+name+'_M',np.stack([albedo,rough,occlusion],-1))

coarse,fine,grain=noise(3),noise(25),noise(135)
vein=np.exp(-abs(coarse+.25*fine)*17);deposits=np.clip((fine+.7*grain-1.4)*.40,0,1)
seam=np.clip((np.abs(noise(8)+.08*fine)-.024)*-18+1,0,1)
height=.27*coarse+.18*fine+.047*grain-.097*vein-.12*seam+.14*deposits
maps('Argillite',height,.71+.12*coarse+.045*fine+.022*grain+.16*vein-.17*seam,.78+.17*deposits+.08*grain-.16*seam,.95-.18*seam-.07*deposits,2.35)
# Chiseled ashlar. Its mossy pores and horizontal comb tooling differ from the polished aisle.
fissure=np.exp(-abs(.5*noise(5)+.2*fine+(Y/N-X/N)*.27)*17)
tooling=np.sin(2*np.pi*(33*Y/N+5*X/N+.11*noise(6)))
grain2=noise(80)
maps('Tufa',.38*coarse+.21*fine+.085*grain2+.05*tooling-.19*fissure,.72+.12*coarse+.055*fine+.034*tooling-.17*fissure,.84+.08*grain-.10*fissure,.94-.23*fissure,2)
# Hammered gold and oxidized iron pick up broad dents and fine chasing from different scales.
dimples=1-abs(noise(18))*.32
scratches=np.clip((np.sin(2*np.pi*(91*X/N+6*Y/N)+.64*noise(4))-.88)*3.2,0,1)
maps('Chasing',.28*dimples+.014*scratches+.03*fine,.83+.074*dimples+.036*fine-.075*scratches,.76+.10*fine+.16*scratches,.97-.086*scratches,1.55)
warp=np.sin(2*np.pi*97*X/N);weft=np.sin(2*np.pi*89*Y/N)
weave=warp*.58+weft*.39+.25*warp*weft
maps('Damask',.055*weave+.15*coarse+.04*fine,.74+.095*weave+.085*coarse+.025*grain,.87+.09*weave,.96-.05*abs(weave),1.4)
bubbles=np.clip((grain2-1.8)*.85,0,1)
glass=fine*.29+coarse*.44+bubbles*.17
maps('PotGlass',glass,.73+.14*coarse+.086*fine+.10*bubbles,.62+.17*fine+.14*bubbles,.98-.09*bubbles,1.6)

# A very soft fragment of colored window light spills onto the slate at the side of the nave.
# Light follows the three-lancet architecture; the center remains clear enough to read combat tells.
wx=-1120+2240*X/(N-1);wy=-1120+2240*Y/(N-1)
illum=np.zeros((N,N,3))
for source_x in (-795,-385,65,530,930):
    for i,(s,h,col) in enumerate([(-63,280,(.19,.38,.65)),(0,375,(.27,.48,.65)),(63,280,(.37,.26,.16))]):
        v=(wy+860)/2.08;u=wx-source_x-(wy+650)*.41-s
        end=np.maximum(0,1-abs(u/28))**.62*58+h
        prof=np.clip((v+8)/16,0,1)*np.clip((end-v)/14,0,1)*np.clip((32-abs(u))/8,0,1)
        lead=np.clip((abs(u)-1.7)/5,.14,1)*np.clip((abs((v+22)%57-28)-1)/5,.3,1)
        scatter=.75+.12*coarse+.065*fine
        illum+=np.array(col)[None,None,:]*(prof*lead*scatter*(.71+.29*np.sin(v*.027)**2))[:,:,None]
# Contact darkening follows the known pier positions and edge mouldings.
contact=np.ones_like(wx)
for cx in (-480,480):
    for cy in (-670,670):
        contact-=.37*np.exp(-((wx-cx)**2+(wy-cy)**2)/(2*80**2))
contact-=.21*np.clip((np.maximum(abs(wx),abs(wy))-725)/370,0,1)
png('T_ClerestoryLight',np.dstack((np.clip(illum,0,1),np.clip(contact,.5,1))))
# Edge-softened sheets for shafts at the upper windows. Fades before reaching the fighting floor.
xx=(X/(N-1)-.5)*2; yy=Y/(N-1);rays=np.exp(-xx**2*6)*np.clip(1-xx**2,0,1)*(.62+.18*np.cos(xx*27)+.08*np.sin(xx*61))
beam=rays*np.sin(np.pi*yy)**1.4*(1-.44*yy)*(.94+.04*coarse)
png('T_IncenseRay',beam)

# The reredos uses the gilt-wood illustration at its native aspect.
copyfile(Path(__file__).with_name('SeveredOath.png'), out / 'T_SeveredOath.png')
from chapel_scans import bake_stone
bake_stone(out)
copyfile(Path(__file__).with_name('VotaryGlass.png'), out / 'T_Votaries.png')
from chapel_fire import bake_fire
bake_fire(out)
print('Wrote chapel surface maps, projected light, votary glass, altar and censer atlas.')
