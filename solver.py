"""solver.py — silhouette (SVG in a 0..5 viewBox, black = filled) -> 5x5 tile grid using only library tiles.
Per cell: try every allowed orientation, keep the one whose pixels best match the target."""
import json, io, sys, numpy as np, cairosvg
from PIL import Image
R=48
cat=json.load(open('catalog.json'))
CORE=set(json.load(open('core.json')))
CLEAN=set(int(k) for k in cat["tiles"])   # كل البلاطات (95)
def rast(svg_body,w=5*R):
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 5 5" width="{w}" height="{w}"><rect width="5" height="5" fill="#fff"/>{svg_body}</svg>'
    return np.array(Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode()))).convert('L'))<128
def tile_rast(d):
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="{R}" height="{R}"><rect width="100" height="100" fill="#fff"/><path d="{d}" fill="#000" fill-rule="evenodd"/></svg>'
    return np.array(Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode()))).convert('L'))<128
def xf(a,rot,flip):
    if flip: a=np.fliplr(a)
    return np.rot90(a,-(rot//90))
LIB=[]
base={i:tile_rast(cat['tiles'][str(i)]['d']) for i in CLEAN}
for o in cat['orients']:
    if o['tile'] in CLEAN: LIB.append((o['key'],xf(base[o['tile']],o['rot'],o['flip'])))
LIB.append(('.',np.zeros((R,R),bool)))
SIMPLE_BONUS={'.':0.02,'0a':0.02}   # prefer empty/full on ties -> cleaner designs
def solve(target):
    grid=[];score=0
    for r in range(5):
        row=[]
        for c in range(5):
            t=target[r*R:(r+1)*R,c*R:(c+1)*R]
            best=max(LIB,key=lambda kv:(1-(kv[1]!=t).mean())+SIMPLE_BONUS.get(kv[0],0))
            score+=1-(best[1]!=t).mean(); row.append(best[0])
        grid.append(row)
    return grid,score/25
if __name__=="__main__":
    body=open(sys.argv[1]).read()
    g,s=solve(rast(body)); print(json.dumps(g),round(s,3))
