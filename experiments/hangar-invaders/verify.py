#!/usr/bin/env python3
"""Play through actual port-2 lines; check game state, native tiles/sprites/pixels."""
import copy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import socket
import subprocess
from PIL import Image

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
FONT={1:'3c7edbffa5245a00',2:'3c7edbffa55aa500',3:'1818181818181818',4:'000000ff00000000'}
FONT.update({ord(c):v+'00' for c,v in zip('0123456789',[
    '3c42464a52623c','1828080808083e','3c42020c30407e','3c42021c02423c',
    '0c1424447e0404','7e407c0202423c','1c20407c42423c','7e020408101010',
    '3c42423c42423c','3c42423e020438'])})
FONT.update({ord(c):v+'00' for c,v in zip('ABCDEFGHIJKLMNOPQRSTUVWXYZ',[
    '182442427e4242','7c42427c42427c','3c42404040423c','78444242424478',
    '7e40407c40407e','7e40407c404040','3c42404e42423c','4242427e424242',
    '3e08080808083e','1e040404444438','42444870484442','4040404040407e',
    '42665a5a424242','4262524a464242','3c42424242423c','7c42427c404040',
    '3c4242424a443a','7c42427c484442','3c42403c02423c','7f080808080808',
    '4242424242423c','42424242422418','4242425a5a6642','42422418244242',
    '41221408080808','7e02041820407e'])})
FONT_BYTES=b''.join(bytes.fromhex(FONT.get(i,'00'*8)) for i in range(256))
SHIP=[0x018000,0x018000,0x03c000,0x07e000,0x0ff000,0x3ffc00,
      0x7ffe00,0xffff00,0xc3c300,0x818100,0x242400,0x181800]+[0]*9
BULLET=[0x800000]*5+[0]*16
SPRITES=b''.join(row.to_bytes(3,'big') for row in SHIP)+b'\0'+b''.join(row.to_bytes(3,'big') for row in BULLET)+b'\0'
CORE=('mode','score','misses','shots','remaining','playerX','bulletActive','bulletX','bulletY',
      'gameTick','formationTimer','formation','direction','fireHeld','newFire','lastJoystick','restarts','updates')

def reset(state):
    state.update(mode=0,score=0,misses=0,shots=0,remaining=12,playerX=120,
                 bulletActive=0,bulletX=0,bulletY=0,gameTick=0,formationTimer=0,
                 formation=5,direction=1,alive=[1]*12)

def initial():
    state={'fireHeld':0,'newFire':0,'lastJoystick':31,'restarts':0,'updates':0}
    reset(state)
    return state

def advance(old,pressed):
    """Independent game rules; no native state is used to calculate outcomes."""
    s=copy.deepcopy(old)
    s['lastJoystick']=31^pressed
    s['newFire']=int(bool(pressed&16) and not s['fireHeld'])
    s['fireHeld']=int(bool(pressed&16))
    s['updates']=(s['updates']+1)%65536
    if s['mode']:
        if s['newFire']:
            s['restarts']=(s['restarts']+1)%256
            reset(s)
        return s
    if pressed&12==4:
        s['playerX']=max(32,s['playerX']-2)
    elif pressed&12==8:
        s['playerX']=min(216,s['playerX']+2)
    s['gameTick']=(s['gameTick']+1)%256
    s['formationTimer']=(s['formationTimer']+1)%32
    if s['formationTimer']==0:
        if (s['formation'],s['direction']) in ((10,1),(5,255)):
            s['direction']=256-s['direction']
        s['formation']+=1 if s['direction']==1 else -1
    if s['bulletActive']:
        if s['bulletY']<4:
            s['bulletActive']=0
            s['misses']=(s['misses']+1)%100
        else:
            s['bulletY']-=4
            for enemy,alive in enumerate(s['alive']):
                left=s['formation']*8+(enemy%4)*40
                top=40+(enemy//4)*16
                if alive and left<=s['bulletX']<left+8 and s['bulletY']<=top+7 and s['bulletY']+4>=top:
                    s['alive'][enemy]=0
                    s['bulletActive']=0
                    s['score']+=1
                    s['remaining']-=1
                    s['mode']=int(s['remaining']==0)
                    break
    if not s['mode'] and s['newFire'] and not s['bulletActive']:
        s['bulletActive']=1
        s['bulletX']=s['playerX']+7
        s['bulletY']=148
        s['shots']=(s['shots']+1)%100
    return s

def planes(state):
    matrix=bytearray(b' '*1000)
    colors=bytearray([1]*1000)
    def text(row,col,value,color=None):
        at=row*40+col
        matrix[at:at+len(value)]=value.encode('ascii')
        if color is not None: colors[at:at+len(value)]=bytes([color])*len(value)
    for row in range(4,11): colors[row*40:(row+1)*40]=bytes([13])*40
    for row in range(4,21):
        for col in (3,29):
            matrix[row*40+col]=3
            colors[row*40+col]=12
    for col in range(3,30):
        matrix[21*40+col]=4
        colors[21*40+col]=12
    text(1,12,'HANGAR INVADERS',7)
    text(2,5,f'SCORE {state["score"]:02d}  MISS {state["misses"]:02d}  SHOTS {state["shots"]:02d}')
    text(23,9,'LEFT RIGHT FIRE  PORT 2',12)
    for enemy,alive in enumerate(state['alive']):
        if alive:
            matrix[(5+enemy//4*2)*40+state['formation']+enemy%4*5]=1+(state['gameTick']//16%2)
    if state['mode']:
        text(15,13,'HANGAR CLEAR')
        text(17,11,'RELEASE THEN FIRE')
    return bytes(matrix),bytes(colors)

def pixels(state,palette):
    matrix,colors=planes(state)
    image=Image.new('RGB',(320,200),palette[0])
    out=image.load()
    for cell,code in enumerate(matrix):
        glyph=FONT_BYTES[code*8:code*8+8]
        for y,row in enumerate(glyph):
            for x in range(8):
                if row&(128>>x): out[(cell%40)*8+x,(cell//40)*8+y]=palette[colors[cell]]
    # Sprite0 has priority over sprite1 when their initial rows touch.
    sprites=[]
    if state['bulletActive']: sprites.append((BULLET,state['bulletX'],state['bulletY'],7))
    sprites.append((SHIP,state['playerX'],152,5))
    for shape,left,top,color in sprites:
        for y,row in enumerate(shape):
            for x in range(24):
                if row&(1<<(23-x)) and 0<=left+x<320 and 0<=top+y<200:
                    out[left+x,top+y]=palette[color]
    return image

def forecast_hit(state,x=None):
    trial=copy.deepcopy(state)
    if x is not None: trial['playerX']=x
    trial=advance(trial,16)
    score=trial['score']
    for _ in range(40):
        trial=advance(trial,0)
        if trial['score']>score: return True
        if not trial['bulletActive']: return False
    return False

def pilot(state):
    if state['bulletActive']:
        # Keep the last shot held through victory, to test no automatic restart.
        return 16 if state['remaining']==1 else 0
    if state['fireHeld']: return 0
    if forecast_hit(state): return 16
    targets=[x for x in range(32,217,2) if forecast_hit(state,x)]
    assert targets,'No reachable live target in the independent game model'
    target=min(targets,key=lambda x:abs(x-state['playerX']))
    return 4 if target<state['playerX'] else 8

def main():
    output=HERE/'build/verification'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    output.mkdir(parents=True)
    report={'passed':False,'samples':[],'captures':[],
            'input_method':'Explicit synthetic CIA1 port-2 lines via VICE Joyport I/O simulation',
            'memory_or_pc_writes':False}
    process=monitor=joy=binary=None
    try:
        bridge_path=HERE/'../bitmap-kefrens/verify.py'
        spec=importlib.util.spec_from_file_location('real_joystick_bridge',bridge_path)
        bridge=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bridge)
        common=bridge.common
        sources=('main.asm','verify.py','build.sh','run.sh','../bitmap-kefrens/verify.py')
        hashes={name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in sources}
        program=HERE/'build/example.prg'
        report.update(source_sha256=hashes,program_sha256=hashlib.sha256(program.read_bytes()).hexdigest())
        labels=common.read_labels(HERE/'build/main.sym')
        palette_path=ROOT/'palettes/colodore.vpl'
        palette=[tuple(int(v,16) for v in line.split()[:3]) for line in palette_path.read_text().splitlines()
                 if line.strip() and not line.startswith('#')]
        with socket.socket() as a,socket.socket() as b:
            a.bind(('127.0.0.1',0)); b.bind(('127.0.0.1',0))
            port,binary_port=a.getsockname()[1],b.getsockname()[1]
        command=common.vice_command(shutil.which('x64sc'),program,port,palette_path)
        command[command.index('+warp')]='-warp'
        command+=['-binarymonitor','-binarymonitoraddress',f'ip4://127.0.0.1:{binary_port}',
                  '-controlport2device','37','-limitcycles','100000000']
        with (output/'vice.log').open('w') as log:
            process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            with common.connect_monitor(process,port) as connection:
                monitor=common.Monitor(connection)
                monitor.run('r')
                monitor.run('sidefx off')
                monitor.run(f'break {labels["inputSample"]:04x}')
                monitor.run(f'break {labels["renderComplete"]:04x}')
                monitor.run(f'break {labels["framePresented"]:04x}')
                monitor.run('disable 2')
                monitor.run('disable 3')
                monitor.run('x')
                pc,raster,last_clock=monitor.registers()
                assert pc==labels['inputSample'] and raster==252
                monitor.run('bank ram')
                assert monitor.memory(output/'font.bin',0x2000,0x27ff)==FONT_BYTES
                assert monitor.memory(output/'sprite-art.bin',0x3000,0x307f)==SPRITES
                monitor.run('bank cpu')
                binary=socket.create_connection(('127.0.0.1',binary_port),timeout=15)
                joy=bridge.Joyport(binary)
                monitor.run('disable 1')
                monitor.run('enable 2')
                monitor.run('enable 3')
                state=initial()
                captures=[]
                def step(pressed,tag,force=False):
                    nonlocal state,last_clock
                    old=state
                    state=advance(state,pressed)
                    index=len(report['samples'])
                    raw=joy.set(pressed)
                    monitor.run('x')
                    pc,render_raster,render_clock=monitor.registers()
                    assert pc==labels['renderComplete']
                    assert 0<render_clock-last_clock<6993,(index,'missed visible-area deadline',render_clock-last_clock)
                    assert render_raster>=252 or render_raster<51
                    monitor.run('x')
                    pc,raster,clock=monitor.registers()
                    assert pc==labels['framePresented'] and raster==252
                    assert abs(clock-last_clock-19656)<16,(index,'PAL cadence',clock-last_clock)
                    monitor.run('bank ram')
                    ram=monitor.memory(output/'current-ram.bin',0x400,0x0fff)
                    for name in CORE:
                        at=labels[name]-0x400
                        actual=int.from_bytes(ram[at:at+(2 if name=='updates' else 1)],'little')
                        assert actual==state[name],(index,name,actual,state[name])
                    assert ram[labels['alive']-0x400:labels['alive']-0x400+12]==bytes(state['alive'])
                    matrix,colors=planes(state)
                    assert ram[:1000]==matrix,(index,'character matrix')
                    assert ram[0x3f8:0x3fa]==b'\xc0\xc1'
                    monitor.run('bank io')
                    vic=monitor.memory(output/'current-vic.bin',0xd000,0xd03f)
                    cia=monitor.memory(output/'current-cia.bin',0xdc00,0xdc03)
                    color=monitor.memory(output/'current-colors.bin',0xd800,0xdbe7)
                    assert bytes(v&15 for v in color)==colors
                    assert cia[0]&31==raw and cia[2]&31==0
                    assert vic[0]==state['playerX']+24 and vic[1]==202
                    assert vic[2]==state['bulletX']+24 and vic[3]==state['bulletY']+50
                    assert vic[0x10]==0 and vic[0x15]==1+2*state['bulletActive']
                    assert all(vic[n]==0 for n in (0x17,0x1b,0x1c,0x1d))
                    assert vic[0x11]&0x7f==0x1b and vic[0x16]&0x3f==8 and vic[0x18]&0xfe==0x18
                    assert vic[0x20]&15==6 and vic[0x21]&15==0 and vic[0x27]&15==5 and vic[0x28]&15==7
                    monitor.run('bank cpu')
                    sample={'frame':index,'tag':tag,'pressed_bits':pressed,'active_low_lines':raw,
                            'state':copy.deepcopy(state),'clock':clock,'render_clock':render_clock,
                            'render_cost_clocks':render_clock-last_clock,'render_raster':render_raster,
                            'field_clocks':clock-last_clock}
                    event=any(state[n]!=old[n] for n in ('score','misses','shots','mode','restarts'))
                    if force or event or index%32==0:
                        path=output/f'frame-{index:04d}.png'
                        monitor.run(f'screenshot "{path}" 2')
                        actual=Image.open(path).convert('RGB').crop((32,35,352,235))
                        expected=pixels(state,palette)
                        wrong=sum(a!=b for a,b in zip(actual.get_flattened_data(),expected.get_flattened_data()))
                        assert wrong==0,(index,'native sprite/character pixels',wrong)
                        expected.save(output/f'expected-{index:04d}.png')
                        (output/f'ram-{index:04d}.bin').write_bytes(ram)
                        (output/f'vic-{index:04d}.bin').write_bytes(vic)
                        report['captures'].append({'frame':index,'tag':tag,'pixels':64000,'wrong_pixels':wrong})
                        captures.append(actual)
                    if state['score']>old['score']:
                        hit=next(i for i,(a,b) in enumerate(zip(old['alive'],state['alive'])) if a!=b)
                        sample['hit']={'enemy':hit,'tile_x_offset':state['bulletX']-(state['formation']*8+hit%4*40),
                                       'bullet_y':state['bulletY']}
                    report['samples'].append(sample)
                    last_clock=clock
                for _ in range(2): step(0,'neutral')
                for _ in range(60): step(4,'left-clamp')
                assert state['playerX']==32
                for _ in range(50): step(16,'held-fire-miss')
                assert (state['misses'],state['shots'],state['score'],state['bulletActive'])==(1,1,0,0)
                for _ in range(2): step(0,'release')
                for _ in range(110): step(8,'right-clamp')
                assert state['playerX']==216
                for _ in range(6): step(12,'opposing-directions')
                assert state['playerX']==216
                for _ in range(3): step(3,'unused-up-down')
                assert state['playerX']==216
                step(16,'right-edge-shot')
                step(0,'busy-release')
                step(16,'busy-fire-edge')
                for _ in range(45): step(16,'busy-held-fire')
                assert (state['misses'],state['shots'],state['score'],state['bulletActive'])==(2,2,0,0)
                step(0,'release-before-play')
                for _ in range(1000):
                    if state['mode']: break
                    step(pilot(state),'real-input-win')
                assert state['mode']==1 and state['score']==12 and state['remaining']==0 and not any(state['alive'])
                assert state['fireHeld']==1 and state['restarts']==0
                for _ in range(8): step(16,'win-held-no-restart',True)
                assert state['mode']==1 and state['restarts']==0
                step(0,'win-fire-release',True)
                step(16,'restart-edge',True)
                assert state['mode']==0 and state['shots']==0 and state['score']==0 and state['restarts']==1
                for _ in range(5): step(16,'restart-held-no-shot',True)
                assert state['shots']==0
                step(0,'restart-release')
                step(16,'restart-first-shot',True)
                assert state['shots']==1 and state['bulletActive']==1
                for _ in range(4): step(0,'restart-flight')
                joy.set(0)
                monitor.run('bank ram')
                assert monitor.memory(output/'font-final.bin',0x2000,0x27ff)==FONT_BYTES
                assert monitor.memory(output/'sprites-final.bin',0x3000,0x307f)==SPRITES
                assert {name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in sources}==hashes
                assert hashlib.sha256(program.read_bytes()).hexdigest()==report['program_sha256']
                connection.sendall(b'quit\n')
                process.wait(timeout=5)
                common.save_animation(captures,output/'gameplay.gif',120)
        assert process.returncode==0
        samples=report['samples']
        report.update(passed=True,vice_exit_code=process.returncode,
                      native_pixels_checked=len(report['captures'])*64000,
                      matrix_bytes_checked=len(samples)*1000,
                      pal_field_clocks=[min(s['field_clocks'] for s in samples),max(s['field_clocks'] for s in samples)],
                      update_work_clocks=[min(s['render_cost_clocks'] for s in samples),max(s['render_cost_clocks'] for s in samples)],
                      input_to_win_frames=next(s['frame'] for s in samples if s['state']['mode']==1),
                      limitations=['Own game/rules/art; original Aloft minigame algorithm is not recovered',
                                   'Rectangle/character-cell collision rules, not per-pixel sprite collision',
                                   'Synthetic joystick lines in native PAL VICE; no physical joystick claim'])
    except Exception as error:
        report['error']=repr(error)
        raise
    finally:
        if joy: report['synthetic_inputs']=joy.transcript
        if binary: binary.close()
        if monitor: (output/'monitor.txt').write_text('\n'.join(monitor.transcript))
        if process and process.poll() is None:
            process.terminate()
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait(timeout=5)
        (output/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({'passed':report['passed'],'frames':len(report['samples']),
                          'captures':len(report['captures']),'receipt':str(output/'verification.json')}),flush=True)

if __name__=='__main__': main()
