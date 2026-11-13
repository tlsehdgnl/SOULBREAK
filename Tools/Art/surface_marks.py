"""Bake seamless tangent normals for steel, 2/2 twill, leather and riveted mail."""
from math import cos, exp, pi, sin, sqrt
from pathlib import Path
import random
import struct


def write_tga(file, size, data):
    hdr=struct.pack('<BBBHHBHHHHBB',0,0,2,0,0,0,0,0,size,size,24,32)
    Path(file).write_bytes(hdr+data)


def bake_textures(folder, size=512):
    rng=random.Random(319)
    tau=2*pi
    cells=[[rng.uniform(-1,1) for _ in range(32)] for _ in range(32)]
    channels={name:[] for name in ('Burnished','Twill','Hide','Mail')}
    masks=bytearray()
    for y in range(size):
        for x in range(size):
            u=x/size;v=y/size
            ix,iy=int(u*32),int(v*32);a=u*32-ix;b=v*32-iy
            a=a*a*(3-2*a);b=b*b*(3-2*b)
            cloud=(cells[iy%32][ix%32]*(1-a)+cells[iy%32][(ix+1)%32]*a)*(1-b)
            cloud+=(cells[(iy+1)%32][ix%32]*(1-a)+cells[(iy+1)%32][(ix+1)%32]*a)*b
            fine=rng.uniform(-1,1)
            brushed=.5+.26*cloud+.075*cos(tau*(v*84+.18*sin(tau*u)) )+.06*fine
            warp=sin(tau*u*58+.31*sin(tau*v*9))
            weft=sin(tau*v*58+.31*sin(tau*u*9))
            twill=.5+.17*(warp+weft)+.19*cos(tau*(40*u+40*v))+.06*fine
            hide=.5+.23*cloud+.17*fine+.05*sin(tau*(63*u+51*v))
            channels['Burnished'].append(.27*brushed)
            channels['Twill'].append(.77*twill)
            channels['Hide'].append(.55*hide)
            # Alternately tilted rings interlock in offset rows. The upper link occludes
            # the lower one wherever they cross. The rivet heads stand above the wire.
            qx=u*24;qy=v*32;top=0
            for row in range(int(qy)-1,int(qy)+2):
                dy=qy-row-.5
                dx=(qx-(row%2)*.5+.5)%1-.5
                distance=sqrt(((dx+dy*.21*(1 if row%2 else -1))/.39)**2+(dy/.70)**2)
                wire=max(0,1-((distance-1)/.22)**2)
                top=max(top,sqrt(wire)*(.84 if row%2 else .75))
            channels['Mail'].append(top*.95+fine*.015)
            for value in (hide,twill,brushed):
                masks.append(round(max(0,min(1,value))*255))
    write_tga(folder/'T_ArmorerMarks.tga',size,masks)
    for name,heights in channels.items():
        data=bytearray()
        for y in range(size):
            for x in range(size):
                dx=2.0*(heights[y*size+(x+1)%size]-heights[y*size+(x-1)%size])
                dy=2.0*(heights[((y+1)%size)*size+x]-heights[((y-1)%size)*size+x])
                norm=sqrt(1+dx*dx+dy*dy)
                data.extend((round(127.5+127.5/norm),round(127.5+127.5*dy/norm),round(127.5-127.5*dx/norm)))
        write_tga(folder/('T_'+name+'_N.tga'),size,data)
