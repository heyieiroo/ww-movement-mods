"""Apply the 'airborne horizontal wall run' patch on top of the jump-patched POP2.EXE.

Usage: python patch_wallrun.py <jump-patched POP2.EXE> <output path>

The input must be the output of patch_jump.py (sha256 below). The input file is never
modified. The script refuses to run if the input hash or any original bytes differ.
"""
import hashlib
import sys
from pathlib import Path

JUMP_PATCHED_SHA256 = "6ccc356273865a9c2396760b4dd7afe0ac371979071c602c53d561c206aa9800"

CAVE_OFFSET = 0x4BA130  # VA 0x8BA130, .text slack beyond the original VirtualSize
CAVE = bytes.fromhex(
    # add esp,8 ; test eax,eax ; je 0x64D797   (replayed hook: no wall contact -> vanilla)
    "83 C4 08 85 C0 0F 84 5C 36 D9 FF"
    # pushad ; sub esp,0x2C ; mov ebx,esp ; edi = [[0xD34A40]+0x48]   (Prince data)
    "60 83 EC 2C 89 E3 8B 3D 40 4A D3 00 8B 7F 48"
    # 0x71E450(obj,&held,[edi+0x10B8],5) ; held == 0 -> skip   (RMB physically held)
    "6A 05 FF B7 B8 10 00 00 8D 43 24 50 FF 35 48 4A D3 00 E8 EF 42 E6 FF 83 C4 10"
    "83 7B 24 00 0F 84 36 01 00 00"
    # 0x4A7980(obj,&v) ; v.z < VZMIN -> skip   (only near the impact, not during the slide)
    "8D 43 18 50 FF 35 48 4A D3 00 E8 03 D8 BE FF 83 C4 08"
    "D9 43 20 D8 1D B8 A2 8B 00 DF E0 F6 C4 01 0F 85 10 01 00 00"
    # 0x490850(obj,&facing)
    "53 FF 35 48 4A D3 00 E8 B0 66 BD FF 83 C4 08"
    # 0x49FA30(obj,0x80,&facing,0.0,&n) ; none -> skip ; 0x47C620(&n) flatten+normalize
    "8D 43 0C 50 FF 35 28 BD 8B 00 53 68 80 00 00 00 FF 35 48 4A D3 00 E8 72 58 BE FF"
    "83 C4 14 85 C0 0F 84 DB 00 00 00 8D 43 0C 50 E8 4E 24 BC FF 83 C4 04"
    # |facing.xy . n.xy| > cos30 (0x8C0E74) -> skip   (head-on stays vanilla, no vertical run)
    "D9 03 D8 4B 0C D9 43 04 D8 4B 10 DE C1 D9 E1 D8 1D 74 0E 8C 00 DF E0 F6 C4 41"
    "0F 84 AF 00 00 00"
    # save the 13 fields 0x526920 can write before failing late
    "FF B7 CC 04 00 00 FF B7 DC 08 00 00 FF B7 E0 08 00 00 FF B7 E4 08 00 00"
    "FF B7 04 02 00 00 FF B7 A8 07 00 00 FF B7 AC 07 00 00 FF B7 B0 07 00 00"
    "FF B7 80 05 00 00 FF B7 84 05 00 00 FF B7 88 05 00 00 FF 77 60"
    "FF B7 40 08 00 00"
    # fn_GotoWallingEntry 0x526920(obj,&ok,&facing) ; ok -> started
    "53 8D 43 28 50 FF 35 48 4A D3 00 E8 D0 C6 C6 FF 83 C4 0C 83 7B 28 00 75 54"
    # failed: restore the 13 fields
    "8F 87 40 08 00 00 8F 47 60 8F 87 88 05 00 00 8F 87 84 05 00 00"
    "8F 87 80 05 00 00 8F 87 B0 07 00 00 8F 87 AC 07 00 00 8F 87 A8 07 00 00"
    "8F 87 04 02 00 00 8F 87 E4 08 00 00 8F 87 E0 08 00 00 8F 87 DC 08 00 00"
    "8F 87 CC 04 00 00"
    # skip: add esp,0x2C ; popad ; jmp 0x64CEBA   (vanilla wall-contact path)
    "83 C4 2C 61 E9 0D 2C D9 FF"
    # started: add esp,0x60 ; popad ; jmp 0x64DAF7   (handler exit, wall run running)
    "83 C4 60 61 E9 41 38 D9 FF"
    # padding ; VZMIN = -10.0f at VA 0x8BA2B8 (file 0x4BA2B8): tuning knob
    "66 90 00 00 20 C1"
)

# (file offset, original bytes, new bytes). File offset = VA - 0x400000.
PATCHES = [
    # PE header: .text VirtualSize 0x4B9120 -> 0x4BA000 so the loader maps the cave bytes
    (0x180,
     bytes.fromhex("20 91 4B 00"),
     bytes.fromhex("00 A0 4B 00")),
    # 0x64CEAF: airborne handler, wall contact confirmed -> jmp to the cave
    (0x24CEAF,
     bytes.fromhex("83 C4 08 85 C0 0F 84 DD 08 00 00"),
     bytes.fromhex("E9 7C D2 26 00 90 90 90 90 90 90")),
    (CAVE_OFFSET, bytes(len(CAVE)), CAVE),
]


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    if src.resolve() == dst.resolve():
        print("Refusing to overwrite the input file; choose a different output path.")
        return 1

    data = bytearray(src.read_bytes())
    if hashlib.sha256(data).hexdigest() != JUMP_PATCHED_SHA256:
        print("Input is not the expected jump-patched POP2.EXE (sha256 mismatch). Nothing written.")
        return 1

    for offset, original, new in PATCHES:
        assert len(original) == len(new)
        if data[offset:offset + len(original)] != original:
            print(f"Unexpected bytes at file offset {offset:#x}. Nothing written.")
            return 1
        data[offset:offset + len(new)] = new

    dst.write_bytes(data)

    written = dst.read_bytes()
    for offset, _, new in PATCHES:
        if written[offset:offset + len(new)] != new:
            print(f"Verification failed at {offset:#x}.")
            return 1
    print(f"Patched copy written to {dst}")
    print(f"sha256: {hashlib.sha256(written).hexdigest()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
