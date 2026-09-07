"""Deterministic, seamless procedural material maps; colors are sRGB encodings
of plausible linear reflectance, not illumination painted into the textures."""
import numpy as np
from PIL import Image
from pathlib import Path
P=Path(__file__).resolve().parents[1]/'public/textures';P.mkdir(exist_ok=True)
rng=np.random.default_rng(3014);N=1024;y,x=np.mgrid[:N,:N];u=x/N;v=y/N
def save(name,base,h,strength=.2):
 rgb=np.clip(np.array(base)[None,None,:]*(1+strength*(h-.5))[:,:,None],0,1);srgb=np.where(rgb<=.0031308,12.92*rgb,1.055*rgb**(1/2.4)-.055);Image.fromarray((srgb*255).astype('uint8')).save(P/(name+'.png'))
 dx=(np.roll(h,-1,1)-np.roll(h,1,1))*.3;dy=(np.roll(h,-1,0)-np.roll(h,1,0))*.3;n=np.stack([-dx,-dy,np.ones_like(h)],2);n/=np.linalg.norm(n,axis=2)[:,:,None];Image.fromarray(((n*.5+.5)*255).astype('uint8')).save(P/(name+'-normal.png'))
noise=rng.random((N,N));grain=np.sin(u*2*np.pi*90+np.sin(v*2*np.pi*3)*2)*.15+np.sin(u*2*np.pi*220+np.sin(v*2*np.pi*7))*.1
row=(x//48);board=rng.uniform(.15,.8,(22,5));h=board[row,(y//256+(row%2))%5]+grain+noise*.09;h[(x%48)<2]=-.5;h[(y+(row%2)*128)%512<2]=-.5
save('oak',(.25,.12,.055),h,.65)
h=noise*.15+.45;save('plaster',(.72,.70,.65),h,.05)
h=.35+noise*.3;h[(x%256<3)|(y%256<3)]=-.2;save('stone',(.38,.36,.31),h,.35)
h=noise*.55+.25+np.sin(x*2.7+y*.35)*.12;save('grass',(.075,.17,.035),h,.9)
h=.4+np.sin(x*np.pi/3)*.16+np.sin(y*np.pi/3)*.16+noise*.08;save('weave',(.36,.29,.18),h,.4)
h=.5+.3*np.sin(u*2*np.pi*16)+noise*.1;h[y%128<4]=0;save('tile',(.27,.085,.035),h,.5)
print('Material maps ready')
