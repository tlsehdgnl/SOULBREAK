"""Bake an original periodic, black-background flame atlas for the braziers."""
import numpy as np
from PIL import Image


def bake_fire(out):
    tile=192
    yy,xx=np.mgrid[:tile,:tile].astype(np.float32)
    h=1.-(yy+.5)/tile
    x=(xx+.5)/tile*2.-1.
    atlas=np.zeros((tile*4,tile*4,3),np.uint8)
    for frame in range(16):
        t=2.*np.pi*frame/16.
        # Individual tongues accelerate, separate and bend as they rise. Motion
        # is periodic so there is no cut when the book repeats.
        heat=np.zeros_like(h)
        for i,(root,high,width) in enumerate([(-.28,.70,.27),(.04,.88,.33),(.30,.51,.23),(-.03,.56,.26)]):
            high*=.94+.07*np.sin(t+i)
            climb=np.clip(h/high,0,1)
            centre=root*(1.-.63*climb)+(.125*np.sin(7.9*h-2*t+i*2.3)+.075*np.sin(17*h-3*t+i))*climb
            breadth=width*(1.05-climb)**.72*(.89+.11*np.sin(h*22-3*t+i))
            d=(breadth-np.abs(x-centre))/(.032+.055*climb)
            tip=(high-h)/(.042+.07*climb)
            density=np.clip(np.minimum(d,tip),0.,1.) * np.clip(h/.047,0.,1.)
            heat=np.maximum(heat,density*(1.-.70*climb))
        fade=np.clip(h/.05,0.,1.)*np.clip((1.-h)/.04,0.,1.)
        emit=heat*fade
        red=np.clip(emit*4.0,0.,1.)
        green=np.clip((emit-.05)*1.4,0.,.85)
        blue=np.clip((emit-.36)*.85,0.,.37)
        rgb=np.stack((red,green,blue),axis=-1)*np.clip(emit[:,:,None]*5.,0.,1.)
        row,col=divmod(frame,4)
        atlas[row*tile:(row+1)*tile,col*tile:(col+1)*tile]=np.uint8(np.clip(rgb,0.,1.)*255.+.5)
    Image.fromarray(atlas).save(out/'T_CenserFire.png',compress_level=6)
