import sys, json
from playwright.sync_api import sync_playwright
def shoot(specs, out, scale=1.0):
    with sync_playwright() as p:
        b=p.chromium.launch(); pg=b.new_page(viewport={'width':400*len(specs),'height':540},device_scale_factor=scale)
        html=open('harness.html').read().replace("<div id=o></div>","<div id=o style='display:flex'></div>")
        html=html.replace("document.getElementById('o').innerHTML=TileCard.cardSVG(window.SPEC||{grid:[]})",
          "document.getElementById('o').innerHTML=("+json.dumps(specs)+").map(s=>{const e=TileCard.validate(s);if(e.length)console.log(e.join(';'));return TileCard.cardSVG(s)}).join('')")
        pg.on('console',lambda m:print('JS:',m.text))
        pg.set_content(html); pg.wait_for_timeout(400); pg.screenshot(path=out); b.close()
if __name__=="__main__":
    specs=[json.load(open(f)) for f in sys.argv[2:]]; shoot(specs,sys.argv[1])
