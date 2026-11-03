"""Generate original low-poly characters, skeletal clips and the fallen sword in Blender (background mode)."""
import bpy, math, json
from mathutils import Vector, Euler, Quaternion
from pathlib import Path
from math import sin, cos, pi
out = Path(__file__).resolve().parents[2] / 'Saved/SBArt'
out.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.unit_settings.system='METRIC'
scene.unit_settings.scale_length=.01
scene.render.fps=30
# Base colors are in linear space. Shared brass, cloth and enamel tie the figures to the chapel.
palette={
 'Basalt':(.043,.058,.084,0,.83,0),'Slate':(.10,.145,.18,0,.75,0),'Stone':(.22,.27,.30,0,.82,0),
 'SilverStone':(.38,.40,.38,0,.79,0),'Mortar':(.054,.079,.09,0,.88,0),'Bronze':(.34,.185,.057,.57,.42,0),
 'Gilt':(.72,.42,.11,.65,.32,0),'Iron':(.065,.09,.13,.68,.39,0),'Steel':(.24,.34,.39,.65,.29,0),
 'Edge':(.58,.72,.72,.72,.24,0),'Leather':(.09,.046,.033,0,.85,0),'Ivory':(.72,.65,.46,.13,.60,0),
 'Azure':(.024,.22,.245,0,.69,0),'DeepBlue':(.021,.078,.12,0,.80,0),'Wine':(.23,.025,.037,0,.76,0),
 'Crimson':(.49,.049,.044,0,.65,0),'Obsidian':(.017,.021,.035,.25,.38,0),
 'Soul':(.035,.78,.78,.1,.31,2.2),'Ember':(1,.25,.034,0,.43,2.4),'Flame':(1,.67,.17,0,.44,4.5),
 'Glass':(.019,.27,.36,.15,.31,1.4),'GlassGold':(.83,.32,.045,.1,.4,1.5),'GlassRed':(.40,.04,.094,.2,.5,1.0)}
(out/'palette.json').write_text(json.dumps(palette))
mats={}
for k,c in palette.items():
 m=bpy.data.materials.new(k); m.diffuse_color=(*c[:3],1); mats[k]=m
class Geometry:
 def __init__(self):
  self.v=[]; self.f=[]; self.m=[]; self.groups={}
 def surface(self, verts, faces, mat, bone=None):
  start=len(self.v); self.v.extend(verts)
  self.f.extend([tuple(start+i for i in f) for f in faces]); self.m.extend([mat]*len(faces))
  if bone: self.groups.setdefault(bone,[]).extend(range(start,len(self.v)))
 def rings(self,center,rings,mat,bone=None,n=8,angle=pi/8):
  x,y,z=center; vs=[(x+rx*cos(angle+2*pi*i/n),y+dy+ry*sin(angle+2*pi*i/n),z+h) for h,rx,ry,dy in rings for i in range(n)]
  fs=[tuple(reversed(range(n)))]
  for j in range(len(rings)-1):
   for i in range(n):
    a=j*n+i;b=j*n+(i+1)%n;fs.append((a,b,b+n,a+n))
  fs.append(tuple(range(len(vs)-n,len(vs)))); self.surface(vs,fs,mat,bone)
 def box(self,p,sz,mat,bone=None):
  x,y,z=p; a,b,c=[v/2 for v in sz]
  self.surface([(x+i*a,y+j*b,z+k*c) for k in (-1,1) for j in (-1,1) for i in (-1,1)],[(0,2,3,1),(4,5,7,6),(0,1,5,4),(1,3,7,5),(3,2,6,7),(2,0,4,6)],mat,bone)
 def beam(self,a,b,r1,r2,mat,bone=None,n=8):
  a,b=Vector(a),Vector(b); d=(b-a).normalized(); t=d.cross(Vector((0,0,1)) if abs(d.z)<.92 else Vector((0,1,0))).normalized(); u=d.cross(t)
  vs=[p+r*(t*cos(2*pi*i/n)+u*sin(2*pi*i/n)) for p,r in ((a,r1),(b,r2)) for i in range(n)]
  self.surface(vs,[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,n+(i+1)%n,n+i) for i in range(n)],mat,bone)
 def panel(self,points,mat,bone=None,thick=1):
  vs=list(map(Vector,points)); d=(vs[1]-vs[0]).cross(vs[2]-vs[0]).normalized()*thick; n=len(vs)
  self.surface(vs+[p-d for p in vs],[tuple(range(n)),tuple(reversed(range(n,2*n)))]+[(i,n+i,n+(i+1)%n,(i+1)%n) for i in range(n)],mat,bone)
 def object(self,name):
  mesh=bpy.data.meshes.new(name);mesh.from_pydata(self.v,[],self.f);mesh.update();ob=bpy.data.objects.new(name,mesh);scene.collection.objects.link(ob)
  keys=list(dict.fromkeys(self.m))
  for k in keys: mesh.materials.append(mats[k])
  uv=mesh.uv_layers.new(name='UVMap')
  for p,m in zip(mesh.polygons,self.m):
   p.material_index=keys.index(m)
   axis=max(range(3),key=lambda i: abs(p.normal[i]))
   for loop in p.loop_indices:
    co=mesh.vertices[mesh.loops[loop].vertex_index].co
    uv.data[loop].uv=(co[(axis+1)%3]/100,co[(axis+2)%3]/100)
  for b,indices in self.groups.items():ob.vertex_groups.new(name=b).add(indices,1,'REPLACE')
  return ob
def export(name,objects,anim=False):
 bpy.ops.object.select_all(action='DESELECT')
 for ob in objects: ob.select_set(True)
 bpy.context.view_layer.objects.active=objects[-1]
 bpy.ops.export_scene.fbx(filepath=str(out/(name+'.fbx')),use_selection=True,add_leaf_bones=False,
  mesh_smooth_type='FACE',bake_anim=anim,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0,
  apply_unit_scale=True,axis_forward='-Y',axis_up='Z',use_custom_props=False)
bones={'Root':((0,0,0),(0,0,8),None),'Pelvis':((0,0,90),(0,0,105),'Root'),'Chest':((0,0,105),(0,0,147),'Pelvis'),
 'Head':((0,0,147),(0,0,181),'Chest'),'Forward':((0,-18,90),(0,-22,90),'Pelvis')}
for side,s in [('R',-1),('L',1)]:
 for b,a,c,parent in [('UpperArm',(25,0,140),(30,-1,112),'Chest'),('Forearm',(30,-1,112),(31,-5,86),'UpperArm'),('Hand',(31,-5,86),(31,-5,76),'Forearm'),
 ('Thigh',(12,0,89),(13,-1,48),'Pelvis'),('Shin',(13,-1,48),(14,0,10),'Thigh'),('Foot',(14,0,10),(14,-17,7),'Shin')]:
  bones[b+side]=((s*a[0],*a[1:]),(s*c[0],*c[1:]),parent if parent in ('Chest','Pelvis') else parent+side)
bones['BladeBase']=((-31,-15,82),(-31,-20,83),'HandR')
bones['BladeTip']=((-31,-104,100),(-31,-109,101),'HandR')
arm=bpy.data.armatures.new('PilgrimRig'); rig=bpy.data.objects.new('Armature',arm);scene.collection.objects.link(rig)
bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
for name,(a,b,parent) in bones.items():
 e=arm.edit_bones.new(name);e.head=a;e.tail=b
 if parent:e.parent=arm.edit_bones[parent]
bpy.ops.object.mode_set(mode='OBJECT')
def sword(g,x,y,z,knight=True,bind=None):
 # Long diamond-section blade with two cutting edges and a tapering central fuller.
 def pos(xx,t,h):return (x+xx,y-t,z+.20*t+h)
 width=6.4 if knight else 4.3
 g.beam(pos(0,-12,0),pos(0,12,0),2.3,2.1,'Leather',bind)
 for t in (-12,-7,-2,3,8):g.beam(pos(0,t,0),pos(0,t+1,0),2.7,2.7,'Gilt',bind)
 for s in (-1,1):g.beam(pos(0,10,0),pos(s*13,16,0),3.2,1.1,'Gilt',bind,5)
 stations=[(12,width*.65),(19,width),(79,width*.71),(99,.08)]
 for (a,w),(b,v) in zip(stations,stations[1:]):
  for side in (-1,1):
   g.panel([pos(0,a,2.4),pos(side*w,a,0),pos(side*v,b,0),pos(0,b,1.3)],'Edge' if side==1 else 'Steel',bind,.7)
   g.panel([pos(0,b,-1.5),pos(side*v,b,0),pos(side*w,a,0),pos(0,a,-2)],'Steel',bind,.5)
 g.beam(pos(0,16,2.5),pos(0,69,1.8),1.05,.55,'Ember' if knight else 'Soul',bind,5)
 g.beam(pos(0,-15,0),pos(0,-11,0),3.1,2.5,'Gilt',bind,6)
def figure(knight):
 g=Geometry(); plate='Iron' if knight else 'Steel'; cloth='Wine' if knight else 'Azure'
 def shell(p,rings,m,b,n=8):g.rings(p,rings,m,b,n)
 shell((0,0,0),[(86,17,11,0),(97,20,13,0),(114,16,12,0)],'Leather','Pelvis')
 shell((0,0,0),[(105,16,12,0),(123,25,17,-1),(139,27 if knight else 23,16,0),(148,13,10,1)],plate,'Chest')
 for z,w in [(108,17),(114,18),(119,19)]:shell((0,0,z),[(0,w,13,0),(2,w+1,14,0),(4,w,13,0)],'Bronze' if knight else 'Steel','Chest')
 for s in (-1,1):
  g.panel([(s*1,-17,124),(s*24,-11,137),(s*17,-15,142),(0,-19,133)],'Gilt' if knight else 'Ivory','Chest')
  g.panel([(s*3,-15,125),(s*21,-12,134),(s*18,-14,125),(s*5,-16,119)],'Steel','Chest')
 shell((0,0,0),[(94,20,14,0),(101,21,14,0),(103,19,13,0)],'Bronze','Pelvis')
 g.box((0,-14,99),(8,3,8),'Gilt','Pelvis')
 # Divided tabard and a cape with a contrasting embroidered stripe.
 for s in (-1,1):
  g.panel([(s*1,-14,96),(s*16,-11,96),(s*20,-10,64),(s*9,-16,55)],cloth,'Pelvis',2)
  g.beam((s*3,-15,92),(s*10,-17,60),1.5,1,'Gilt','Pelvis',4)
  g.panel([(s*5,10,145),(s*24,6,138),(s*29,23,62),(s*7,26,50)],'Crimson' if knight else 'DeepBlue','Chest',2)
  g.beam((s*19,11,134),(s*24,24,65),1.4,.7,'Bronze' if knight else 'Azure','Chest')
 # Helm: hooded turquoise pilgrim or crowned, split-visor knight.
 shell((0,0,0),[(146,9,9,0),(151,13,12,0),(165,15,14,-1),(177,12,11,0),(183,4,5,2)],plate if knight else 'DeepBlue','Head',10)
 if knight:
  for s in (-1,1):
   g.panel([(s*13,-7,169),(s*2,-16,171),(s*1,-17,165),(s*11,-11,161)],'Steel','Head')
   g.beam((s*2,-16.8,166),(s*12,-10,167),1.25,.8,'Ember','Head',4)
   g.panel([(s*13,-9,162),(s*2,-17,164),(0,-17,148),(s*10,-11,155)],'Iron','Head')
   g.beam((s*12,0,170),(s*17,3,194),3.5,.2,'Gilt','Head',5)
  g.beam((0,-11,176),(0,-14,194),3.2,.2,'Gilt','Head',5)
 else:
  g.panel([(-11,-9,169),(0,-15,174),(11,-9,169),(7,-14,155),(0,-16,150),(-7,-14,155)],'Obsidian','Head')
  for s in (-1,1):
   g.beam((s*2,-16,165),(s*8,-13,166),1.1,.7,'Soul','Head',4)
   g.beam((0,-15,174),(s*12,-10,168),1.7,1,'Ivory','Head')
  shell((0,0,0),[(144,14,13,0),(150,15,14,-1),(155,11,11,-1)],'Azure','Head')
 for side,s in [('R',-1),('L',1)]:
  a='UpperArm'+side; f='Forearm'+side; h='Hand'+side; th='Thigh'+side; sh='Shin'+side; ft='Foot'+side
  g.beam((s*25,0,140),(s*30,-1,114),8,6,'Leather',a)
  w=19 if knight and side=='R' else (14 if knight else 11)
  shell((s*25,0,137),[(-11,w*.8,11,0),(-7,w,14,0),(3,w+1,14,0),(10,w*.7,11,0),(13,4,6,0)],'Bronze' if knight and side=='R' else plate,a)
  shell((s*25,0,135),[(-8,w,14,0),(-5,w+1,14.5,0)],'Gilt',a)
  if knight and side=='R':
   for i in range(3):
    g.beam((s*(21+i*5),-6+i*4,146),(s*(26+i*9),-5+i*4,155+i*2),3.4,.3,'Gilt',a,5)
   g.beam((s*16,-12,140),(s*32,-13,133),1.7,1.4,'Ember',a)
  g.beam((s*30,-1,112),(s*31,-5,88),7.6,5.4,plate,f)
  for z in (95,105):shell((s*30,-3,z),[(0,7.8,7,0),(2,8,7,0)],'Bronze',f)
  shell((s*31,-5,83),[(-5,4,5,0),(0,6,6,0),(7,5,5,0)],'Iron',h)
  g.beam((s*12,0,87),(s*13,-1,50),10,7,'Leather',th)
  shell((s*13,0,72),[(-13,8,8,0),(3,10,10,0),(9,9,9,0)],plate,th)
  shell((s*13,-1,48),[(-6,7,8,-1),(0,10,10,-2),(6,8,8,0)],'Bronze',sh)
  g.beam((s*13,-1,44),(s*14,0,11),7,4.3,plate,sh)
  g.beam((s*13,-8,42),(s*14,-5,15),1.8,1,'Gilt',sh,5)
  shell((s*14,-5,1),[(0,7,14,-2),(5,7.8,15,-3),(12,6,9,2)],'Iron',ft)
 if knight:
  # Tall kite shield fixed to left forearm, fluted face with solar boss.
  x=34;y=-12
  pts=[(x-16,y,114),(x,y-3,122),(x+16,y,114),(x+15,y,88),(x,y-2,62),(x-15,y,88)]
  g.panel(pts,'Iron','ForearmL',4)
  for a,b in zip(pts,pts[1:]+pts[:1]):g.beam(a,b,1.7,1.7,'Gilt','ForearmL',5)
  for v in ((x-12,y-1,109),(x+12,y-1,109),(x,y-3,67)):g.beam((x,y-6,100),v,2,1,'Bronze','ForearmL')
  g.beam((x,y-3,100),(x,y-9,100),6,2,'Gilt','ForearmL')
 sword(g,-31,-5,82,knight,'HandR')
 return g
for name,knight in [('Hero',False),('Knight',True)]:
 ob=figure(knight).object(name); ob.parent=rig; mod=ob.modifiers.new('Rig','ARMATURE');mod.object=rig
 export('SK_'+name,[ob,rig]); bpy.data.objects.remove(ob,do_unlink=True)
g=Geometry();sword(g,0,0,0);ob=g.object('FallenBlade');export('SM_FallenBlade',[ob]);bpy.data.objects.remove(ob,do_unlink=True)
# Rotations use model-space axes in the rest pose; the armature supplies parent-relative motion.
def pose(**kw):return kw
idle=pose(UpperArmR=(-12,-9,-6),ForearmR=(-31,0,8),UpperArmL=(4,8,0),ForearmL=(-16,0,0),ThighR=(-5,0,0),ThighL=(5,0,0))
def keyframe(frame,angles):
 for b in rig.pose.bones:
  e=angles.get(b.name,(0,0,0)); basis=arm.bones[b.name].matrix_local.to_quaternion()
  b.rotation_mode='QUATERNION'; rotation=basis.inverted()@Euler(tuple(math.radians(v) for v in e)).to_quaternion()@basis
  rotation.make_compatible(b.rotation_quaternion); b.rotation_quaternion=rotation
  if b.name=='Pelvis':
   b.location=basis.inverted()@Vector((0,0,angles.get('hip_height',0)))
   b.keyframe_insert(data_path='location',frame=frame)
  b.keyframe_insert(data_path='rotation_quaternion',frame=frame)
def clip(name,duration,frames):
 action=bpy.data.actions.new(name);rig.animation_data_create();rig.animation_data.action=action
 end=round(duration*30);scene.frame_start=1;scene.frame_end=end+1
 for t,p in frames:keyframe(1+round(t*end),{**idle,**p})
 scene.frame_set(1);export('AN_'+name,[rig],True)
def walk(a):
 return pose(ThighR=(-a,0,0),ThighL=(a,0,0),ShinR=(max(0,a)*.9,0,0),ShinL=(max(0,-a)*.9,0,0),UpperArmL=(-a*.7,6,0),UpperArmR=(a*.45-10,-9,0),Chest=(0,2,a*.12))
clip('Idle',2,[(0,{}),(.5,pose(Chest=(-2,0,2),Head=(1,-1,-2),ForearmR=(-34,0,8))),(1,{})])
clip('Walk',.84,[(0,walk(34)),(.25,walk(0)),(.5,walk(-34)),(.75,walk(0)),(1,walk(34))])
clip('Run',.60,[(0,walk(56)),(.25,walk(0)),(.5,walk(-56)),(.75,walk(0)),(1,walk(56))])
wind=pose(Chest=(-5,-4,-32),UpperArmR=(-107,-32,-25),ForearmR=(-50,0,-18),UpperArmL=(-12,20,12))
cut=pose(Chest=(13,5,54),UpperArmR=(-60,36,54),ForearmR=(-10,0,45),ThighL=(-16,0,0))
back=pose(Chest=(3,0,40),UpperArmR=(-45,28,62),ForearmR=(-31,0,40))
wide=pose(Chest=(9,-6,-43),UpperArmR=(-67,-48,-46),ForearmR=(-10,0,-48))
clip('Cut',.60,[(0,{}),(.24,wind),(.52,cut),(.68,cut),(1,{})])
clip('ReturnCut',.75,[(0,cut),(.24,back),(.53,wide),(.68,wide),(1,{})])
clip('SwordSweep',1.60,[(0,{}),(.29,wind),(.4,wind),(.50,cut),(.63,cut),(1,{})])
brace=pose(Chest=(-5,0,18),UpperArmR=(-62,-17,-15),ForearmR=(-71,0,55),UpperArmL=(-25,12,0),ThighR=(-11,0,0))
clip('Parry',.5,[(0,{}),(.12,brace),(.40,brace),(1,{})])
guard=pose(Chest=(-9,0,-19),UpperArmL=(-51,12,0),ForearmL=(-49,0,0))
push=pose(Chest=(17,0,-30),UpperArmL=(-78,-10,-12),ForearmL=(-9,0,0),ThighR=(-25,0,0))
clip('Bash',1.27,[(0,{}),(.31,guard),(.36,guard),(.45,push),(.6,push),(1,{})])
lift=pose(Chest=(-12,-10,-9),ThighL=(-77,0,0),ShinL=(92,0,0),UpperArmL=(-32,36,0),UpperArmR=(-22,-39,0))
land=pose(Chest=(24,12,5),ThighL=(-25,0,0),ShinL=(31,0,0),ThighR=(-17,0,0),ShinR=(27,0,0))
clip('Stomp',2.05,[(0,{}),(.34,lift),(.43,lift),(.51,land),(.72,land),(1,{})])
tuck=pose(Chest=(40,0,0),Head=(23,0,0),ThighR=(-84,0,0),ThighL=(-72,0,0),ShinR=(96,0,0),ShinL=(99,0,0),UpperArmR=(-61,0,0),UpperArmL=(-71,0,0))
# Pelvis rotation keeps the roll in place while actor movement supplies travel.
clip('Evade',.48,[(0,{}),(.18,{**tuck,'Pelvis':(40,0,0),'hip_height':-28}),(.36,{**tuck,'Pelvis':(118,0,0),'hip_height':-19}),
 (.57,{**tuck,'Pelvis':(209,0,0),'hip_height':-15}),(.78,{**tuck,'Pelvis':(307,0,0),'hip_height':-27}),(1,{'Pelvis':(360,0,0)})])
recoil=pose(Chest=(-28,-17,-14),Head=(-16,0,9),UpperArmL=(12,40,0),UpperArmR=(20,-49,0),ThighR=(-23,0,0),ShinR=(36,0,0))
clip('Stagger',1,[(0,{}),(.16,recoil),(.49,recoil),(1,{})])
fall=pose(Chest=(24,-13,-10),Head=(24,0,0),UpperArmL=(-24,43,0),UpperArmR=(-31,-37,0),ThighL=(-37,0,0),ShinL=(51,0,0))
clip('Death',1.25,[(0,{}),(.22,recoil),(.45,{**fall,'Pelvis':(-18,36,-5),'hip_height':-37}),(.79,{**fall,'Pelvis':(-26,87,-9),'hip_height':-71}),(1,{**fall,'Pelvis':(-25,83,-9),'hip_height':-72})])
charge=pose(Pelvis=(2,-6,-9),Chest=(20,-8,-41),Head=(-10,0,26),UpperArmR=(16,-30,-47),ForearmR=(-38,0,-29),
 UpperArmL=(-30,14,25),ForearmL=(-42,0,4),ThighL=(-32,0,0),ShinL=(41,0,0),ThighR=(11,0,0),hip_height=-10)
rise=pose(Pelvis=(0,0,24),Chest=(-12,9,43),Head=(5,-11,-25),UpperArmR=(-128,21,59),ForearmR=(-32,-12,39),
 UpperArmL=(7,23,4),ForearmL=(-15,0,0),ThighL=(-18,0,0),ShinL=(26,0,0))
clip('OathCut',.85,[(0,{}),(.21,charge),(.32,charge),(.43,pose(Chest=(15,0,8),UpperArmR=(-52,-14,-8),ForearmR=(-34,0,3),ThighL=(-35,0,0),ShinL=(23,0,0))),(.57,rise),(.72,rise),(1,{})])
