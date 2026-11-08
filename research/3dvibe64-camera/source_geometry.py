#!/usr/bin/env python3
"""Exact arithmetic reference for culling conventions, not a raster acceptance."""
import argparse
from fractions import Fraction as F
import hashlib
import itertools
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/3dvibe64-camera'
PINS = {
    'analysis/accepted-02/camera-proof.json': '6023d45cbf7a47ff4f74d61211df512d077cbd046d01537d2a83f05c3a7fa536',
    'primary-reading/codebase-backface.html': '261764f03243c379a2f66dfb9aa95889b217f9cfcbbb2919e618aed411319642',
    'primary-reading/csdb-49250.html': '71a4b1fcfeaa1501bd5a95020a7bb72c36732e5afb9abb010636214bc5aa8023',
}


def pin(path):
    data = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def area(a,b,c):
    return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])


def determinant(a,b,c):
    return (a[0]*(b[1]*c[2]-b[2]*c[1])-
            a[1]*(b[0]*c[2]-b[2]*c[0])+
            a[2]*(b[0]*c[1]-b[1]*c[0]))


def sign(x):
    return (x>0)-(x<0)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    for name,digest in PINS.items():
        assert pin(BASE/name)['sha256']==digest,name
    wiki=(BASE/'primary-reading/codebase-backface.html').read_text()
    forum=(BASE/'primary-reading/csdb-49250.html').read_text()
    assert 'already transformed into 2D' in wiki
    assert 'C*-3-1 &gt; 0' in forum and 'C&gt;e' in forum
    proof=json.loads((BASE/'analysis/accepted-02/camera-proof.json').read_text())
    assert proof['input_and_full_scalar_integrity_pass']
    assert not proof['classifier_all_decoded_images_preserved']
    rows=[]
    clouds={}
    for frame in proof['frames']:
        points=frame['points']
        key=json.dumps(points,separators=(',',':'))
        clouds.setdefault(key,[]).append([frame['dataset'],frame['frame']])
        for face in frame['face_planes']:
            p=[points[i] for i in face['vertices']]
            assert all(v[2]>0 for v in p)
            side=-determinant(*p)
            assert side==face['signed_eye_side']
            normalized=[(F(v[0],v[2]),F(-v[1],v[2])) for v in p]
            projected_area=area(*normalized)
            expected=F(side,p[0][2]*p[1][2]*p[2][2])
            assert projected_area==expected and sign(projected_area)==sign(side)
            actual=face.get('captured_projected_area_Q2')
            rows.append(dict(dataset=frame['dataset'],frame=frame['frame'],face=face['face_id'],
                signed_eye_side=side,exact_normalized_area=str(projected_area),
                captured_area_Q2=actual,
                actual_area_sign_differs=(sign(actual)!=sign(side)) if actual is not None else None))
    grid=list(itertools.product(range(-1,2),repeat=2));checks=0
    for a,b,c in itertools.product(grid,repeat=3):
        wiki_area=(b[1]-a[1])*(c[0]-b[0])-(b[0]-a[0])*(c[1]-b[1])
        assert wiki_area==-area(a,b,c)
        checks+=1
    forum_cases=[]
    for nz in (-1,0,1):
        expression=-3*nz-1
        proposed=nz>F(-1,3)
        corrected=nz<F(-1,3)
        assert (expression>0)==corrected and proposed!=corrected
        forum_cases.append(dict(normal_z=nz,plane_expression=expression,
                                direct_visible=expression>0,printed_final_greater_visible=proposed))
    assert len(rows)==120 and checks==729
    result=dict(scope='Exact mathematical identities and source-convention checks only; the camera classifier still fails native-image preservation.',
        producer=pin(Path(__file__).resolve()),inputs=[pin(BASE/n) for n in PINS],
        capture_windows=len(proof['frames']),distinct_3D_clouds=len(clouds),
        duplicated_cloud_windows=[v for v in clouds.values() if len(v)>1],
        exact_perspective_identity='area((x/z,-y/z)) = -det(P0,P1,P2)/(z0*z1*z2) = camera_side/(z0*z1*z2)',
        triangle_checks=rows,positive_depth_triangles=len(rows),wiki_2D_convention_cases=checks,
        forum_final_inequality_counterexamples=forum_cases,
        unchanged_camera_classifier_image_preservation=False,
        limitations=['No SDK, renderer, CPU model, compiler or emulator runs here.',
                     'Exact rational projection is a reference, not the SDK lookup/raster output.',
                     'An actual area-sign disagreement does not uniquely isolate table bucketing versus coordinate rounding.',
                     'The forum counterexamples concern its printed final inequality, not any executable.'])
    args.output.mkdir(parents=True,exist_ok=False)
    out=args.output/'source-geometry-proof.json'
    out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(accepted_reference=True,triangle_checks=len(rows),distinct_clouds=len(clouds),
        actual_sign_disagreements=sum(r['actual_area_sign_differs'] is True for r in rows),
        bytes=out.stat().st_size,sha256=hashlib.sha256(out.read_bytes()).hexdigest())))


if __name__=='__main__':
    main()
