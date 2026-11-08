#!/usr/bin/env node
/** Generate original mathematical artwork in NUFLI's actual hardware planes. */
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const crypto = require('node:crypto');
const { decodeNufli } = require('./decode-nufli.cjs');

const here = __dirname;
const output = path.join(here, 'build');
fs.mkdirSync(output, { recursive: true });
const provenance = JSON.parse(fs.readFileSync(path.join(here, 'SOURCE.json'), 'utf8'));
for (const entry of provenance.vendored_files) {
  const bytes = fs.readFileSync(path.join(here, entry.file));
  const hash = crypto.createHash('sha256').update(bytes).digest('hex');
  if (hash !== entry.sha256) throw new Error(`Vendored source identity changed: ${entry.file}`);
}
const source = ['nufli-data.js', 'nufli-export.js']
  .map(file => fs.readFileSync(path.join(here, file), 'utf8')).join('\n');
const { encodeNufli, encodeNufliPrg } = vm.runInNewContext(`${source}\n({ encodeNufli, encodeNufliPrg });`);

const plan = {
  bitmap: new Uint8Array(8000), screenColors: new Uint8Array(4000),
  spriteBits: new Uint8Array(3600), bugHiresBits: new Uint8Array(600),
  bugMulticolorBits: new Uint8Array(600), bugColors: new Uint8Array(400),
  registerUpdates: new Uint8Array(606)
};
const spectrum = [2, 8, 7, 13, 3, 14, 4, 10];
const initialUnderlay = [2, 8, 7, 5, 3, 4];
const initialEdge = [1, 2, 6, 7];
plan.registerUpdates.set(initialUnderlay);
for (let band = 0; band < 100; band += 1) {
  const edge = band === 0 ? initialEdge : [
    spectrum[(band >> 3) % 8], spectrum[((band >> 3) + 2) % 8],
    spectrum[((band >> 3) + 4) % 8], spectrum[((band >> 3) + 6) % 8]
  ];
  plan.bugColors.set(edge, band * 4);
}
for (let band = 1; band <= 100; band += 1) {
  const edge = plan.bugColors.subarray(Math.min(band, 99) * 4, Math.min(band, 99) * 4 + 4);
  plan.registerUpdates.set([
    spectrum[(band >> 3) % 8], 0x70 | edge[0], 0x50 | edge[1],
    0xe0 | edge[2], 0x60 | edge[3], spectrum[((band >> 3) + 4) % 8]
  ], band * 6);
}
for (let sprite = 0; sprite < 8; sprite += 1) {
  plan.registerUpdates[(63 + sprite * 2) * 6 + 5] = 0x11 + sprite * 2;
}

const inks = [1, 15, 13, 7, 10, 3];
const papers = [0, 6, 11, 4, 2, 9];
for (let band = 0; band < 100; band += 1) {
  for (let column = 0; column < 40; column += 1) {
    const ink = inks[(Math.floor(column / 3) + Math.floor(band / 8)) % inks.length];
    const paper = papers[(Math.floor(column / 7) + Math.floor(band / 10)) % papers.length];
    plan.screenColors[band * 40 + column] = (ink << 4) | paper;
  }
}
for (let y = 0; y < 200; y += 1) {
  for (let x = 0; x < 320; x += 1) {
    const radius = Math.hypot(x - 168, (y - 100) * 1.3);
    const wave = Math.sin(radius * 0.13 + 2 * Math.sin(y * 0.09)) + Math.sin(x * 0.06 - y * 0.08);
    const ink = x >= 312 ? ((x + y) & 3) < 2 : wave > 0.55;
    if (ink) plan.bitmap[(y >> 3) * 320 + (x >> 3) * 8 + (y & 7)] |= 128 >> (x & 7);
    if (x < 24 && ((x + y) % 12) < 2) {
      plan.bugHiresBits[y * 3 + (x >> 3)] |= 128 >> (x & 7);
    }
  }
  for (let x = 24; x < 312; x += 2) {
    const inside = ((x - 168) / 136) ** 2 + ((y - 100) / 88) ** 2 < 1;
    const exposed = inside ? Math.sin((x - 24) / 12 + y / 10) > -0.15 : ((x + 3 * y) % 28) < 8;
    if (exposed) {
      const bit = (x - 24) >> 1;
      plan.spriteBits[y * 18 + (bit >> 3)] |= 128 >> (bit & 7);
    }
  }
  for (let x = 0; x < 24; x += 2) {
    const code = (Math.floor(x / 4) + Math.floor(y / 4)) % 4;
    plan.bugMulticolorBits[y * 3 + (x >> 3)] |= code << (6 - (x & 7));
  }
}

const nuf = encodeNufli(plan);
const program = encodeNufliPrg(plan);
const indices = decodeNufli(nuf);
fs.writeFileSync(path.join(output, 'example.nuf'), nuf);
fs.writeFileSync(path.join(output, 'example.prg'), program);
fs.writeFileSync(path.join(output, 'indices.bin'), indices);
for (const [name, bytes] of Object.entries(plan)) fs.writeFileSync(path.join(output, `${name}.bin`), bytes);

const contributions = {};
for (const field of ['bitmap', 'spriteBits', 'bugHiresBits', 'bugMulticolorBits']) {
  const alternative = { ...plan, [field]: new Uint8Array(plan[field].length) };
  const pixels = decodeNufli(encodeNufli(alternative));
  contributions[field] = indices.reduce((sum, value, index) => sum + (value !== pixels[index]), 0);
  if (contributions[field] === 0) throw new Error(`Artwork fails to expose ${field}`);
}
const staticUpdates = new Uint8Array(plan.registerUpdates);
for (let band = 1; band <= 100; band += 1) {
  for (let slot = 0; slot < 6; slot += 1) {
    if ((staticUpdates[band * 6 + slot] >> 4) !== 1) staticUpdates[band * 6 + slot] = initialUnderlay[slot];
  }
}
const staticPixels = decodeNufli(encodeNufli({ ...plan, registerUpdates: staticUpdates }));
contributions.registerColorChanges = indices.reduce((sum, value, index) => sum + (value !== staticPixels[index]), 0);
if (contributions.registerColorChanges === 0) throw new Error('Artwork fails to expose raster color updates');
const histogram = Array.from({ length: 16 }, (_, color) => indices.reduce((sum, value) => sum + (value === color), 0));
const report = {
  title: 'Spectral interference weave', width: 320, height: 200,
  program_bytes: program.length, nuf_bytes: nuf.length,
  program_sha256: crypto.createHash('sha256').update(program).digest('hex'),
  nuf_sha256: crypto.createHash('sha256').update(nuf).digest('hex'),
  indices_sha256: crypto.createHash('sha256').update(indices).digest('hex'),
  color_histogram: histogram, counterfactual_changed_pixels: contributions,
  note: 'Counterfactuals are independently decoded file comparisons, not additional native captures.'
};
fs.writeFileSync(path.join(output, 'artwork.json'), JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report, null, 2));
