#!/usr/bin/env python3
"""Bounded first-display map from observed original Colors native RAM.

Only the RAM-only modulo-three helper and four matrix builders are interpreted.
No IRQ, register-writing display helper, hardware read, or full frame is run.
The input is an observed native image, not an independently decoded bundle.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from py65.devices.mpu6502 import MPU

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'build/research/colors'
sys.path.insert(0,str(ROOT/'research/quondam'))
from snapshot_state import read_snapshot
IMAGE_SHA='d03eee9b41f9142ac459609966b2396d77ec134fb1e055d2bf521aff0679e34f'


def sha(data):return hashlib.sha256(data).hexdigest()


class Ram:
    def __init__(self,data):self.data=data;self.writes=set()
    def __getitem__(self,a):
        assert not 0xd000<=a<0xe000,'I/O read rejected'
        return self.data[a]
    def __setitem__(self,a,v):
        assert not 0xd000<=a<0xe000,'I/O write rejected'
        self.data[a]=v;self.writes.add(a)


def run_helper(original,entry,configure,expected,allowed):
    data=bytearray(original);configure(data)
    ram=Ram(data);cpu=MPU(memory=ram,pc=entry);cpu.p=cpu.UNUSED;cpu.sp=255
    cpu.stPushWord(0x4ff)
    reference=bytearray(data);expected(reference)
    ram.writes.clear()
    for steps in range(5000):
        if cpu.pc==0x500:break
        assert (0x8045<=cpu.pc<0x8052 if entry==0x8045 else 0x8423<=cpu.pc<0x8442)
        cpu.step()
    else:raise AssertionError('Helper did not return')
    assert data==reference,'Full RAM differs from independent helper formula'
    assert ram.writes<=allowed and cpu.sp==255
    return dict(instructions=steps,nominal_cpu_cycles=cpu.processorCycles,
                full65536_RAM_bytes_exact=True,written_addresses=sorted(ram.writes),
                returned_PC=cpu.pc,x=cpu.x,y=cpu.y)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture',type=Path,default=BASE/'native-01')
    parser.add_argument('--output',type=Path,default=BASE/'first-display-analysis')
    args=parser.parse_args()
    image=(args.capture/'ram-first-entry.bin').read_bytes()
    assert len(image)==65536 and sha(image)==IMAGE_SHA
    state=read_snapshot(args.capture/'first-entry.vsf')
    assert state['cia']['CIA2']['pra']==0xf8 and state['cia']['CIA2']['ddra']==0x3c
    assert image[0x8045:0x8052]==bytes.fromhex('a2 00 e8 e0 03 d0 02 a2 00 8e 46 80 60')
    assert image[0x8052:0x8072]==bytes.fromhex('a9 3c 8d 02 dd ad 46 80 f0 0a c9 01 f0 0c a9 9e 8d 18 d0 60 a9 9a 8d 18 d0 60 a9 9c 8d 18 d0 60')
    assert image[0x8423:0x8442]==bytes.fromhex('a2 00 18 8a a0 00 91 46 69 06 c8 c0 28 d0 f7 a5 46 69 27 85 46 90 02 e6 47 e8 e0 06 d0 e5 60')
    assert image[0x8e53:0x8e5f]==bytes.fromhex('20 45 80 20 52 80 20 72 80 20 42 84')
    counter=[]
    for phase in range(3):
        next_phase=(phase+1)%3
        result=run_helper(image,0x8045,lambda m,p=phase:m.__setitem__(0x8046,p),
                          lambda m,p=next_phase:m.__setitem__(0x8046,p),{0x8046})
        result.update(input_phase=phase,output_phase=next_phase);counter.append(result)
    bases=[int.from_bytes(image[0x9500+i:0x9502+i],'little') for i in range(0,8,2)]
    assert bases==[0x2400,0x64f0,0xa5e0,0xe6d0]
    matrices=[]
    for base in bases:
        def configure(m,b=base):m[0x46:0x48]=b.to_bytes(2,'little')
        def expected(m,b=base):
            for row in range(6):
                for column in range(40):m[b+40*row+column]=6*column+row
            m[0x46:0x48]=(b+240).to_bytes(2,'little')
        result=run_helper(image,0x8423,configure,expected,set(range(base,base+240))|{0x46,0x47})
        result.update(base=base,rows=6,columns=40,cell_formula='6*column+local_row');matrices.append(result)
    reveal=list(image[0x9652:0x9691]);assert sorted(reveal)==list(range(63))
    phases=[dict(phase=0,D018=0x9a,first_pointer_write=0x8c,second_pointer_write=0x8d,first_color=2,second_color=5),
            dict(phase=1,D018=0x9c,first_pointer_write=None,second_pointer_write=0x8e,first_color=5,second_color=2),
            dict(phase=2,D018=0x9e,first_pointer_write=0x8d,second_pointer_write=None,first_color=2,second_color=5)]
    banks=[dict(DDRA=0x3c+i,base=0x4000*i,screen=0x2400+0x4000*i,
                charsets=[0x2800+0x4000*i,0x3000+0x4000*i,0x3800+0x4000*i]) for i in range(4)]
    result=dict(pass_=True,observed_image_sha256=IMAGE_SHA,native_snapshot_sha256=state['file_sha256'],
        input_scope='Observed original first native payload; no independent packed-bundle oracle',
        script_sha256=sha(Path(__file__).read_bytes()),counter_cases=counter,matrix_cases=matrices,
        phase_helper=0x8045,phase_operand=0x8046,known_helper_calls=[0x8c71,0x8e53],
        calls_do_not_establish_native_cadence=True,phase_register_writes=phases,
        retained_pointer_semantics='None means preserve incoming pointer, not an implied phase-independent value',
        banks_with_PRA_low00=banks,initial_CIA2=dict(pra=0xf8,ddra=0x3c),
        color_RAM_clear=dict(pc=0x836c,cells=1024,value=0),
        sprite_clear=dict(pc=0x83f6,bases=[0x2300,0x6300,0xa300,0xe300],bytes_per_bank=192),
        sprite_reveal=dict(pc=0x8442,calls=63,index_permutation=reveal,source_planes=[0x96c0,0x9700,0x9740],
                           first_bank_destinations=[0x2300,0x2340,0x2380],replicated_in_all_four_banks=True),
        sprite_state=dict(enable=255,behind_char_foreground=255,pairs=[[0,4],[1,5],[2,6],[3,7]],
                          x_offsets=[0,24,48,72],y_targets=[54,75,96,117,138,159,180,201,222,243]),
        visible_background_source=dict(pc=0x8cba,value=6),above_canvas_background_source=dict(pc=0x8c6c,value=0),
        checkpoints=[dict(pc=0x8e4e,role='next field raster4 before phase/pointer changes; previous whole PAL beam completed'),
                     dict(pc=0x8fd6,role='raster252 end service; sprite DMA may continue below this point'),
                     dict(pc=0x8e5c,role='after phase and sprite palette setup, before one-byte reveal call')],
        scope='Three RAM-only modulo cases and four RAM-only builders plus source mapping. No IRQ execution, VIC/drive mock, frame simulation, pixel oracle, analog blend or native cadence claim.')
    result['pass']=result.pop('pass_')
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/'first-display-contract.json').write_text(json.dumps(result,indent=2)+'\n')
    print('PASS: 3 modulo helpers + 4 six-row matrices; no hardware execution')


if __name__=='__main__':main()
