"""Forge the original Pilgrim and Warden, their detachable gear and their shared performances."""
import bpy, json
from mathutils import Vector
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import forged_detail as detail
from surface_marks import bake_textures
from math import sin, cos, pi
out = Path(__file__).resolve().parents[2] / 'Saved/SBArt'
out.mkdir(parents=True, exist_ok=True)
bake_textures(out)
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
 'StormSteel':(.115,.174,.224,.68,.34,0),'Mail':(.04,.064,.083,.62,.53,0),
 'SeaSilk':(.018,.125,.17,.06,.69,0),'Lining':(.65,.51,.28,.18,.53,0),
 'Velvet':(.115,.012,.037,0,.85,0),'Patina':(.045,.11,.115,.53,.57,0),
 'Glass':(.019,.27,.36,.15,.31,1.4),'GlassGold':(.83,.32,.045,.1,.4,1.5),'GlassRed':(.40,.04,.094,.2,.5,1.0)}
# Charcoal iron, desaturated verdigris wool, oxblood, rubbed edges and old brass.
palette.update({
 'Iron':(.12,.136,.151,.87,.34,0),'Steel':(.34,.37,.38,.86,.26,0),
 'StormSteel':(.19,.213,.225,.87,.29,0),'Edge':(.57,.59,.60,.92,.2,0),
 'Leather':(.103,.061,.042,0,.59,0),'Mail':(.145,.148,.144,.79,.51,0),
 'Bronze':(.34,.218,.110,.77,.38,0),'Gilt':(.48,.329,.15,.80,.33,0),
 'Wine':(.129,.049,.053,0,.79,0),'Velvet':(.104,.033,.038,0,.80,0),
 'DeepBlue':(.039,.068,.073,0,.74,0),'SeaSilk':(.073,.135,.138,0,.77,0),
 'Lining':(.30,.237,.157,.09,.62,0),'Patina':(.095,.15,.148,.55,.47,0),
 'Obsidian':(.014,.016,.020,.18,.57,0)})
(out/'palette.json').write_text(json.dumps(palette))
mats={}
for k,c in palette.items():
 m=bpy.data.materials.new(k); m.diffuse_color=(*c[:3],1); mats[k]=m
class Geometry:
 def __init__(self):
  self.v=[]; self.f=[]; self.m=[]; self.groups={}; self.weighted={}; self.smooth=[]; self.uv={}
 def surface(self, verts, faces, mat, bone=None, smooth=False):
  start=len(self.v); self.v.extend(verts)
  self.f.extend([tuple(start+i for i in f) for f in faces]); self.m.extend([mat]*len(faces))
  self.smooth.extend([smooth]*len(faces))
  if bone: self.groups.setdefault(bone,[]).extend(range(start,len(self.v)))
 def object(self,name):
  mesh=bpy.data.meshes.new(name);mesh.from_pydata(self.v,[],self.f);mesh.update();ob=bpy.data.objects.new(name,mesh);scene.collection.objects.link(ob)
  keys=list(dict.fromkeys(self.m))
  for k in keys: mesh.materials.append(mats[k])
  uv=mesh.uv_layers.new(name='UVMap')
  for p,m,smooth in zip(mesh.polygons,self.m,self.smooth):
   p.use_smooth=smooth
   p.material_index=keys.index(m)
   axis=max(range(3),key=lambda i: abs(p.normal[i]))
   for loop in p.loop_indices:
    co=mesh.vertices[mesh.loops[loop].vertex_index].co
    uv.data[loop].uv=self.uv.get(mesh.loops[loop].vertex_index,(co[(axis+1)%3]/48,co[(axis+2)%3]/48))
  for b,indices in self.groups.items():ob.vertex_groups.new(name=b).add(indices,1,'REPLACE')
  for i,weights in self.weighted.items():
   for b,w in weights.items():
    if w>0: (ob.vertex_groups.get(b) or ob.vertex_groups.new(name=b)).add([i],w,'REPLACE')
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
# Append accessory joints after the original rig; both figures share the bind pose.
bones.update({
 'ShieldPlate':((32,-15,101),(32,-15,111),'ForearmL'),
 'KneePlateL':((13,-9,48),(13,-9,56),'ShinL'),
 'CloakTop':((0,12,144),(0,15,120),'Chest'),
 'CloakMid':((0,15,120),(0,20,86),'CloakTop'),
 'CloakHem':((0,20,86),(0,25,54),'CloakMid')})
arm=bpy.data.armatures.new('PilgrimRig'); rig=bpy.data.objects.new('Armature',arm);scene.collection.objects.link(rig)
bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
for name,(a,b,parent) in bones.items():
 e=arm.edit_bones.new(name);e.head=a;e.tail=b
 if parent:e.parent=arm.edit_bones[parent]
bpy.ops.object.mode_set(mode='OBJECT')
def sword(g,x,y,z,knight=True,bind=None):
 # Single connected diamond section. Broad forte, shallow fuller, distal taper.
 def pos(w,t,h):return (x+w,y-t,z+.2*t+h)
 width=3.85 if knight else 2.95
 detail.tube(g,[pos(0,t,0) for t in (-11.5,-9,-3,3,9)],lambda u:1.60+.32*sin(pi*u),'Leather',bind,16)
 # Helical wire on the leather-wrapped grip.
 detail.tube(g,[pos(1.82*cos(i*.48),-10.8+19.6*i/100,1.82*sin(i*.48)) for i in range(101)],.25,'Bronze',bind)
 for s in (-1,1):
  detail.tube(g,[pos(s*w,t,h) for w,t,h in [(0,9.2,0),(4,9.7,.5),(9,10.6,.7),(13.6,13,.25),(14.5,14.4,-.3)]],
              lambda u:1.65-1.01*u,'Bronze' if knight else 'Steel',bind,12)
  detail.stud(g,*pos(s*14.2,14.0,-.15),1.03,'Bronze',bind)
 stations=[(10,width*.93,1.65),(14,width,1.7),(24,width*.88,1.49),(65,width*.63,1.14),(87,width*.43,.73),(98,.09,.10)]
 for s in (-1,1):
  for zside in (-1,1):
   for (a,w,h),(b,v,q) in zip(stations,stations[1:]):
    lane=[(0,h),(.13*w,h*.67),(.28*w,h*.77),(.83*w,.29*h),(w,0)]
    nextlane=[(0,q),(.13*v,q*.67),(.28*v,q*.77),(.83*v,.29*q),(v,0)]
    for n in range(4):
     verts=[pos(s*lane[n][0],a,zside*lane[n][1]),pos(s*lane[n+1][0],a,zside*lane[n+1][1]),
            pos(s*nextlane[n+1][0],b,zside*nextlane[n+1][1]),pos(s*nextlane[n][0],b,zside*nextlane[n][1])]
     g.surface(verts,[((3,2,1,0) if s*zside>0 else (0,1,2,3))],'Edge' if n==3 else 'Iron' if n==1 else 'Steel',bind)
 detail.stud(g,*pos(0,-13.7,0),3.12,'Bronze',bind)
 for s in (-1,1):
  detail.stud(g,*pos(0,-13.7,s*2.3),1.25,'Patina',bind)
for name,knight in [('Hero',False),('Knight',True)]:
 g=detail.figure(Geometry(),knight)
 sword(g,-31,-5,82,knight,'HandR')
 ob=g.object(name);ob.parent=rig
 mod=ob.modifiers.new('Rig','ARMATURE');mod.object=rig
 export('SK_'+name,[ob,rig])
 bpy.data.objects.remove(ob,do_unlink=True)
def static_piece(name,g,pivot):
 g.groups.clear();g.weighted.clear()
 g.v=[Vector(p)-Vector(pivot) for p in g.v]
 ob=g.object(name)
 export('SM_'+name,[ob]);bpy.data.objects.remove(ob,do_unlink=True)
g=Geometry();sword(g,0,0,0);static_piece('FallenBlade',g,(0,0,0))
g=Geometry();detail.shield(g);static_piece('FallenShield',g,bones['ShieldPlate'][0])
g=Geometry();detail.poleyn(g,1,'KneePlateL');static_piece('FallenKnee',g,bones['KneePlateL'][0])
from choreography import Performance
Performance(arm,rig,scene,export).author_all()
