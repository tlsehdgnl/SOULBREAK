"""Bespoke garment patterns and armour plates in the rig's centimetre coordinates.

The shell rows are cross-sections through a body. The open patches are fitted metal,
leather or cut cloth, with a rolled edge or a turned hem where the edge is visible.
"""
from math import sin, cos, pi, exp, sqrt
from mathutils import Vector

TAU = 2*pi


def patch(g, point, nu, nv, mat, bone, weight=None, flip=False, repeat=(1, 1)):
    verts = [point(i/nu, j/nv) for j in range(nv+1) for i in range(nu+1)]
    faces = []
    for j in range(nv):
        for i in range(nu):
            a=j*(nu+1)+i
            q=(a,a+1,a+nu+2,a+nu+1)
            faces.append(q[::-1] if flip else q)
    start=len(g.v)
    g.surface(verts, faces, mat, bone, True)
    for j in range(nv+1):
        for i in range(nu+1):
            v=start+j*(nu+1)+i
            g.uv[v]=(repeat[0]*i/nu,repeat[1]*j/nv)
            if weight:
                g.weighted[v]=weight(i/nu,j/nv)
    return point


def shell(g, rows, mat, bone, center=(0,0), n=40, ripple=None):
    # rows rise from bottom to top, storing height, width, depth, and optional fore-aft offset
    vs=[]
    for j,(z,rx,ry,dy) in enumerate(rows):
        for i in range(n):
            a=TAU*i/n
            d=ripple(a,j/(len(rows)-1)) if ripple else 0
            vs.append((center[0]+(rx+d)*cos(a),center[1]+dy+(ry+d)*sin(a),z))
    faces=[(j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i)
           for j in range(len(rows)-1) for i in range(n)]
    g.surface(vs,faces,mat,bone,True)
    # Separate cap vertices preserve the crease at the lip.
    g.surface(vs[:n],[tuple(reversed(range(n)))],mat,bone)
    g.surface(vs[-n:],[tuple(range(n))],mat,bone)


def tube(g, points, r, mat, bone, n=8):
    """Sweep a circular wire on a parallel-transport frame through all its bends."""
    p=list(map(Vector,points))
    v=[]; saved=None
    for i,pt in enumerate(p):
        d=(p[min(i+1,len(p)-1)]-p[max(0,i-1)]).normalized()
        if saved is None:
            saved=d.cross(Vector((0,0,1)) if abs(d.z)<.9 else Vector((0,1,0))).normalized()
        norm=(saved-d*d.dot(saved)).normalized()
        other=d.cross(norm);saved=norm
        rr=r(i/(len(p)-1)) if callable(r) else r
        v.extend(pt+rr*(cos(TAU*k/n)*norm+sin(TAU*k/n)*other) for k in range(n))
    faces=[(j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i)
           for j in range(len(p)-1) for i in range(n)]
    g.surface(v,faces,mat,bone,True)


def stud(g,x,y,z,r,mat,bone):
    shell(g,[(z-r*.62,r*.35,r*.35,0),(z-r*.44,r*.78,r*.78,0),
             (z,r,r,0),(z+r*.44,r*.78,r*.78,0),(z+r*.64,r*.27,r*.27,0)],mat,bone,(x,y),12)


def border(g,p,r,mat,bone):
    for edge in (lambda t:p(t,0),lambda t:p(t,1),lambda t:p(0,t),lambda t:p(1,t)):
        tube(g,[edge(i/18) for i in range(19)],r,mat,bone)


def cloth_fold(a,t):
    return .69*cos(13*a+1.6*t)+.42*sin(9*a-2*t)+.23*sin(17*a+.8*t)


def body(g,k):
    mail='Mail'
    # Linen aketon and mail shirt remain under all removable plate.
    shell(g,[(86,15,10,0),(92,18.5,12,0),(99,16.2,11,0),(106,16,11.6,0)],
          'Leather','Pelvis',ripple=cloth_fold)
    shell(g,[(101,15.4,11.2,0),(108,16,11.9,0),(118,19.3,13.3,-.5),(129,22,15,-.5),
             (138,23.1,13.8,0),(144,18.4,10.7,.7),(149,8.3,7.7,0)],
          mail,'Chest',ripple=lambda a,t:.40*cloth_fold(a,t))
    # Deeply formed, single-piece cuirass: slight medial ridge, scooped armscyes,
    # belly curved away below the floating ribs. No artificial crown on the shoulders.
    def breast(u,v):
        a=(u-.5)*TAU
        c=max(0,cos(a))
        waist=16.6+7.8*sin(v*pi*.70)
        x=waist*sin(a)
        ry=12.0+4.5*sin(pi*v*.83)
        y=-cos(a)*ry-1.7*c**8*sin(v*pi)+.55*v
        z=108.5+32*v+3.4*abs(sin(a))**2*(1-v)**2+4*c*v**3-7*abs(sin(a))**6*v**3
        return x,y,z
    patch(g,breast,64,20,'Iron' if k else 'Leather','Chest',repeat=(3,1))
    for v,r in [(0,.85),(1,.7)]:
        tube(g,[breast(i/80,v) for i in range(81)],r,'Bronze' if k else 'Steel','Chest')
    for layer in range(3):
        z=101+layer*3.4; r=17.6+layer*.45
        shell(g,[(z,r,12.5,0),(z+.45,r+.55,13,0),(z+1.4,r+.65,13.2,0),(z+4.4,r-.4,12.5,0)],
              'Iron' if k else 'StormSteel','Chest')
    for s in (-1,1):
        for i in range(3 if k else 0):
            u0=.5+s*(.027+i*.021); ut=.5+s*(.16+i*.025)
            pts=[]
            for j in range(22):
                t=j/21;u=u0+(ut-u0)*t*t
                x,y,z=breast(u,.06+t*.82)
                pts.append((x,y-.36,z))
            tube(g,pts,lambda t:.22+.4*sin(pi*t),'Steel','Chest')
    if not k:
        # Brigandine rivets follow the overlapped plates riveted to the inside of
        # the buff-leather jacket. Small groups form the traditional three-stud pattern.
        for side in (-1,1):
            for row in range(5):
                for col in range(3):
                    u=.5+side*(.035+col*.052+(row%2)*.013)
                    v=.13+row*.137
                    for du,dv in ((-.005,.01),(.005,.01),(0,-.010)):
                        x,y,z=breast(u+du,v+dv)
                        stud(g,x,y-.30,z,.34,'Bronze','Chest')
        for side in (-1,1):
            for i in range(3):
                def welt(u,v):
                    uu=.5+side*(.018+.214*u)
                    vv=.18+i*.24+(v-.5)*.022+.045*u
                    x,y,z=breast(uu,vv)
                    return x,y-.27,z
                patch(g,welt,16,2,'Obsidian','Chest')
    # Gorget sits inside the shoulders; separate lower edge visible from behind.
    shell(g,[(140,17.5,12.5,1),(141.4,18,13,1),(145.6,10.3,9.4,0),
             (148.8,9.2,8,0),(149.5,9.6,8.4,0)],'Iron','Chest')
    for z in (146.1,148.2):
        shell(g,[(z,9.9,8.6,0),(z+.6,10.1,8.8,0)],'Bronze','Chest')
    shell(g,[(96.3,18.8,13.2,0),(97,19.3,13.8,0),(102,19.1,13.6,0),(102.6,18.5,13.2,0)],
          'Leather','Pelvis')
    # Iron buckle, including the spindle and tongue.
    shp=[(-3,-14.1,97),(3,-14.1,97),(3.8,-14.2,98),(3.8,-14.2,101.5),
         (3,-14.1,102),(-3,-14.1,102),(-3.7,-14.2,101.5),(-3.7,-14.2,98),(-3,-14.1,97)]
    tube(g,shp,.59,'Bronze','Pelvis')
    tube(g,[(0,-14.7,97),(.4,-15,100),(.7,-14.3,101)],.36,'Steel','Pelvis')
    # Armored skirt is slashed at front and back for riding.
    for s,name in [(-1,'R'),(1,'L')]:
        bone='Thigh'+name
        def skirt(u,v):
            a=(u-.5)*2.92
            wid=16.7+4*v
            x=s*(.7+wid*cos(a))
            y=-(14.2+4.3*v)*sin(a)
            fold=1.5*sin(5*a-1.3*v)*v
            return x+s*fold,y-.75*fold,97-v*(27+7*cos(2*a)+1.5*sin(7*a))
        patch(g,skirt,29,13,'Velvet' if k else 'DeepBlue',bone,flip=s<0,repeat=(1.7,1))
        tube(g,[skirt(i/36,1) for i in range(37)],.47,'Wine' if k else 'SeaSilk',bone)
        for i in range(4 if k else 2):
            def tasset(u,v):
                a=(u-.5)*1.9-.43
                radius=17.7+1.1*i+.7*v
                return (s*radius*cos(a),radius*sin(a),
                        96.5-i*4.4-5.8*v-2*cos(a)*v)
            patch(g,tasset,18,4,'Iron' if k else 'StormSteel',bone,flip=s>0)
            tube(g,[tasset(j/22,1) for j in range(23)],.34,'Steel',bone)
            for u in (.14,.86):
                x,y,z=tasset(u,.28);stud(g,x,y,z,.64,'Bronze',bone)


def upper_limb(g,k,s,name):
    a,f,h='UpperArm'+name,'Forearm'+name,'Hand'+name
    shell(g,[(110.5,5.6,5.8,-.4),(115,7.1,7,-.5),(125,8.3,7.8,-.4),(135,8.7,8,.6),(141,6,6.8,0)],
          'Mail',a,(s*27,0),32,lambda a,t:.4*cloth_fold(a,t))
    # Three articulated lames tucked under a domed spaulder. Rolled hems and the
    # slightly swept-back flange catch grazing light at gameplay camera distances.
    for layer in range(3 if k or s<0 else 1):
        z=124.7+layer*3.2; w=(9.3 if not k else (13.8 if s<0 else 11.3))+layer*.68
        shell(g,[(z,w*.89,w*.84,0),(z+.5,w,w*.94,0),(z+1.5,w*1.015,w*.96,0),
                 (z+4.7,w*.94,w*.88,.2)],'Iron' if k else 'StormSteel',a,(s*(27.6-.5*layer),0))
    bigger=(k and s<0)
    def spaulder(u,v):
        az=TAU*u
        theta=.065+v*(1.61+.18*cos(az)*s)
        rx=(16.6 if bigger else 13.0 if k else 11.5)
        shift=(.7 if not bigger else 1.9)*cos(6*az)*sin(theta)**3
        return (s*25.8+(rx+shift)*cos(az)*sin(theta),
                .4+(rx*.91+shift)*sin(az)*sin(theta),(134 if k else 135)+(14 if bigger else 11.6)*cos(theta))
    patch(g,spaulder,48,13,'Iron' if k else 'StormSteel' if s<0 else 'Leather',a,flip=True,repeat=(2,1))
    tube(g,[spaulder(i/64,1) for i in range(65)],.83,'Bronze' if bigger else 'Steel',a)
    for u in (.09,.23,.39,.63,.81,.94):
        x,y,z=spaulder(u,.89);stud(g,x,y,z,.72,'Bronze',a)
    if bigger:
        def crack(u,v):
            x,y,z=spaulder(u,v)
            return (x-.25,y-.4,z+.18)
        tube(g,[crack(u,v) for u,v in [(.70,.34),(.69,.51),(.72,.62),(.675,.72),(.68,.86),(.64,.99)]],
             .68,'Ember',a)
        for j in range(3):
            tube(g,[spaulder(.57+j*.11,i/24) for i in range(3,25)],lambda t:.28+.39*sin(pi*t),'Bronze',a)
    shell(g,[(84,4.1,4.1,-4.7),(89,4.6,4.6,-4.2),(98,5.9,5.4,-3.1),
             (105.5,6.4,5.8,-1.9),(112,5.4,5.3,-.5)],'Leather',f,(s*30,0),32)
    def vam(u,v):
        az=(u-.5)*4.75+.7*s
        rx=4.8+2*v+.45*sin(pi*v)
        return (s*30+rx*sin(az),-4.35+3.3*v-rx*cos(az),
                89+19*v+2.2*cos(az)*v-1.6*cos(az)*(1-v))
    patch(g,vam,24,8,'Iron' if k else 'StormSteel',f)
    tube(g,[vam(i/25,1) for i in range(26)],.48,'Steel',f)
    # Natural padded elbow and leather-backed metacarpal with separated armoured fingers.
    shell(g,[(107,5.7,5.3,-1.2),(109.6,6.9,6.2,-.3),(113.5,6.7,6.1,0),
             (115.1,5.9,5.3,0)],'Iron',f,(s*30,0),30)
    shell(g,[(79.4,3.8,3.8,-.9),(81.3,5,4.6,-.5),(84.5,5.5,4.9,0),
             (87.2,4.7,4.1,0),(89.2,4,3.9,.1)],'Leather',h,(s*31,-5),28)
    for i in range(4):
        x=s*(27.5+i*2.03);z=82.5-abs(i-1.5)*.45
        pts=[(x,-6,z),(x,-8.6,z-.7),(x,-9.3,z-2.9),(x,-8.2,z-4.5),(x,-6.3,z-4.7)]
        tube(g,pts,lambda t:1.28-.37*t,'Leather',h)
        stud(g,x,-9,z-1.1,1.25,'Iron',h)
    tube(g,[(s*26.6,-6.5,85),(s*25.6,-8,83.2),(s*26.6,-9.8,81.4),(s*28.6,-10,80.5)],1.4,'Leather',h)


def poleyn(g,s,bone):
    # Outboard fan and centered rounded cop form one removable assembly.
    cx=s*13
    def cup(u,v):
        a=(u-.5)*3.85
        theta=.19+v*2.68
        return (cx+8.2*sin(a)*sin(theta),-4.7-(6.7+.6*cos(3*a))*cos(a)*sin(theta),48+6.6*cos(theta)+1.8*max(0,cos(a))**5*(1-v)**2)
    patch(g,cup,29,14,'StormSteel',bone,flip=True)
    if bone=='KneePlateL':
        # A pointed poleyn is carried over the joint by the two straps. The cracked
        # gilded ridge and separate wing mark its breakable silhouette.
        def ridge(u,v):
            width=4.7*(.18+sin(pi*v)**.85)
            q=2*u-1
            return (cx+q*width,-10.8-1.45*sin(pi*v)-1.10*(1-abs(q))+.40*q*q,
                    38.2+17.1*v+1.0*abs(q))
        patch(g,ridge,12,20,'Bronze',bone)
        tube(g,[ridge(.43,.89),ridge(.51,.71),ridge(.32,.60),ridge(.60,.49),ridge(.54,.25)],
             .29,'Ember',bone)
    for v in (.05,.95):
        tube(g,[cup(i/24,v) for i in range(25)],.52,'Bronze',bone)
    def fan(u,v):
        wid=1-.47*abs(2*v-1)
        return (s*(19.3+4.1*wid*sin(pi*u)), -6+9*u,46.7+(v-.5)*16*wid-2*u)
    patch(g,fan,14,14,'Iron',bone)
    border(g,fan,.38,'Bronze',bone)
    for t in (.15,.85):
        x,y,z=fan(.33,t);stud(g,x,y,z,.77,'Bronze',bone)


def lower_limb(g,k,s,name):
    th,sh,ft='Thigh'+name,'Shin'+name,'Foot'+name
    shell(g,[(46.1,5.9,6.1,-.2),(52,6.9,7,-.6),(62,8.1,7.9,0),
             (76,9.4,9.1,.4),(85,9.3,9.2,1.3),(90,6.7,6.9,1.5)],'Leather',th,(s*12.7,0),36,cloth_fold)
    def cuisse(u,v):
        a=(u-.5)*3.8
        r=7.3+2.5*v
        return (s*12.7+r*sin(a),-r*cos(a),52+28*v+3*cos(a)*v)
    patch(g,cuisse,26,10,'Iron' if k else 'StormSteel',th)
    tube(g,[cuisse(i/27,.03) for i in range(28)],.44,'Steel',th)
    shell(g,[(8,4.1,4.4,0),(16,4.4,4.7,0),(29,5.9,6.4,1.3),(37,6.8,6.9,1.1),
             (43,6.1,6.5,0),(49,5.6,6,0),(53,5.7,6,0)],'Leather',sh,(s*13.6,0),32,cloth_fold)
    def greave(u,v):
        a=(u-.5)*4.4
        r=4.65+2.25*sin(pi*v*.7)
        return (s*13.7+r*sin(a),-.3-r*cos(a)-.75*max(0,cos(a))**10,12.8+29*v+2.8*cos(a)*(1-v))
    patch(g,greave,27,12,'Iron' if k else 'StormSteel',sh)
    border(g,greave,.36,'Steel',sh)
    for z,r in ((19.1,5.4),(36.5,7.0),(46,6.3)):
        shell(g,[(z,r,r,0),(z+.6,r+.35,r+.32,0),(z+2.0,r,r+.15,0)],'Leather',sh,(s*13.6,0),30)
    poleyn(g,s,'KneePlateL' if k and s>0 else sh)
    for j in range(3):
        z=9.1+j*1.9
        shell(g,[(z,4.5,4.7,0),(z+.70,5.2,5.1,-.1),(z+1.5,4.65,4.6,0)],
              'Leather',sh,(s*13.8,0),28,lambda a,t:.27*cos(3*a+j))
    # Anatomical almond silhouette, broad metatarsals and a narrower heel.
    def shoe(u,v):
        a=TAU*u
        heel=max(0,sin(a))
        r=(1-.28*heel)
        profile=(.97 if v<.18 else 1-v**2.5*.58)
        return (s*14+6.3*cos(a)*r*profile,-5.5+(.65+.35*profile)*13.5*sin(a)+3.9*v*v,
                .8+v*(7.5+6*heel))
    patch(g,shoe,36,11,'Leather',ft)
    # The boot tongue and hose bridge the articulated ankle. Each vertex here
    # blends from the foot to the shin, so dorsiflexion cannot expose a gap.
    def ankle(u,v):
        a=TAU*u
        r=4.55-.6*v+.45*sin(pi*v)
        return (s*14+r*cos(a),-.5+(r+.45)*sin(a),5.0+13.6*v)
    patch(g,ankle,28,10,'Leather',None,lambda u,v:{ft:1-v,sh:v})
    sole=[(shoe(i/40,0)[0],shoe(i/40,0)[1],.53) for i in range(40)]
    g.surface(sole,[tuple(reversed(range(len(sole))))],'Leather',ft)
    for z in (0.1,1.2):
        tube(g,[(shoe(i/42,0)[0],shoe(i/42,0)[1],z+.45) for i in range(43)],.67,'Obsidian',ft)
    for j in range(4):
        y=-5.8-j*3.1; w=6.0-j*.55;h=7.8-j*.8
        def sab(u,v):
            a=(u-.5)*2.65
            return (s*14+w*sin(a),y-3.7*v-1.2*cos(a),2.2+(h-.6*v)*cos(a))
        patch(g,sab,17,4,'Iron',ft)
        tube(g,[sab(i/20,.96) for i in range(21)],.26,'Steel',ft)


def cloak(g,k):
    cloth='Velvet' if k else 'SeaSilk'
    # Diagonal half-circle cut on the pilgrim, split and heavier on the knight.
    # Nonparallel folds gather at the neck and open toward the wind-worn hem.
    def warp(u,v):
        q=2*u-1
        turn=q*(1.53-.39*v)
        w=(22.1 if k else 19.7)+(11 if k else 8)*v
        phase=pi*(q*(4.9+v*.6)+.58*sin(v*3.55)+q*q*.56)
        folds=(.8+2.45*v)*cos(phase)+.8*cos(phase*1.86+.85)
        y0=18.5+8.7*v+2.8*v*v
        x=w*sin(turn)+q*folds*.48+(1.8 if k else -4.1)*v*v
        y=y0*cos(turn)+5.1*v+folds*(.5+.5*cos(turn))
        length=(97-6*abs(q)+3.4*q) if k else (83-16*q-10*q*q)
        slit=11*exp(-((q-.18)/.041)**2) if k else 0
        # Little notches in the selvage never interrupt the continuous sheet above the hem.
        wear=sum(h*exp(-((q-c)/w0)**2) for c,w0,h in [(-.88,.034,4.1),(-.51,.022,2.9),(.68,.043,4.5)])
        z=146.6-7.3*abs(q)**1.6-v*length+v**8*(1.7*sin(phase)+wear+slit)
        return Vector((x,y,z))
    def weights(u,v):
        centers=(0,.34,.72,1)
        names=('Chest','CloakTop','CloakMid','CloakHem')
        for i in range(3):
            if v<=centers[i+1]:
                a=(v-centers[i])/(centers[i+1]-centers[i])
                return {names[i]:1-a,names[i+1]:a}
        return {names[-1]:1}
    patch(g,warp,76,35,cloth,None,weights,repeat=(2.2,3.2))
    def inset(u0,u1,v0,v1,mat,offset=.24):
        def uv(u,v):return (u0+(u1-u0)*u,v0+(v1-v0)*v)
        def pt(u,v):
            a,b=uv(u,v);return warp(a,b)+Vector((0,offset,0))
        patch(g,pt,max(3,round(abs(u1-u0)*76)),max(2,round(abs(v1-v0)*35)),mat,None,
              lambda u,v:weights(*uv(u,v)),repeat=(1,1))
    for a in (.019,.965):
        inset(a,a+.012,.014,.983,'Wine' if k else 'DeepBlue')
        inset(a+.017,a+.021,.035,.971,'Lining')
    inset(.01,.99,.953,.967,'Wine' if k else 'DeepBlue')
    inset(.045,.955,.94,.944,'Lining')
    # Worn hand-stitched sigil on the back, directly conforming to the curved cloth.
    def stitch(path,width,material):
        for (a,b),(c,d) in zip(path,path[1:]):
            length=max(.001,sqrt((c-a)**2+((d-b)*1.7)**2))
            nx,ny=-(d-b)*1.7/length*width,(c-a)/length*width*.62
            def uv(u,v):return (a+(c-a)*v+(u-.5)*nx,b+(d-b)*v+(u-.5)*ny)
            def pt(u,v):
                x,y=uv(u,v)
                return warp(x,y)+Vector((0,.41,0))
            patch(g,pt,2,max(3,int(length*76)),material,None,lambda u,v:weights(*uv(u,v)))
    ink='Bronze' if k else 'Lining'
    # The open shrine is woven in three narrow bands, with empty space inside.
    for side in (-1,1):
        x=lambda s:.48+side*s
        stitch([(x(.035),.19),(x(.16),.27),(x(.135),.365),(x(.066),.404)],.012,ink)
        stitch([(x(.13),.289),(x(.074),.301),(x(.039),.355)],.011,ink)
        stitch([(x(.016),.466),(x(.012),.308),(x(.02),.268),(x(0),.222)],.010,ink)
    # Shoulder mantle in a second cut. The broad diagonal sweep leads into the clasp.
    def mantle(u,v):
        a=(u-.5)*TAU
        r=(9.3+(15.5+2.5*cos(a+1.1))*v)
        x=r*sin(a)
        y=-(8.7+11.9*v)*cos(a)+.7
        z=150.1-8.5*v-6.0*v*sin(a+.5)-(1.4+1.6*v)*sin(2.2*pi*v+1.5*sin(a))-.7*cos(7*a+v)*v
        return (x,y,z)
    patch(g,mantle,56,12,'Wine' if k else 'DeepBlue','Chest',repeat=(2.4,1))
    tube(g,[mantle(i/66,1) for i in range(67)],.42,'Wine' if k else 'SeaSilk','Chest')
    for i in range(2):
        tube(g,[mantle(t/50,.39+i*.22+.07*sin(TAU*t/50)) for t in range(51)],
             .46,'Velvet' if k else 'SeaSilk','Chest')
    x,y,z=mantle(.32,.73)
    stud(g,x,y-.7,z,2.65,'Bronze','Chest')
    stud(g,x,y-1.8,z,.89,'Patina','Chest')


def head(g,k):
    b='Head'
    # Three-dimensional skull, decreasing in width at the temples and jaw.
    if k:
        shell(g,[(148.2,5.6,6.1,-.3),(150.4,7.7,8.9,-.3),(154.8,9.4,10.4,-.3),
                 (161,10.5,10.4,.1),(165.8,10.9,10.6,.3),(169.8,10.4,10.0,.6),
                 (173.4,8.7,8.7,1.2),(176,5.6,6.1,1.4),(177.4,1,2,1.9)],
              'Iron',b,n=48)
    else:
        # The enclosed wool hood conceals the rear half of the cap entirely. A
        # trimmed face insert forms the brow without clipping through the crown.
        def forehead(u,v):
            a=(u-.5)*3.15
            return (10.5*sin(a)*(1-.22*v),-.3-10.6*cos(a)*(1-.25*v),158.9+14*v)
        patch(g,forehead,34,10,'Iron',b)
    # Narrow horizontal openings sit between two forged components. Recesses stay
    # dark even in the sun, and a thin ember is visible deep in the knight's visor.
    def face(u,v,upper):
        a=(u-.5)*2.86
        c=cos(a);x=10.8*sin(a)
        if upper:
            z=163.9+1.24*abs(sin(a))+(8.2-3.3*abs(sin(a)))*v
            y=-(11.2+.7*sin(pi*v)+1.5*(1-v)*c**6)*c
        else:
            z=150.5+4.7*abs(sin(a))+(12.3-3.9*abs(sin(a)))*v
            y=-(9.7+2.0*v+(6.3 if k else 1.5)*c**4*sin(pi*v/1.4))*c
        return (x,y-.7,z)
    for up in (True,False):
        fn=lambda u,v:face(u,v,up)
        patch(g,fn,38,9,'StormSteel' if k else 'Iron',b)
        tube(g,[fn(i/38,0 if up else 1) for i in range(39)],.33,'Steel',b)
    for s in (-1,1):
        for row in range(3):
            for col in range(4):
                u=.5+s*(.075+col*.052+(row%2)*.019)
                x,y,z=face(u,.32+row*.16,False)
                tube(g,[(x,y-.6,z),(x+s*.12,y-.7,z+.68)],.36,'Obsidian',b)
        x=9.85*s;stud(g,x,-4.5,164.1,1.55,'Bronze',b)
        if k:
            tube(g,[(s*1.2,-12.2,163.6),(s*4.0,-11.75,163.8),(s*6.7,-9.8,164.4)],
                 lambda t:.27-.1*t,'Ember',b)
    if not k:
        # A sewn wool hood has a true elliptical aperture and enough depth to shadow
        # the steel face. Front and back are continuous and the pointed tail drapes.
        def hood(u,v):
            a=TAU*u;c=cos(a);s=sin(a)
            size=(1+.23*sin(pi*v))*(1-.987*v**4.8)
            x=11.3*s*size-1.8*v*v
            z=163.5+(13.4*c+1.1*c*c)*size+2.3*sin(pi*v)-7.4*v**3
            y=-10.4-2.7*c+1.7*abs(s)+26.8*v+1.2*sin(3*a+v*3)*sin(pi*v)
            return x,y,z
        patch(g,hood,58,24,'SeaSilk',b,repeat=(2,1))
        tube(g,[hood(i/70,0) for i in range(71)],.81,'DeepBlue',b)
        for side in (.018,.982):
            tube(g,[hood(side,v/25) for v in range(26)],.32,'DeepBlue',b)
    else:
        # Hammered crest: a low fluted comb and a narrow cloth tail, held by a brass ferrule.
        for s in (-1,1):
            def comb(u,v):
                y=-10.4+23*u
                z=167.5+10*sin(pi*u)**.65+v*(.3+3.6*sin(pi*u)**.9)
                return (s*(1.75-1.24*v)*sin(pi*u)**.6,y,z)
            patch(g,comb,28,4,'Bronze',b,flip=s<0)
        stud(g,0,5.4,178.3,2.2,'Bronze','Head')
        for j in range(17):
            def plume(u,v):
                w=(2.9+.7*sin(j))*(1-v*.86)
                return (1.1+2.45*sin(j*.75)+w*(u-.5)-6.7*v*v,
                        5.4+j*.22+15.4*sin(pi*v*.70)+6.3*v,
                        178.9+1.6*sin(j*.51)+15.8*sin(pi*v)-30*v**2.3)
            patch(g,plume,4,18,'Velvet' if j%3 else 'Wine',b)


def shield(g):
    # Curved heater: laminated wood, leather backing, folded iron face and riveted rim.
    b='ShieldPlate'
    def surface(u,v,back=0):
        q=2*u-1
        w=2.0+18.2*sin(v*pi*.58)**.84
        x=32+w*q
        y=-24.0-5.2*(1-q*q)*sin(pi*(.11+.77*v))+back
        z=66+57*v-3.3*q*q*v**5+1.7*q*q*(1-v)
        return x,y,z
    patch(g,surface,30,25,'Iron',b)
    patch(g,lambda u,v:surface(u,v,2.3),30,25,'Leather',b,flip=True)
    for edge in (lambda t:surface(t,0),lambda t:surface(t,1),lambda t:surface(0,t),lambda t:surface(1,t)):
        tube(g,[edge(i/38) for i in range(39)],1.12,'Bronze',b)
    # Broad painted chevron and vertical iron reinforcement on a battered field.
    for s in (-1,1):
        def chevron(u,v):
            uu=.5+s*(.016+.44*u)
            vv=.71-.29*u-.065*v
            x,y,z=surface(uu,vv);return x,y-.3,z
        patch(g,chevron,18,4,'Velvet',b)
        for i in range(9):
            x,y,z=surface(.5+s*.454,.11+i*.102)
            stud(g,x,y-.36,z,.79,'Bronze',b)
    for q in (.20,.80):
        def rail(u,v):
            a=q+(u-.5)*.014
            x,y,z=surface(a,.12+.8*v)
            return x,y-.47,z
        patch(g,rail,3,22,'Bronze',b)
    tube(g,[surface(.5,i/35) for i in range(36)],lambda t:.60+.42*sin(pi*t),'Steel',b)
    for a in (0,pi/2,pi,3*pi/2):
        # Four applied metal petals form the broken votive cross.
        def leaf(u,v):
            width=sin(pi*v)*(.028 if cos(a) else .043)
            x=(.11*cos(a)*v-width*sin(a)*(2*u-1))
            z=(.096*sin(a)*v+width*cos(a)*(2*u-1))
            xx,y,zz=surface(.5+x,.625+z)
            return xx,y-.74-.52*sin(pi*u)*sin(pi*v),zz
        patch(g,leaf,6,12,'Bronze',b)
    x,y,z=surface(.50,.625);stud(g,x,y-.8,z,2.05,'Steel',b)
    # A riveted umbo encloses the fist while the shield is braced. Its depth is
    # fitted to the clenched gauntlet in the charge and guard, in shield-bone space.
    def boss(u,v):
        az=TAU*u
        a=.016+(pi*.5-.016)*v
        x=32+12.7*cos(az)*sin(a)
        z=93+15*sin(az)*sin(a)
        vv=(z-66)/57
        w=2+18.2*sin(pi*.58*vv)**.84
        q=(x-32)/w
        y=-24-5.2*(1-q*q)*sin(pi*(.11+.77*vv))
        return x,y-.8-16.1*cos(a)**1.22,z
    patch(g,boss,46,18,'StormSteel',b,flip=True)
    tube(g,[boss(i/56,1) for i in range(57)],.87,'Bronze',b)
    for i in range(8):
        x,y,z=boss(i/8,.985);stud(g,x,y-.47,z,.71,'Bronze',b)
    for j in range(4):
        tube(g,[boss(j*.25,v/18) for v in range(3,18)],lambda v:.18+.32*sin(pi*v),'Steel',b)
    # Leather covered enarmes span the concave rear: the hand closes around the
    # lower grip while the broad upper band retains the forearm.
    for t in (.45,.70):
        pts=[surface(.5+(.14*cos(i*pi/16)),t,2.4+8.7*sin(i*pi/16)) for i in range(17)]
        tube(g,pts,1.0,'Leather',b)


def gear(g):
    # Saddlebag sewn from two soft hides and a belt-suspended, empty sword scabbard.
    shell(g,[(80,3.2,3.2,0),(81.2,5.5,4.6,0),(84.3,6.3,5.2,0),
             (90,6.2,5.3,0),(93.8,5.7,4.4,0),(95,4.7,3.4,0)],'Leather','Pelvis',(-19,1),32)
    tube(g,[(-23.6,-1,93),(-23.3,-3.9,91),(-19.5,-4.5,87.6),(-15.5,-4,90.5),(-14,-1.1,93)],
         .53,'Lining','Pelvis')
    stud(g,-19,-4.8,88.1,.76,'Bronze','Pelvis')
    p=Vector((17.3,-1.9,91));q=Vector((28.1,15.3,31))
    spine=lambda t:p.lerp(q,t)
    for i in range(2):
        start=.0 if i==0 else .94;end=.94 if i==0 else 1
        tube(g,[spine(start+(end-start)*j/16) for j in range(17)],
             lambda t:(2.5-.75*t) if i==0 else (1.75-1.25*t),
             'Leather' if i==0 else 'Bronze','Pelvis',12)
    for a in (.025,.21):
        tube(g,[spine(a),spine(a+.018)],2.62,'Bronze','Pelvis',16)
    for qz in (86,91):
        tube(g,[(14,-8,qz+6),(19,-2.5,qz),(19.5,.7,qz-1)],1.0,'Leather','Pelvis')


def figure(g,k):
    body(g,k)
    for s,name in ((-1,'R'),(1,'L')):
        lower_limb(g,k,s,name)
        upper_limb(g,k,s,name)
    cloak(g,k)
    harness(g,k)
    head(g,k)
    (shield if k else gear)(g)
    return g


def harness(g,k):
    """Load-bearing cross strap, laced bracers and a footed rear baldric."""
    def baldric(u,v):
        x=17.0-33.6*v+(u-.5)*3.35
        z=140.5-34.0*v+(u-.5)*2.7
        width=16.9+6.5*(1-v*.77)
        ry=12.6+3.7*sin(pi*(.10+.66*(1-v)))
        y=-ry*sqrt(max(.05,1-(x/width)**2))-2.75
        return x,y,z
    patch(g,baldric,6,32,'Leather','Chest',repeat=(.2,1.15))
    for u in (.12,.88):
        tube(g,[baldric(u,i/35) for i in range(36)],.18,'Lining','Chest')
    for v in (.3,.34,.8):
        tube(g,[baldric(i/10,v) for i in range(11)],.40,'Bronze','Chest')
    for s,side in ((-1,'R'),(1,'L')):
        # Narrow plain leather straps keep the vambrace's open inside seam closed.
        for j in range(2):
            z=93.6+9*j;radius=5.45+j*.68
            shell(g,[(z,radius,radius-.2,0),(z+.4,radius+.2,radius,0),
                     (z+1.8,radius+.1,radius-.1,0)],'Leather','Forearm'+side,(s*30,-3.6+1.2*j),28)
            stud(g,s*(30+radius),-3.6,z+1,.64,'Bronze','Forearm'+side)
        # Greave and articulated elbow latch straps. Warden lames have chasing along each edge.
        for j in range(2 if k else 1):
            def flute(u,v):
                a=-.56-j*.33+(u-.5)*.16
                r=7.75+2.5*v
                return (s*(12.7+r*sin(a)),-r*cos(a)-.24,54+20*v+2*cos(a)*v)
            patch(g,flute,5,18,'Steel','Thigh'+side)
    if k:
        # Blackened gorget of overlapping plates beneath the decorated red shoulder covering.
        for j in range(3):
            def bevor(u,v):
                a=(u-.5)*2.2
                rx=12.1+j*1.3;ry=11.5+j*1.8
                return (rx*sin(a),-ry*cos(a)-1,
                        147.2-j*2.2-3.3*v-3.8*cos(a)**4*v)
            patch(g,bevor,24,5,'Iron','Chest')
            tube(g,[bevor(i/26,1) for i in range(27)],.30,'Steel','Chest')
        # Heraldic rondel hangs over the heart on a short chain of flattened links.
        for j in range(15):
            v=j/14
            x=-11.9+24*v;z=142.8-6.1*sin(pi*v);y=-15.3-3*sin(pi*v)
            pts=[(x+.70*cos(i*TAU/10),y+.42*sin(i*TAU/10),z+1.10*sin(i*TAU/10)) for i in range(11)]
            tube(g,pts,.21,'Bronze','Chest',6)
        stud(g,.2,-18.7,134.8,2.12,'Bronze','Chest')
        stud(g,.2,-20.0,134.8,.93,'Ember','Chest')
