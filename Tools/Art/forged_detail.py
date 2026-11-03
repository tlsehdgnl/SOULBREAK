"""Silversmithing and cloth patterns for the Warden and the Pilgrim, in rig centimeters."""
from math import cos, pi, sin
from mathutils import Vector


def line(g, points, radius, color, bone):
    for a, b in zip(points, points[1:]):
        g.beam(a, b, radius, radius, color, bone, 6)


def jewel(g, point, size, color, bone):
    g.rings(point, [(-size*.55, size*.58, size*.58, 0),
                    (0, size, size*.87, 0),
                    (size*.66, size*.53, size*.5, 0)], color, bone, 8)


def repoussee(g, border, ridge, surface, binding, bone, width=1):
    """Embossed faces with an actual rolled border and raised crest."""
    count = len(border)
    g.surface(border + [ridge], [(i, (i+1) % count, count) for i in range(count)], surface, bone)
    line(g, border + border[:1], width, binding, bone)


def sigil(g, x, y, z, size, bone, back=False, hot=False):
    direction = 1 if back else -1
    gold = 'Gilt'
    for i in range(12):
        angle = i*pi/6
        inner = .51*size
        tip = size*(1 if i%3==0 else .81 if i%2==0 else .69)
        dx, dz = cos(angle),sin(angle)
        g.panel([(x+inner*dx-.07*size*dz,y,z+inner*dz+.07*size*dx),
                 (x+tip*dx,y+direction*.2,z+tip*dz),
                 (x+inner*dx+.07*size*dz,y,z+inner*dz-.07*size*dx)],gold,bone,.25)
    ring=[(x+size*.47*cos(2*pi*i/16),y+direction*.2,z+size*.47*sin(2*pi*i/16)) for i in range(16)]
    line(g,ring+ring[:1],size*.045,'Bronze',bone)
    points=[(x,y,z+size*.47),(x+size*.18,y,z),(x,y,z-size*.47),(x-size*.18,y,z)]
    repoussee(g,points,(x,y+direction*1.1,z), 'Ember' if hot else 'Soul','Gilt',bone,size*.032)


def coat_of_mail(g, knight):
    # Alternating links are individually shaded planes along exposed rib and hip flanks.
    for side in (-1,1):
        for row in range(8):
            z=101+row*2.3
            for col in range(5):
                theta=.75+col*.42+(row%2)*.17
                x=side*(17.2+(z-101)*.24)*cos(theta)
                y=-13.8*sin(theta)
                g.panel([(x-1,y,z+1),(x,y-.6,z-.1),(x+1.1,y,z+.3),(x,y-.5,z-1.15)],
                        'Mail' if (col+row)%3 else 'Steel','Chest',.3)
        for row in range(5):
            for col in range(4):
                x=side*(6.8+col*3.2+(row%2))
                z=81+row*2.3
                g.panel([(x-1.15,-12.8,z+1),(x,-13.2,z-.5),(x+1,-12.8,z+.6),
                         (x,-13,z-1)],'Mail','Pelvis',.35)


def torso(g, knight):
    coat_of_mail(g,knight)
    for s in (-1,1):
        front=[(s*1.1,-16.5,143),(s*12,-16.3,146),(s*24,-9,139),
               (s*20,-12,127),(s*8,-17,120),(s*2,-18,127)]
        ridge=(s*12,-19,133)
        repoussee(g,front,ridge,'Steel' if knight else 'StormSteel','Bronze','Chest',.8)
        line(g,[(s*5,-18.7,130),(s*11,-20,134),(s*19,-14,139)],.61,'Gilt','Chest')
        for row in range(3):
            z=102+row*4.5
            g.panel([(s*2,-15.8,z),(s*16,-11,z+1),(s*16.3,-10,z+4.5),(s*3,-16,z+3.6)],
                    'Steel' if row%2 else 'StormSteel','Chest',1)
        # Jointed hip tassets. The lower edge moves with the thigh, not the torso.
        th='ThighR' if s<0 else 'ThighL'
        for i in range(3):
            z=87-i*6.2
            border=[(s*11,-10,z+4),(s*22,-4,z+2),(s*23,-2,z-4),(s*15,-9,z-7),(s*9,-12,z-3)]
            repoussee(g,border,(s*16,-10.5,z-1),'Iron' if knight else 'StormSteel','Bronze',th,.54)
            jewel(g,(s*20,-6.8,z+1),.95,'Gilt',th)
        # Slightly overlapping collar supplies layered relief behind the hood/crown.
        g.rings((s*6,0,144),[(0,9,12,0),(2.2,10,13,0),(5,8.4,10.5,.5)],
                'Iron' if knight else 'Azure','Chest',12)
    sigil(g,0,-18.5,134,7.8 if knight else 5.5,'Chest',hot=knight)
    # Cinched riding belt; individual brass loops and a signed buckle.
    for x in (-16,-10,10,16):
        y=-13.8+abs(x)*.18
        g.box((x,y,98.5),(1.8,1.6,7.3),'Gilt','Pelvis')
    g.box((0,-15,98),(9.4,2.7,8),'Bronze','Pelvis')
    g.box((0,-17,98),(5.4,1.1,4.8),'Obsidian','Pelvis')
    g.panel([(-2.1,-17.7,98),(0,-17.7,100.2),(2.1,-17.7,98),(0,-17.7,95.8)],
            'Ember' if knight else 'Soul','Pelvis',.3)


def cape(g, knight):
    """Pleated, skinned mantle. The upper band follows the shoulders, the skirt follows the pelvis."""
    def position(u,t):
        # u across the back, t down the cape.
        width=(23.5 if knight else 20.5)+(8.6 if knight else 10.5)*t
        scallop=(1+cos(5*pi*u))*.5
        length=(93 if knight else 88)+9*(1-u*u)+(0 if knight else -9*u)
        x=u*width+(0 if knight else -3.8*t*t)
        pleats=(1.5+4*t)*cos((u+.07)*pi*4.5)
        y=15.2+12.8*t+(1-u*u)*4.5-9*u*u+pleats
        z=145-5.0*u*u-t*length+scallop*3.9*t**4
        return (x,y,z)
    def weight(u,t):
        lower=min(.88,t*1.14)
        leg=t*t*.13
        return {'Chest':1-lower,'Pelvis':lower-leg,
                ('ThighL' if u>=0 else 'ThighR'):leg}
    def facet(points,mat,offset=0):
        n=len(g.v)
        verts=[]
        for u,t in points:
            x,y,z=position(u,t)
            verts.append((x,y+offset,z))
        g.surface(verts,[tuple(range(len(points)))],mat)
        for i,(u,t) in enumerate(points):
            g.weighted[n+i]=weight(u,t)
    base='Wine' if knight else 'Azure'
    shades=('Velvet','Crimson') if knight else ('DeepBlue','SeaSilk')
    for i in range(30):
        u=-1+2*i/30; v=-1+2*(i+1)/30
        tint=shades[0] if cos((u+.07)*pi*4.5)<-.5 else shades[1] if cos((u+.07)*pi*4.5)>.62 else base
        for j in range(7):
            a=j/7; b=(j+1)/7
            facet([(u,a),(v,a),(v,b),(u,b)],tint)
    def band(u,v,t,b,mat):
        for j in range(10):
            a=t+(b-t)*j/10;c=t+(b-t)*(j+1)/10
            facet([(u,a),(v,a),(v,c),(u,c)],mat,.48)
    for s in (-1,1):
        band(s*.92,s*.957,.02,.99,'Gilt')
        band(s*.86,s*.878,.045,.955,'Lining')
    for i in range(24):
        a=-.95+i*1.9/24;b=a+1.9/24
        facet([(a,.94),(b,.94),(b,.965),(a,.965)],'Gilt',.50)
    # Split-halo and hanging blade are embroidered into the rear view.
    for i in range(28):
        a=2*pi*i/28;b=2*pi*(i+1)/28
        if i in (6,7,20,21):
            continue
        facet([(.48*cos(a),.285+.108*sin(a)),(.48*cos(b),.285+.108*sin(b)),
               (.395*cos(b),.285+.09*sin(b)),(.395*cos(a),.285+.09*sin(a))],
              'Bronze' if knight else 'Lining',.75)
    for s in (-1,1):
        facet([(0,.166),(s*.075,.255),(s*.058,.385),(0,.747)],
              'Gilt' if s<0 else 'Ivory',.85)
        facet([(0,.40),(s*.27,.341),(s*.30,.365),(s*.06,.435)],
              'Gilt',.85)
    for i in range(5):
        u=(i-2)*.126
        facet([(u,.795),(u+.03,.812),(u,.83),(u-.03,.812)],'Lining',.62)


def pilgrim(g):
    cape(g,False)
    # Hood: a deep angular opening, brow piping, cowl folds and a trailing point.
    for s in (-1,1):
        border=[(s*.7,-16,176),(s*10.5,-13,173),(s*16,-6,164),(s*12,-9,151),(s*5,-14,147),
                (s*7.8,-15,158),(s*11,-13.8,166)]
        repoussee(g,border,(s*11,-16,163),'DeepBlue','SeaSilk','Head',.6)
        g.panel([(s*4,7,180),(s*13,8,173),(s*11,13,155),(s*1,21,149)],'Azure','Head',1)
        line(g,[(s*13,-8.5,167),(s*12.5,-12.8,159),(s*5,-15,151)],.55,'Lining','Head')
        jewel(g,(s*7,-12.2,147),1.35,'Gilt','Chest')
    # A shoulder scarf and contrasting lining give the pilgrim an asymmetric profile.
    for i in range(3):
        z=141+i*3
        g.rings((0,0,z),[(0,16-i,13,-.5),(2,17-i,14,-1),(3.3,15-i,12,-.4)],
                'SeaSilk' if i==1 else 'Azure','Chest',14)
    line(g,[(-18,-10,139),(-9,-17.4,127),(1,-17.6,116),(12,-11.8,104)],2.1,'Leather','Chest')
    for x,z in [(-12,131),(-5,123),(4,113)]:
        g.box((x,-18,z),(3,1,1.4),'Bronze','Chest')
    # Fluted satchel, flask and small chained soul lantern.
    g.rings((17,2,90),[(-10,6,5,0),(-6,8,6,0),(3,8.4,6,0),(7,6,5,0)],'Leather','Pelvis',10)
    line(g,[(12,-3,94),(18,-5.4,88),(24,-1,93)],.75,'Bronze','Pelvis')
    g.beam((-16,-1,96),(-22,-1,84),.75,.75,'Gilt','Pelvis')
    for z,r in [(76,3.5),(79,5),(84,4)]:
        g.rings((-22,-1,z),[(0,r,r,0),(1.1,r,r,0)],'Bronze','Pelvis')
    jewel(g,(-22,-1,80),3.8,'Soul','Pelvis')
    for side,s in [('L',1),('R',-1)]:
        a='UpperArm'+side
        for layer in range(3):
            z=137-layer*3.5
            repoussee(g,[(s*17,-8,z+2),(s*24,-13,z+2),(s*34,-5,z),(s*35,2,z-3),
                         (s*29,-10,z-6),(s*18,-10,z-4)],(s*27,-12,z+.9),'StormSteel','Bronze',a,.55)
        # Wrapped leather vambraces and slim raised silver ridges.
        for i in range(5):
            z=91+i*3.6
            line(g,[(s*25,-5,z),(s*30,-10,z+2),(s*35,-4,z+3)],.7,'Leather','Forearm'+side)


def warden(g):
    cape(g,True)
    # A ridged, scalloped crown and rear helm fan differentiate the silhouette.
    for i in range(11):
        a=2*pi*i/11
        x,y=12*cos(a),11*sin(a)
        g.beam((x,y,174),(x*1.21,y*1.24,184+6*(i%3==0)),2.1,.18,'Bronze','Head',5)
    for s in (-1,1):
        line(g,[(s*1,-17.4,165),(s*7,-15,167.5),(s*13,-10,169)],.72,'Gilt','Head')
        for i in range(3):
            x=s*(3.3+i*2.4)
            line(g,[(x,-16.3+i*.7,160),(x,-15+i*.7,153+i*.8)],.55,'Obsidian','Head')
        # Sweep the top blades of the gilded pauldron backward like broken cathedral spires.
        for i in range(3):
            z=142-i*5.1; w=(21 if s<0 else 16)-i*1.4
            g.rings((s*26,0,z),[(-4,w*.83,13-i*.6,0),(-1,w,14-i*.7,0),
                    (1.5,w*.97,14-i*.7,0),(4,w*.72,11,0)],'Bronze' if s<0 else 'Iron','UpperArm'+('R' if s<0 else 'L'),12)
            if s<0:
                line(g,[(-28,-14,z+1),(-36,-10,z-1),(-44,-3,z-2)],1,'Gilt','UpperArmR')
        for j in range(3):
            x=s*(19+j*4);y=8-j*4
            pts=[(x,y,146),(x+s*6,y,148),(x+s*(9+j*1.5),y+6,163-j*1.9),(x+s*2,y+6,154)]
            g.panel(pts,'Gilt' if s<0 else 'Steel','UpperArmR' if s<0 else 'UpperArmL',1.2)
    # The heated seam zigzags through the actual destructible shoulder subtree.
    line(g,[(-17,-12,147),(-25,-16,143),(-24,-16,139),(-35,-12,138),(-33,-9,134),(-42,-7,131)],
         1.25,'Ember','UpperArmR')
    sigil(g,-30,-15,140,5.4,'UpperArmR',hot=True)
    # Pauldron rivets and crowned mark at the point the player is aiming for.
    for x,y,z in [(-17,-10,140),(-40,-8,139),(-42,3,136),(-32,-10,131)]:
        jewel(g,(x,y,z),1.6,'Gilt','UpperArmR')


def shield(g):
    x=34;y=-15.2
    outline=[(x-19,y,113),(x-14,y,119),(x,y-1,126),(x+14,y,119),(x+19,y,113),
             (x+16,y,85),(x+5,y,65),(x,y,59),(x-5,y,65),(x-16,y,85)]
    center=(x,y-7,98)
    repoussee(g,outline,center,'StormSteel','Bronze','ForearmL',1.9)
    for i in range(10):
        a=Vector(outline[i]);b=Vector(outline[(i+1)%10]);p=Vector(center)
        g.panel([p.lerp(a,.84),p.lerp(b,.84),p.lerp(b,.74),p.lerp(a,.74)],'Gilt','ForearmL',.5)
    line(g,[(x,y-2.3,123),(x,y-7.5,98),(x,y-1,62)],1.2,'Gilt','ForearmL')
    sigil(g,x,y-8,103,12,'ForearmL',hot=True)
    for i in (0,2,4,5,9):
        a=Vector(outline[i]).lerp(Vector(center),.09)
        jewel(g,(a.x,a.y-1,a.z),1.2,'Gilt','ForearmL')


def limbs(g,knight):
    for name,s in [('R',-1),('L',1)]:
        hand='Hand'+name
        for i in range(4):
            x=s*(27.5+i*2.0);z=81-abs(i-1.5)*.6
            g.beam((x,-8.4,z+3),(x,-11.2,z),1.25,1.15,'StormSteel',hand)
            g.beam((x,-11.2,z),(x,-10,z-2.4),1.13,.82,'Iron',hand)
            jewel(g,(x,-9.7,z+2.3),1.08,'Steel',hand)
        shin='Shin'+name
        border=[(s*13,-11,48),(s*19,-8,38),(s*17,-6,17),(s*14,-9,12),(s*10,-8,20),(s*8,-7,38)]
        repoussee(g,border,(s*13.8,-11,34),'StormSteel','Bronze',shin,.69)
        foot='Foot'+name
        for i in range(3):
            g.rings((s*14,-7-i*3.4,2),[(0,6.5,6,0),(2.5,7.1,7,0),(5.2,5.6,5.8,0)],
                    'Iron' if i%2 else 'StormSteel',foot,10)
        for z,r in ((22,5.8),(40,8.1)):
            g.rings((s*13.7,-1,z),[(0,r,r-.4,0),(1.8,r+.4,r,0)],'Bronze',shin,12)


def sword_mount(g,pos,knight,bind):
    # Quillons protect the palm and return toward the fuller. Wrapped grip with a pommel seal.
    for s in (-1,1):
        pts=[pos(s*2,11,-1.2),pos(s*8,14,.2),pos(s*17,18,.1),pos(s*14,12,-.8),pos(s*7,8,-1.2)]
        g.panel(pts,'Bronze',bind,1.4)
        line(g,[pos(s*3,11,.7),pos(s*9,14,1.5),pos(s*16,18,.5)],.8,'Gilt',bind)
        g.panel([pos(0,20,2.5),pos(s*2.5,23,2),pos(s*.9,65,1.8),pos(0,72,1.85)],
                'Patina' if knight else 'DeepBlue',bind,.4)
    jewel(g,pos(0,-15,0),3.6,'Gilt',bind)
    jewel(g,pos(0,-16,2.3),1.55,'Ember' if knight else 'Soul',bind)


def finish(g,knight):
    torso(g,knight)
    limbs(g,knight)
    if knight:
        warden(g)
        shield(g)
    else:
        pilgrim(g)
