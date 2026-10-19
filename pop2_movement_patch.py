"""Prince of Persia: Warrior Within (Steam, POP2.EXE) movement patch.

Changes:
  * Jump addon: direction + Space is a forward jump instead of a roll.
    Hold Shift (walk) with direction + Space to roll.
  * Wall-run addon: hold the wall-run button (right mouse by default) while jumping or
    rebounding into a wall at an angle (not head-on) to start a horizontal wall run
    from mid-air. Keep holding it to chain runs.

Usage: python pop2_movement_patch.py <path to original POP2.EXE> [output path]

The output defaults to POP2_patched.EXE next to the input. The original file is never
modified. Back it up, then replace POP2.EXE with the patched file. The script only accepts
the unmodified Steam POP2.EXE and checks every byte it changes. Requires Python 3.8+.
"""
import hashlib
import sys
from pathlib import Path

ORIGINAL_SHA256 = "5559117d013155bbad608cedc2fd0dd272f37ed92c936fc4e151287f3b5ff1cb"
PATCHED_SHA256 = "7c65edf1b541b2cdbbb0517fd47de2735f3c4c722c102a505ed62d9dd7abd60d"

# Code caves. Addresses in comments are virtual addresses; file offset = VA - 0x400000.
JUMP_CAVE = bytes.fromhex(
    # cmp dword [0x93F07C], 1.0 ; jne roll ; 9x nop   (walk mode -> roll)
    "81 3D 7C F0 93 00 00 00 80 3F 75 1B 90 90 90 90 90 90 90 90 90"
    # mov dword [esp+0x1C], 6.0 ; mov esi, 0x27 ; jmp 0x4DCEAB   (forward jump)
    "C7 44 24 1C 00 00 C0 40 BE 27 00 00 00 E9 C1 87 C5 FF"
    # mov dword [ebp+0x448], 2 ; jmp 0x4DD33B   (original roll)
    "C7 85 48 04 00 00 02 00 00 00 E9 42 8C C5 FF"
)

WALLRUN_CAVE = bytes.fromhex(
    # add esp,8 ; test eax,eax ; je 0x64D797   (replayed hook: no wall contact -> vanilla)
    "83 C4 08 85 C0 0F 84 5C 36 D9 FF"
    # pushad ; sub esp,0x2C ; mov ebx,esp ; edi = [[0xD34A40]+0x48]   (Prince data)
    "60 83 EC 2C 89 E3 8B 3D 40 4A D3 00 8B 7F 48"
    # 0x71E450(obj,&held,[edi+0x10B8],5) ; held == 0 -> skip   (wall-run button held)
    "6A 05 FF B7 B8 10 00 00 8D 43 24 50 FF 35 48 4A D3 00 E8 EF 42 E6 FF 83 C4 10"
    "83 7B 24 00 0F 84 36 01 00 00"
    # 0x4A7980(obj,&v) ; v.z < VZMIN -> skip   (only near the impact, not late in a slide)
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
    # padding ; VZMIN = -10.0f at VA 0x8BA2B8 (file 0x4BA2B8)
    "66 90 00 00 20 C1"
)

# (file offset, original bytes, new bytes)
PATCHES = [
    # Jump addon: 0x4DD331 roll block entry -> jmp to the jump cave
    (0xDD331,
     bytes.fromhex("C7 85 48 04 00 00 02 00 00 00"),
     bytes.fromhex("E9 8D 73 3A 00 90 90 90 90 90")),
    # Jump addon: roll/jump cave in int3 padding at 0x8846C3
    (0x4846C3, bytes([0xCC]) * len(JUMP_CAVE), JUMP_CAVE),
    # Wall-run addon: PE header, .text VirtualSize 0x4B9120 -> 0x4BA000 (maps the cave)
    (0x180,
     bytes.fromhex("20 91 4B 00"),
     bytes.fromhex("00 A0 4B 00")),
    # Wall-run addon: 0x64CEAF airborne wall contact -> jmp to the wall-run cave
    (0x24CEAF,
     bytes.fromhex("83 C4 08 85 C0 0F 84 DD 08 00 00"),
     bytes.fromhex("E9 7C D2 26 00 90 90 90 90 90 90")),
    # Wall-run addon: cave in the .text slack at 0x8BA130
    (0x4BA130, bytes(len(WALLRUN_CAVE)), WALLRUN_CAVE),
]


def main() -> int:
    if len(sys.argv) not in (2, 3):
        print(__doc__)
        return 2
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2]) if len(sys.argv) == 3 else src.with_name("POP2_patched.EXE")
    if not src.is_file():
        print(f"Input not found: {src}")
        return 1
    if src.resolve() == dst.resolve():
        print("Refusing to overwrite the input file; choose a different output path.")
        return 1

    data = bytearray(src.read_bytes())
    sha = hashlib.sha256(data).hexdigest()
    if sha == PATCHED_SHA256:
        print("This file is already patched. Nothing written.")
        return 1
    if sha != ORIGINAL_SHA256:
        print("Input is not the original Steam POP2.EXE (sha256 mismatch). Nothing written.")
        return 1

    for offset, original, new in PATCHES:
        assert len(original) == len(new)
        if data[offset:offset + len(original)] != original:
            print(f"Unexpected bytes at file offset {offset:#x}. Nothing written.")
            return 1
        data[offset:offset + len(new)] = new

    if hashlib.sha256(data).hexdigest() != PATCHED_SHA256:
        print("Internal error: patched result has an unexpected sha256. Nothing written.")
        return 1

    dst.write_bytes(data)
    if hashlib.sha256(dst.read_bytes()).hexdigest() != PATCHED_SHA256:
        print(f"Verification of {dst} failed; delete it and try again.")
        return 1
    print(f"Patched copy written to {dst}")
    print("Back up the original POP2.EXE, then replace it with the patched file.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
