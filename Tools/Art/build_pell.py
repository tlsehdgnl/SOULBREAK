"""Build a lashed oak practice pell with an independently moving leather targe.

Run in Blender background mode. Units are centimeters and the target pivot is
88 cm above the fixed stand, matching ASBTrainingDummy.
"""
from pathlib import Path
from math import sin, cos, pi
import random
from hashlib import sha256
from urllib.request import urlopen
import bpy
from mathutils import Vector

out = Path(__file__).resolve().parents[2] / 'Saved/SBArmory'
out.mkdir(parents=True, exist_ok=True)
# Scans by Rob Tuytel, distributed by Poly Haven under CC0. Source images are
# needed only when rebuilding the Unreal materials from scratch.
scans = [
    ('AshColor', 'rough_wood', 'diff', 'abc46d8e3163d911220f4ec3a4043b68d2b0c6d750513f80871211acfefb2a98'),
    ('AshNormal', 'rough_wood', 'nor_dx', 'f917fe96a4d4fd314b2a1bb335ab49cfadca0185c1f5b5f9c75a0ad487c0b033'),
    ('AshRough', 'rough_wood', 'rough', '4e9ea9962a7e8b69057937e6723c4b0134b949c1ee5cdb5f3687a54113027b09'),
    ('HideColor', 'brown_leather', 'albedo', '7e9e1d6566d1fd91d4ceb4966c4820361e85d53a7a828b6bab3b2a093a876cd1'),
    ('HideNormal', 'brown_leather', 'nor_dx', '4262b981d5485419908bca32bf9e4e7063e3f7f0f4206f80cd2a6ebaf79fc845'),
    ('HideRough', 'brown_leather', 'rough', 'f9739ef2da2e3d17b9ec253f5042f61b10dc10f3ae28f6cf6491650d3d1b0ca3'),
]
for key, asset, channel, digest in scans:
    path=out/f'T_Pell{key}.jpg'
    if path.is_file() and sha256(path.read_bytes()).hexdigest()==digest:
        continue
    url=f'https://dl.polyhaven.org/file/ph-assets/Textures/jpg/1k/{asset}/{asset}_{channel}_1k.jpg'
    with urlopen(url,timeout=45) as response:
        data=response.read()
    if sha256(data).hexdigest()!=digest:
        raise ValueError(f'Unexpected image contents for {asset}/{channel}')
    path.write_bytes(data)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system = 'METRIC'
bpy.context.scene.unit_settings.scale_length = .01
rng = random.Random(747)
palette = {name: bpy.data.materials.new(name) for name in ('Ash','Hide','Iron','Bronze','Leather','Ivory')}


class Mesh:
    def __init__(self):
        self.verts = []
        self.faces = []
        self.materials = []
        self.smooth = []

    def surface(self, verts, faces, mat, smooth=False):
        at = len(self.verts)
        self.verts.extend(verts)
        self.faces.extend([tuple(at+i for i in face) for face in faces])
        self.materials.extend([mat]*len(faces))
        self.smooth.extend([smooth]*len(faces))

    def tube(self, path, radii, mat, sides=8, smooth=True):
        points = list(map(Vector,path))
        vs = []
        for j,p in enumerate(points):
            tangent = (points[min(len(points)-1,j+1)]-points[max(0,j-1)]).normalized()
            ref = Vector((1,0,0)) if abs(tangent.x)<.85 else Vector((0,1,0))
            a = tangent.cross(ref).normalized()
            b = tangent.cross(a)
            radius = radii[j] if isinstance(radii,list) else radii
            for i in range(sides):
                angle = i*2*pi/sides
                vs.append(p+radius*(a*cos(angle)+b*sin(angle)))
        faces = [tuple(reversed(range(sides)))]
        for j in range(len(points)-1):
            for i in range(sides):
                n=(i+1)%sides
                faces.append((j*sides+i,j*sides+n,(j+1)*sides+n,(j+1)*sides+i))
        faces.append(tuple(range(len(vs)-sides,len(vs))))
        self.surface(vs,faces,mat,smooth)

    def binding(self, z, radius, turns):
        # Compressed three-strand winding, with a small twist still visible at the camera.
        for strand in range(3):
            path=[]
            steps=turns*66
            for i in range(steps+1):
                angle=2*pi*i/66
                twist=8*angle+strand*2*pi/3
                dist=radius+.49*cos(twist)
                path.append((dist*cos(angle),dist*sin(angle),z+1.84*i/66+.49*sin(twist)))
            self.tube(path,.60,'Leather',5)

    def export(self, name):
        mesh=bpy.data.meshes.new(name)
        mesh.from_pydata(self.verts,[],self.faces)
        mesh.update()
        obj=bpy.data.objects.new(name,mesh)
        bpy.context.scene.collection.objects.link(obj)
        slots=list(dict.fromkeys(self.materials))
        for slot in slots:mesh.materials.append(palette[slot])
        layer=mesh.uv_layers.new(name='Surface')
        for face,mat,smooth in zip(mesh.polygons,self.materials,self.smooth):
            face.material_index=slots.index(mat)
            face.use_smooth=smooth
            axis=max(range(3),key=lambda i:abs(face.normal[i]))
            axes=((1,2),(0,2),(0,1))[axis]
            for li in face.loop_indices:
                co=mesh.vertices[mesh.loops[li].vertex_index].co
                layer.data[li].uv=(co[axes[0]]/45,co[axes[1]]/55)
        bpy.ops.object.select_all(action='DESELECT')
        bpy.context.view_layer.objects.active=obj
        obj.select_set(True)
        bpy.ops.export_scene.fbx(filepath=str(out/(name+'.fbx')),use_selection=True,
            axis_forward='-Y',axis_up='Z',apply_unit_scale=True,mesh_smooth_type='FACE',bake_anim=False)
        print(name,len(mesh.vertices),len(mesh.polygons))


base=Mesh()
base.tube([(0,0,0),(.5,-.3,6),(0,.3,43),(-1,.2,85),(0,0,99)],
          [11.6,11.9,10.4,9.7,9.1],'Ash',14,False)
for i in range(3):
    a=i*2*pi/3+.13
    d=Vector((cos(a),sin(a),0))
    base.tube([d*36+Vector((0,0,4)),d*32+Vector((0,0,6)),d*9+Vector((0,0,39))],
              [5.8,6.2,5.8],'Ash',7,False)
base.binding(9,11.1,4)
base.binding(61,10.2,4)
base.export('SM_PellStand')

target=Mesh()
target.tube([(0,0,0),(0,0,39),(-1,0,66),(1,.2,85),(1,0,90)],
            [9.8,10.2,8.1,7.4,6.8],'Ash',15,False)
target.tube([(-49,0,44),(-33,0,46),(0,0,45),(35,0,42),(48,0,43)],
            [3.9,4.2,5.5,4.4,3.6],'Ash',10,False)
target.binding(4,10,4)
target.binding(72,8.1,5)

# A board core with a steamed rim and a dished, scarred hide facing.
# Faces point towards aisle center and entry. Rivets are separate domed studs.
levels=[(1,-13.2),(10,-12.8),(20,-10.8),(28,-8.6),(30,-7.0),(30.3,-4.0),(29.3,-2.8)]
n=72
verts=[]
for ix,(r,y) in enumerate(levels):
    for i in range(n):
        a=2*pi*i/n
        scallop=.36*sin(a*5)+.19*sin(a*9+.2)
        verts.append((cos(a)*(r+scallop),y-3.1+(.21*sin(9*a+ix)),43+sin(a)*(r+scallop)*1.09))
# Reuse vertices within each ring for continuous curved specular highlights.
faces=[]
for j in range(len(levels)-1):
    for i in range(n):
        k=(i+1)%n
        faces.append((j*n+i,(j+1)*n+i,(j+1)*n+k,j*n+k))
target.surface(verts,faces,'Hide',True)
target.surface(verts[-n:], [tuple(reversed(range(n)))], 'Ash')
for i in range(34):
    a=2*pi*i/34
    x,z=27.1*cos(a),43+29.55*sin(a)
    target.tube([(x,-11.4,z),(x,-12.45,z),(x,-12.65,z)],[.94,.76,.26],'Bronze',10)
for band in (8.8,23.7):
    # Needle holes and hand-stitched broken lines, with seams subtly off-center.
    for i in range(round(band*1.8)):
        a=2*pi*i/round(band*1.8)
        b=a+.14/band*8
        y=-15.95+(band/29)**2*5.
        target.tube([(band*cos(a),y,43+1.09*band*sin(a)),
                     (band*cos(b),y-.22,43+1.09*band*sin(b))],.28,'Ivory',5)
for i in range(25):
    z=rng.uniform(23,63)
    x=rng.uniform(-15,15)
    length=rng.uniform(1.3,7.4)
    dx,dz=rng.uniform(-2,2),length
    def scar_y(x,z):return -16.47+((x*x+((z-43)/1.09)**2)/840)*5
    target.surface([(x,scar_y(x,z)-.18,z),(x+.36,scar_y(x,z)-.18,z+.15),
                    (x+dx,scar_y(x+dx,z+dz)-.14,z+dz)],[(0,1,2)],'Leather')
target.tube([(0,-15,43),(0,-16.3,43),(0,-19.5,43),(0,-20.1,43)],
            [5.7,5.8,3.7,1.1],'Iron',32)
for i in range(7):
    a=2*pi*i/7
    target.tube([(6.75*cos(a),-15.5,43+6.75*sin(a)),(6.75*cos(a),-16.6,43+6.75*sin(a))],
                [.68,.45],'Bronze',8)
# Spare coiled lash and frayed ends make the back readable when circling it.
for s in (-1,1):
    target.tube([(s*9,3,58),(s*12,4,51),(s*11,6,43),(s*8,5,37)],1.25,'Leather')
target.export('SM_LeatherTarge')
