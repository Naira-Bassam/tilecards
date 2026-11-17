# ChatGPT image prompt — v3 (no number badge, design-quality rules, valid examples)

## Attach, in this order
1. `shapes_reference.png`    → IMAGE 1: the ONLY allowed tiles
2. `valid_examples.png`      → IMAGE 2: three CORRECT results (cat, fish, rabbit) built only from IMAGE 1 tiles — shows the quality level and how details are made from tiles
3. your own reference cards/grids (optional) → IMAGE 3: style only
4. `blank_card_template.png` → IMAGE 4: the empty card (no number badge)

## Paste as ONE message (change only the last 2 lines)

```
You are a TILE-PUZZLE composer, not an illustrator. You never draw a picture and then overlay a grid.
You place pre-made tiles into cells; the picture appears only as the result of the tiles touching.

IMAGES
- IMAGE 1 = the COMPLETE catalogue of allowed tiles (a black shape on white, each in its own square).
- IMAGE 2 = three correct finished examples (cat, fish, rabbit). They show the expected QUALITY and how eyes, ears, tail, fins and bodies are made from tiles. Never copy their layout.
- IMAGE 3 = extra style examples, if provided.
- IMAGE 4 = blank card. Keep its layout, colours and grid exactly. There is NO number and NO badge on the card.

STEP 1 - PLAN IN TEXT FIRST (before generating any image)
Write a 5x5 table (rows 1-5 top to bottom, columns A-E left to right). For every cell write EMPTY or:
"tile at row r, column c of IMAGE 1, rotation 0/90/180/270, mirrored yes/no".
- Every cell holds ONE whole tile or is EMPTY. 10-22 filled cells is typical; filling all 25 is not required.
- EVERY part of the character (head, ears, eyes, beak, body, wings, tail, legs, trunk...) must come from a tile in the table.
- If no tile can make a detail (thin legs, toes, claws, whiskers, fingers), do NOT draw it. Use the closest tile (bar, triangle, square) or leave it out.
- Curves only from the curved tiles that exist in IMAGE 1 (quarter-discs, semicircles, circles, rings, arcs). No smooth outline running through several cells.
- Make diagonals and curves continue correctly into the neighbouring cell.

DESIGN QUALITY (the picture must be recognisable, not just valid)
- Do not make the character a solid block. Use at least 6 DIFFERENT tile types and keep plain full-black squares to a minimum.
- Give it its signature features from tiles: eyes (a black square with a round hole, or a small circle), ears/beak/trunk/fins/tail from triangles, quarter-discs, rings or bars. Animals need eyes.
- Shape the head and body with diagonal and curved tiles (cheeks, shoulders, chin, back). Break symmetry where natural (curled tail, different sides).
- Use empty cells to define the outline. Centre the character and use most of the grid.
- Every request gets a NEW composition: change pose, view (front/side) and emphasised feature.

STEP 2 - GENERATE THE IMAGE FROM THE TABLE (cell by cell)
HARD RULES
1. Grid: EXACTLY 5 columns and EXACTLY 5 rows = 25 square cells (not 6 rows, not 4). Same size/position as IMAGE 4.
2. Each tile fills its own cell at its ORIGINAL size. Allowed: rotate 90/180/270, mirror. Forbidden: scale, crop, stretch, thin, redraw, merge tiles, add new shapes.
3. Inside the grid: pure black on pure white only. No gray, colour, shading, outlines, thin lines, text, decoration.
4. Grid lines are drawn AFTER the tiles: thin, light grey, straight, evenly spaced.

STEP 3 - AUDIT BEFORE ANSWERING
Check every cell against IMAGE 1. If any cell has a shape that is not in IMAGE 1 (or a scaled/thinned/stretched version), or the grid is not 5x5, regenerate. Deliver only an image that passes.

CARD (follow IMAGE 4)
Turquoise rounded card, white panel with the grid on top. Below it, centred: the Arabic name large and bold, and under it the English name in capitals.
Nothing else on the card. Copy the text exactly; correct Arabic letter joining, right-to-left.

REQUEST
Character (English): Owl
Character (Arabic): بومة
```

## Follow-up messages if a rule is broken
- Wrong grid: `The grid has N rows. It must be exactly 5 columns x 5 rows. Regenerate, same character.`
- Invented shape: `The [part] is not made of tiles from IMAGE 1. Redo it using only tiles from IMAGE 1, or leave that detail out.`
- Drawing look: `This looks like a drawing with a grid on top. Rebuild it cell by cell from whole tiles at original size.`
- Plain block: `Too many plain black squares and no face. Add eyes and shape the outline with diagonal and curved tiles.`
