/* tilecard.js — deterministic renderer: JSON spec -> SVG card.  No AI inside; the model only writes the JSON. */
(function (g) {
  const CAT = g.TILE_CATALOG; // {tiles:{id:{d}}, orients:{key:{tile,rot,flip}}}
  function cellTransform(o) {
    // flip first, then rotate clockwise about the tile centre (matches build_catalog.py)
    return `${o.rot ? `rotate(${o.rot} 50 50) ` : ''}${o.flip ? 'translate(100 0) scale(-1 1)' : ''}`.trim();
  }
  function validate(spec) {
    const errs = [];
    if (!spec || !Array.isArray(spec.grid) || spec.grid.length !== 5) errs.push('grid must have 5 rows');
    else spec.grid.forEach((row, r) => {
      if (!Array.isArray(row) || row.length !== 5) errs.push(`row ${r} must have 5 cells`);
      else row.forEach((k, c) => { if (k !== '.' && k !== '#' && !CAT.orients[k]) errs.push(`unknown tile "${k}" at row ${r}, col ${c}`); });
    });
    return errs;
  }
  function gridGroup(spec, opts) {
    const o = Object.assign({ cell: 100, fill: '#111', stroke: null }, opts);
    let s = '';
    for (let r = 0; r < 5; r++) for (let c = 0; c < 5; c++) {
      const k = (spec.grid[r] || [])[c] || '.';
      let inner = '';
      if (k === '#') inner = `<rect width="100" height="100" fill="${o.fill}" ${o.stroke ? `stroke="${o.stroke}"` : ''}/>`;
      else if (k !== '.') {
        const ori = CAT.orients[k];
        if (!ori) inner = `<rect x="8" y="8" width="84" height="84" fill="#e33" opacity=".5"/>`;
        else inner = `<g transform="${cellTransform(ori)}"><path d="${CAT.tiles[ori.tile].d}" fill="${o.fill}" fill-rule="evenodd" ${o.stroke ? `stroke="${o.stroke}" stroke-width="${o.sw || 2}" stroke-linejoin="round"` : ''}/></g>`;
      }
      s += `<g transform="translate(${c * 100} ${r * 100})">${inner}</g>`;
    }
    return s;
  }
  function esc(t) { return String(t).replace(/[&<>]/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[m])); }
  function cardSVG(spec) {
    const W = 400, H = 540, GP = 30, GS = 340, M = 10, cs = (GS - 2 * M) / 5; // cell size in px
    const k = cs / 100;
    let lines = '';
    for (let i = 0; i <= 5; i++) {
      lines += `<line x1="${GP + M + i * cs}" y1="${GP + M}" x2="${GP + M + i * cs}" y2="${GP + M + 5 * cs}" stroke="#9aa1a8" stroke-width="1.5"/>`;
      lines += `<line x1="${GP + M}" y1="${GP + M + i * cs}" x2="${GP + M + 5 * cs}" y2="${GP + M + i * cs}" stroke="#9aa1a8" stroke-width="1.5"/>`;
    }
    const isz = 0.1; // icon: 500 units -> 50px
    return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" font-family="Cairo, 'Noto Sans Arabic', Arial, sans-serif">
<rect width="${W}" height="${H}" rx="30" fill="#58C3DF"/>
<rect x="${GP}" y="${GP}" width="${GS}" height="${GS}" rx="6" fill="#fff"/>
<g transform="translate(${GP + M} ${GP + M}) scale(${k})">${gridGroup(spec)}</g>${lines}
<g transform="translate(${W / 2 - 25} 386) scale(${isz})">${gridGroup(spec, { fill: '#fff', stroke: '#14566f', sw: 9 })}</g>
<text x="${W / 2}" y="486" text-anchor="middle" font-size="40" font-weight="800" fill="#0f2a3a" direction="rtl">${esc(spec.name_ar || '')}</text>
<text x="${W / 2}" y="520" text-anchor="middle" font-size="24" font-weight="800" fill="#0f2a3a" letter-spacing="1">${esc((spec.name_en || '').toUpperCase())}</text>
<path d="M0 ${H - 62} a62 62 0 0 1 62 62 H30 a30 30 0 0 1 -30 -30 z" fill="#7a63a8" opacity="0"/>
${spec.number ? `<circle cx="30" cy="${H - 30}" r="22" fill="#7a63a8"/><text x="30" y="${H - 22}" text-anchor="middle" font-size="22" font-weight="800" fill="#fff">${esc(spec.number)}</text>` : ''}
</svg>`;
  }
  g.TileCard = { cardSVG, validate, gridGroup, cellTransform };
})(typeof window !== 'undefined' ? window : globalThis);
