#!/usr/bin/env node
/** Actual adjacent converter, three host-decoded NUFLI targets.
 * Writes only research artifacts; no app edits, emulator, browser or downloads.
 */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { spawnSync } = require('node:child_process');

const root = path.resolve(__dirname, '../..');
let app = path.resolve(root, '../c64');
let output = path.join(root, 'build/research/nufli/converter-variants');
for (let i = 2; i < process.argv.length; i += 2) {
  assert.ok(['--app', '--output'].includes(process.argv[i]), 'Use --app PATH or --output PATH');
  assert.ok(process.argv[i + 1], 'Missing option path');
  if (process.argv[i] === '--app') app = path.resolve(process.argv[i + 1]);
  else output = path.resolve(process.argv[i + 1]);
}
const base = path.join(root, 'build/research/nufli');
const cases = [
  ['forgotten', '03-FORGOTTEN___.NUF',
    '7f5a5c5bff0bc9e5f5dbdeac66bb6ea263a7e76155dfd9507c51d87b266637dd',
    '8cc4caf3cf94363e11b0c32f3ce500124946bba764750464615c90d2dcf4ebf4'],
  ['oldsmobil', '04-OLDSMOBIL___.NUF',
    '346539f232c7b73437b17c442799b1e1457f21d7c30de2a00fee2029138b3bb8',
    '4cb1bce269d858a5525a11f24112549a14fe9bdc94756ba241f898bbf25c13ad'],
  ['wrong-way', '03-WRONG_WAY___.NUF',
    'c443239cd27be998b6d2879143ba324302f0101186192837792dc8c7586b6883',
    'f0386d4d99bf26f68757ae3a46a456efc69de7e33dc522192f205e563c6a88d4']
];
const sha = data => crypto.createHash('sha256').update(data).digest('hex');
function execute(program, args, cwd = root) {
  const run = spawnSync('rtk', ['proxy', program, ...args], { cwd, encoding: 'utf8', maxBuffer: 8 * 1024 * 1024 });
  assert.equal(run.status, 0, `${program} failed: ${run.stderr}`);
  return run.stdout;
}
function digestFiles(directory, names) {
  return names.map(file => ({ file, sha256: sha(fs.readFileSync(path.join(directory, file))) }));
}
function saveBinary(file, bytes) {
  if (fs.existsSync(file)) {
    assert.deepEqual(fs.readFileSync(file), Buffer.from(bytes), 'Existing artifact differs; choose a new output folder');
  } else fs.writeFileSync(file, bytes);
}
function paletteFile(file) {
  return fs.readFileSync(file, 'utf8').split(/\r?\n/)
    .filter(line => line.trim() && !line.trimStart().startsWith('#'))
    .map(line => line.trim().split(/\s+/).slice(0, 3).map(value => parseInt(value, 16)));
}
function mismatches(actual, expected) {
  assert.equal(actual.length, expected.length);
  return actual.reduce((count, value, i) => count + Number(value !== expected[i]), 0);
}
const python = String.raw`
import hashlib,json,sys
from pathlib import Path
from PIL import Image
root,out,original,indices,palette_file=map(Path,sys.argv[1:])
sys.path.insert(0,str(root/'research/nufli'))
from decode_nuf import decode
sha=lambda b:hashlib.sha256(b).hexdigest()
palette=[tuple(int(v,16) for v in line.split()[:3]) for line in palette_file.read_text().splitlines()
         if line.strip() and not line.lstrip().startswith('#')]
assert len(palette)==16
target=indices.read_bytes(); preview=(out/'expected-indices.bin').read_bytes()
assert len(target)==len(preview)==64000 and max(target)<16 and max(preview)<16
input_decoded,*_=decode(original.read_bytes())
assert input_decoded==target,'Stored host input differs from independent logical decoder'
nuf=(out/'converted.nuf').read_bytes()
program=(out/'converted.prg').read_bytes()
load=int.from_bytes(program[:2],'little')
assert load==0x0801
first=2+0x2000-load
payload=bytes((0,0x20))+program[first:first+0x5a00]
assert payload==nuf,'Public PRG payload differs from public NUF export'
got,owners,controls,uncovered=decode(nuf)
from_program,*_=decode(payload)
differences=[dict(x=i%320,y=i//320,expected=want,actual=actual)
             for i,(actual,want) in enumerate(zip(got,preview)) if actual!=want]
assert got==from_program
for name,values in [('input-target.png',target),('fitted-preview.png',preview),('independent-export.png',got)]:
 image=Image.new('RGB',(320,200));image.putdata([palette[v] for v in values]);image.save(out/name)
result=dict(status='pass' if not differences else 'fail',all64000_input_host_indices_match_original_logical_decode=True,
            fitted_preview_vs_independent_export_mismatches=len(differences),
            mismatches=differences,PRG_payload_equals_NUF=True,ownership=owners,
            register_control_kinds=controls,uncovered_bug_fallback_pixels=uncovered,
            source_target_changed_pixels=sum(a!=b for a,b in zip(target,preview)),
            independent_export_indices_sha256=sha(got),
            scope='Logical NUFLI file decoding only; these original targets and fitted exports are not native-proven by this check')
(out/'independent-decode.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
`;

function main() {
  fs.mkdirSync(output, { recursive: true });
  const appNames = ['fli.js', 'nufli-data.js', 'nufli.js', 'nufli-export.js', 'nufli/source.json',
    'tests/fixtures/sprite-images.cjs', 'tests/fixtures/nufli-decode.cjs', 'palettes/colodore.vpl'];
  const sources = digestFiles(app, appNames);
  const researchSources = digestFiles(root, ['research/nufli/decode_nuf.py', 'research/nufli/extract.py',
    'palettes/colodore.vpl', 'build/research/nufli/decode-validation.json', 'build/research/nufli/extraction.json']);
  const extraction = JSON.parse(fs.readFileSync(path.join(base, 'extraction.json')));
  const head = execute('git', ['rev-parse', 'HEAD'], app).trim();
  const status = execute('git', ['status', '--porcelain'], app).trim();
  const { createContext, palette, bands, image } = require(path.join(app, 'tests/fixtures/sprite-images.cjs'));
  const { decodeNufli } = require(path.join(app, 'tests/fixtures/nufli-decode.cjs'));
  const context = createContext(['fli.js', 'nufli-data.js', 'nufli.js', 'nufli-export.js']);
  const palettePath = path.join(app, 'palettes/colodore.vpl');
  assert.deepEqual(palette.map(color => color.rgb), paletteFile(palettePath));
  assert.deepEqual(paletteFile(palettePath), paletteFile(path.join(root, 'palettes/colodore.vpl')));
  const results = [];
  const receipt = { status: 'running', application: app, application_head: head,
    application_status_at_start: status, application_worktree_clean_at_start: status === '',
    application_sources: sources, research_sources: researchSources,
    script_sha256: sha(fs.readFileSync(__filename)), node_version: process.version,
    palette_rgb: palette.map(color => color.rgb), cases: results,
    scope: 'Actual application fitter/public exporters, host-decoded targets, two independent file decoders; no browser/emulator/native/NTSC/physical-machine proof.',
    quality_note: 'Source-color changes are quality metrics; only preview/export disagreement fails the logical consistency gate.' };
  const save = () => fs.writeFileSync(path.join(output, 'variants-audit.json'), JSON.stringify(receipt, null, 2) + '\n');
  save();
  for (const [id, stem, originalSha, targetSha] of cases) {
    const directory = path.join(output, id);
    fs.mkdirSync(directory, { recursive: true });
    const originalRecord = extraction.files.find(row => row.sha256 === originalSha);
    assert.ok(originalRecord, `Missing original extraction record for ${stem}`);
    const originalFile = path.join(root, originalRecord.path);
    const inputFile = path.join(base, `${stem}-indices.bin`);
    const original = fs.readFileSync(originalFile);
    const target = fs.readFileSync(inputFile);
    assert.equal(sha(original), originalSha);
    assert.equal(sha(target), targetSha);
    assert.equal(target.length, 64000);
    assert.ok(target.every(value => value < 16));
    assert.equal(mismatches(decodeNufli(original), target), 0);
    const pixels = image();
    for (let p = 0; p < target.length; p += 1) pixels.data.set([...palette[target[p]].rgb, 255], p * 4);
    const started = Date.now();
    const fitted = context.optimizeNufliImage(pixels, palette, bands);
    const nuf = context.encodeNufli(fitted);
    const program = context.encodeNufliPrg(fitted);
    const preview = Uint8Array.from({ length: 64000 }, (_, p) => {
      const rgb = Array.from(fitted.pixels.data.subarray(p * 4, p * 4 + 3));
      const color = palette.findIndex(entry => entry.rgb.every((value, i) => value === rgb[i]));
      assert.notEqual(color, -1, 'Fitted preview is not a real C64 palette color');
      assert.equal(fitted.pixels.data[p * 4 + 3], 255);
      return color;
    });
    saveBinary(path.join(directory, 'converted.nuf'), nuf);
    saveBinary(path.join(directory, 'converted.prg'), program);
    saveBinary(path.join(directory, 'expected-indices.bin'), preview);
    const localMismatch = mismatches(decodeNufli(nuf), preview);
    const independent = JSON.parse(execute('python3', ['-c', python, root, directory, originalFile, inputFile, palettePath]));
    const row = { id, input_stem: stem, original_program: originalFile, original_program_sha256: originalSha,
      target_indices: inputFile, target_indices_sha256: targetSha, original_native_proven: false,
      directory: path.relative(root, directory), status: localMismatch === 0 && independent.status === 'pass' ? 'pass' : 'fail',
      application_decoder_vs_fitted_preview_mismatches: localMismatch, independent_python_decode: independent,
      fit_export_analysis_wall_ms: Date.now() - started,
      program: 'converted.prg', program_bytes: program.length, program_sha256: sha(program),
      nuf: 'converted.nuf', nuf_bytes: nuf.length, nuf_sha256: sha(nuf),
      expected: 'expected-indices.bin', expected_pixels: preview.length, expected_sha256: sha(preview),
      fitted_preview_changed_pixels_vs_input: mismatches(preview, target),
      fitted_native_validation_status: 'not run; artifacts prepared for root-owned native validation' };
    results.push(row);
    fs.writeFileSync(path.join(directory, 'case-audit.json'), JSON.stringify(row, null, 2) + '\n');
    save();
    console.log(JSON.stringify({ id, status: row.status, changed_input_pixels: row.fitted_preview_changed_pixels_vs_input,
      preview_export_mismatches: localMismatch, independent_mismatches: independent.fitted_preview_vs_independent_export_mismatches,
      program: path.join(directory, 'converted.prg'), expected: path.join(directory, 'expected-indices.bin') }));
    assert.equal(row.status, 'pass', `Preview/export discrepancy in ${id}; artifacts retained, checker leaves application files unchanged`);
  }
  assert.deepEqual(digestFiles(app, appNames), sources, 'Actual loaded app sources changed during this run');
  assert.deepEqual(digestFiles(root, researchSources.map(row => row.file)), researchSources, 'Independent reference sources changed during this run');
  receipt.application_head_at_end = execute('git', ['rev-parse', 'HEAD'], app).trim();
  receipt.application_status_at_end = execute('git', ['status', '--porcelain'], app).trim();
  receipt.loaded_sources_unchanged_during_run = true;
  receipt.status = 'pass';
  save();
}

try { main(); } catch (error) { console.error(error); process.exitCode = 1; }
