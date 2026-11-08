#!/usr/bin/env python3
"""Check a signed-plane example from the retained culling article using rationals.

This executes no SDK, original demo, CPU model or emulator. It does not establish
the visibility of any captured SDK polygon or a speed improvement.
"""

import argparse
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'build/research/3dvibe64-overdraw/primary-culling/rotation-backface.pdf'
SOURCE_SHA = '4c6eabf015843c9edd5c9ae002278fac6acc5dd50951d2a1a390bf2a64157465'


def pin(path):
    data = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(data),
                sha256=hashlib.sha256(data).hexdigest())


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def serial(value):
    if isinstance(value, F):
        return str(value)
    if isinstance(value, (tuple, list)):
        return [serial(x) for x in value]
    if isinstance(value, dict):
        return {k: serial(v) for k, v in value.items()}
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert pin(SOURCE)['sha256'] == SOURCE_SHA
    rows = []
    rotations = [(F(1), F(0)), (F(0), F(1)), (F(-1), F(0)), (F(0), F(-1))]
    rotations += [(F(sc*99,101), F(ss*20,101)) for sc in (1,-1) for ss in (1,-1)]
    for c, s in rotations:
        assert c*c+s*s == 1
        x_axis, y_axis = (c,s), (-s,c)
        vertices = [tuple(y_axis[i]+sign*x_axis[i] for i in range(2)) for sign in (-1,1)]
        assert dot(x_axis,y_axis) == 0 and dot(y_axis,y_axis) == 1
        printed_residuals = [dot(y_axis,p)+1 for p in vertices]
        outward_residuals = [dot(y_axis,p)-1 for p in vertices]
        assert printed_residuals == [F(2),F(2)]
        assert outward_residuals == [F(0),F(0)]
        camera_distance = F(4)
        camera = (-camera_distance,F(0))
        direct = dot(y_axis,tuple(camera[i]-vertices[0][i] for i in range(2))) > 0
        reduced = y_axis[0] < -1/camera_distance
        printed = y_axis[0] < 1/camera_distance
        inward = tuple(-v for v in y_axis)
        assert direct == reduced == (dot(inward,camera)+1 < 0)
        rows.append(dict(x_axis=x_axis,y_axis=y_axis,vertices=vertices,
                         printed_plane_residuals=printed_residuals,
                         corrected_outward_plane_residuals=outward_residuals,
                         camera=camera,direct_outward_visible=direct,
                         corrected_threshold_visible=reduced,printed_threshold_visible=printed))
    # Exact tangent case for strict visibility: n.x=-3/5 and camera.x=-5/3.
    normal, point, eye = (F(-3,5),F(4,5)), (F(-3,5),F(4,5)), (F(-5,3),F(0))
    tangent = dot(normal,tuple(eye[i]-point[i] for i in range(2)))
    assert tangent == 0 and not (normal[0] < -1/F(5,3))
    result = serial(dict(
        accepted=True,producer=pin(Path(__file__).resolve()),source=pin(SOURCE),
        source_scope='Printed mathematical example on pages2-3; not the unnamed1991 executable.',
        rotations=rows,vertex_incidence_checks=2*len(rows),
        printed_threshold_disagreements=sum(r['direct_outward_visible'] != r['printed_threshold_visible'] for r in rows),
        tangent=dict(normal=normal,point=point,camera=eye,residual=tangent,strict_front_facing=False),
        three_dimensional_extension=dict(convention='outward unit normal n; face plane n dot P=d; eye E=(0,0,-C), C>0',
            exact_expression='n dot (E-P) > 0',reduced_threshold='n_z < -d/C',
            warning='Reverse the inequality when reversing the normal. General camera/object movement requires updating the transformed plane/camera relation.'),
        limitations=['Exact rational math only; no measured instruction cost or code generation.',
                     'The PDF implementation/history claim is not independently bound to a released demo.',
                     'This does not diagnose a sign bug in the SDK or original1991 production.']))
    args.output.mkdir(parents=True,exist_ok=False)
    target=args.output/'normal-plane-proof.json'
    target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(accepted=True,vertex_checks=16,threshold_disagreements=result['printed_threshold_disagreements'],
                          bytes=target.stat().st_size,sha256=hashlib.sha256(target.read_bytes()).hexdigest())))


if __name__ == '__main__':
    main()
