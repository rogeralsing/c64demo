#!/usr/bin/env python3
"""Source-specific integer contours and marker drawing for original EOD."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT/'build/research/eod'
PINS = {
    'research/eod/frame_case.py': 'dccc4527a0a12f4df9f190dfcbd504a9b20c2747611e54fc20a404e062b886de',
    'build/research/eod/frame-analysis/accepted-01/frame-proof.json': 'ef77c7a2d93d110ce5caa8c60c313d8d7313325ba51e9d355cff9e855535bb50',
    'research/eod/geometry.py': '7c70f18cc1f586ddb8be70f8a4be5bd9ce67a456eb2d4772ef74cb3f97415d4b',
    'build/research/eod/geometry-analysis/accepted-01/geometry-proof.json': '33d4119215b249e76c8093a71d655cacb6b9d8c58804c73315915ef734a55cec',
    'build/research/eod/file-analysis/accepted-03/EdgeOfDisgrace_1a/trackmo-051.decoded.prg': 'e4899712681147b233a960d675aab369feebac4ba149073f1051d45f78b5312c',
    'build/research/eod/file-analysis/accepted-03/EdgeOfDisgrace_1a/trackmo-052.decoded.prg': '3adc5e1b6990cf41b3d93954de9d92bd3da62b4b562fc636cbd827cf94d67c04',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def artifact(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=sha(raw))


def load_geometry():
    spec = importlib.util.spec_from_file_location('eod_pinned_geometry', ROOT/'research/eod/geometry.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def adc(a, b, carry=0):
    value = a+b+carry
    return value & 255, int(value > 255)


def sbc(a, b, carry=1):
    value = a-b-(1-carry)
    return value & 255, int(value >= 0)


def add_word(word, step, carry=0):
    lo, carry = adc(word & 255, step & 255, carry)
    hi, carry = adc(word >> 8, step >> 8, carry)
    return lo | hi << 8, carry


def initialize_contour_tables(incoming):
    """$12F6 reciprocal builder, checked against an independent rational form."""
    memory = bytearray(incoming)
    for divisor in range(256):
        remainder, quotient = 1, 0
        for _ in range(24):
            doubled = remainder*2
            take = doubled >= 256 or (doubled & 255) >= divisor
            remainder = ((doubled & 255)-divisor) & 255 if take else doubled
            quotient = ((quotient << 1) | int(take)) & 0xffffff
        expected = 0xffffff if divisor <= 1 else (1 << 24)//divisor
        assert quotient == expected
        for page, shift in ((0xad00,0), (0xae00,8), (0xaf00,16)):
            memory[page+divisor] = (quotient >> shift) & 255
    return memory


class Contours:
    """Semantic source stages, not an instruction decoder/CPU state machine."""
    def __init__(self, incoming, half_entry_carry=1, outer_final_step=True):
        assert len(incoming) == 65536
        self.m = bytearray(incoming)
        assert [incoming[a] for a in (0xe9, 0xeb, 0xed, 0xef)] == [0xb0, 0xb2, 0xb4, 0xb6]
        self.edge_writes = set()
        self.intersection_reads = set()
        self.marker_writes = []
        self.internal_lines = []
        self.outer_edges = []
        self.edges = []
        self.cells_checked = set()
        self.half_entry_carry = half_entry_carry
        self.outer_final_step = outer_final_step

    def word(self, address):
        return self.m[address] | self.m[address+1] << 8

    def difference(self, value, index, carry=1):
        lo, carry = sbc(self.m[0xb000+value+index], self.m[0xb400+(value ^ 255)+index], carry)
        hi, carry = sbc(self.m[0xb200+value+index], self.m[0xb600+(value ^ 255)+index], carry)
        return lo | hi << 8, carry

    def partial_coefficient(self, value, divisor):
        """The three original AD/AE/AF difference-table terms of $5CB2."""
        p, _ = self.difference(value, self.m[0xaf00+divisor])
        q, _ = self.difference(value, self.m[0xae00+divisor])
        low, middle, high = q & 255, p & 255, p >> 8
        middle, carry = adc(q >> 8, middle)
        high = (high+carry) & 255
        r, _ = self.difference(value, self.m[0xad00+divisor])
        low, carry = adc(r >> 8, low)
        if carry:
            middle = (middle+1) & 255
            if middle == 0:
                high = (high+1) & 255
        return [low, middle, high]

    def multiply_coefficient(self, delta, coefficient):
        """Original $5CFD extraction and negative one's-complement convention."""
        assert -127 <= delta <= 127
        value = abs(delta)
        p, _ = self.difference(value, coefficient[2])
        q, _ = self.difference(value, coefficient[1])
        low = q & 255
        high = ((p & 255)+(q >> 8)) & 255
        r, _ = self.difference(value, coefficient[0])
        low, carry = adc(r >> 8, low)
        high = (high+carry) & 255
        result = low | high << 8
        return result ^ 65535 if delta < 0 else result

    def edge_base(self, edge):
        base = self.m[0x6187+edge] | self.m[0x6193+edge] << 8
        assert base == 0x61a0+32*edge
        return base

    def store_intersection(self, edge, level, x, y):
        assert 0 <= level < 16 and 0 <= x < 64 and 0 <= y < 128
        base = self.edge_base(edge)
        for address, value in ((base+level, x), (base+16+level, y)):
            self.m[address] = value
            self.edge_writes.add(address)

    def intersection(self, edge, level, axis):
        address = self.edge_base(edge)+16*axis+level
        assert address in self.edge_writes, ('consumed stale intersection', edge, level, axis)
        self.intersection_reads.add(address)
        return self.m[address]

    def vertex(self, base):
        assert base in range(0x40, 0x70, 6)
        return self.m[base+1], self.m[base+3], self.m[base+5]

    def prepare_edges(self):
        """$5B56: directed edge records -> band bounds/intersection rows."""
        for edge in range(11, -1, -1):
            if not self.m[0x6133+edge]:
                continue
            a = self.vertex(self.m[0x613f+edge])
            b = self.vertex(self.m[0x614b+edge])
            if self.m[0xa100+b[2]] < self.m[0xa100+a[2]]:
                a, b = b, a
            x0, y0, s0 = a
            x1, y1, s1 = b
            first, last = self.m[0xa100+s0], self.m[0xa100+s1]
            assert 0 <= first <= last < 16
            self.m[0x616f+edge], self.m[0x617b+edge] = first, last
            item = dict(edge=edge, endpoints=[list(a), list(b)], levels=[first, last], writes=[])
            self.edges.append(item)
            if first == last:
                continue
            if s1 == self.m[0xa000+s1]:
                self.store_intersection(edge, last, x1, y1)
                item['writes'].append([last, x1, y1])
                last -= 1
                if last == first:
                    continue
            divisor = (s1-s0) & 255
            assert divisor > 0
            xq, yq = x0*256+128, y0*256+128
            partial = (self.m[0xa010+s0]-s0) & 255
            if partial != 16:
                coefficient = self.partial_coefficient(partial, divisor)
                sx = self.multiply_coefficient(x1-x0, coefficient)
                sy = self.multiply_coefficient(y1-y0, coefficient)
                first += 1
                xq, _ = add_word(xq, sx)
                yq, _ = add_word(yq, sy)
                self.store_intersection(edge, first, xq >> 8, yq >> 8)
                item['writes'].append([first, xq >> 8, yq >> 8])
                if first == last:
                    continue
            coefficient = [self.m[p+divisor] for p in (0xa200, 0xa300, 0xa400)]
            sx = self.multiply_coefficient(x1-x0, coefficient)
            sy = self.multiply_coefficient(y1-y0, coefficient)
            for level in range(first+1, last+1):
                xq, _ = add_word(xq, sx)
                yq, _ = add_word(yq, sy)
                self.store_intersection(edge, level, xq >> 8, yq >> 8)
                item['writes'].append([level, xq >> 8, yq >> 8])
        return dict(edges=self.edges, computed_intersection_bytes=len(self.edge_writes))

    def slope(self, x0, x1, y0, y1):
        dx, half_dy = x1-x0, abs(y1-y0)//2
        assert 0 < dx < 64 and 0 <= half_dy < 64
        p, carry = self.difference(half_dy, self.m[0xaf00+dx])
        q, _ = self.difference(half_dy, self.m[0xae00+dx], carry)
        low, carry = adc(p & 255, q >> 8)
        high = ((p >> 8)+carry) & 255
        word = low | high << 8
        return word ^ 65535 if y1 < y0 else word

    @staticmethod
    def initial_y(slope, y0, phase):
        hi = slope >> 8
        half_hi = (hi >> 1) | (hi & 128)
        if phase == 0:
            fraction = 0x40 if y0 & 1 else 0xc0
            integer = (half_hi+(y0 >> 1)+(y0 & 1)) & 255
        else:
            fraction = 0xc0 if y0 & 1 else 0x40
            integer = (half_hi+(y0 >> 1)) & 255
        return fraction | integer << 8

    @staticmethod
    def mask(pattern, phase, x):
        if phase == 0:
            return ((pattern & 0xc0), (pattern & 0x30), (pattern & 0xc0) >> 4, (pattern & 0x30) >> 4)[x & 3]
        return ((pattern & 12) << 4, (pattern & 3) << 4, pattern & 12, pattern & 3)[x & 3]

    def check_cell(self, phase, x, half):
        k = x//2 if half else x
        code = ((0xb800 if phase == 0 else 0xba00) if half else (0xbc00 if phase == 0 else 0xc000))+16*k
        destination = 0x7800+phase*0x400+64*(x//4)
        maskvar = (0x18 if k & 1 == 0 else 0x1a) if half else 0x18+(x & 3)
        lo, hi = ((6, 7) if half else (0x1c, 0x1d))
        expected = (b'\xb9'+destination.to_bytes(2, 'little')+bytes((0x45, maskvar))+
                    b'\x99'+destination.to_bytes(2, 'little')+bytes((0x8a,0x65,lo,0xaa,0x98,0x65,hi,0xa8)))
        assert self.m[code:code+16] == expected, ('generated cell', hex(code))
        table_lo, table_hi = (((0x1b7d, 0x1b9d) if phase == 0 else (0x1bbd, 0x1bdd)) if half
                             else ((0x1a7d, 0x1abd) if phase == 0 else (0x1afd, 0x1b3d)))
        assert self.m[table_lo+k] | self.m[table_hi+k] << 8 == code
        self.cells_checked.add(code)
        return destination

    def plot(self, phase, x, integer, pattern, half):
        destination = self.check_cell(phase, x, half)
        address, mask = destination+integer, self.mask(pattern, phase, x)
        assert 0x7800 <= address < 0x8000
        self.m[address] ^= mask
        self.marker_writes.append(dict(address=address, mask=mask, phase=phase, x=x, integer=integer))

    def line(self, x0, x1, y0, y1, pattern):
        """General source $1856 full/half-X paths, with its carry conventions."""
        assert 0 <= x0 < 64 and 0 <= x1 < 64 and 0 <= y0 < 128 and 0 <= y1 < 128
        if x1 < x0:
            x0, x1, y0, y1 = x1, x0, y1, y0
        if x0 == x1:
            return
        slope = self.slope(x0, x1, y0, y1)
        doubled = (slope << 1) & 65535
        for phase in (0, 1):
            first, second = ((0xc0, 0x30), (12, 3))[phase]
            a, b = bool(pattern & first), bool(pattern & second)
            if not a and not b:
                continue
            q = self.initial_y(slope, y0, phase)
            half = not (a and b)
            if not half:
                positions, carry, step = list(range(x0, x1)), 0, slope
            else:
                positions = [x for x in range(x0, x1) if bool(x & 1) == bool(b)]
                if positions and positions[0] != x0:
                    q, _ = add_word(q, slope, 1 if a else 0)
                carry, step = self.half_entry_carry, doubled
            for i, x in enumerate(positions):
                self.plot(phase, x, q >> 8, pattern, half)
                # $1856 places endpoint RTS at +8: the final cell does not step.
                if i+1 < len(positions):
                    q, carry = add_word(q, step, carry)

    def internal(self):
        """$5D50: walk the two intensity chains of every visible quad."""
        for face in range(5, -1, -1):
            if not self.m[0x60fd+face]:
                continue
            vertices = [self.m[p+face] for p in (0x611b, 0x6121, 0x6127, 0x612d)]
            edges = [self.m[p+face] for p in (0x6103, 0x6109, 0x610f, 0x6115)]
            forward = min(range(4), key=lambda k: (self.vertex(vertices[k])[2], k))
            backward = (forward-1) & 3
            fe, be = edges[forward], edges[backward]
            level, fend = self.m[0x616f+fe], self.m[0x617b+fe]
            bend = self.m[0x617b+be]
            for _ in range(128):
                if level == fend:
                    forward = (forward+1) & 3
                    if forward == backward:
                        break
                    fe = edges[forward]
                    level, fend = self.m[0x616f+fe], self.m[0x617b+fe]
                    continue
                if level == bend:
                    backward = (backward-1) & 3
                    if backward == forward:
                        break
                    be = edges[backward]
                    bend = self.m[0x617b+be]
                    continue
                level += 1
                assert 0 <= level < 16
                x0, x1 = self.intersection(fe, level, 0), self.intersection(be, level, 0)
                y0, y1 = self.intersection(fe, level, 1), self.intersection(be, level, 1)
                pattern = self.m[0x60ec+level] ^ self.m[0x60ed+level]
                self.internal_lines.append(dict(face=face, level=level, edges=[fe,be], XY=[x0,x1,y0,y1], pattern=pattern))
                self.line(x0,x1,y0,y1,pattern)
            else:
                raise AssertionError('internal chain did not terminate')
        return self.internal_lines

    def outer(self):
        """$5E65: silhouette edges, including their per-segment full-X ramp."""
        for edge in range(11, -1, -1):
            if self.m[0x6133+edge] != 1:
                continue
            x0,y0,s0 = self.vertex(self.m[0x613f+edge])
            x1,y1,s1 = self.vertex(self.m[0x614b+edge])
            low, high = self.m[0x616f+edge], self.m[0x617b+edge]
            item = dict(edge=edge, XY=[x0,x1,y0,y1], levels=[low,high])
            self.outer_edges.append(item)
            if low == high:
                item['kind'] = 'uniform1856'
                self.line(x0,x1,y0,y1,self.m[0x60ed+low])
                continue
            if x1 < x0:
                x0,x1,y0,y1,s0,s1 = x1,x0,y1,y0,s1,s0
            if x0 == x1:
                item['kind'] = 'zero-width'
                continue
            xs, levels = [x0], []
            if high-low == 1:
                levels = [self.m[0xa100+s0], self.m[0xa100+s1]]
                xs.append(self.intersection(edge,high,0))
            elif self.intersection(edge,low+1,0) < self.intersection(edge,high,0):
                levels = list(range(low,high+1))
                xs.extend(self.intersection(edge,k,0) for k in range(low+1,high+1))
            else:
                levels = list(range(high,low-1,-1))
                xs.extend(self.intersection(edge,k,0) for k in range(high,low,-1))
            xs.append(x1)
            assert len(xs) == len(levels)+1 and all(a <= b for a,b in zip(xs,xs[1:]))
            for k,x in enumerate(xs): self.m[0x60cc+k] = x
            for k,level in enumerate(levels): self.m[0x60dd+k] = level
            slope = self.slope(x0,x1,y0,y1)
            item.update(kind='segmented-full-X', x_segments=xs, segment_levels=levels, slope=slope)
            for phase in (0,1):
                q = self.initial_y(slope,y0,phase)
                for k,level in enumerate(levels):
                    carry, pattern = 0, self.m[0x60ed+level]
                    for x in range(xs[k],xs[k+1]):
                        self.plot(phase,x,q >> 8,pattern,False)
                        # Outer path plants RTS at +15, after the last ADCs.
                        if self.outer_final_step or x+1 < xs[k+1]:
                            q,carry = add_word(q,slope,carry)
        return self.outer_edges


def run_stages(incoming, **options):
    model = Contours(initialize_contour_tables(incoming), **options)
    assert model.m[0xad00:0xb000] == incoming[0xad00:0xb000]
    model.prepare_edges()
    edges = bytes(model.m[0x616f:0x6187]+model.m[0x61a0:0x6320])
    model.internal()
    internal = bytes(model.m[0x7800:0x8000])
    model.outer()
    return model, dict(edges=edges, internal=internal, outer=bytes(model.m[0x7800:0x8000]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    out = parser.parse_args().output.resolve()
    out.relative_to((BASE/'contour-analysis').resolve())
    assert not out.exists(), 'Choose a fresh output directory'
    for name, expected in PINS.items():
        assert sha((ROOT/name).read_bytes()) == expected, name
    frame = json.loads((BASE/'frame-analysis/accepted-01/frame-proof.json').read_text())
    geometry_proof = json.loads((BASE/'geometry-analysis/accepted-01/geometry-proof.json').read_text())
    assert frame['pass_'] and geometry_proof['pass_']
    assert frame['case_sha256'] == 'b5218a5a088bb0343970327b8ddfc03ea3c177f6bf471db5a739f4bd00817af9'
    captures = {c['stem']: c for c in frame['captures']}
    memories, inputs = {}, [artifact(ROOT/p) for p in PINS]
    for stem in ('begin','visibility','edges','internal','outer','body-complete'):
        record = captures[stem]['ram']
        path = ROOT/record['path']
        raw = path.read_bytes()
        assert len(raw) == record['bytes'] == 65536 and sha(raw) == record['sha256']
        memories[stem] = raw
        inputs.append(artifact(path))
    expected_PC = dict(begin=0x546a,visibility=0x5476,edges=0x5479,internal=0x547c,outer=0x547f)
    assert all(captures[k]['registers']['pc'] == v for k,v in expected_PC.items())
    assert captures['body-complete']['registers']['pc'] == 0x17db
    assert all(not captures[k]['registers']['flags'] & 8 for k in memories)
    assert memories['begin'][0x7800:0x8000] == memories['visibility'][0x7800:0x8000]
    geometry = load_geometry()
    original = geometry.original_memory()
    guards = []
    def guard(address, value, role):
        expected = bytes.fromhex(value)
        assert original[address:address+len(expected)] == expected
        guards.append(dict(address=address, bytes=value, role=role))
    guard(0x5b56,'a00bb93361f011','edgeflags select twelve edge records')
    guard(0x5d50,'a005b9fd60f007','faceflags select six internal contour walks')
    guard(0x5e65,'a00bb93361c901d025','silhouette is edgeflag exactly1')
    guard(0x5cfd,'08100449ff6901','signed coefficient multiplication saves original flags')
    guard(0x5d45,'38a9ffe518aaa9ffe51960','negative coefficient result is ones complement')
    guard(0x196d,'861fc41ff02c','half-X nonempty comparison establishes carry1')
    guard(0x1913,'a960a0089104','ordinary line endpoint RTS before step at+8')
    guard(0x5ff4,'a960a00f9104','segmented outer endpoint RTS after ADCs at+15')
    guard(0x6019,'a696a49718201e6086968597','outer segment clears carry and keeps next XY accumulator')
    guard(0x12f6,'a2008604a9008506a901','reciprocal numerator/remainder initialization')
    # First bounded result: projected records and flags are captured inputs.
    boundary_model, boundary = run_stages(memories['visibility'])
    # Stronger result: use only begin-state and independently predicted upstream stages.
    state = geometry.initialize_tables(memories['begin'])
    state = initialize_contour_tables(state)
    upstream = []
    for name in ('ramp_stage','coefficient_stage','vertex_stage','visibility_stage'):
        state, details = getattr(geometry,name)(state)
        upstream.append(dict(stage=name, details=details))
    for a,z in ((0x40,0x70),(0x60ed,0x6103),(0x6133,0x613f)):
        assert state[a:z] == memories['visibility'][a:z]
    chained_model, chained = run_stages(state)
    assert boundary == chained
    native_edges = memories['edges'][0x616f:0x6187]+memories['edges'][0x61a0:0x6320]
    assert chained['edges'] == native_edges
    assert chained['internal'] == memories['internal'][0x7800:0x8000]
    assert chained['outer'] == memories['outer'][0x7800:0x8000] == memories['body-complete'][0x7800:0x8000]
    assert len(chained_model.edge_writes) == len(chained_model.intersection_reads) == 78
    assert chained_model.edge_writes == chained_model.intersection_reads
    controls = []
    for label, options in (('half-X entry carry0 instead of original CPY carry1',dict(half_entry_carry=0)),
                           ('outer endpoint RTS before final ADCs instead of after them',dict(outer_final_step=False))):
        _, rejected = run_stages(state,**options)
        changed = [dict(address=0x7800+i, modeled=a, original=b)
                   for i,(a,b) in enumerate(zip(rejected['outer'],chained['outer'])) if a != b]
        assert changed
        controls.append(dict(variant=label,rejected=True,marker_byte_mismatches=len(changed),examples=changed[:8]))
    zero_seed = bytearray(state)
    zero_seed[0x7800:0x8000] = bytes(2048)
    _, rejected = run_stages(zero_seed)
    changed = [dict(address=0x7800+i,modeled=a,original=b)
               for i,(a,b) in enumerate(zip(rejected['outer'],chained['outer'])) if a != b]
    assert len(changed) == sum(bool(x) for x in memories['begin'][0x7800:0x8000]) == 17
    controls.append(dict(variant='Assume the entire incoming marker plane is zero',rejected=True,
        marker_byte_mismatches=len(changed),examples=changed,
        reason='Actual begin-state has17nonzero marker bytes; retain incoming state rather than invent a whole-plane clear.'))
    out.mkdir(parents=True)
    outputs = []
    for name,raw in (('captured-input-edges.bin',boundary['edges']),
                     ('captured-input-internal-marker-7800.bin',boundary['internal']),
                     ('captured-input-final-marker-7800.bin',boundary['outer']),
                     ('predicted-edges.bin',chained['edges']),
                     ('predicted-internal-marker-7800.bin',chained['internal']),
                     ('predicted-frame-marker-7800.bin',chained['outer']),
                     ('contours.checked.py',Path(__file__).read_bytes())):
        (out/name).write_bytes(raw)
        outputs.append(dict(name=name,bytes=len(raw),sha256=sha(raw)))
    stage_hashes = {k:dict(bytes=len(v),sha256=sha(v),all_native_bytes_equal=True) for k,v in chained.items()}
    model = chained_model
    proof = dict(pass_=True,scope='One complete original stable-frame marker-plane prediction from begin546A through independent upstream geometry and own contours/lines; no complete visible-output or general-pose claim',
        producer=artifact(Path(__file__)),inputs=inputs,original_guards=guards,
        captured_input_boundary=dict(input='visibility5476 projected records/flags and incoming markers',results=stage_hashes,
            separately_retained=True,limits='This first pass alone does not independently compute upstream geometry.'),
        complete_begin_chain=dict(input='begin546A only; no captured later stage outputs supplied to model',upstream=upstream,
            results=stage_hashes,equal_to_captured_input_boundary=True,incoming_marker_bytes=2048,
            incoming_marker_sha256=sha(memories['begin'][0x7800:0x8000]),incoming_nonzero_marker_bytes=17,
            reciprocal_table_bytes=768,reciprocal_formula='FFFFFF at0/1;floor(2^24/d) at2..255',
            original_division_loop_checks=256,generated_plot_cell_guards=len(model.cells_checked)),
        contours=dict(active_edges=len(model.edges),edge_details=model.edges,
            minmax_bytes=24,intersection_bytes=384,computed_intersection_bytes=78,preserved_unused_intersection_bytes=306,
            consumed_intersection_bytes=78,every_consumed_intersection_fresh=True,
            internal_line_calls=len(model.internal_lines),internal_lines=model.internal_lines,
            outer_edge_calls=len(model.outer_edges),outer_edges=model.outer_edges),
        marker_result=dict(start=0x7800,bytes=2048,all_bytes_equal=True,sha256=sha(chained['outer']),
            plot_operations=len(model.marker_writes),nonzero_mask_operations=sum(bool(w['mask']) for w in model.marker_writes),
            distinct_written_addresses=len({w['address'] for w in model.marker_writes}),
            marker_plot_records_sha256=sha(json.dumps(model.marker_writes,sort_keys=True,separators=(',',':')).encode())),
        negative_controls=controls,
        limits=['One original pose/frame; accepted stage captures are the comparison oracle, never the model output seed.',
            'Begin-state object angles, static source data and runtime initialization context remain inputs. Independent stage arithmetic comes from the pinned geometry producer.',
            'Generic line/outer recurrences are exact for this retained in-range workload; arbitrary clipping, overflowed coordinates, new objects and every visibility branch are not accepted.',
            'Unused intersection cells preserve incoming data, but all78consumed cells are freshly computed for the same frame.',
            'Incoming marker state is preserved, including17nonzero bytes. A zero-only seed hypothesis was rejected before the first receipt; no completed target buffer seeds either model.',
            'Marker identity is not displayed-span/palette/scanout identity. Common prefix reconstruction/clear and publication are separate.',
            'No timing prediction, deliveredFPS, optimization, CPU interpreter, emulator, new native execution or build occurs here.'],outputs=outputs)
    raw = (json.dumps(proof,indent=2)+'\n').encode()
    (out/'contour-proof.json').write_bytes(raw)
    print(json.dumps(dict(pass_=True,receipt_bytes=len(raw),receipt_sha256=sha(raw),
        final_marker_sha256=sha(chained['outer']),internal_lines=len(model.internal_lines),outer_edges=len(model.outer_edges),
        plot_operations=len(model.marker_writes),controls=[c['marker_byte_mismatches'] for c in controls]),indent=2))


if __name__ == '__main__':
    main()
