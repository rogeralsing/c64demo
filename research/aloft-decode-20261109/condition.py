#!/usr/bin/env python3
"""Source-bound finite proof of the earlier VICE checkpoint-condition failure."""
import argparse
import hashlib
import json
from pathlib import Path
import tarfile
import traceback

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/aloft-decode-20261109'
ARCHIVE = ROOT / 'build/research/quondam/hardware-source/vice-3.10.tar.gz'
ARCHIVE_SHA = '8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1'
OLD = ROOT / 'build/research/aloft-20261109'
OLD_PROOF = OLD / 'native-analysis/accepted-01/native-proof.json'
NEW_PROOF = BASE / 'native-analysis/accepted-01/native-proof.json'
PROOF_PINS = {
    OLD_PROOF: '02243d0cbae68edad8aa5a51aec9e22e9cfa4c52f918f1ba30db9e5226b19eb4',
    NEW_PROOF: 'bf53a544369a8acddde7354874b9f93302728497bd59a12c5c97b19e5c691b41',
}
EXPRESSIONS = {
    'old': '@ram:$0810 == $a9 && @ram:$0811 == $ff',
    'grouped': '(@ram:$0810 == $a9) && (@ram:$0811 == $ff)',
}
SOURCE_PINS = {
    'monitor/mon_parse.y': '895e22af66ca56a78dd1fda373f30d00f4ab19812f531a590aa2900e68e5bb12',
    'monitor/monitor.c': '9bf9005de5245b9645baeb953e88adc0bdeaf94277aa3469cb5e40e25e597edc',
    'monitor/mon_lex.l': None,
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def meta(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=sha(raw))


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def source_contract():
    assert sha(ARCHIVE.read_bytes()) == ARCHIVE_SHA
    result, contents = [], {}
    with tarfile.open(ARCHIVE) as archive:
        for relative, pin in SOURCE_PINS.items():
            member = 'vice-3.10/src/' + relative
            assert len([m for m in archive.getmembers() if m.name == member]) == 1
            raw = archive.extractfile(member).read()
            if pin is not None:
                assert sha(raw) == pin
            retained = BASE / 'autostart-analysis/source-01' / relative.replace('/', '__')
            assert retained.read_bytes() == raw
            contents[relative] = raw.decode()
            result.append(dict(member=member, member_sha256=sha(raw), retained=meta(retained)))
    grammar, evaluator, lexer = [contents[k] for k in ('monitor/mon_parse.y', 'monitor/monitor.c', 'monitor/mon_lex.l')]
    assert '%left<cond_op> COND_OP' in grammar
    assert 'cond_expr: cond_expr COND_OP cond_expr' in grammar
    assert '| L_PAREN cond_expr R_PAREN' in grammar
    assert 'evaluation is strictly left to right.' in grammar
    assert '==    { yylval.i = e_EQU; return COND_OP; }' in lexer
    assert '&&    { yylval.i = e_LOGICAL_AND; return COND_OP; }' in lexer
    assert 'cnode->value = (value_1 == value_2);' in evaluator
    assert 'cnode->value = (value_1 && value_2);' in evaluator
    assert 'uint8_t byte1;' in evaluator and 'return byte1;' in evaluator
    return dict(archive=meta(ARCHIVE), sources=result,
        grammar='All condition operators share the left-associative COND_OP token. Explicit parentheses create grouped subtrees.',
        RAM_read_domain=[0, 255], logical_AND_result_domain=[0, 1],
        old_tree=['==', ['&&', ['==', ['RAM', 0x0810], 0xa9], ['RAM', 0x0811]], 0xff],
        grouped_tree=['&&', ['==', ['RAM', 0x0810], 0xa9], ['==', ['RAM', 0x0811], 0xff]])


def load_case(proof_path):
    assert sha(proof_path.read_bytes()) == PROOF_PINS[proof_path]
    proof = json.loads(proof_path.read_text())
    assert proof['pass_'] and proof['session']['owned_process_reaped']
    found = {Path(row['path']).name: row for row in proof['case_files']}
    inputs, data = [meta(proof_path)], {}
    for name in ('events.jsonl', 'received.bin', 'sent.bin', 'input.bin'):
        path = ROOT / found[name]['path']
        assert meta(path) == found[name]
        inputs.append(meta(path))
        data[name] = path.read_bytes()
    rows = {r['sequence']: r for r in map(json.loads, data['events.jsonl'].decode().splitlines()) if r['kind'] == 'response'}
    for row in rows.values():
        raw = data['received.bin'][row['received_first']:row['received_end']]
        assert raw.decode(errors='replace') == row['response']
    return proof, rows, inputs, data


def finite_model():
    # C logical && returns integer0/1. Python's value-returning `and` must not
    # be used without these explicit Boolean conversions.
    old_true, grouped_true, witnesses = 0, 0, []
    for first in range(256):
        for second in range(256):
            old = int(bool(first == 0xa9) and bool(second)) == 0xff
            grouped = bool(first == 0xa9) and bool(second == 0xff)
            old_true += old
            grouped_true += grouped
            if grouped:
                witnesses.append([first, second])
    assert old_true == 0 and grouped_true == 1 and witnesses == [[0xa9, 0xff]]
    return dict(complete_byte_pairs=65536, old_true_pairs=old_true,
        grouped_true_pairs=grouped_true, grouped_true_witnesses=witnesses,
        reason='The old outermost comparison tests a C logical0/1 result against255. It is false for every possible pair of RAM bytes.',
        scope='Finite monitor-condition algebra, not C64 instruction execution or a general monitor parser.')


def run(out):
    old, old_rows, old_inputs, _ = load_case(OLD_PROOF)
    new, new_rows, new_inputs, _ = load_case(NEW_PROOF)
    assert old_rows[3]['command'] == 'break exec $0810 if ' + EXPRESSIONS['old']
    assert 'Setting checkpoint 1 condition to: ' + EXPRESSIONS['old'] in old_rows[3]['response']
    assert old_rows[4]['command'] == 'x' and old_rows[4]['status'] == 'interrupted'
    assert new_rows[24]['command'] == 'break 021c if ' + EXPRESSIONS['old']
    assert new_rows[25]['command'] == 'break 021c if ' + EXPRESSIONS['grouped']
    assert 'BREAK: 6  C:$021c' in new_rows[24]['response']
    assert 'BREAK: 7  C:$021c' in new_rows[25]['response']
    assert new_rows[27]['command'] == 'disable 4'
    assert new_rows[28]['status'] == 'completed' and new_rows[28]['command'] == 'x'
    assert new_rows[28]['response'].startswith('#7 (Stop on  exec 021c)')
    assert '#6 ' not in new_rows[28]['response']
    packet = next(c for c in new['captures'] if c['stem'] == 'first-packet-ready')
    packet_path = ROOT / packet['ram']['path']
    assert meta(packet_path) == packet['ram']
    assert packet_path.read_bytes()[0x0810:0x0812] == bytes.fromhex('a9ff')
    assert packet['registers']['pc'] == 0x021c and packet['registers']['clock'] == 9380860
    contract, algebra = source_contract(), finite_model()
    comparison = dict(old_checkpoint_sequence=3, old_guard=EXPRESSIONS['old'],
        old_missed_stop_is_explained_by_always_false_predicate=True,
        fresh_ungrouped_probe_sequence=24, fresh_grouped_probe_sequence=25,
        disabled_unconditional_packet_checkpoint_sequence=27, fresh_stop_sequence=28,
        actual_hit_checkpoint=7, actual_PC=0x021c, actual_clock=9380860,
        actual_guard_bytes=[0xa9, 0xff], source_and_native_grouped_result_agree=True,
        note='The fresh probes run at packet-ready021C against the original0810byte pair. They do not replay the older execution or alter its evidence.')
    body = dict(source=contract, finite_algebra=algebra, native_comparison=comparison)
    write(out / 'condition-contract.json', body)
    proof = dict(pass_=True, scope='Exact cause of an earlier always-false VICE guard, primary grammar/evaluator, exhaustive byte-pair algebra and a fresh grouped-guard witness.',
        producer=meta(Path(__file__)), inputs=old_inputs + new_inputs + [meta(packet_path), meta(ARCHIVE)] + [s['retained'] for s in contract['sources']],
        expressions=EXPRESSIONS, results=body,
        outputs=[dict(name=p.name, bytes=p.stat().st_size, sha256=sha(p.read_bytes())) for p in sorted(out.iterdir())],
        limits=['Neither older native files nor their original unresolved-cause statements are overwritten.',
                'The finite domain is all65536pairs of unsigned byte reads for this exact expression, not arbitrary monitor conditions.',
                'The native witness establishes the grouped predicate at one originalpacket boundary; full native custody belongs to the separate closed-case proof.',
                'No emulator, CPU interpreter, process, network or downloaded host source runs in this producer.'])
    write(out / 'condition-proof.json', proof)
    return meta(out / 'condition-proof.json')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    output = parser.parse_args().output.resolve()
    assert output.is_relative_to(BASE / 'condition-analysis')
    output.mkdir(parents=True, exist_ok=False)
    source = Path(__file__).read_bytes()
    (output / 'condition.checked.py').write_bytes(source)
    try:
        print(json.dumps(dict(pass_=True, proof=run(output))))
    except Exception as error:
        write(output / 'failure.json', dict(pass_=False, error=repr(error), traceback=traceback.format_exc(), producer_sha256=sha(source)))
        raise
