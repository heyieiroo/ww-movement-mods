"""Apply the 'Space while moving = forward jump, Shift+Space = roll' patch to POP2.EXE.

Usage: python patch_jump.py <vanilla POP2.EXE> <output path>

The input file is never modified. The script refuses to run if the input is not
the analysed vanilla build or if any original bytes differ from what is expected.
"""
import hashlib
import sys
from pathlib import Path

VANILLA_SHA256 = "5559117d013155bbad608cedc2fd0dd272f37ed92c936fc4e151287f3b5ff1cb"

# (file offset, original bytes, new bytes). File offset = VA - 0x400000.
PATCHES = [
    # 0x4DD331: roll block entry -> jmp to code cave
    (0xDD331,
     bytes.fromhex("C7 85 48 04 00 00 02 00 00 00"),
     bytes.fromhex("E9 8D 73 3A 00 90 90 90 90 90")),
    # 0x8846C3: code cave in int3 padding
    (0x4846C3,
     bytes([0xCC]) * 54,
     bytes.fromhex(
         # cmp dword [0x93F07C], 1.0 ; jne roll ; 9x nop   (walk mode -> roll)
         "81 3D 7C F0 93 00 00 00 80 3F 75 1B 90 90 90 90 90 90 90 90 90"
         # mov dword [esp+0x1C], 6.0 ; mov esi, 0x27 ; jmp 0x4DCEAB   (forward jump)
         "C7 44 24 1C 00 00 C0 40 BE 27 00 00 00 E9 C1 87 C5 FF"
         # mov dword [ebp+0x448], 2 ; jmp 0x4DD33B   (original roll)
         "C7 85 48 04 00 00 02 00 00 00 E9 42 8C C5 FF")),
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
    if hashlib.sha256(data).hexdigest() != VANILLA_SHA256:
        print("Input is not the expected vanilla POP2.EXE (sha256 mismatch). Nothing written.")
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
