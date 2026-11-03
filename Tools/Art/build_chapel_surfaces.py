"""Author the cathedral's relief, microsurface, projected glass and triptych textures."""
from pathlib import Path
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
    dx=(np.roll(relief,-1,1)-np.roll(relief,1,1))*steepness
    dy=(np.roll(relief,1,0)-np.roll(relief,-1,0))*steepness
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

# A 2:3 hand-drawn icon, rendered in stained enamel. Coordinates are in design pixels.
H,W=960,640
y,x=np.mgrid[:H,:W]
cloud=np.fft.ifft2(np.fft.fft2(rng.normal(size=(H,W)))*np.exp(-((np.fft.fftfreq(H)[:,None]*45)**2+(np.fft.fftfreq(W)[None,:]*45)**2))).real
cloud=(cloud-cloud.mean())/cloud.std()
cells=np.zeros((H,W,3))
grid=60;nx=W//grid+5;ny=H//grid+5
px=rng.uniform(.15,.85,(ny,nx));py=rng.uniform(.15,.85,(ny,nx));base=rng.random((ny,nx))
nearest=np.ones((H,W))*1e8;second=nearest.copy(); IDs=np.zeros((H,W),int)
ix=x//grid+2;iy=y//grid+2
for dy in (-1,0,1):
    for dx in (-1,0,1):
        gx=ix+dx;gy=iy+dy;d=((gx-2+px[gy,gx])*grid-x)**2+((gy-2+py[gy,gx])*grid-y)**2
        win=d<nearest;second=np.minimum(second,np.where(win,nearest,d));nearest=np.minimum(nearest,d);IDs=np.where(win,gy*nx+gx,IDs)
tone=base.flatten()[IDs];lead=np.clip((np.sqrt(second)-np.sqrt(nearest))*.33,.09,1.)
for i,(a,b) in enumerate([(.032,.09),(.070,.235),(.102,.278)]):
    cells[:,:,i]=(a+(b-a)*tone)*(lead*.85+.15)
img=cells
ink=np.array((.029,.044,.051));gilt=np.array((.69,.436,.145));ivory=np.array((.82,.77,.54))
def poly(pts,c):
    ax=np.array(pts);a,b=np.maximum(0,np.floor(ax.min(0)).astype(int));d,e=np.minimum([W-1,H-1],np.ceil(ax.max(0)).astype(int))
    if a>d or b>e:return
    xx=x[b:e+1,a:d+1]+.5;yy=y[b:e+1,a:d+1]+.5;mask=np.zeros(xx.shape,bool)
    for (p,q),(r,s) in zip(pts,pts[1:]+pts[:1]):
        if q!=s:mask^=((yy>q)!=(yy>s))&(xx<(r-p)*(yy-q)/(s-q)+p)
    img[b:e+1,a:d+1][mask]=c
def line(a,b,w,c):
    px,py=a;qx,qy=b;vx=qx-px;vy=qy-py;d=np.hypot(vx,vy)
    if d<=0:return
    u=-vy*w/(2*d);v=vx*w/(2*d);poly([(px+u,py+v),(qx+u,qy+v),(qx-u,qy-v),(px-u,py-v)],c)
def outline(pts,c,w=3,edge=ink):
    poly(pts,c)
    for a,b in zip(pts,pts[1:]+pts[:1]):line(a,b,w,edge)
def ring(cx,cy,r,w,c,n=80):
    pts=[(cx+r*np.cos(j*2*np.pi/n),cy+r*np.sin(j*2*np.pi/n)) for j in range(n)]
    for a,b in zip(pts,pts[1:]+pts[:1]):line(a,b,w,c)
# Cloisonné border, head of the chapel's sunburst, hand-cut chips in its halo.
for inset,width,col in [(8,13,ink),(21,6,gilt),(32,4,(.24,.17,.09)),(42,2,gilt)]:
    pts=[(inset,inset),(W-inset,inset),(W-inset,H-inset),(inset,H-inset)]
    for a,b in zip(pts,pts[1:]+pts[:1]):line(a,b,width,col)
for sy in (85,875):
    for j in range(17):
        a=63+j*32;outline([(a,sy-10),(a+11,sy),(a,sy+10),(a-11,sy)],gilt if j%2==0 else (.15,.33,.33),2)
for j in range(48):
    a=j*2*np.pi/48;ca,sa=np.cos(a),np.sin(a)
    outer=177 if j%2==0 else 157
    outline([(320+ca*112,334+sa*112),(320+ca*outer-sa*4,334+sa*outer+ca*4),(320+ca*(outer+19),334+sa*(outer+19)),(320+ca*126+sa*5,334+sa*126-ca*5)],(.68,.38,.111) if j%3 else (.40,.23,.103),2)
for rr,ww,col in [(112,6,ink),(108,4,gilt),(88,4,ivory),(82,2,gilt),(154,2,gilt)]:
    ring(320,334,rr,ww,col)
# The votaries mirror each other, in turquoise and oxblood. Each points to a broken blade.
for sign in (-1,1):
    def P(u,v):return (320+sign*u,v)
    cloak=(.085,.24,.272) if sign<0 else (.29,.075,.108)
    for rr,ww,col in [(49,6,ink),(45,3,gilt),(52,2,ivory)]:ring(*P(184,511),rr,ww,col)
    parts=[
        ([(174,542),(214,558),(245,698),(258,798),(115,802),(130,739),(143,658)],cloak),
        ([(164,549),(193,553),(170,636),(121,720),(130,663)],(.19,.39,.37) if sign<0 else (.52,.176,.164)),
        ([(206,573),(226,607),(240,710),(203,679)],(.065,.11,.14)),
        ([(172,474),(193,473),(216,503),(205,545),(173,551),(145,526),(149,500)],(.079,.12,.155)),
        ([(149,505),(168,488),(193,495),(182,506),(160,514)],ivory),
        ([(153,516),(178,509),(174,535),(162,539)],(.58,.40,.23)),
        ([(148,593),(165,606),(133,642),(87,621),(95,607),(126,619)],(.58,.45,.253)),
        ([(89,621),(75,610),(66,593),(72,591),(83,604),(75,583),(80,579),(93,605),(101,609)],ivory)]
    for pts,c in parts:outline([P(u,v) for u,v in pts],c,3)
    for k in range(5):line(P(177+k*8,622+k*5),P(130+k*22,780-k*3),2.3,gilt)
# The long axial sword is interrupted by a broken tessera; the blade doubles as a cathedral lancet.
parts=[([(312,746),(329,752),(336,828),(321,851),(305,824)],gilt), ([(308,625),(333,624),(330,766),(309,766)],(.22,.16,.09)),
       ([(238,601),(266,607),(306,619),(320,607),(335,619),(374,607),(403,599),(384,629),(343,650),(320,641),(300,651),(257,628)],gilt),
       ([(300,606),(301,466),(329,432),(342,420),(339,600),(322,625)],(.67,.71,.61)),
       ([(321,616),(321,470),(337,440),(339,600)],(.29,.50,.50)),
       ([(297,445),(301,331),(322,166),(345,332),(339,397),(315,422)],(.79,.80,.66)),
       ([(322,166),(345,332),(339,397),(317,419),(325,356)],(.33,.57,.58))]
for pts,c in parts:outline(pts,c,3)
for j in range(6):line((310,662+j*14),(330,657+j*14),2,gilt)
for pts in [[(356,407),(375,385),(365,416),(349,429)],[(281,453),(266,475),(268,446),(285,432)]]:outline(pts,(.67,.29,.087),2)
# A few geometric stars and dotted glass striae keep large flat regions from reading as printed paper.
for _ in range(135):
    xx=rng.integers(49,W-48);yy=rng.integers(111,H-111)
    if np.mean(img[yy,xx])>.24:continue
    d=rng.uniform(1,3);poly([(xx-d,yy),(xx,yy-d*1.6),(xx+d,yy),(xx,yy+d*1.6)],(.31,.334,.245))
patina=np.clip(.88+.055*cloud+.026*rng.normal(size=(H,W)),.68,1.1)
img*=patina[:,:,None];png('T_SeveredOath',np.clip(img,0,1)**(1/2.2))
print('Wrote five microsurface pairs, stained-light projection, incense mask and altar icon.')
