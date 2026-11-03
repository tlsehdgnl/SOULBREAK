"""Build the chapel of the Severed Sun. Run in Blender 4.3 background mode.

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
(out / 'chapel_materials.json').write_text(json.dumps(palette))
V=[]; F=[]; M=[]
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
def flame(x,y,z,sz):
    taper((x,y,z),(x+sz*.18,y,z+sz*.85),sz*.38,sz*.31,'Wick',6)
    taper((x+sz*.18,y,z+sz*.72),(x-sz*.1,y+.08*sz,z+sz*1.7),sz*.37,0,'Wick',6)
    taper((x,y-.09*sz,z),(x+sz*.08,y-.13*sz,z+sz*.83),sz*.29,0,'Fire',6)
def brazier(x,y,scale=1):
    for z,h,r1,r2,m in [(0,8,31,31,'Iron'),(8,10,31,16,'Burnished'),(18,54,10,7,'Iron'),(72,8,10,23,'Gold'),(80,18,17,38,'Burnished'),(98,4,38,37,'Gold'),(102,4,34,32,'Coal')]:
        taper((x,y,z*scale),(x,y,(z+h)*scale),r1*scale,r2*scale,m)
    for i in range(7):
        a=2*pi*i/7; d=18 if i else 0; flame(x+cos(a)*d*scale,y+sin(a)*d*scale,102*scale,(12+(7-i)*2)*scale)
    for i in range(4):
        a=i*pi/2;taper((x+21*scale*cos(a),y+21*scale*sin(a),85*scale),(x+40*scale*cos(a),y+40*scale*sin(a),121*scale),4*scale,1,'Iron',5)

# Twenty-metre nave. The joints and inlays are below one centimetre in height.
box(0,0,-28,2260,2180,55,'Mortar')
for row in range(-12,13):
    x=row*91; shift=48 if row%2 else 0
    for col in range(-11,12):
        y=col*99+shift
        if abs(y)>1100:continue
        box(x,y,-4.6,89.9,97.9,9,rng.choice(['SlabA','SlabA','SlabC','SlabB','SlabD']))
        if rng.random()<.12:
            x0=x+rng.uniform(-29,10);y0=y-49
            strip([(x0,y0,.03),(x0+13,y0+19,.03),(x0+7,y0+28,.03),(x0+21,y0+36,.03)],1.1,'Mortar')
for y in (-836,836,-809,809):box(0,y,.05,2160,3, .32,'Burnished')
for x in (-833,833):box(x,0,.05,4,1657,.32,'Burnished')
for r,w,m in [(377,5,'Gold'),(368,2,'Oxide'),(340,4,'Burnished'),(282,3,'Gold'),(261,3,'Oxide'),(76,4,'Gold'),(67,2,'Burnished')]:
    rim(60,0,.38,r,r+w,m)
for i in range(40):
    a=i*2*pi/40;d=17 if i%5 else 28
    strip([(60+cos(a)*344,sin(a)*344,.39),(60+cos(a)*(344+d),sin(a)*(344+d),.39)],3.2,'Gold')
for i in range(16):
    a=i*pi/8;v=(cos(a),sin(a));w=(-v[1],v[0]);len1=260 if not i%2 else 180
    def gp(d,h):return (60+v[0]*d+w[0]*h,v[1]*d+w[1]*h,.42)
    plate([gp(75,0),gp(125,-14),gp(len1,0)],'Burnished');plate([gp(75,0),gp(len1,0),gp(125,12)],'Gold')
for x in (-558,-545):
    for y in range(-720,721,70):box(x,y,.25,3,49,.35,'Rune' if x==-545 else 'Gold')

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
        w=1110 if axis=='x' else 1060
        # Jambs and inset gothic lancets read in the level even with flat lighting.
        wallbox(axis,sign,w,0,520,2280,80,1056,'Deep',-38)
        for q,mat in [(22,'Carving'),(72,'Chalk'),(81,'Tracery'),(299,'Carving'),(313,'Chalk'),(507,'Chalk'),(515,'Gold'),(970,'Carving')]:
            wallbox(axis,sign,w,0,q,2250,25,9 if q not in (22,299,970) else 30,mat,9)
        for j in range(5):
            for i in range(17):
                t=(i-8)*134+(j%2)*67
                wallbox(axis,sign,w,t,37+j*55,132,15,53,rng.choice(['SlabA','SlabC','Carving']),6)
        for t in [-870,-440,0,440,870]:
            if axis=='x' and t==0:continue
            wallbox(axis,sign,w,t,476,306,16,827,'Mortar',14)
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
        co=mesh.vertices[mesh.loops[loop].vertex_index].co;uv.data[loop].uv=(co[i]/182,co[j]/182)
bpy.context.view_layer.objects.active=ob;ob.select_set(True)
bpy.ops.export_scene.fbx(filepath=str(out/'SM_Nave.fbx'),use_selection=True,add_leaf_bones=False,bake_anim=False,axis_forward='-Y',axis_up='Z',apply_unit_scale=True,mesh_smooth_type='FACE')
print('SOULBREAK chapel:',len(V),'vertices;',len(F),'polygons;',len(slots),'materials.')
