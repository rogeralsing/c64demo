#!/usr/bin/env python3
"""Static loader checkpoints from original boot and file-derived SFX output.

No CPU, drive, ROM or effect is executed. Installer and later reused addresses
are kept separate; the 44-byte sender correspondence is checked exactly.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'build/research/second-reality/binary'
PROOF_SHA='92f272cd978c594467c72a9be0536b29685fbbe0e68e1b18a71d8b9c2718cdfd'
def sha(b):return hashlib.sha256(b).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=BASE)
    args=parser.parse_args()
    proof=(BASE/'boot-proof.json').read_bytes();assert sha(proof)==PROOF_SHA
    metadata=json.loads(proof);blob=(BASE/'side1-boot.prg').read_bytes()
    assert sha(blob)==metadata['boot_sha256']
    original=bytearray(65536);original[0x801:0xaf89]=blob[2:]
    unpacked=(BASE/'file-derived-unpacked.ram').read_bytes()
    core=metadata['RAM_only_decompressor']
    assert sha(unpacked[core['output_first']:core['output_end_exclusive']])==core['output_sha256']
    installer=bytearray(65536)
    installer[0xc000:0xc100]=original[0x980:0xa80]
    installer[0xca00:0xce89]=original[0xab00:0xaf89]
    assert installer[0xc028:0xc02b]==bytes.fromhex('20 00 ca')
    assert installer[0xca1f:0xca22]==bytes.fromhex('20 ba ff')
    assert installer[0xc04e:0xc051]==bytes.fromhex('4c 0d 08')
    assert unpacked[0xcf00:0xcf15]==bytes.fromhex('24 ea 29 ef 8d 93 cf 20 58 cf 20 74 cf ad 93 cf c9 01 d0 01 60')
    first=bytes(installer[0xcb2d:0xcb59]);second=bytes(unpacked[0xcf94:0xcfc0])
    normalized=bytearray(first);patches=[]
    for offset in (2,5,8,11):
        assert first[offset:offset+3]==bytes.fromhex('20 3c cb')
        assert second[offset:offset+3]==bytes.fromhex('20 a3 cf')
        normalized[offset+1:offset+3]=b'\xa3\xcf'
        patches.append(dict(offset=offset,original_target=0xcb3c,later_target=0xcfa3))
    assert normalized==second
    checkpoints=[]
    for phase,memory,points in [
        ('original boot installer',installer,[(0xc000,'first copied wrapper'),(0xca00,'drive installer'),(0xca1f,'first KERNAL call')]),
        ('independently decompressed image',unpacked,[(0x9400,'first program entry'),(0xc000,'later main program; different from installer'),
            (0xce0b,'concrete call to CF00'),(0xcf00,'custom C64 loader'),(0xcf58,'transport bank-bit preparation'),
            (0xcf74,'handshake'),(0xcf94,'byte sender'),(0xcfc0,'byte receiver')])]:
        for pc,role in points:checkpoints.append(dict(phase=phase,pc=pc,role=role,first20_bytes=memory[pc:pc+20].hex(' ')))
    report=dict(pass_=True,script_sha256=sha(Path(__file__).read_bytes()),reference_proof_sha256=PROOF_SHA,
                sender_comparison=dict(installer_range=[0xcb2d,0xcb59],later_range=[0xcf94,0xcfc0],bytes=44,
                    original_sha256=sha(first),later_sha256=sha(second),JSR_relocations=patches,
                    all_other_bytes_exact=True),checkpoints=checkpoints,
                installer_unknown_padding=dict(source=[0xaf89,0xb000],destination=[0xce89,0xcf00],bytes=119),
                streamed_drive_image=dict(source=[0xcbbb,0xcebb],bytes=768,
                    file_unestablished_suffix=[0xce89,0xcebb],file_unestablished_bytes=50),
                scope='Static original-byte mapping and exact relocated sender comparison; no protocol execution, named loader version or display timing assertion.')
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/'loader-checkpoints.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS: 44 sender bytes match after four JSR relocations; installer/loaded checkpoints remain distinct')


if __name__=='__main__':main()
