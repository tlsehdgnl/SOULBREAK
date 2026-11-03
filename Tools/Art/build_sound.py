"""Synthesize chapel ambience, combat foley and the nave's seamless mineral detail."""
from pathlib import Path
import math
import struct
import sys
import wave
import zlib
import numpy as np
out=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[2]/'Saved/SBLevel'
out.mkdir(parents=True,exist_ok=True)
rate=32000
rng=np.random.default_rng(1985)
def t(d):return np.arange(round(d*rate))/rate
def low_noise(n,width):
    noise=rng.normal(0,1,n)
    kernel=np.ones(width)/width
    return np.convolve(noise,kernel,'same')*math.sqrt(width)
def bandnoise(n,lo,hi):
    f=np.fft.rfftfreq(n,1/rate);v=np.fft.rfft(rng.normal(size=n));gain=np.exp(-np.maximum(0,np.log(np.maximum(1,f)/hi))**2*17-np.maximum(0,np.log(lo/np.maximum(1,f)))**2*17)
    x=np.fft.irfft(v*gain,n);return x/(np.std(x)+1e-10)
def ring(u,base,ratios,decay):
    return sum((1/(1+i*.74))*np.sin(2*np.pi*u*base*r)*np.exp(-u*(1+.35*i)/decay) for i,r in enumerate(ratios))
def pluck(u,f,decay):
    return ring(u,f,[1,1.999,3.014,4.001,6.006],decay)*(1-np.exp(-u*75))
def hall(a,wet=.22):
    a=a.astype(np.float64)
    chans=[]
    for side in (1,2):
        h=np.zeros(round(rate*.51));h[0]=1
        for i,(delay,gain) in enumerate(((.039,.29),(.061,-.19),(.088,.21),(.115,.13),(.159,-.16),(.207,.11),(.296,-.08),(.389,.07),(.46,.035))):
            h[int((delay+side*.0019*(i%3))*rate)]=wet*gain
        n=len(a)+len(h)-1;nfft=1<<(n-1).bit_length();chans.append(np.fft.irfft(np.fft.rfft(a,nfft)*np.fft.rfft(h,nfft),nfft)[:n])
    return np.column_stack(chans)
def save(name,a,gain=.7,reverb=.5):
    if a.ndim==1:a=hall(a,reverb)
    fade=min(160,len(a)//4);a[:fade]*=np.linspace(0,1,fade)[:,None];a[-fade:]*=np.linspace(1,0,fade)[:,None]
    a=np.tanh(a/(np.max(np.abs(a))+1e-9)*1.49)*gain
    with wave.open(str(out/('S_'+name+'.wav')),'wb') as w:w.setparams((2,2,rate,0,'NONE','not compressed'));w.writeframes((a*32767).astype('<i2').tobytes())
def make_fx(name,d):
    u=t(d);n=len(u)
    if name=='Swing':
        a=bandnoise(n,850,6500)*np.exp(-((u-.115)/.055)**2)+.29*np.sin(2*pi*(850*u-800*u*u))*np.exp(-((u-.126)/.064)**2)
    elif name=='Dodge':a=bandnoise(n,110,750)*np.exp(-((u-.13)/.085)**2)+.36*bandnoise(n,800,2350)*np.exp(-((u-.26)/.038)**2)
    elif name in ['Impact','Shield','Parry']:
        base={'Impact':207,'Shield':126,'Parry':554}[name];a=.8*ring(u,base,[1,1.56,2.72,4.13,6.7],.20 if name!='Parry' else .49)+.86*bandnoise(n,680,6800)*np.exp(-u*49)+.46*ring(u,69,[1,2.22],.055)
        if name=='Parry':a+=.7*ring(u,843,[1,1.337,2.006,2.99],.53)
    elif name=='Break':
        a=1.21*ring(u,63,[1,1.45,2.68],.17)+.81*bandnoise(n,195,6900)*np.exp(-u*14)
        for k in range(25):
            at=rng.uniform(.011,.49);idx=int(at*rate);v=u[:n-idx];f=rng.uniform(294,1700)
            a[idx:]+=(.56-k*.013)*ring(v,f,[1,1.93,3.52],rng.uniform(.071,.24))
    elif name in ['Stomp','BodyHit','Step','HeavyStep']:
        decay={'Stomp':.30,'BodyHit':.086,'Step':.048,'HeavyStep':.092}[name];freq={'Stomp':43,'BodyHit':67,'Step':95,'HeavyStep':59}[name]
        a=.91*np.sin(2*pi*(freq*u+4.3*(1-np.exp(-u*22))))*np.exp(-u/decay)+.64*bandnoise(n,70,960)*np.exp(-u/(decay*.43))
        if name in ['Stomp','HeavyStep']:a+=.22*ring(u,188,[1,2.19,3.7],.12)+.16*bandnoise(n,670,5200)*np.exp(-u/.072)
    elif name=='Bell':a=ring(u,146.83,[1,1.202,2.01,2.67,4.09],.93)*(1-np.exp(-u*170))
    return a
pi=math.pi
for name,d in [('Swing',.59),('Impact',.83),('Shield',.90),('Parry',1.38),('Dodge',.51),('Break',1.61),('Stomp',1.37),('BodyHit',.53),('Step',.27),('HeavyStep',.47),('Bell',2.45)]:
    save(name,make_fx(name,d),.42 if name in ['Step','HeavyStep'] else .73,.63)
for name,notes in [('Victory',[(0,146.83),(.16,220),(.36,293.66),(.62,349.22),(.92,440),(1.28,587.33)]),('Defeat',[(0,220.0),(.41,207.65),(.8,174.61),(1.29,146.83)])]:
    u=t(4.2);a=np.zeros_like(u)
    for at,f in notes:
        i=int(at*rate);v=u[:len(u)-i];a[i:]+=pluck(v,f,.97)+.31*pluck(v,f*.5,1.1)
    save(name,a,.62,.99)
# A slow D/A pedal and antiphonal bell harmonics, tuned to integer loop cycles.
duration=24;u=t(duration);n=len(u);chans=[]
for side in (-1,1):
    a=np.zeros_like(u)
    for k,(freq,amp) in enumerate([(73.416,.125),(110,.095),(146.83,.061),(220,.026),(293.66,.018),(349.23,.014)]):
        f=round(freq*duration)/duration
        a+=amp*(.81+.19*np.sin(2*pi*(k%3+1)*u/duration+side*.2*k))*np.sin(2*pi*f*u+.18*np.sin(2*pi*u/duration)+k+side*.13*k)
    for at,note in [(1.7,440),(7.6,349.23),(13.45,293.66),(18.6,329.63)]:
        v=np.mod(u-at,duration);a+=.062*pluck(v, note,1.15)*(1+side*.10*math.sin(at))
    wind=bandnoise(n,59,540);wind*=np.sin(pi*u/duration)**2
    a+=.011*wind
    chans.append(a)
amb=np.column_stack(chans)
with wave.open(str(out/'S_Chapel.wav'),'wb') as w:w.setparams((2,2,rate,0,'NONE','not compressed'));w.writeframes((amb*32767).astype('<i2').tobytes())
# Aperiodic-looking but exactly tileable mineral flecks and hairline veins.
N=512;y,x=np.mgrid[:N,:N];k=np.hypot(np.fft.fftfreq(N)[:,None]*N,np.fft.fftfreq(N)[None,:]*N)
def field(c):
    v=np.fft.ifft2(np.fft.fft2(rng.normal(size=(N,N)))*np.exp(-(k/c)**2)).real
    return v/v.std()
coarse=field(6);fine=field(59);grain=field(250);veins=np.exp(-np.abs(coarse+.21*field(21))*24)
arr=np.uint8(np.clip(209+13*coarse+7*fine+8*grain-19*veins,120,253))
def chunk(tag,b):return struct.pack('>I',len(b))+tag+b+struct.pack('>I',zlib.crc32(tag+b)&0xffffffff)
raw=b''.join(b'\0'+r.tobytes() for r in arr)
(out/'T_Mineral.png').write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',N,N,8,0,0,0,0))+chunk(b'IDAT',zlib.compress(raw,8))+chunk(b'IEND',b''))
print('Generated 14 stereo cues and a mineral tile in',out)
