# ChatGPT image prompt — v4

Attach in this order:
1. `shapes_reference.png`  → IMAGE 1 (the only allowed tiles)
2. `valid_examples.png`    → IMAGE 2 (three correct results: cat, fish, rabbit)
3. `blank_card_template.png` → IMAGE 3 (empty card, no number)

Paste as ONE message. Change only the last two lines.

```
ROLE
You compose pictures from puzzle tiles on a 5 x 5 grid. You are NOT an illustrator: never draw a picture and put a grid over it.
You choose one whole tile per cell; the picture appears only where tiles touch.

IMAGES
IMAGE 1 = the complete catalogue of allowed tiles. Nothing outside it may appear in the grid.
IMAGE 2 = three correct results (cat, fish, rabbit): quality level and the way details are made from tiles. Never copy their layout.
IMAGE 3 = blank card. Keep its layout, colours and 5x5 grid exactly. The card has no number and no badge.

SIMPLICITY RULE (most important for quality)
A clear, simple, well-connected picture is better than a complicated one. Build the picture mainly from these simple tiles of IMAGE 1:
full black square; empty cell; half-square triangles (black fills the bottom-left, bottom-right, top-left or top-right half, split by a diagonal);
quarter-discs (a rounded corner); circle; black square with a round white hole (used as an EYE); small tent triangle and inverted tent triangle (used as ear / nose / beak);
semicircle; square with a triangular notch; bowtie; thick quarter ring (used as a curled tail); plain bars.
Patterned or decorative tiles (grids of small squares, stripes, wheels, fans, saw blades, stars, spirals, tiny floating squares) are FORBIDDEN unless the character truly needs them.
Never place a tile that does not connect to the rest of the picture (no floating bits).

METHOD - follow in order, write steps 1-3 in the chat BEFORE generating the image
Step 1  SILHOUETTE: draw a 5x5 mask with # (black) and . (white). Decide the 2-3 features that make the character recognisable
        (ears, beak, trunk, tail, fins, wings, mane...). Exaggerate them. Use 10-20 black cells. Symmetric for front views.
Step 2  TILES: turn each cell into a tile.
        - black cell inside the shape      -> full black square
        - diagonal edge (45 degrees)       -> half-square triangle facing the right way
        - rounded edge                     -> quarter-disc, semicircle or circle
        - eye                              -> black square with round white hole (or a small circle)
        - empty                            -> EMPTY
        Write a table: row 1..5, columns A..E, each cell = tile name + rotation/mirror, or EMPTY.
Step 3  CHECK: diagonals and curves continue into neighbouring cells; every part (ears, eyes, beak, body, tail, legs) is made of a tile;
        if a detail cannot be made from a tile (thin legs, toes, claws, whiskers, fingers) it is LEFT OUT. A character without feet is fine.
Step 4  GENERATE exactly what the table says, cell by cell.

HARD RULES
1. Exactly 5 columns x 5 rows = 25 square cells (never 6 rows). Same grid position and size as IMAGE 3.
2. Each tile fills its own cell at its original size. Allowed: rotate 90/180/270, mirror. Forbidden: scale, crop, stretch, thin, redraw, merge, invent.
3. Inside the grid: pure black and pure white only. No gray, colour, shading, outlines, thin lines, text.
4. Grid lines are thin, light grey, straight, and drawn after the tiles.
5. Every request gets a new composition (pose, view, emphasis).

FINAL AUDIT before answering
Compare every cell with IMAGE 1. If any cell contains something that is not an exact tile from IMAGE 1, or the grid is not 5x5, or the picture does not read as the character at a glance, redo it.

CARD
Turquoise rounded card, white panel with the grid on top. Below it, centred: the Arabic name in large bold letters and under it the English name in capitals.
Nothing else on the card. Copy the text exactly, with correct right-to-left Arabic letter joining.

WORKED EXAMPLES OF STEP 1-2 (layout only, for other characters)
CAT (front)                         FISH (facing right)                 RABBIT (front)
mask:  . # . # .                    mask:  . . # . .                    mask:  . # . # .
       . # # # .                           # # # # .                           . # . # .
       # # # # #                           # # # # .                           . # # # .
       . # # # .                           # # # # .                           . # # # .
       . # # # #                           . . . . .                           # # # # #
tiles: ears = triangles (apex up, outer side vertical); eyes = black squares with round white holes; cheeks = triangles at the sides;
       nose = inverted triangle in the centre cell; body top corners = quarter-discs; tail = thick quarter ring curling up.
       fish: tail = two triangles; back fin = one triangle; body corners = triangles; eye = square with round hole.
       rabbit: ears = tall black columns; eyes = two notch tiles + a bowtie tile forming two white diamonds; feet = triangles at the bottom corners.

REQUEST
Character (English): Owl
Character (Arabic): بومة
```

## If a rule is broken
- Wrong grid: `The grid has N rows. It must be exactly 5 columns x 5 rows. Regenerate.`
- Invented/odd tile: `The [part] is not an exact tile from IMAGE 1. Rebuild with simple tiles only, or leave the detail out.`
- Messy/noisy: `Too many different tiles and floating bits. Redo with the simple tiles only, start from the 5x5 mask.`
- Looks like a drawing: `Rebuild it cell by cell from whole tiles at original size.`
