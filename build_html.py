import json, base64, sys
c=json.load(open('catalog.json')); CORE=set(json.load(open('core.json')))
tiles={str(k):{"d":v["d"]} for k,v in c["tiles"].items()}
orients={o["key"]:{"tile":str(o["tile"]),"rot":o["rot"],"flip":o["flip"]} for o in c["orients"]}
cat="window.TILE_CATALOG="+json.dumps({"tiles":tiles,"orients":orients},separators=(',',':'))+";"
js=open('tilecard.js').read()
open('catalog.js','w').write(cat)
def font(fn): return base64.b64encode(open('node_modules/@fontsource/cairo/files/'+fn,'rb').read()).decode()
def build(embed_fonts):
    css = ("@font-face{font-family:Cairo;font-weight:800;src:url(data:font/woff2;base64,%s) format('woff2');unicode-range:U+0600-06FF,U+200C-200E,U+2010-2011,U+204F,U+2E41,U+FB50-FDFF,U+FE80-FEFC}"
           "@font-face{font-family:Cairo;font-weight:800;src:url(data:font/woff2;base64,%s) format('woff2');unicode-range:U+0000-00FF}") % (font('cairo-arabic-800-normal.woff2'),font('cairo-latin-800-normal.woff2')) if embed_fonts else ""
    link = "" if embed_fonts else '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Cairo:wght@800&display=swap">'
    return cat,js,css,link
if __name__=="__main__":
    cat,js,css,link=build(True)
    # test harness page: renders a spec from window.SPEC
    open('harness.html','w').write(f"<!doctype html><meta charset=utf-8><style>{css}body{{margin:0;background:#fff}}</style><body><div id=o></div><script>{cat}</script><script>{js}</script><script>document.getElementById('o').innerHTML=TileCard.cardSVG(window.SPEC||{{grid:[]}})</script>")
