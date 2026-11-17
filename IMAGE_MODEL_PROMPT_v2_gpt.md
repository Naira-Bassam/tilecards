# ChatGPT image prompt — v2 (fixes: invented legs, "illustration + grid overlay", thin lines)

## Attach, in this order
1. `shapes_reference.png`  (IMAGE 1 — the only allowed tiles)
2. your example grids / cards sheet  (IMAGE 2 — style only)
3. `blank_card_template.png`  (IMAGE 3 — layout to keep)

## Paste this as ONE message (edit the last 3 lines each time)

```
You are a TILE-PUZZLE composer, not an illustrator. You never draw a picture and then overlay a grid.
You place pre-made tiles into cells. The picture appears only as the result of the tiles touching.

IMAGES
- IMAGE 1 = the COMPLETE catalogue of allowed tiles (black shape on white, each in its own square).
- IMAGE 2 = finished examples. Style reference only. Do not copy any.
- IMAGE 3 = blank card. Keep its layout, colours and grid exactly.

STEP 1 - PLAN IN TEXT FIRST (write this before generating any image)
Write a 5x5 table (rows 1-5 top to bottom, columns A-E left to right). For every cell write either
EMPTY or: "tile #N from IMAGE 1 (position in the catalogue: row r, column c), rotation 0/90/180/270, mirrored yes/no".
Rules for the plan:
- Every cell holds ONE whole tile, or is EMPTY. 10-22 cells filled is typical; 25 is not required.
- Every part of the character (head, beak, eye, body, wing, tail, legs/feet, ears, trunk, etc.) must come from a tile in the table.
- If no tile in IMAGE 1 can make a detail (for example thin legs, toes, claws, whiskers, fingers), DO NOT draw that detail.
  Replace it with the closest tile (a bar, a triangle, a square) or leave it out. A character without feet is fine.
- Curves are allowed ONLY as the curved tiles that exist in IMAGE 1 (quarter-discs, semicircles, circles, arcs). No smooth outline that runs through several cells.
- Make sure diagonals and curves continue correctly into the neighbouring cell.

STEP 2 - GENERATE THE IMAGE FROM THE TABLE
Render exactly what the table says, cell by cell.
HARD RULES
1. Grid: EXACTLY 5 columns and EXACTLY 5 rows = 25 square cells. Not 6 rows. Same size/position as IMAGE 3.
2. Each tile fills its own cell at its ORIGINAL size. You may rotate (90/180/270) or mirror. You may NOT scale, crop, stretch, thin, redraw, merge two tiles into one shape, or add new shapes.
3. Inside the grid: pure black shapes on pure white only. No gray, no colour, no shading, no outlines, no thin lines, no text, no decoration.
4. Grid lines are drawn AFTER the tiles, thin, light grey, straight, evenly spaced.
5. The result must clearly read as the requested character (front or side view, stylised, centred).
6. Every request gets a NEW composition.

STEP 3 - AUDIT BEFORE YOU ANSWER
Look at the image you made, cell by cell, and compare with IMAGE 1. If ANY cell contains a shape that is not in IMAGE 1
(or a scaled/thinned/stretched version of one), or the grid is not 5x5, regenerate. Only deliver an image that passes.

CARD (follow IMAGE 3)
Turquoise rounded card, white panel with the grid on top; Arabic name large and bold below it, English name in capitals under that;
purple circle badge bottom-left with the number. Copy text exactly, correct Arabic letter joining, right-to-left.

REQUEST
Character (English): Cat
Character (Arabic): قطة
Card number: 11
```

## If the result still breaks a rule — reply with one of these
- Wrong grid:  `The grid has N rows. It must be exactly 5 columns x 5 rows. Regenerate, same character.`
- Invented shape: `The [legs/beak/tail] is not made of tiles from IMAGE 1. Redo it using only tiles from IMAGE 1, or leave that detail out.`
- Illustration look: `This looks like a drawing with a grid on top. Rebuild it cell by cell from whole tiles, each at original size.`

## Score each try with the table in `IMAGE_MODEL_PROMPT.md`
