#!/usr/bin/env python3
"""Own folded-panel geometry exported as small per-line VIC controls."""
import json
import math
from pathlib import Path

HERE=Path(__file__).resolve().parent


def geometry(phase):
    angle=phase*math.tau/16
    top=92+round(4*math.sin(angle))
    ys=(top,top+60,top+120)
    xs=(
        (64+round(12*math.sin(angle)),64+round(16*math.sin(angle)),
         64+round(12*math.cos(angle+.6))),
        (96+round(8*math.sin(angle+.7)),96+round(8*math.sin(angle+2)),
         96+round(8*math.cos(angle))),
        (168+round(16*math.cos(angle+.4)),168+round(16*math.sin(angle+.5)),
         168+round(16*math.cos(angle+1))),
        (232+round(8*math.cos(angle)),232+round(8*math.sin(angle+1.8)),
         232+round(8*math.cos(angle+.2))),
    )
    return ys,xs


def crossing(knots,ys,y):
    section=0 if y<ys[1] else 1
    delta=knots[section+1]-knots[section]
    offset=y-ys[section]
    height=ys[section+1]-ys[section]
    return knots[section]-((-delta*offset)//height)


def main():
    output=HERE/"build"
    output.mkdir(exist_ok=True)
    data=bytearray()
    records=[]
    for phase in range(16):
        ys,edges=geometry(phase)
        planes=[[],[],[],[],[]]
        for y in range(80,224):
            current=max(ys[0],min(ys[2],y))
            following=max(ys[0],min(ys[2],y+1))
            values=(crossing(edges[2],ys,current),crossing(edges[1],ys,following),
                    crossing(edges[0],ys,following),0x10 if ys[0]<=y+1<ys[2] else 0x20,
                    crossing(edges[3],ys,following))
            for plane,value in zip(planes,values): plane.append(value)
        for plane in planes: data.extend(plane)
        records.append({"phase":phase,"ys":ys,"edges":edges})
    (output/"poses.bin").write_bytes(data)
    (output/"geometry.json").write_text(json.dumps(records,indent=2)+"\n")
    print("Prepared16 original folded-panel edge schedules; no polygon pixels.")


if __name__=="__main__":
    main()
