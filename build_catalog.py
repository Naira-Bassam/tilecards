import json, io, numpy as np, cairosvg
from PIL import Image
paths=json.load(open('paths_raw.json'))
R=48
def raster(d):
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="{R}" height="{R}"><rect width="100" height="100" fill="#fff"/><path d="{d}" fill="#000" fill-rule="evenodd"/></svg>'
    return np.array(Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode()))).convert('L'))<128
def xform(a,rot,flip):
    if flip: a=np.fliplr(a)
    return np.rot90(a,-(rot//90))   # clockwise
def glyph(a,n=6):
    h=R//n; g=[]
    for r in range(n):
        g.append("".join('#' if a[r*h:(r+1)*h,c*h:(c+1)*h].mean()>0.5 else '.' for c in range(n)))
    return g
# decorative / photo-like tiles excluded from the default library
DECOR={13,14,30,31,45,46,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89,92,93,37,38}
NAMES={0:"full square",1:"tent (small triangle, base on bottom edge)",2:"bowtie (two triangles meeting at centre)",3:"half-square diagonal triangle",
4:"square with triangular notch",5:"big quarter disc",6:"big quarter disc (concave edge)",7:"small quarter disc in corner",8:"small quarter disc in corner",
9:"square with round hole",10:"square with big round hole",11:"small circle",12:"full circle",15:"wide shallow arc cap",16:"wide arc cap",17:"big curved wedge",18:"big curved wedge",
19:"arc cap",20:"arc cap",21:"curved slope",22:"curved slope",23:"curved slope",24:"curved sliver",25:"curved sliver",26:"curved corner",27:"semicircle bite from top",28:"half disc hanging from top",
29:"rounded wedge",32:"thick quarter ring",33:"centered small square",34:"square frame",35:"corner square",36:"L shape",39:"half rectangle (vertical bar)",40:"two opposite corner squares",41:"plus/cross",
42:"vertical bar centered",43:"two thin bars",44:"three thin bars",47:"edge square",48:"rounded square",49:"rounded square frame",50:"small corner triangle",51:"small corner triangle",
52:"octagon-corners cut (one)",53:"octagon (4 corners cut)",54:"two corners cut",55:"octagon frame",56:"gentle slope wedge",57:"slope (trapezoid)",58:"slope (trapezoid)",59:"gentle slope wedge",
60:"very low slope sliver",61:"low slope wedge",62:"slope wedge",63:"slope wedge",64:"slope wedge (tall)",65:"slope wedge (tall)",66:"low slope wedge",67:"sliver slope",68:"tall triangle (apex top centre)",
69:"diagonal band with corners",70:"diagonal stripe",71:"T / arrow shape",72:"chevron <",73:"X cross",74:"zigzag teeth (bottom)",90:"tiny centered square",91:"two small squares",94:"horizontal bar"}
tiles={};orients=[]
for i in range(95):
    d=paths[str(i)]; a=raster(d)
    tiles[i]={"name":NAMES.get(i,f"tile {i}"),"decor":i in DECOR,"d":d}
    seen=[]; k=0
    for flip in (0,1):
        for rot in (0,90,180,270):
            b=xform(a,rot,flip)
            if any((b!=s).mean()<0.012 for s in seen): continue
            seen.append(b)
            orients.append({"key":f"{i}{chr(97+k)}","tile":i,"rot":rot,"flip":flip,"glyph":glyph(b),"decor":i in DECOR}); k+=1
json.dump({"tiles":tiles,"orients":orients},open('catalog.json','w'))
core=[o for o in orients if not o["decor"]]
print("orientations total",len(orients),"core",len(core))
