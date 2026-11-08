#!/usr/bin/env python3
"""Compare orthographic candidates against mathematical pixels in native PAL VICE."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess

from PIL import Image, ImageChops

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
QUADS = ((0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6))
FLAT = (1,1,2,2,3,3)
WIDTH, HEIGHT = 80, 50
GEOMETRY_SCALE = 1024


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


core = module("ortho_reference_helpers", HERE / "verify.py")
shared = module("ortho_monitor", ROOT / "verify.py")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def geometry(phase):
    yaw = 4 * phase + 1
    pitch = core.rounded(24 * math.sin(math.tau * phase / 64 + .4))
    roll = 4 * phase
    sy, cy, sp, cp, sr, cr = (core.rounded(16384 * math.sin((a % 256) * math.tau / 256))
                              for a in (yaw,yaw+64,pitch,pitch+64,roll,roll+64))
    def multiply(value, coefficient):
        return (value * coefficient + 8192) // 16384

    basis = []
    for axis in range(3):
        x,y,z = (14 * GEOMETRY_SCALE if axis == j else 0 for j in range(3))
        rx = multiply(x,cy) + multiply(z,sy)
        rz = multiply(z,cy) - multiply(x,sy)
        ry = multiply(y,cp) - multiply(rz,sp)
        rz = multiply(rz,cp) + multiply(y,sp)
        rx,ry = multiply(rx,cr)-multiply(ry,sr),multiply(rx,sr)+multiply(ry,cr)
        basis.append((rx,ry,rz))
    vertices = [tuple(sum(basis[a][j] * (1 if v & (1<<a) else -1)
                          for a in range(3)) for j in range(3)) for v in range(8)]
    rotated = [tuple((value+512)//GEOMETRY_SCALE for value in point) for point in vertices]
    projected = [(40+x,25-y) for x,y,z in rotated]
    assert all(0 <= x < WIDTH and 0 <= y < HEIGHT for x,y in projected)
    visible=[]
    for face in QUADS:
        a,b,c,d = (projected[v] for v in face)
        area = core.cross(a,b,c) + core.cross(a,c,d)
        visible.append(int(area>0))
        if area>0:
            assert all(core.cross(p,q,r)>=0 for p,q,r in
                       ((a,b,c),(b,c,d),(c,d,a),(d,a,b))), (phase,"nonconvex face",face)
            assert core.cross(a,b,c)>0, (phase,"degenerate UV triangle",face)
    return dict(yaw=yaw,pitch=pitch,roll=roll,basis=basis,vertices=vertices,
                rotated=rotated,projected=projected,visible=visible)


def rigid_metrics(phase, basis, vertices, projected, enforce=True):
    """Physical invariants against a float rotation, independent of fixed-point arithmetic."""
    axes=[tuple(value/GEOMETRY_SCALE for value in point) for point in basis]
    lengths=[math.sqrt(sum(value*value for value in axis)) for axis in axes]
    angles=[math.degrees(math.acos(max(-1,min(1,sum(a*b for a,b in zip(axes[i],axes[j]))
                    /(lengths[i]*lengths[j]))))) for i,j in ((0,1),(0,2),(1,2))]
    yaw=(4*phase+1)*math.tau/256
    pitch=core.rounded(24*math.sin(math.tau*phase/64+.4))*math.tau/256
    roll=4*phase*math.tau/256
    internal_errors=[];screen_errors=[]
    for vertex,point in enumerate(vertices):
        x,y,z=(14 if vertex & (1<<axis) else -14 for axis in range(3))
        rx=x*math.cos(yaw)+z*math.sin(yaw)
        rz=z*math.cos(yaw)-x*math.sin(yaw)
        ry=y*math.cos(pitch)-rz*math.sin(pitch)
        rz=rz*math.cos(pitch)+y*math.sin(pitch)
        rx,ry=rx*math.cos(roll)-ry*math.sin(roll),rx*math.sin(roll)+ry*math.cos(roll)
        internal_errors.extend(abs(actual/GEOMETRY_SCALE-ideal)
                               for actual,ideal in zip(point,(rx,ry,rz)))
        screen_errors.extend(abs(actual-ideal) for actual,ideal in
                             zip(projected[vertex],(40+rx,25-ry)))
    metrics=dict(basis_length_min=min(lengths),basis_length_max=max(lengths),
                 max_basis_relative_length_error=max(abs(value/14-1) for value in lengths),
                 axis_angle_min_degrees=min(angles),axis_angle_max_degrees=max(angles),
                 max_axis_angle_error_degrees=max(abs(value-90) for value in angles),
                 max_internal_coordinate_error_samples=max(internal_errors),
                 max_screen_coordinate_error_samples=max(screen_errors))
    if enforce:
        assert metrics["max_basis_relative_length_error"]<.002,(phase,"nonrigid edge lengths",metrics)
        assert metrics["max_axis_angle_error_degrees"]<.2,(phase,"nonorthogonal axes",metrics)
        assert metrics["max_internal_coordinate_error_samples"]<.01,(phase,"3D corner error",metrics)
        assert metrics["max_screen_coordinate_error_samples"]<=.501,(phase,"projected corner error",metrics)
    return metrics


def convex_hull(points):
    points=sorted(set(points))
    def half(sequence):
        result=[]
        for point in sequence:
            while len(result)>1 and core.cross(result[-2],result[-1],point)<=0:
                result.pop()
            result.append(point)
        return result
    return half(points)[:-1]+half(reversed(points))[:-1]


def contains(polygon,x,y):
    return all(core.cross(p,q,(x,y))>0 or
               (core.cross(p,q,(x,y))==0 and core.top_left(p,q))
               for p,q in zip(polygon,polygon[1:]+polygon[:1]))


def mapped_uv(mapping, gradients, origin, x, y):
    result=[]
    for gx,gy in gradients:
        dx,dy=x-origin[0],y-origin[1]
        exact=(gx*dx+gy*dy)//256
        if mapping == "exact":
            value=exact
        elif mapping == "tiles":
            ax,ay=x&~1,y&~1
            value=(gx*(ax-origin[0])+gy*(ay-origin[1]))//256
            value+=(gx*(x-ax)+gy*(y-ay)+128)//256
        elif mapping == "separable":
            value=(gx*dx)//256+(gy*dy)//256
        else:
            raise ValueError(mapping)
        delta=(value-exact)&15
        assert delta in (0,1,15), (mapping,origin,x,y,delta)
        result.append((value&15,exact&15,delta!=0))
    return result


def reference(phase, mapping):
    record=geometry(phase)
    texture=core.source_texture(phase)
    samples=bytearray(WIDTH*HEIGHT)
    owners=set()
    textured=flat=changed=uv_changed=0
    for face,ids in enumerate(QUADS):
        if not record["visible"][face]:
            continue
        polygon=[record["projected"][v] for v in ids]
        a,b,c,d=polygon
        area=core.cross(a,b,c)
        gradients=((4096*(c[1]-b[1])//area,4096*(b[0]-c[0])//area),
                   (-4096*(b[1]-a[1])//area,4096*(b[0]-a[0])//area))
        for y in range(min(v[1] for v in polygon),max(v[1] for v in polygon)):
            for x in range(min(v[0] for v in polygon),max(v[0] for v in polygon)):
                if not contains(polygon,x,y):
                    continue
                assert (x,y) not in owners, (phase,"overlapping faces",face,x,y)
                owners.add((x,y))
                if face==4:
                    u,v=mapped_uv(mapping,gradients,a,x,y)
                    color=texture[u[0]+16*v[0]]
                    changed+=color!=texture[u[1]+16*v[1]]
                    uv_changed+=u[2] or v[2]
                    textured+=1
                else:
                    color=FLAT[face]
                    flat+=1
                samples[y*WIDTH+x]=color
    hull=convex_hull(record["projected"])
    silhouette={(x,y) for y in range(HEIGHT) for x in range(WIDTH) if contains(hull,x,y)}
    assert owners==silhouette,(phase,"silhouette gaps or excess",len(owners^silhouette))
    return dict(**record,texture=texture,samples=bytes(samples),
                textured_samples=textured,flat_samples=flat,
                changed_texture_colors=changed,changed_uv_samples=uv_changed)


def inputs(folder):
    paths=set(HERE.glob("*.asm")) | set(folder.glob("*.asm")) | set(folder.glob("*.py"))
    paths.update((Path(__file__).resolve(),HERE/"verify.py",ROOT/"verify.py",HERE.parent/"build-one.sh"))
    return {str(p.relative_to(ROOT)):sha(p) for p in sorted(paths)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folder",type=Path,default=HERE/"ortho")
    parser.add_argument("--mapping",choices=("exact","tiles","separable"),default="separable")
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    folder=args.folder.resolve()
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    output=args.output.resolve() if args.output else folder/"build/verification"/stamp
    output.mkdir(parents=True,exist_ok=True)
    status=folder/"build/latest-verification.json"
    status.parent.mkdir(parents=True,exist_ok=True)
    status.write_text(json.dumps(dict(status="running",output=str(output)))+"\n")
    references=[reference(p,args.mapping) for p in range(64)]
    with (output/"build.log").open("w") as log:
        subprocess.run(["sh",str(HERE.parent/"build-one.sh"),str(folder)],check=True,stdout=log,stderr=subprocess.STDOUT)
    source_hashes=inputs(folder)
    program=folder/"build/example.prg"
    program_hash=sha(program)
    labels=shared.read_labels(folder/"build/main.sym")
    for rel,digest in source_hashes.items():
        dst=output/"inputs"/rel
        dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(ROOT/rel,dst)
    shutil.copy2(program,output/"example.prg")
    shutil.copy2(folder/"build/main.sym",output/"main.sym")
    palette_file=ROOT/"palettes/colodore.vpl"
    palette=[tuple(int(x,16) for x in line.split()[:3]) for line in palette_file.read_text().splitlines()
             if line.strip() and not line.lstrip().startswith("#")]
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1",0));port=reservation.getsockname()[1]
    command=shared.vice_command(os.environ.get("VICE","x64sc"),program,port,palette_file)
    process=monitor=None
    observations=[];images=[];geometry_metrics=[]
    try:
        with (output/"vice.log").open("w") as log:
            process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
            monitor=shared.Monitor(shared.connect_monitor(process,port))
            monitor.run("r")
            monitor.run(f'break ${labels["framePresented"]:04x}')
            for index in range(66):
                monitor.run("x")
                registers=monitor.run("r")
                monitor.run("bank ram")
                ram=monitor.memory(output/f"pose-{index:02d}.ram",0,65535)
                phase=index%64;ref=references[phase]
                assert ram[labels["shownPhase"]]==phase,(index,"phase")
                assert int.from_bytes(ram[labels["presentationCount"]:labels["presentationCount"]+2],"little")==index+1
                for label,angle in (("angleYaw","yaw"),("anglePitch","pitch"),("orthoAngleRoll","roll")):
                    assert ram[labels[label]]==(ref[angle]&255),(phase,label,ram[labels[label]],ref[angle])
                def words(name,count):
                    start=labels[name]
                    return [int.from_bytes(ram[start+2*i:start+2*i+2],"little",signed=True) for i in range(count)]
                native_basis=list(zip(*(words("orthoBasis"+axis,3) for axis in "XYZ")))
                native_vertices=list(zip(*(words("orthoVertex"+axis,8) for axis in "XYZ")))
                assert native_basis==ref["basis"],(phase,"Q10 basis",native_basis,ref["basis"])
                assert native_vertices==ref["vertices"],(phase,"Q10 corners",native_vertices,ref["vertices"])
                for axis,name in enumerate(("rotatedX","rotatedY","rotatedZ")):
                    core.assert_bytes(ram[labels[name]:labels[name]+8],bytes(v[axis]&255 for v in ref["rotated"]),f"phase{phase} {name}")
                for axis,name in enumerate(("projectedX","projectedY")):
                    core.assert_bytes(ram[labels[name]:labels[name]+8],bytes(v[axis] for v in ref["projected"]),f"phase{phase} {name}")
                native_projected=list(zip(*(ram[labels[name]:labels[name]+8] for name in ("projectedX","projectedY"))))
                geometry_metrics.append(rigid_metrics(phase,native_basis,native_vertices,native_projected))
                core.assert_bytes(ram[labels["faceVisible"]:labels["faceVisible"]+6],bytes(ref["visible"]),f"phase{phase} culling")
                core.assert_bytes(ram[0x5000:0x5100],ref["texture"],f"phase{phase} texture")
                screen=ram[labels["shownScreenHigh"]]*256
                assert screen in (0x400,0xc00) and (not observations or screen!=observations[-1]["screen"])
                actual=core.decode_matrix(ram[screen:screen+1000])
                core.assert_bytes(actual,ref["samples"],f"phase{phase} all4000samples")
                core.assert_bytes(ram[0x2000:0x2800],core.charset(),"fixed charset")
                monitor.run("bank cpu")
                vic=monitor.memory(output/f"vic-{index:02d}.bin",0xd000,0xd02e)
                assert (vic[0x11]&0x7f)==0x1b and (vic[0x16]&0x3f)==0x18
                assert (vic[0x18]&0xfe)==(((screen//1024)<<4)|8)
                assert vic[0x15]==0 and tuple(v&15 for v in vic[0x20:0x24])==(0,0,6,3)
                if not index:
                    colors=monitor.memory(output/"color-ram.bin",0xd800,0xdbe7)
                    assert {v&15 for v in colors}=={9}
                fields=re.search(r"^\.;[0-9a-fA-F]{4}\s+(.*)$",registers,re.M)[1].split()
                raster,cycle,clock=map(int,fields[-3:])
                assert 0<=raster<35,(index,"late publish",raster,cycle)
                record=dict(phase=phase,yaw=ref["yaw"],pitch=ref["pitch"],roll=ref["roll"],
                            screen=screen,clock=clock,raster=[raster,cycle],textured_samples=ref["textured_samples"])
                if index:
                    previous=(phase-1)%64
                    image_path=output/f"visible-phase-{previous:02d}-{index:02d}.png"
                    monitor.run(f'screenshot "{image_path}" 2')
                    actual_image=Image.open(image_path).convert("RGB")
                    expected=Image.new("RGB",actual_image.size,palette[0])
                    expected.paste(core.expected_canvas(references[previous],palette),(32,35))
                    difference=ImageChops.difference(actual_image,expected)
                    if difference.getbbox():
                        expected.save(output/"expected-failed.png");difference.save(output/"difference-failed.png")
                        raise AssertionError((index,"native pixels",difference.getbbox()))
                    images.append(actual_image);record["screenshot"]=image_path.name
                observations.append(record)
            monitor.connection.sendall(b"quit\n");process.wait(timeout=5)
        assert inputs(folder)==source_hashes,"Source changed during native playback"
        assert sha(program)==program_hash
        intervals=[];pal_fields=[];groups={True:[],False:[]}
        for first,last in zip(observations,observations[1:]):
            interval=last["clock"]-first["clock"]
            beam_delta=63*(last["raster"][0]-first["raster"][0])+last["raster"][1]-first["raster"][1]
            assert interval>0 and (interval-beam_delta)%19656==0
            intervals.append(interval);pal_fields.append((interval-beam_delta)//19656)
            groups[references[last["phase"]]["visible"][4]!=0].append(interval)
        durations=[max(10,round(value/985248*100)*10) for value in intervals[:64]]
        images[0].save(output/"orthographic-cube.gif",save_all=True,append_images=images[1:64],duration=durations,loop=0,optimize=False)
        total=sum(r["textured_samples"] for r in references)
        changed=sum(r["changed_texture_colors"] for r in references)
        geometry_summary={key:(min(row[key] for row in geometry_metrics) if key.endswith("_min") or
                                      "_min_degrees" in key else max(row[key] for row in geometry_metrics))
                          for key in geometry_metrics[0]}
        report=dict(pass_=True,mapping=args.mapping,folder=str(folder),program_sha256=program_hash,
                    source_sha256=source_hashes,presentations=66,poses=64,live_geometry=True,
                    complete_screen_samples=264000,complete_native_images=65,
                    native_geometry=geometry_summary,
                    motion=dict(rotation_order=["Y yaw","X pitch","Z roll"],angle_units_per_turn=256,
                                yaw="4*phase+1",pitch="round(24*sin(2*pi*phase/64+0.4))",roll="4*phase",
                                cycle_poses=64,projected_pose_count=len({tuple(row["projected"]) for row in references})),
                    geometry_contract=dict(fractional_bits=10,trig_fractional_bits=14,
                                           max_relative_length_error=.002,max_angle_error_degrees=.2,
                                           max_internal_coordinate_error_samples=.01,
                                           max_screen_coordinate_error_samples=.501,
                                           rounding="nearest; ties toward positive infinity"),
                    mean_updates_per_second=985248/(sum(intervals)/len(intervals)),
                    pal_fields_per_update=[min(pal_fields),max(pal_fields)],
                    visibility_timing={"visible" if key else "hidden":dict(jobs=len(values),updates_per_second=985248/(sum(values)/len(values))) for key,values in groups.items() if values},
                    quality=dict(max_declared_uv_error_texels_per_axis=0 if args.mapping=="exact" else 1,
                                 textured_samples=total,changed_colors_vs_exact=changed,
                                 changed_color_fraction=changed/total if total else 0),
                    animation_duration_ms=durations,observations=observations,command=command,
                    limits=["Native expected pixels use the declared mapping; the one-texel UV bound is relative to the Q8 affine plane from the first three rounded face corners, not the ideal physical UV plane.",
                            "Final rounded face corners need not form exact parallelograms; all visible convex quads tile the rounded cube silhouette without gaps or overlaps at every pose.",
                            "The yaw/pitch/roll animation advances one phase per completed update; variable render cost still causes variable angular speed.",
                            "Different projection and motion path from the perspective baseline; physical hardware and analog CRT output not covered."])
        report["pass"]=report.pop("pass_")
        (output/"proof.json").write_text(json.dumps(report,indent=2)+"\n")
        shutil.copy2(output/"orthographic-cube.gif",folder/"build/orthographic-cube.gif")
        status.write_text(json.dumps(dict(status="pass",output=str(output),program_sha256=program_hash))+"\n")
        print(json.dumps({k:v for k,v in report.items() if k not in ("source_sha256","observations","animation_duration_ms","command")},indent=2))
    except BaseException as error:
        status.write_text(json.dumps(dict(status="fail",output=str(output),error=repr(error)))+"\n")
        raise
    finally:
        if process is not None and process.poll() is None:
            process.kill();process.wait(timeout=5)
        if monitor is not None:
            (output/"monitor.log").write_text("\n".join(monitor.transcript))
            monitor.connection.close()


if __name__=="__main__":
    main()
