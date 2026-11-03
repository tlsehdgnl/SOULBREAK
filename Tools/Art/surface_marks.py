"""Bake tiled etched metal and woven fabric masks. No external textures are required."""
from math import cos, pi, sin
import struct
import random

def bake_texture(target, size=256):
    rng=random.Random(319)
    cells=[[rng.uniform(-1,1) for _ in range(32)] for _ in range(32)]
    data=bytearray()
    for y in range(size):
        for x in range(size):
            # Bilinear islands give metal broad oxidized patches; fine scratches lie along the grain.
            u=x/size*32; v=y/size*32
            ix,iy=int(u),int(v); a,b=u-ix,v-iy
            n=(cells[iy%32][ix%32]*(1-a)+cells[iy%32][(ix+1)%32]*a)*(1-b)
            n+=(cells[(iy+1)%32][ix%32]*(1-a)+cells[(iy+1)%32][(ix+1)%32]*a)*b
            phase=2*pi*(y*47/size+.08*sin(2*pi*x/size)+.08*n)
            brushed=.55+.22*n+.1*cos(phase)+rng.uniform(-.085,.085)
            crossing=sin(2*pi*x*56/size)*sin(2*pi*y*56/size)
            linen=.51+.19*crossing+.17*n+rng.uniform(-.06,.06)
            pores=.5+.25*n+rng.uniform(-.18,.18)
            for value in (pores, linen, brushed):
                data.append(round(max(0,min(1,value))*255))
    header=struct.pack('<BBBHHBHHHHBB',0,0,2,0,0,0,0,0,size,size,24,32)
    target.write_bytes(header+data)
