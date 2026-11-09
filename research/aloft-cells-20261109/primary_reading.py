#!/usr/bin/env python3
"""Offline, bounded primary-source reading and byte transformations; no CPU model."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


BASE = Path("build/research/aloft-cells-20261109/primary-analysis")
HTTP_PINS = {
    "acquisition-01": "5cd4a0a87784d137159d02c27c3d6b31d9b1c5af9cb0b8961e0298b3b9bbc917",
    "acquisition-02": "a0c4f4e2c28282ffee356d7c4eb8643bc6fc76d6f32b70b1b29a0eccf5bb9a7f",
    "acquisition-03": "741d21fd6a52d5157424fc8eadcbd0e52754ad14c5d737a3eb37c75bd3aa103f",
    "acquisition-04": "0f161b07b1b2264b197b829151dfbe406c6c1b676e53c6c17385f0dbea2b5e56",
}
COLOR = Path("build/research/aloft-decode-20261109/color-analysis/accepted-01")
COLOR_PROOF_SHA = "44bbc6a94b22db33d81dc9f15178f1303a2db19fb22484292e0c6f894f00f4b2"
EFFECT = Path("build/research/aloft-decode-20261109/effect-analysis/accepted-01/effect-binding-proof.json")
EFFECT_SHA = "882027ffe37e5651ec2c18ea7a3e511824d10f5d15da264c73b855fb6769c5ce"
VICE_SOURCE_SHA = "a7e30daad739ffc4df275c3cb36c790cc03134fd822cf15489135f85cfe5f842"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def identity(path: Path, data: bytes | None = None) -> dict:
    data = path.read_bytes() if data is None else data
    return {"path": str(path), "bytes": len(data), "sha256": digest(data)}


def pinned(repo: Path, path: Path, sha: str) -> bytes:
    data = (repo / path).read_bytes()
    if digest(data) != sha:
        raise ValueError(f"input identity changed: {path}")
    return data


def d011_read(stored_register: int, raster_line: int) -> int:
    """VICE 3.10 viciisc read expression, not a scanout/timing model."""
    if not (0 <= stored_register <= 255 and 0 <= raster_line <= 511):
        raise ValueError("byte register and nine-bit raster required")
    return (stored_register & 0x7F) | ((raster_line & 0x100) >> 1)


def d011_inc_read(read_byte: int) -> dict:
    """Instruction data values only; the caller supplies the actual read byte."""
    if not 0 <= read_byte <= 255:
        raise ValueError("read byte required")
    final = (read_byte + 1) & 255
    return {"read": read_byte, "dummy_write": read_byte, "final_write": final}


def text_anchor(text: str, first: str, last: str | None = None, *, occurrence="last") -> dict:
    pos = text.rfind(first) if occurrence == "last" else text.find(first)
    if pos < 0:
        raise ValueError(f"missing textual anchor: {first}")
    end = pos + len(first) if last is None else text.find(last, pos + len(first))
    if end < 0:
        raise ValueError(f"missing terminal anchor: {last}")
    selected = text[pos:end]
    return {
        "first_marker": first,
        "terminal_marker_excluded": last,
        "first_line": text.count("\n", 0, pos) + 1,
        "last_line": text.count("\n", 0, max(pos, end - 1)) + 1,
        "decoded_text_utf8_bytes": len(selected.encode()),
        "decoded_text_utf8_sha256": digest(selected.encode()),
    }


def line_guard(text: str, first: int, last: int, fragments: list[str]) -> dict:
    selected = "\n".join(text.splitlines()[first - 1:last])
    for fragment in fragments:
        if fragment not in selected:
            raise ValueError(f"missing primary code fragment at {first}: {fragment}")
    return {"first_line": first, "last_line": last, "sha256": digest(selected.encode()),
            "required_fragments": fragments}


def write_json(out: Path, name: str, obj: object) -> dict:
    data = (json.dumps(obj, indent=2, sort_keys=True) + "\n").encode()
    (out / name).write_bytes(data)
    return {"name": name, "bytes": len(data), "sha256": digest(data)}


def produce(repo: Path, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=False)
    inputs, responses, body_texts = [], [], {}
    for directory, sha in HTTP_PINS.items():
        path = BASE / directory / "http.json"
        raw = pinned(repo, path, sha)
        inputs.append(identity(path, raw))
        manifest = json.loads(raw)
        if manifest["schema"] != "primary-http-retention-v1":
            raise ValueError("unknown acquisition schema")
        for response in manifest["responses"]:
            row = dict(response)
            row["manifest"] = str(path)
            if "transport_error" in response:
                if "SSLCertVerificationError" not in response["transport_error"]:
                    raise ValueError("unexpected acquisition failure")
                row["has_HTTP_response"] = False
            else:
                bodypath = path.parent / response["body"]
                body = pinned(repo, bodypath, response["sha256"])
                if len(body) != response["bytes"] or response["status"] != 200:
                    raise ValueError("changed HTTP body/status")
                row["body"] = str(bodypath)
                row["has_HTTP_response"] = True
                encoding = "utf-8" if response["name"] == "bauer" else "latin1"
                body_texts[(directory, response["name"])] = body.decode(encoding)
            responses.append(row)
    assert len(responses) == 14
    assert sum(row["has_HTTP_response"] for row in responses) == 11

    bauer = body_texts[("acquisition-01", "bauer")]
    assert "by Christian Bauer" in bauer and "2024-09-29" in bauer[:600]
    h6 = body_texts[("acquisition-03", "bruce-hacking6")]
    h7 = body_texts[("acquisition-03", "bruce-hacking7")]
    h10 = body_texts[("acquisition-03", "bruce-hacking10")]
    assert "Sept. 5, 1993" in h6[:900] and "Feb. '94" in h7[:900]
    assert "June 30, 1995" in h10[:900]
    author_anchors = {
        "bauer": {title: text_anchor(bauer, title, following) for title, following in [
            ("3.5. Bad Lines", "3.6. Memory access"),
            ("3.7.2. VC and RC", "3.7.3 Graphics modes"),
            ("3.7.3.5. ECM text mode", "3.7.3.6. Invalid text mode"),
            ("3.7.3.7. Invalid bitmap mode 1", "3.7.3.9. Idle state"),
            ("3.14.2. FLD", "3.14.3. FLI"),
            ("3.14.4. Linecrunch", "3.14.5. Doubled text lines"),
        ]},
        "hacking6": {
            "author": text_anchor(h6, "by Pasi 'Albert' Ojala"),
            "article": text_anchor(h6, "Opening the borders\n", "_Example routine_"),
            "FLD": text_anchor(h6, "_Scrolling the screen_", "_Garbage appearing_"),
        },
        "hacking7": {
            "author": text_anchor(h7, "by Marek Klampar (klampar@elf.stuba.sk)"),
            "article_and_code": text_anchor(h7, "FLD - Scrolling the screen\n", "Tech-tech - more resolution"),
        },
        "hacking10": {
            "author": text_anchor(h10, "by Pasi 'Albert' Ojala <albert@cs.tut.fi>"),
            "article": text_anchor(h10, "BFLI - New graphics modes 2\n", "Making stable raster routines"),
        },
    }
    # These are content markers, not a proof that a historical article is an exact VIC model.
    assert "AND #$07" in h7 and "STA $D011" in h7
    assert "Linecrunch combined" in h10 and "bad line delaying technique" in h10
    pasi = body_texts[("acquisition-02", "pasi-dev")]
    assert "https://www.ffd2.com/fridge/chacking/" in pasi
    bruce_index = body_texts[("acquisition-02", "hacking-index")]
    assert "official C= Hacking site" in bruce_index and "hacking10.txt" in bruce_index
    linus = body_texts[("acquisition-01", "linus-paper")]
    assert "Anonymous" in linus and "Sat 23-Apr-2022" in linus

    vice_path = BASE / "retained-vice-01/source.json"
    vice_raw = pinned(repo, vice_path, VICE_SOURCE_SHA)
    inputs.append(identity(vice_path, vice_raw))
    vice = json.loads(vice_raw)
    pinned(repo, Path(vice["archive"]), vice["sha256"])
    texts = {}
    for member in vice["members"]:
        raw = pinned(repo, Path(member["path"]), member["sha256"])
        assert len(raw) == member["bytes"]
        texts[Path(member["path"]).name] = raw.decode()
    vice_anchors = {
        "D011_store": line_guard(texts["vicii-mem.c"], 145, 156,
            ["vicii.ysmooth = value & 0x7;", "vicii.regs[0x11] = value;", "update_raster_line();"]),
        "D011_read": line_guard(texts["vicii-mem.c"], 501, 512,
            ["(vicii.regs[addr] & 0x7f) | ((tmp & 0x100) >> 1)"]),
        "INC_data_order": line_guard(texts["6510core.c"], 1175, 1188,
            ["tmp = load_func(tmp_addr);", "dummy_func(tmp_addr, tmp);",
             "tmp = (tmp + 1) & 0xff;", "store_func(tmp_addr, tmp, 1);"]),
        "INC_absolute_dispatch": line_guard(texts["6510core.c"], 3408, 3410,
            ["case 0xee:", "INC(p2, 3, LOAD_ABS, STORE_ABS, DUMMY_STORE_ABS_RMW)"]),
        "dummy_write": line_guard(texts["6510core.c"], 721, 724,
            ["STORE_DUMMY(addr, value)"]),
    }
    color_raw = pinned(repo, COLOR / "color-stream-proof.json", COLOR_PROOF_SHA)
    inputs.append(identity(COLOR / "color-stream-proof.json", color_raw))
    color = json.loads(color_raw)
    generation = color["completed_bundles"][31]
    assert generation["bundle"] == 31
    ram = masks = physical = None
    for file in generation["files"][:3]:
        raw = pinned(repo, COLOR / file["name"], file["sha256"])
        assert len(raw) == file["bytes"] == 65536
        if file["name"].endswith("memory.bin"): ram = raw
        elif "known-mask" in file["name"]: masks = raw
        else: physical = raw
    assert all(masks[0xF000:0xF840]) and all(physical[0xF000:0xF840])
    source_guards = {}
    for addr, expected in [(0xF7EC, "ee11d0"), (0xF80F, "a9188d11d0")]:
        data = bytes.fromhex(expected)
        assert ram[addr:addr + len(data)] == data
        source_guards[f"{addr:04X}"] = expected
    effect_raw = pinned(repo, EFFECT, EFFECT_SHA)
    inputs.append(identity(EFFECT, effect_raw))
    assert json.loads(effect_raw)["pass_"] is True

    values = [d011_inc_read(value) for value in range(256)]
    for stored in range(256):
        for raster_msb in range(2):
            read = d011_read(stored, raster_msb << 8)
            assert read == (stored & 127) | (raster_msb << 7)
            assert values[read]["dummy_write"] == read
            assert values[read]["final_write"] == (read + 1) & 255
    assert [d011_inc_read(v)["final_write"] for v in range(0x18, 0x20)] == list(range(0x19, 0x21))
    math = {"schema": "d011-increment-data-values-v1", "instruction_input": "actual CPU D011 read byte",
            "domain_read_bytes": 256, "stored_byte_and_raster_MSB_cases": 512,
            "rows": values, "example_read_values_18_through_1F": values[0x18:0x20],
            "predicts_access_cycles_or_VIC_side_effects": False}
    outputs = [write_json(out, "d011-values.json", math),
               write_json(out, "primary-anchors.json", {"authored_content": author_anchors,
                   "VICE": vice_anchors, "VICE_members": vice["members"],
                   "generation31_source_guards": source_guards}),
               write_json(out, "http-retention.json", {"responses": responses,
                   "successful_bodies": 11, "body_bytes": sum(r.get("bytes", 0) for r in responses),
                   "TLS_failures_without_HTTP_response": 3})]
    proof = {
        "pass_": True,
        "scope": "bounded authored primary reading plus register-byte transformation; no CPU or VIC scanout model",
        "producer": identity(Path(__file__).resolve().relative_to(repo)),
        "inputs": inputs,
        "selected_primary_content": [
            {"id": "bauer", "authority": "author-hosted research reference, current revision 2024-09-29"},
            {"id": "hacking6", "authority": "signed Pasi Ojala article, magazine contributor's mirror"},
            {"id": "hacking7", "authority": "signed Marek Klampar article and example, contributor's mirror"},
            {"id": "hacking10", "authority": "signed Pasi Ojala article and example, contributor's mirror"},
            {"id": "VICE", "authority": "official versioned implementation source; not a silicon timing proof"},
        ],
        "excluded_as_technical_authority": [
            "anonymous late-linecrunch comments beneath Linus's Raster paper",
            "Codebase64 article reformatting; retained as discovery context only",
            "AI/secondary technique-summary search hits; not acquired or used",
        ],
        "failures_preserved": [
            "three certificate-validation failures; no certificate bypass or HTTP-response inference",
            "first local HTML inspection assumed UTF-8 and failed; later declared Latin-1 used",
            "a web search output exceeded the tool output budget; no result inferred",
        ],
        "local_binding": {"original_generation": 31, "source_guards": source_guards,
            "prior_bounded_native_association_receipt": str(EFFECT),
            "does_not_prove_runtime_cell_selection_or_timing": True},
        "required_before_mechanism_binding": [
            "generated cell selection, runtime SMC and exact actual D011 values/read raster MSB",
            "ordered read/dummy/final bus accesses with VIC phase and stall coverage",
            "DEN latch, badline condition, RC, VC, VCBASE, VMLI and idle/display state",
            "D011 ECM/BMM, D016 MCM, D018 and effective VIC bank at relevant fetches",
            "matrix/color-line contents, glyph or bitmap bytes, border/fetch latches and committed viewport oracle",
        ],
        "limits": [
            "No new creator-content search for Aloft itself, nor claimed Aloft creator explanation.",
            "Article conditions are hypotheses to test against original execution, not a label inferred from appearance.",
            "D011 math predicts data values only, not badlines, mode pipelines, frame timing or pixels.",
            "No native expected RAM, generated native code or final image seeds these transformations.",
        ],
        "outputs": outputs,
    }
    write_json(out, "primary-reading-proof.json", proof)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    produce(args.repo.resolve(), args.output.resolve())


if __name__ == "__main__":
    main()
