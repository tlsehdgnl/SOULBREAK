"""Build the chapel of the Severed Sun. Run in Blender 4.5 LTS background mode.

The FBX is a single batched environment mesh. Gameplay collision lives on separate,
simple volumes in the Unreal level so floor inlay and masonry never snag characters.
"""
import bpy
import json
import math
import random
from mathutils import Vector
from pathlib import Path
from math import sin, cos, pi
from sys import argv
out = Path(argv[argv.index('--') + 1]) if '--' in argv else Path(__file__).resolve().parents[2] / 'Saved/SBLevel'
out.mkdir(parents=True, exist_ok=True)
rng = random.Random(481516)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = .01

# Colors are linear reflectances. The fluting and chamfers keep the silhouettes
# legible at gameplay distances; aged stone changes subtly from block to block.
palette = {
    'Deep':((.036,.052,.073),.86,0,0), 'Mortar':((.062,.077,.09),.9,0,0),
    'SlabA':((.137,.169,.184),.65,0,0), 'SlabB':((.174,.197,.199),.70,0,0),
    'SlabC':((.12,.147,.165),.68,0,0), 'SlabD':((.206,.215,.201),.66,0,0),
    'Parchment':((.44,.405,.316),.76,0,0),'Chalk':((.34,.346,.307),.72,0,0),
    'Carving':((.248,.273,.27),.64,0,0),'Tracery':((.252,.216,.137),.58,.1,0),
    'Iron':((.091,.094,.087),.52,.56,0),'Gold':((.55,.34,.091),.43,.62,0),
    'Burnished':((.32,.177,.064),.48,.45,0),'Oxide':((.096,.176,.172),.67,.2,0),
    'Enamel':((.047,.118,.148),.43,.18,0),'Oxblood':((.194,.035,.044),.83,0,0),
    'Velvet':((.292,.048,.054),.777,0,0),'ClothGold':((.594,.386,.137),.66,.15,0),
    'CyanGlass':((.065,.43,.466),.48,.08,1.9), 'SeaGlass':((.075,.24,.33),.43,.08,1.45),
    'IvoryGlass':((.604,.628,.441),.45,.08,1.90),'AmberGlass':((.76,.323,.078),.43,.08,1.85),
    'RubyGlass':((.472,.069,.09),.41,.06,1.65),'Coal':((.235,.047,.012),.84,0,.9),
    'Wick':((.97,.42,.083),.43,0,3.2),'Fire':((1.0,.715,.265),.41,0,4.35),
    'Wax':((.638,.505,.299),.76,0,0),'Rune':((.316,.551,.463),.45,.2,.62)
}
palette.update({
    'Deep':((.017,.025,.044),.84,0,0),'Mortar':((.031,.042,.053),.86,0,0),
    'SlabA':((.063,.084,.093),.58,0,0),'SlabB':((.081,.100,.106),.59,0,0),
    'SlabC':((.055,.073,.084),.63,0,0),'SlabD':((.101,.114,.105),.57,0,0),
    'Parchment':((.30,.291,.250),.67,0,0),'Chalk':((.235,.253,.235),.65,0,0),
    'Carving':((.152,.179,.189),.72,0,0),'Tracery':((.205,.159,.095),.55,.18,0),
    'CyanGlass':((.018,.255,.374),.41,.02,.90),'SeaGlass':((.016,.111,.219),.43,.02,.83),
    'IvoryGlass':((.41,.383,.243),.39,.03,.94),'AmberGlass':((.585,.205,.04),.38,.02,1.01),
    'RubyGlass':((.343,.031,.072),.40,.02,.95),'Rune':((.18,.35,.32),.41,.10,.30),
    'Icon':((1.,1.,1.),.52,.24,.41),'Incense':((.23,.36,.49),.9,0,.07)
})
palette.update({
    'Pavement': ((.372,.39,.39),.95,0,0), 'ChoirPaving': ((.41,.405,.387),.88,0,0),
    'Ashlar': ((.58,.58,.53),1.,0,0), 'Sootstone': ((.19,.215,.24),1.,0,0),
    'Parchment': ((.75,.68,.54),.99,0,0), 'Chalk': ((.63,.66,.59),.99,0,0),
    'Carving': ((.42,.46,.44),.95,0,0), 'Tracery': ((.25,.24,.205),.84,.06,0),
    'Memorial': ((.34,.30,.22),.86,.30,0), 'Purbeck': ((.23,.245,.23),.83,.02,0),
    'VaultWeb': ((.26,.23,.20),.99,0,0), 'SaintGlass': ((1.,1.,1.),.6,0,.55),
    'FlameSheet': ((1,.33,.02),1,0,.9), 'Coal': ((.027,.019,.014),.99,0,.025),
    'Oak': ((.104,.047,.021),.74,0,0), 'Sculpture': ((.72,.65,.55),.99,0,0),
    'CyanGlass': ((.087,.198,.195),.65,.02,.43), 'SeaGlass': ((.049,.115,.15),.67,.02,.42),
    'IvoryGlass': ((.42,.41,.33),.56,0,.46), 'AmberGlass': ((.36,.21,.085),.59,.01,.48),
    'RubyGlass': ((.205,.045,.054),.57,.01,.44),
})
(out / 'chapel_materials.json').write_text(json.dumps(palette))
V=[]; F=[]; M=[]
art_uv={}
def surface(v,f,mat):
    n=len(V);V.extend([tuple(p) for p in v]);F.extend(tuple(n+i for i in face) for face in f);M.extend([mat]*len(f))
def box(x,y,z,dx,dy,dz,mat):
    a,b,c=dx/2,dy/2,dz/2
    surface([(x+i*a,y+j*b,z+k*c) for k in (-1,1) for j in (-1,1) for i in (-1,1)],
            [(0,2,3,1),(4,5,7,6),(0,1,5,4),(1,3,7,5),(3,2,6,7),(2,0,4,6)],mat)
def taper(p,q,r1,r2,mat,n=8,phi=0):
    p,q=Vector(p),Vector(q);d=(q-p).normalized();u=d.cross(Vector((0,0,1)) if abs(d.z)<.95 else Vector((0,1,0))).normalized();v=d.cross(u)
    verts=[a+r*(u*cos(phi+2*pi*i/n)+v*sin(phi+2*pi*i/n)) for a,r in ((p,r1),(q,r2)) for i in range(n)]
    surface(verts,[tuple(range(n-1,-1,-1)), tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],mat)
def rod(p,q,r,mat,n=8):taper(p,q,r,r,mat,n)
def rim(cx,cy,z,ri,ro,mat,n=96,a=0,b=2*pi):
    for j in range(n):
        p=a+(b-a)*j/n;q=a+(b-a)*(j+1)/n
        surface([(cx+ri*cos(p),cy+ri*sin(p),z),(cx+ro*cos(p),cy+ro*sin(p),z),(cx+ro*cos(q),cy+ro*sin(q),z),(cx+ri*cos(q),cy+ri*sin(q),z)],[(0,1,2,3)],mat)
def plate(points,mat):
    surface(points,[tuple(range(len(points)))],mat)
def strip(points,width,mat):
    for (x,y,z),(a,b,c) in zip(points,points[1:]):
        l=max(.001,math.hypot(a-x,b-y));u=(y-b)*width/l/2;v=(a-x)*width/l/2
        plate([(x+u,y+v,z),(x-u,y-v,z),(a-u,b-v,c),(a+u,b+v,c)],mat)
def post(x,y,base,h,r):
    pieces=[(0,.025,1.65,1.65,'Carving'),(.025,.047,1.68,1.46,'Chalk'),(.047,.07,1.40,1.41,'Parchment'),(.07,.11,1.37,.99,'Carving'),
            (.11,.12,1.10,1.01,'Burnished'),(.12,.71,.96,.86,'Carving'),(.71,.725,.99,1.01,'Parchment'),(.725,.745,.96,.89,'Carving'),(.745,.89,.88,.89,'Chalk'),(.89,.925,1.00,1.18,'Parchment'),(.925,.95,1.2,1.36,'Carving'),(.95,.98,1.38,1.35,'Chalk'),(.98,1,1.46,1.46,'Carving')]
    for s,t,a,b,m in pieces:taper((x,y,base+h*s),(x,y,base+h*t),r*a,r*b,m)
    for i in range(8):
        a=2*pi*i/8;dx=r*.78*cos(a);dy=r*.78*sin(a)
        taper((x+dx,y+dy,base+h*.12),(x+dx*.92,y+dy*.92,base+h*.89),r*.29,r*.25,'Chalk' if i%2==1 else 'Carving',8)
def flame(x,y,z,size):
    if size<=3:
        # A candle has a much shorter point than an open brazier fire.
        taper((x,y,z),(x+.075*size,y,z+.86*size),size*.28,0.,'Fire',7)
        return
    phase=rng.randrange(16)
    for angle_offset in (0,pi*.54):
        angle=rng.uniform(-.16,.16)+angle_offset
        dx=size*.92*cos(angle);dy=size*.92*sin(angle);height=size*2.5
        corners=[(x-dx,y-dy,z),(x+dx,y+dy,z),(x+dx+size*.12,y+dy,z+height),(x-dx+size*.12,y-dy,z+height)]
        n=len(V);plate(corners,'FlameSheet')
        for k,(u,v) in enumerate(((.005,.005),(.995,.005),(.995,.995),(.005,.995))):
            art_uv[n+k]=(phase+u,v)
def brazier(x,y,scale=1):
    for z,h,r1,r2,m in [(0,8,31,31,'Iron'),(8,10,31,16,'Burnished'),(18,54,10,7,'Iron'),(72,8,10,23,'Gold'),(80,18,17,38,'Burnished'),(98,4,38,37,'Gold'),(102,4,34,32,'Coal')]:
        taper((x,y,z*scale),(x,y,(z+h)*scale),r1*scale,r2*scale,m)
    for i in range(8):
        a=i*pi/4;distance=rng.uniform(7,23)*scale;dz=105*scale
        px=x+distance*cos(a);py=y+distance*sin(a)
        taper((px-8*scale,py-3*scale,dz),(px+9*scale,py+4*scale,dz+4*scale),4.2*scale,3.4*scale,'Coal',6)
    for i in range(5):
        a=2*pi*i/5;d=13 if i else 0
        flame(x+cos(a)*d*scale,y+sin(a)*d*scale,102*scale,(15 if i else 22)*scale)
    for i in range(4):
        a=i*pi/2;taper((x+21*scale*cos(a),y+21*scale*sin(a),85*scale),(x+40*scale*cos(a),y+40*scale*sin(a),121*scale),4*scale,1,'Iron',5)

# Twenty-metre nave. The joints and inlays are below one centimetre in height.
# Center tesserae and flanking flagstones meet at the original procession bands.
# All photographed grout and wear are continuous over the paving, including the combat seal.
box(0,0,-26,2650,2300,50,'Pavement')
for band_y in (-634,634):
    box(0,band_y,-.71,2650,122,1.,'ChoirPaving')
for y in (-836,836,-809,809):box(0,y,.05,2160,3, .32,'Burnished')
for x in (-833,833):box(x,0,.05,4,1657,.32,'Burnished')
for r,w,m in [(377,5,'Memorial'),(368,2,'Purbeck'),(340,4,'Purbeck'),(282,3,'Memorial'),(261,3,'Purbeck'),(76,4,'Memorial'),(67,2,'Purbeck')]:
    rim(60,0,.38,r,r+w,m)
for i in range(40):
    a=i*2*pi/40;d=17 if i%5 else 28
    strip([(60+cos(a)*344,sin(a)*344,.39),(60+cos(a)*(344+d),sin(a)*(344+d),.39)],3.2,'Memorial')
for i in range(16):
    a=i*pi/8;v=(cos(a),sin(a));w=(-v[1],v[0]);len1=260 if not i%2 else 180
    def gp(d,h):return (60+v[0]*d+w[0]*h,v[1]*d+w[1]*h,.42)
    plate([gp(75,0),gp(125,-9),gp(len1,0)],'Purbeck');plate([gp(75,0),gp(len1,0),gp(125,8)],'Memorial')

# Profiles in (tangent, height) on each of the four walls.
def wallpoint(axis,sign,w,t,z,offset=0):
    q=sign*(w-offset)
    return (q,t,z) if axis=='x' else (t,q,z)
def wallbox(axis,sign,w,t,z,width,depth,height,mat,offset=0):
    p=wallpoint(axis,sign,w,t,z,offset);box(*p,*((depth,width,height) if axis=='x' else (width,depth,height)),mat)
def pointed_profile(half,height,steps=10):
    # Two-circle pointed arch. Each lobe is tangent to its jamb at the spring.
    k=(height*height-half*half)/(2*half);r=k+half
    angle=math.atan2(height,k)
    left=[(k-r*cos(angle*i/steps),r*sin(angle*i/steps)) for i in range(steps+1)]
    return left+[(-t,z) for t,z in reversed(left[:-1])]
def arch(axis,sign,w,tcenter,spring,half,h,r,mat,offset=0):
    p=lambda t,z:wallpoint(axis,sign,w,t+tcenter,spring+z,offset)
    curve=pointed_profile(half,h)
    for a,b in zip(curve,curve[1:]):rod(p(*a),p(*b),r,mat,6)
def arch_blocks(axis,sign,w,tc,spring,half,h,depth):
    inner=pointed_profile(half,h,8);outer=pointed_profile(half+26,h+31,8)
    for i in range(len(inner)-1):
        pts=[inner[i],inner[i+1],outer[i+1],outer[i]];verts=[wallpoint(axis,sign,w,t+tc,z+spring,offset) for offset in (depth-14,depth) for t,z in pts]
        surface(verts,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],rng.choice(['Carving','Chalk','Carving','Parchment']))
def glass_lancet(axis,sign,w,tc,sill,sw,h,offset=0):
    p=lambda t,z,d=offset:wallpoint(axis,sign,w,tc+t,sill+z,d)
    stem=h*.67;profile=pointed_profile(sw,(h-stem),8)
    outline=[(-sw,0),(sw,0),(sw,stem)]+list(reversed([(a,b+stem) for a,b in profile]))+[(-sw,stem)]
    if h>190:
        # The outer form clips each rectangular panel to a real lancet.
        points=[(-sw,0),(sw,0)]+list(reversed([(a,b+stem) for a,b in profile]))
        start_vertex=len(V);plate([p(t,z) for t,z in points],'SaintGlass')
        index=round(tc/70)%3
        for k,(t,z) in enumerate(points):
            art_uv[start_vertex+k]=((index+.007+.986*(t/sw+1)*.5)/3.,.005+.990*z/h)
        for i in (-1,1):
            rod(p(i*sw,0,offset+2),p(i*sw,stem,offset+2),2.5,'Tracery')
        for fraction in (.27,.55):
            rod(p(-sw,h*fraction,offset+1),p(sw,h*fraction,offset+1),.72,'Iron',5)
        arch(axis,sign,w,tc,sill+stem,sw,h-stem,2.8,'Tracery',offset+2)
        return
    plate([p(t,z) for t,z in outline],'SeaGlass')
    # Lead cames, lozenge glass and the candle/flame motif.
    for i in range(3):
        z=(i+.5)*stem/3;hw=sw*.87;hh=stem/6*.91
        glass=rng.choice(['SeaGlass','CyanGlass','IvoryGlass','AmberGlass'])
        plate([p(-hw,z,offset+1),p(0,z-hh,offset+1),p(hw,z,offset+1),p(0,z+hh,offset+1)],glass)
        v=[p(-hw,z,offset+2),p(0,z-hh,offset+2),p(hw,z,offset+2),p(0,z+hh,offset+2)]
        for a,b in zip(v,v[1:]+v[:1]):rod(a,b,1.5,'Iron',5)
    for i in (-1,1):rod(p(i*sw,0,offset+3),p(i*sw,stem,offset+3),3.1,'Tracery')
    rod(p(0,0,offset+3),p(0,stem+3,offset+3),1.9,'Iron')
    arch(axis,sign,w,tc,sill+stem,sw,h-stem,3.2,'Tracery',offset+3)
def circle_wall(axis,sign,w,tc,zc,r,thick,mat,offset,n=64):
    p=lambda a:wallpoint(axis,sign,w,tc+cos(a)*r,zc+sin(a)*r,offset)
    for i in range(n):rod(p(2*pi*i/n),p(2*pi*(i+1)/n),thick,mat,6)
def rose(axis,sign,w,zc,r,offset):
    tc=0; p=lambda t,z,d=offset:wallpoint(axis,sign,w,t,zc+z,d)
    def polar(a,dist,shift=0):return p(dist*cos(a),dist*sin(a),offset+shift)
    for i in range(16):
        a=(i+.5)*pi/8; delta=pi/16
        for j,(d1,d2) in enumerate([(.12,.37),(.37,.69),(.70,.94)]):
            tiles=['AmberGlass','IvoryGlass','CyanGlass','SeaGlass','RubyGlass']
            m=tiles[([0,1,2,3][i%4]+j)%5]
            plate([polar(a-delta,d1*r),polar(a-delta,d2*r),polar(a,d2*r*1.01),polar(a+delta,d2*r),polar(a+delta,d1*r),polar(a,d1*r)],m)
        rod(polar(a-delta,r*.12,2),polar(a-delta,r*.945,2),2.0,'Iron',6)
        # Alternate petal tips and tiny oculi radiating out from the boss.
        for side in (-1,1):rod(polar(a,r*.36,4),polar(a+delta*side,r*.68,4),2.8,'Tracery',6)
        circle_wall(axis,sign,w,cos(a)*r*.831,zc+sin(a)*r*.831,r*.09,2.6,'Tracery',offset+5,12)
    for rad,sz,m in [(.12,.028,'Gold'),(.37,.012,'Tracery'),(.69,.017,'Tracery'),(.96,.027,'Chalk'),(1,.03,'Parchment'),(1.055,.017,'Gold'),(1.1,.035,'Carving')]:
        circle_wall(axis,sign,w,0,zc,r*rad,r*sz,m,offset+7)
    plate([polar(a*2*pi/16,r*.115,3) for a in range(16)],'IvoryGlass')
def banner(axis,sign,w,t,top,length,width,offset):
    # Scalloped and split, with a stitched sunburst crest on the face.
    p=lambda u,z,d=0:wallpoint(axis,sign,w,t+u,z,offset+d)
    rod(p(-width*.65,top,1),p(width*.65,top,1),4,'Gold')
    for i in range(8):
        a=width*(-.5+i/8);b=a+width/8
        def foot(u):return top-length+abs(u)*.91+(11 if u==0 else 0)
        d1=2.5*cos(i*pi/2);d2=2.5*cos((i+1)*pi/2)
        plate([p(a,top,d1),p(b,top,d2),p(b,foot(b),d2),p(a,foot(a),d1)],'Velvet' if i%4 in (1,2) else 'Oxblood')
    for u in [-width*.39,width*.39]:rod(p(u,top-7,5),p(u,top-length+width*.51,5),1.6,'ClothGold',4)
    cz=top-length*.36;r=width*.17
    for i in range(12):
        a=2*pi*i/12;u=cos(a);v=sin(a)
        rod(p(u*r*1.19,cz+v*r*1.19,6),p(u*r*(1.7 if i%2==0 else 1.42),cz+v*r*(1.7 if i%2==0 else 1.42),6),1.5,'ClothGold',5)
    circle_wall(axis,sign,w,t,cz,r,1.6,'ClothGold',offset+6,24)
    plate([p(0,cz+r*.78,7),p(r*.52,cz,7),p(0,cz-r*.78,7),p(-r*.52,cz,7)],'ClothGold')
    rod(p(0,cz-r*1.5,5),p(0,top-length+width*.4,5),1,'ClothGold',4)

for axis in ('x','y'):
    for sign in (-1,1):
        w=(1255 if sign==1 else 1110) if axis=='x' else 1060
        # Jambs and inset gothic lancets read in the level even with flat lighting.
        wallbox(axis,sign,w,0,520,2510,80,1056,'Ashlar',-38)
        for q,mat in [(22,'Carving'),(72,'Chalk'),(81,'Tracery'),(299,'Carving'),(313,'Chalk'),(507,'Chalk'),(515,'Gold'),(970,'Carving')]:
            wallbox(axis,sign,w,0,q,2250,25,9 if q not in (22,299,970) else 30,mat,9)
        wallbox(axis,sign,w,0,159,2430,13,277,'Ashlar',9)
        for t in [-870,-440,0,440,870]:
            if axis=='x' and t==0:continue
            wallbox(axis,sign,w,t,476,306,16,827,'Sootstone',14)
            for k in (-1,1):
                pt=wallpoint(axis,sign,w,t+146*k,0,33);post(*pt[:2],0,560,20)
            for d,rad in [(20,143),(31,134)]:
                arch(axis,sign,w,t,553,rad,202,7,'Chalk' if d==20 else 'Tracery',d)
            arch_blocks(axis,sign,w,t,553,145,208,17)
            for shift in (-73,0,73):glass_lancet(axis,sign,w,t+shift,321,31,327-(abs(shift)*.81),30)
            for l in range(3):
                x,y,z=wallpoint(axis,sign,w,t-67+l*67,0,34)
                taper((x,y,95),(x,y,286),9,8,'Chalk')
            wallbox(axis,sign,w,t,312,311,45,13,'Parchment',28)
        for t in [-1062,-658,-221,221,658,1062]:
            pt=wallpoint(axis,sign,w,t,0,27);post(*pt[:2],0,884,29)
            if abs(t)<800:banner(axis,sign,w,t,802,247,75,72)
        if axis=='x':
            # An oversized solar reliquary stands at both ends of the nave.
            wallbox(axis,sign,w,0,377,338,40,750,'Mortar',11)
            for k in (-1,1):
                for j in range(9):
                    wallbox(axis,sign,w,k*137,j*31+16,38,38,29,'Carving' if j%2 else 'Chalk',34)
                for t in range(5):
                    wallbox(axis,sign,w,k*(13+22*t),126,20,13,246,'Deep',48)
                wallbox(axis,sign,w,k*67,100,111,15,7,'Bronze' if 'Bronze' in palette else 'Burnished',50)
            arch_blocks(axis,sign,w,0,263,139,156,48)
            for k in (-1,1):glass_lancet(axis,sign,w,k*48,264,33,78,47)
            rose(axis,sign,w,670,201,49)
            for q in (-1,1):
                b=wallpoint(axis,sign,w,q*272,0,100);brazier(*b[:2],1.15)
        if axis=='y':
            for t in (-680,680):
                b=wallpoint(axis,sign,w,t,0,80);brazier(*b[:2],1)

# Four collision-matched compound pillars, their ceiling ribs and gilded bosses.
for x in (-480,480):
    for y in (-670,670):
        post(x,y,0,548,42)
        for a in range(4):
            dx,dy=cos(a*pi/2),sin(a*pi/2)
            taper((x+34*dx,y+34*dy,460),(x+57*dx,y+57*dy,545),8,17,'Parchment',6)
        for vx,vy in [(0,-y),( -x,0),(-x,-y)]:
            curve=pointed_profile(math.hypot(vx,vy),342,14)[:15]
            mag=math.hypot(vx,vy)
            pts=[(x+(t+mag)*vx/mag,y+(t+mag)*vy/mag,548+z) for t,z in curve]
            for i in range(len(pts)-1):
                rod(pts[i],pts[i+1],15 if vx==0 or vy==0 else 10,'Carving',6)
                a,b=pts[i],pts[i+1];rod((a[0],a[1],a[2]-9),(b[0],b[1],b[2]-9),3.5,'Tracery',6)
for x,y in [(0,0),(-480,0),(480,0),(0,-670),(0,670)]:
    taper((x,y,870),(x,y,901),11,27,'Gold')
# High roof prevents an empty black sky on upward camera movement.
for y in (-1,1):
    plate([(-1158,0,1009),(1158,0,1009),(1158,1096*y,901),(-1158,1096*y,901)],'Deep')
# Small votive groups, fallen masonry in outer corners, boundary moulding.
for sx in (-1,1):
    for sy in (-1,1):
        for i in range(11):
            x=sx*rng.uniform(805,990);y=sy*rng.uniform(675,901);h=rng.uniform(8,29)
            taper((x,y,0),(x,y,h),rng.uniform(9,19),rng.uniform(7,16),'Carving',rng.randint(4,6),rng.random())
        for i in range(15):
            x=sx*(976+rng.uniform(-35,28));y=sy*(394+rng.uniform(-41,56));h=rng.uniform(6,22)
            taper((x,y,0),(x,y,h),3.6,3.3,'Wax');flame(x,y,h,3)

# High altar built into the apse, behind the collision boundary. Its paired
# pinnacles, crocket leaves and enamel reredos silhouette the knight from across the nave.
def moulded_base(x,y,z,dx,dy):
    for h,w,m in [(4,1,'Carving'),(3,.96,'Tracery'),(9,.91,'Deep'),(2,.97,'Gold')]:
        box(x,y,z+h*.5,dx*w,dy*w,h,m);z+=h
def finial(x,y,z,h):
    taper((x,y,z),(x,y,z+h*.14),9,11,'Tracery',8)
    taper((x,y,z+h*.14),(x,y,z+h*.80),10,2,'Parchment',8)
    taper((x,y,z+h*.80),(x,y,z+h),3,0,'Gold',6)
    for a in (0,pi*.5,pi,pi*1.5):
        for i in (0,1,2):
            p=(x+cos(a)*(8-i*2),y+sin(a)*(8-i*2),z+h*(.27+i*.17))
            taper(p,(p[0]+cos(a)*5,p[1]+sin(a)*5,p[2]+9),3,0,'Chalk',5)
for s in (-1,1):
    y=137*s;moulded_base(1032,y,0,34,46)
    post(1033,y,17,279,13)
    for h,r,m in [(301,16,'Carving'),(309,21,'Tracery'),(317,18,'Parchment')]:
        taper((1033,y,h),(1033,y,h+7),r,r-1,m)
    finial(1032,y,324,89)
    for z in (82,305):
        box(1041,y,z,44,43,5,'Tracery')
# Thin actual inset icon foil. The UVs on this panel alone cover the whole illustration.
icon_x,icon_z,icon_half,icon_h=1037,69,112,326
corners=[(icon_x,-icon_half,icon_z),(icon_x,icon_half,icon_z),(icon_x,icon_half,icon_z+icon_h),(icon_x,-icon_half,icon_z+icon_h)]
plate(corners,'Icon')
for d,r,m in [(1,5,'Iron'),(7,2,'Gold')]:
    for a,b in zip(corners,corners[1:]+corners[:1]):
        rod((a[0]-d,a[1],a[2]),(b[0]-d,b[1],b[2]),r,m,8)
moulded_base(1047,0,6,59,331)
box(1035,0,42,55,309,34,'Deep')
box(1033,0,61,61,318,6,'Chalk')
for j in range(-3,4):
    y=j*39
    for k in (-1,1):
        rod((1008,y,48),(1008,y+k*13,37),1.3,'Gold',5)
        rod((1008,y+k*13,37),(1008,y,28),1.3,'Tracery',5)
for k in (-1,1):
    arch('x',1,1049,0,395,116+k*4,52+k*4,3,'Gold' if k==1 else 'Tracery',16)
for i in range(-5,6):
    finial(1033,i*21,397+(1-abs(i)/6)*31,20 if i%2 else 29)
# Narrow blind-arcade bays carved beneath the clerestory. The little cinquefoil
# crowns and dark recesses remain readable even when the local lamps are out.
for axis in ('x','y'):
    for sg in (-1,1):
        w=(1255 if sg==1 else 1110) if axis=='x' else 1060
        for center in [-867,-438,438,867]:
            for delta in [-70,0,70]:
                t=center+delta
                wallbox(axis,sg,w,t,174,61,5,170,'Deep',40)
                for side in (-1,1):
                    rod(wallpoint(axis,sg,w,t+side*26,94,44),wallpoint(axis,sg,w,t+side*26,207,44),3,'Carving',6)
                arch(axis,sg,w,t,207,26,54,3,'Tracery',44)
                for side in (-1,1):
                    arch(axis,sg,w,t+side*13,203,13,33,1.8,'Chalk',45)
                circle_wall(axis,sg,w,t,240,5,1.5,'Gold',45,10)
                # A foliated molding sits inside each panel.
                for k in (0,1,2):
                    zz=123+k*21
                    a=wallpoint(axis,sg,w,t,zz,46)
                    b=wallpoint(axis,sg,w,t+(-1 if k%2 else 1)*8,zz+12,47)
                    taper(a,b,2.3,.1,'Tracery',5)
# Thin stone spokes and brass nails articulate the rhythm of the vaulted ceiling.
for x in (-480,0,480):
    for s in (-1,1):
        path=[(x+q, s*(742+q*.43),888-q*.15) for q in range(-430,431,43)]
        for a,b in zip(path,path[1:]):rod(a,b,4.8,'Carving',6)
for r in [286,326]:
    for j in range(32):
        a=j*pi/16
        p=lambda k,d:(60+(r+k)*cos(a)-d*sin(a),(r+k)*sin(a)+d*cos(a),.45)
        plate([p(-5,0),p(0,-2.5),p(5,0),p(0,2.5)],'Burnished')
# Four shafts in the air above the side chapels, with fading ends and cross-section.
# Each is a two-triangle strip rather than a scene-wide volumetric scattering pass.
for sx,sy in [(-430,-1),(460,-1),(-440,1),(455,1)]:
    top=Vector((sx,sy*995,579));foot=Vector((sx+207,sy*132,38))
    for shift in (-36,18):
        a=top+Vector((shift,0,0));b=foot+Vector((shift*1.3,0,0))
        verts=[a+Vector((-21,0,0)),a+Vector((21,0,0)),b+Vector((52,0,0)),b+Vector((-52,0,0))]
        plate(verts,'Incense')

# The rose lights the east apse from behind a triumphal arch. The choir stalls,
# effigies, balustrades and piers sit past the arena boundary at x=1007.
def loft(rings, material, sides=16, modulation=0., phase=0.):
    verts=[]
    for x,y,z,rx,ry in rings:
        for k in range(sides):
            a=2*pi*k/sides
            ripple=1.+modulation*(.58*cos(7*a+phase)+.25*sin(3*a-.03*z)+.17*cos(5*a+.008*z))
            verts.append((x+rx*cos(a)*ripple,y+ry*sin(a)*ripple,z))
    last=(len(rings)-1)*sides
    faces=[tuple(reversed(range(sides))),tuple(last+k for k in range(sides))]
    for row in range(len(rings)-1):
        for k in range(sides):
            k1=(k+1)%sides;o=row*sides
            faces.append((o+k,o+k1,o+sides+k1,o+sides+k))
    surface(verts,faces,material)

def mourner(x,y,sign):
    # Knees and shoulders deform the stone mantle. The cowl is hollow towards
    # the crossing and the separately modeled lowered face is in its own shadow.
    box(x,y,8,88,99,16,'Purbeck');box(x,y,19,81,93,7,'Chalk')
    for z,h,r,d in [(23,9,49,45),(32,10,44,37),(42,66,37,39),(108,8,41,46),(116,5,49,47)]:
        taper((x,y,z),(x,y,z+h),r,d,'Purbeck' if z==42 else 'Carving',8,pi/8)
    base=121
    body=[(0,3,0,29,36),(2,1,8,26,32),(0,0,31,23,28),(-2,-1,53,22,25),
          (0,-1,83,15,19),(2,0,102,18,22),(1,0,124,17,29),(0,0,139,12,24),(-3,0,147,8,11)]
    loft([(x+dx,y+dy*sign,base+h,rx,ry) for dx,dy,h,rx,ry in body],'Sculpture',36,.18,.4*sign)
    # Deep sweeping folds curve around the bent front leg. A weathered soldier's
    # long sword rests point-down, with the gloved hands folded on its pommel.
    for k in range(8):
        a=pi*.48+k*pi/7
        points=[]
        for j in range(6):
            q=j/5;ang=a+.29*sin(q*pi)*sign;r=28-11*q
            points.append((x+r*cos(ang),y+(r+3)*sin(ang),base+3+102*q))
        for j in range(5):taper(points[j],points[j+1],2.1-j*.19,1.9-j*.16,'Sculpture',6)
    for side in (-1,1):
        p=(x,y+side*22,base+131);a=(x-11,y+side*28,base+101);b=(x-25,y+side*6,base+116)
        taper(p,a,10,8,'Sculpture',9);taper(a,b,8,6,'Sculpture',9)
        loft([(b[0],b[1],b[2]-3,6,5),(b[0]-4,b[1],b[2]+3,5,5),(b[0]-5,b[1],b[2]+6,3,3)],'Carving',10)
    rod((x-30,y,base+16),(x-30,y,base+115),2.3,'Memorial',5)
    rod((x-30,y-13,base+102),(x-30,y+13,base+102),2.2,'Memorial',6)
    # Open cowl. Elliptical rings run from the front opening to the back cap.
    contour=[(cos(a*2*pi/32),sin(a*2*pi/32)) for a in range(32)]
    hc=base+152
    verts=[(x+dx-.13*zr*v,y+yr*u,hc+zr*v+dz) for dx,yr,zr,dz in
           [(-16,8,11,0),(-14,15,18,1),(-7,17,21,3),(3,17,22,5),(11,12,17,4),(15,3,7,1)] for u,v in contour]
    faces=[(r*32+k,r*32+(k+1)%32,(r+1)*32+(k+1)%32,(r+1)*32+k) for r in range(5) for k in range(32)]
    surface(verts,faces,'Sculpture')
    loft([(x-11,y,hc-10,3,3),(x-12,y,hc-5,5,6),(x-11,y,hc+4,5.5,6.4),(x-10,y,hc+9,3,4)],'Carving',14)
    taper((x-14,y,hc+3),(x-18,y,hc-1),2.0,1.0,'Sculpture',5)

# Carved reverse archivolts and voussoirs over the axial apse; short lateral
# arches terminate at the real outer walls and give the aisle shadows depth.
for sign in (-1,1):
    post(1072,sign*402,0,350,32)
    for dx in (-22,22):
        post(1072+dx,sign*417,0,355,13)
    arch_blocks('x',1,1133,sign*696,331,271,271,40)
    arch('x',1,1133,sign*696,331,263,264,8,'Carving',52)
    arch('x',1,1133,sign*696,331,254,258,3,'Chalk',56)
    post(1078,sign*980,0,333,30)
    mourner(1038,sign*582,sign)
    # Overlapping deep-set oak seats below the stone wall. Paneled ends, armrests,
    # curved choir misericords and the brass nail row break up the facade.
    for j in range(4):
        y=sign*(235+j*59)
        box(1194,y,9,103,58,18,'Purbeck');box(1214,y,100,17,55,165,'Oak')
        box(1195,y,183,56,60,7,'Oak');box(1182,y,44,59,56,11,'Oak')
        box(1204,y,119,5,42,97,'Carving');box(1200,y,117,4,33,82,'Oak')
        for edge in (-1,1):
            yy=y+edge*25
            rod((1175,yy,50),(1175,yy,71),3.5,'Oak')
            rod((1175,yy,72),(1206,yy,74),3.6,'Oak')
            taper((1212,yy,182),(1212,yy,207),5,0,'Oak',8)
    box(1170,sign*696,4,143,487,8,'Purbeck')
    box(1181,sign*696,12,128,470,8,'Carving')
for side_w,off,r,material in [(409,41,9,'Carving'),(398,56,5,'Chalk'),(383,65,4,'Tracery')]:
    arch('x',1,1125,0,353,side_w,452,r,material,off)
arch_blocks('x',1,1133,0,353,408,458,51)
# Shallow steps below the screen fill the distance to the backwall. Each nosing
# faces into the playable space while staying flush with its collision boundary.
for front,height,span in [(1009,7,728),(1050,14,708),(1091,22,686)]:
    east=1260
    box((east+front)/2,0,height*.5,east-front,span,height,'Purbeck')

# Two iron candle coronas hung from the vault in the side aisles. In elevation
# the chain is catenary-like rather than standing unsupported on a horizontal ring.
def corona(cx,cy,z,rad):
    three=[(cx+rad*cos((k+.2)*2*pi/3),cy+rad*sin((k+.2)*2*pi/3),z+3) for k in range(3)]
    rod((cx,cy,z+111),(cx,cy,939),1.5,'Iron',6)
    for anchor in three:
        mid=((anchor[0]+cx)*.5,(anchor[1]+cy)*.5,(anchor[2]+z+111)*.5-4)
        rod(anchor,mid,1.2,'Iron',6);rod(mid,(cx,cy,z+111),1.2,'Iron',6)
    for i in range(32):
        a=i*pi/16;b=(i+1)*pi/16
        p=lambda t,dz:(cx+rad*cos(t),cy+rad*sin(t),z+dz)
        for dz in (-5,4):rod(p(a,dz),p(b,dz),2.3,'Iron',6)
        if i%2==0:
            rod(p(a,-6),p(a,6),1.7,'Memorial',6)
            if i%4==0:
                px,py,pz=p(a,6);taper((px,py,pz),(px,py,pz+10),2.5,2.2,'Wax',7);flame(px,py,pz+10,2.2)
for sy in (-1,1):
    for x in (-179,619):corona(x,sy*770,457 if x<0 else 486,43)

# Nine quadripartite vaults. Each web rises from its springing directly to the
# diagonal groin. The textured intrados meets the ridges under the old roof shell.
def arch_rise(half,coordinate,rise):
    centre=(rise*rise-half*half)/(2.*half)
    r=centre+half
    return math.sqrt(max(0.,r*r-(centre+abs(coordinate))**2))
def vault(x0,x1,y0,y1):
    spanx=(x1-x0)/2;spany=(y1-y0)/2
    cx=(x1+x0)/2;cy=(y1+y0)/2
    spring=565;rise=351
    def vertex(u,v):
        x=u*spanx;y=v*spany
        hx=arch_rise(spanx,x,rise);hy=arch_rise(spany,y,rise)
        # The slightly bombed panels break flat reflections on the curved masonry.
        h=max(hx,hy)+5*math.sin(pi*abs(u*v))
        return (cx+x,cy+y,spring+h)
    steps=16
    vertices=[vertex(-1+2*i/steps,-1+2*j/steps) for j in range(steps+1) for i in range(steps+1)]
    stride=steps+1
    faces=[(j*stride+i,j*stride+i+1,(j+1)*stride+i+1,(j+1)*stride+i) for j in range(steps) for i in range(steps)]
    surface(vertices,faces,'VaultWeb')
    for k in (-1,1):
        pts=[vertex(-1+2*i/steps,k*(-1+2*i/steps)) for i in range(steps+1)]
        for a,b in zip(pts,pts[1:]):
            rod((a[0],a[1],a[2]-4),(b[0],b[1],b[2]-4),5.8,'Carving',7)
    taper((cx,cy,spring+rise-15),(cx,cy,spring+rise+2),8,14,'Tracery',10)
for x0,x1 in [(-1130,-480),(-480,480),(480,1280)]:
    for y0,y1 in [(-1080,-670),(-670,670),(670,1080)]:vault(x0,x1,y0,y1)

# Export with world-oriented UVs so that mineral and fabric detail stays on scale.
mesh=bpy.data.meshes.new('Nave');mesh.from_pydata(V,[],F);mesh.update();ob=bpy.data.objects.new('Nave',mesh);scene.collection.objects.link(ob)
slots=list(dict.fromkeys(M))
for name in slots:
    mat=bpy.data.materials.new(name);mat.diffuse_color=(*palette[name][0],1);mesh.materials.append(mat)
uv=mesh.uv_layers.new(name='Surface')
for poly,name in zip(mesh.polygons,M):
    poly.material_index=slots.index(name);n=poly.normal
    axis=max(range(3),key=lambda i:abs(n[i]))
    i,j=((1,2),(0,2),(0,1))[axis]
    for loop in poly.loop_indices:
        co=mesh.vertices[mesh.loops[loop].vertex_index].co
        if name in ('FlameSheet','SaintGlass'):
            uv.data[loop].uv=art_uv[mesh.loops[loop].vertex_index]
        elif name=='Icon':
            uv.data[loop].uv=((co.y+icon_half)/(icon_half*2),(co.z-icon_z)/icon_h)
        elif name=='Incense':
            uv.data[loop].uv=[(0,1),(1,1),(1,0),(0,0)][loop-poly.loop_start]
        else:
            scale={'Pavement':235, 'ChoirPaving':475, 'Ashlar':362, 'Sootstone':262, 'Sculpture':145,'VaultWeb':311}.get(name,175)
            uv.data[loop].uv=(co[i]/scale,co[j]/scale)
bpy.context.view_layer.objects.active=ob;ob.select_set(True)
bpy.ops.export_scene.fbx(filepath=str(out/'SM_Nave.fbx'),use_selection=True,add_leaf_bones=False,bake_anim=False,axis_forward='-Y',axis_up='Z',apply_unit_scale=True,mesh_smooth_type='FACE')
print('SOULBREAK chapel:',len(V),'vertices;',len(F),'polygons;',len(slots),'materials.')
