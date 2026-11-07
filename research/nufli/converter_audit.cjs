#!/usr/bin/env node
/** Reproduce the bounded NUFLI audit of the adjacent, actual c64 converter.
 * No emulator/browser/host download is executed. Only pinned source text is
 * downloaded if absent; output is written under this research checkout.
 */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const crypto = require('node:crypto');
const { spawnSync } = require('node:child_process');

const root = path.resolve(__dirname, '../..');
let app = path.resolve(root, '../c64');
let output = path.join(root, 'build/research/nufli/converter-audit');
for (let i = 2; i < process.argv.length; i += 2) {
  assert.ok(['--app', '--output'].includes(process.argv[i]), 'Use --app PATH or --output PATH');
  assert.ok(process.argv[i + 1], 'Missing option path');
  if (process.argv[i] === '--app') app = path.resolve(process.argv[i + 1]);
  else output = path.resolve(process.argv[i + 1]);
}
const base = path.join(root, 'build/research/nufli');
const originalFile = path.join(base, 'amigaconverts+samples/02-SMOKING_FISH.NUF.prg');
const oracleFile = path.join(base, '02-SMOKING_FISH.NUF-indices.bin');
const originalSha = 'f44e6c1c3285683d2d73864e6d676e68539b77beb3e43daabd4a22adaa929093';
const oracleSha = '670f0c5aaf1d1e714ec5fb0f820f58dcd3719e73ef447b025e4fcf6395c0e426';
const sha = data => crypto.createHash('sha256').update(data).digest('hex');
function execute(program, args, cwd = root) {
  const run = spawnSync(program, args, { cwd, encoding: 'utf8', maxBuffer: 8 * 1024 * 1024 });
  assert.equal(run.status, 0, `${program} failed: ${run.stderr}`);
  return run.stdout;
}

// This address-formula reader is independent of the application's packing
// tables and RECOIL-based test fixture. Its logical pixels were matched against
// both native original-program screenshots before this converter audit.
const python = String.raw`
import hashlib,json,sys
from pathlib import Path
root,out,mode=Path(sys.argv[1]),Path(sys.argv[2]),sys.argv[3]
sys.path.insert(0,str(root/'research/nufli'))
from decode_nuf import decode,screen,normal_sbyte,sprite_row,bug_hires,bug_multi
original=root/'build/research/nufli/amigaconverts+samples/02-SMOKING_FISH.NUF.prg'
if mode=='plan':
 b=original.read_bytes()[2:]
 updates=[b[a+i] for i in range(101) for a in (0x400,0x480,0x800,0x880,0xc00,0xc80)]
 colors=[b[0x1ff7]&15,b[0x1ff1]&15,b[0x1ff6]&15,b[0x1ff0]&15]; bug=[]
 for i in range(100):
  if i:
   for command in updates[i*6:i*6+6]:
    kind=command>>4
    if kind in (7,5,14,6): colors[{7:0,5:1,14:2,6:3}[kind]]=command&15
  bug.extend(colors)
 plan={'bitmap':list(b[0x4000:0x5400]+b[0x1400:0x1f40]),
 'screenColors':[b[screen(i)+x] for i in range(100) for x in range(40)],
 'spriteBits':[b[normal_sbyte(24+x*16,y)] for y in range(200) for x in range(18)],
 'bugHiresBits':[b[bug_hires(y//2)+((sprite_row(y)+x)&63)] for y in range(200) for x in range(3)],
 'bugMulticolorBits':[b[bug_multi(y//2)+((sprite_row(y)+x)&63)] for y in range(200) for x in range(3)],
 'bugColors':bug,'registerUpdates':updates}
 print(json.dumps(plan))
elif mode=='check':
 native=(root/'build/research/nufli/02-SMOKING_FISH.NUF-indices.bin').read_bytes(); rows=[]
 for name in ('repacked-original.nuf','smoking-fish-current.nuf'):
  want=native if name=='repacked-original.nuf' else (out/'refitted-preview-indices.bin').read_bytes()
  blob=(out/name).read_bytes(); got,owners,controls,uncovered=decode(blob)
  count=sum(a!=b for a,b in zip(got,want)); assert count==0
  rows.append({'file':name,'sha256':hashlib.sha256(blob).hexdigest(),
   'independent_python_vs_declared_pixel_oracle_mismatches':count,
   'source_color_changes_from_native_original':sum(a!=b for a,b in zip(got,native)),
   'uncovered_bug_fallback_pixels':uncovered,'ownership':owners})
 print(json.dumps(rows))
else: raise ValueError(mode)
`;

async function main() {
  fs.mkdirSync(output, { recursive: true });
  const original = fs.readFileSync(originalFile);
  const expected = fs.readFileSync(oracleFile);
  assert.equal(sha(original), originalSha);
  assert.equal(sha(expected), oracleSha);
  assert.equal(expected.length, 64000);
  const nativeReceipt = path.join(base, 'native-analysis/native-comparison.json');
  const native = JSON.parse(fs.readFileSync(nativeReceipt));
  assert.equal(native.program_sha256, originalSha);
  assert.equal(native.logical_indices_sha256, oracleSha);
  assert.equal(native.exact_full_image_match, true);

  const provenance = JSON.parse(fs.readFileSync(path.join(app, 'nufli/source.json')));
  assert.equal(provenance.revision, 1440);
  const sourceFiles = [];
  for (const [name, expectedHash] of Object.entries(provenance.sha256)) {
    const local = path.join(output, name);
    if (!fs.existsSync(local)) {
      const response = await fetch(provenance.source + name);
      assert.equal(response.ok, true, `Source fetch failed for ${name}`);
      fs.writeFileSync(local, Buffer.from(await response.arrayBuffer()));
    }
    const bytes = fs.readFileSync(local);
    assert.equal(sha(bytes), expectedHash, `Pinned source changed: ${name}`);
    sourceFiles.push({ file: name, url: provenance.source + name, sha256: expectedHash });
  }
  const { createContext, palette, bands, image } = require(path.join(app, 'tests/fixtures/sprite-images.cjs'));
  const { decodeNufli } = require(path.join(app, 'tests/fixtures/nufli-decode.cjs'));
  const context = createContext(['fli.js', 'nufli-data.js', 'nufli.js', 'nufli-export.js']);
  const tables = vm.runInContext('C64_NUFLI_DATA', context);
  const header = fs.readFileSync(path.join(output, 'mufflon.h'), 'utf8').replace(/\/\*[\s\S]*?\*\//g, '');
  const sourceMatches = {};
  assert.equal(Object.keys(tables).length, 12);
  for (const [name, data] of Object.entries(tables)) {
    const expression = new RegExp('\\b' + name + '\\s*\\[[^=]*=\\s*\\{([\\s\\S]*?)\\};');
    const match = header.match(expression);
    assert.ok(match, `${name}: missing source array`);
    const values = (match[1].match(/0x[0-9a-f]+|\b\d+\b/ig) || []).map(Number);
    assert.deepEqual(Array.from(data), values, `${name}: original source array differs`);
    sourceMatches[name] = { entries: data.length, exact: true };
  }
  const nativePaletteFile = path.join(app, 'palettes/colodore.vpl');
  const nativePalette = fs.readFileSync(nativePaletteFile, 'utf8').split(/\r?\n/)
    .filter(line => line.trim() && !line.trimStart().startsWith('#'))
    .map(line => line.trim().split(/\s+/).slice(0, 3).map(value => parseInt(value, 16)));
  assert.deepEqual(palette.map(color => color.rgb), nativePalette);
  const mismatches = (actual, target) => {
    assert.equal(actual.length, target.length);
    return actual.reduce((sum, value, i) => sum + Number(value !== target[i]), 0);
  };
  const originalDecoderMismatch = mismatches(decodeNufli(original), expected);
  assert.equal(originalDecoderMismatch, 0);
  const plan = JSON.parse(execute('python3', ['-c', python, root, output, 'plan']));
  fs.writeFileSync(path.join(output, 'original-plan.json'), JSON.stringify(plan) + '\n');
  for (const key in plan) plan[key] = Uint8Array.from(plan[key]);
  const repacked = context.encodeNufli(plan);
  const repackedProgram = context.encodeNufliPrg(plan);
  fs.writeFileSync(path.join(output, 'repacked-original.nuf'), repacked);
  fs.writeFileSync(path.join(output, 'repacked-original.prg'), repackedProgram);
  const repackedDecoderMismatch = mismatches(decodeNufli(repacked), expected);
  assert.equal(repackedDecoderMismatch, 0);

  const target = image();
  for (let p = 0; p < expected.length; p += 1) target.data.set([...palette[expected[p]].rgb, 255], p * 4);
  const fitted = context.optimizeNufliImage(target, palette, bands);
  const fittedNuf = context.encodeNufli(fitted);
  const fittedProgram = context.encodeNufliPrg(fitted);
  const preview = Uint8Array.from({ length: 64000 }, (_, p) => {
    const rgb = Array.from(fitted.pixels.data.subarray(p * 4, p * 4 + 3));
    const color = palette.findIndex(entry => entry.rgb.every((v, i) => v === rgb[i]));
    assert.notEqual(color, -1, 'Preview pixel is not a real palette color');
    assert.equal(fitted.pixels.data[p * 4 + 3], 255);
    return color;
  });
  const exportMismatch = mismatches(decodeNufli(fittedNuf), preview);
  const sourceChanges = mismatches(preview, expected);
  assert.equal(exportMismatch, 0);
  fs.writeFileSync(path.join(output, 'smoking-fish-current.nuf'), fittedNuf);
  fs.writeFileSync(path.join(output, 'smoking-fish-current.prg'), fittedProgram);
  fs.writeFileSync(path.join(output, 'expected-indices.bin'), preview);
  fs.writeFileSync(path.join(output, 'refitted-preview-indices.bin'), preview);
  const pythonCheck = JSON.parse(execute('python3', ['-c', python, root, output, 'check']));

  const newerRegions = [['main', 0x1000, 0x11f5], ['detect', 0x1f40, 0x1f65],
    ['aux1', 0x23c0, 0x23de], ['aux2', 0x27c0, 0x27de], ['aux3', 0x2bc0, 0x2bde]];
  const changes = [];
  for (let i = 0; i < original.length; i += 1) if (original[i] !== repacked[i]) changes.push(i - 2);
  assert.ok(changes.every(i => newerRegions.some(([, first, end]) => first <= i && i < end)));
  const sources = ['fli.js', 'nufli.js', 'nufli-export.js', 'nufli-data.js', 'nufli/source.json',
    'tests/nufli.test.cjs', 'tests/fixtures/nufli-decode.cjs', 'tests/fixtures/sprite-images.cjs']
    .map(file => ({ file, sha256: sha(fs.readFileSync(path.join(app, file))) }));
  const gitHead = execute('git', ['rev-parse', 'HEAD'], app).trim();
  const gitStatus = execute('git', ['status', '--porcelain'], app).trim();
  const result = { status: 'pass', application: app, application_head: gitHead,
    application_worktree_clean: gitStatus === '', application_status: gitStatus,
    script_sha256: sha(fs.readFileSync(__filename)), node_version: process.version,
    original_program_sha256: originalSha, native_oracle_indices_sha256: oracleSha,
    original_native_receipt_sha256: sha(fs.readFileSync(nativeReceipt)),
    original_native_receipt: path.relative(root, nativeReceipt), source_files: sourceFiles, inputs: sources,
    sourceMatches, originalDecoderMismatch, repackedDecoderMismatch,
    fittedPreviewVsExportMismatch: exportMismatch, refitOriginalSourceColorChanges: sourceChanges,
    independent_python_decode: pythonCheck, original_repacked_changed_bytes: changes.length,
    all_changed_bytes_are_newer_original_player: true,
    original_repacked_regions: newerRegions.map(([name, first, end]) => ({ name, first, end,
      changed_bytes: changes.filter(i => first <= i && i < end).length })),
    program: 'smoking-fish-current.prg', programBytes: fittedProgram.length,
    programSha256: sha(fittedProgram), nufSha256: sha(fittedNuf),
    expected: 'expected-indices.bin', expectedPixels: expected.length,
    expectedSha256: sha(preview),
    palette_sha256: sha(fs.readFileSync(nativePaletteFile)),
    focused_tests_reproduction: 'node --test tests/nufli.test.cjs (run separately; this script does not claim to run them)',
    quality_note: 'Refit source-color changes are a quality measurement, not by themselves a preview/export correctness failure.',
    scope: 'Actual current fitter and public exporters, real native-proved picture, two independent file decoders. No emulator/browser/NTSC/physical-machine execution.' };
  fs.writeFileSync(path.join(output, 'application-audit.json'), JSON.stringify(result, null, 2) + '\n');
  console.log(JSON.stringify({ status: result.status, application_head: gitHead, clean: result.application_worktree_clean,
    originalDecoderMismatch, repackedDecoderMismatch, fittedPreviewVsExportMismatch: exportMismatch,
    refitOriginalSourceColorChanges: sourceChanges, programSha256: result.programSha256,
    receipt: path.relative(root, path.join(output, 'application-audit.json')) }, null, 2));
}
main().catch(error => { console.error(error); process.exitCode = 1; });
