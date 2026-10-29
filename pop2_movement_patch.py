"""Prince of Persia: Warrior Within (Steam, POP2.EXE) movement patch.

Changes:
  * Jump key: a new "Jump" action in the Controls menu (after Roll/Jump, default V).
    It acts as Space everywhere, but direction + Jump is a forward jump instead of a roll.
    Space is vanilla again (direction + Space = roll). Existing profiles start with the
    new action unbound: bind it in the menu or use Default settings.
  * Wall-run addon: hold the wall-run button (right mouse by default) while jumping or
    rebounding into a wall to start a wall run from mid-air. Keep holding it to chain runs.
    At an angle the run is horizontal; head-on (within 30 degrees) it is vertical. Vertical
    air runs are optional (the script asks); without them a head-on contact stays vanilla.
  * Stairs-jump fix: a normal jump can no longer land before its apex. Fixes the instant
    landing when jumping up a slope or stairs near an edge (also present in vanilla).
  * Story-trigger fix: the game refuses story triggers while the Prince is in a jump, so
    jumping through or over one could skip story progress (also present in vanilla). Such a
    trigger now fires when he lands, as if he had walked through it. Jumping over counts down
    to the take-off height. Only story triggers are affected.
  * Angled wall jump: jump off a horizontal wall run with the Jump key (V by default) to leap
    45 degrees toward the running direction. Space still jumps straight out from the wall.

Usage: python pop2_movement_patch.py <path to original POP2.EXE> [output file or folder]
           [--vertical-wallruns | --no-vertical-wallruns]

Without either option the script asks whether to include vertical wall runs from jumps
(Enter = yes; with no console to answer, yes). The output defaults to POP2_patched.EXE next to the input. The original file is never
modified. Back it up, then replace POP2.EXE with the patched file. The script only accepts
the unmodified Steam POP2.EXE and checks every byte it changes. Requires Python 3.8+.
"""
import argparse
import hashlib
import sys
from pathlib import Path

ORIGINAL_SHA256 = "5559117d013155bbad608cedc2fd0dd272f37ed92c936fc4e151287f3b5ff1cb"
# sha256 of the output with and without vertical wall runs from jumps
PATCHED_SHA256_VERTICAL = "d938ffb98c67a49d30a41130a876b7fedda2eaf5e9dee9570cbe945fe54b025a"
PATCHED_SHA256_HORIZONTAL = "3245e9119059103d989e168dd98ee4ef9c065914c3f6f87547ff751b28c6a412"

# sha256 -> description of builds produced by earlier versions of this script
KNOWN_OLDER_BUILDS = {
    "6ccc356273865a9c2396760b4dd7afe0ac371979071c602c53d561c206aa9800": "jump addon",
    "7c65edf1b541b2cdbbb0517fd47de2735f3c4c722c102a505ed62d9dd7abd60d": "jump + wall-run addons",
    "28ec8372bc2d167e67f449106deb708b9d63e84554bdf4b6978c540ea8b769a6":
        "jump + wall-run addons + stairs-jump fix",
    "88193b3d610c10c8ebe33a5cfb25fd27c59c2f27d6a6b81a92ecb676a817f926":
        "jump key + wall-run addon + stairs-jump fix",
    "9138830c28532a319ac20e230ccc7a2c1055fc486a6e871debadfd599bc4d642":
        "jump key + wall-run addon with vertical runs + stairs-jump and story-trigger fixes",
    "f9b40d56f5828243a0ab15cfee02bf873a8f20198f2fae8bdc1fcccc3c3073c9":
        "jump key + wall-run addon + stairs-jump and story-trigger fixes",
}

# Code caves. Addresses in comments are virtual addresses; file offset = VA - 0x400000.
JUMP_CAVE = bytes.fromhex(
    # test byte [0x93F062], 1 ; je roll ; 12x nop   (pad bit 16 = Jump key held, set by PAD_CAVE)
    "F6 05 62 F0 93 00 01 74 1E 90 90 90 90 90 90 90 90 90 90 90 90"
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
    # |facing.xy . n.xy| > cos30 (0x8C0E74) -> skip   (head-on stays vanilla, no vertical run;
    # the je at 0x8BA1EF is removed by VERTICAL_WALLRUN_PATCH)
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
    # started: jmp 0x8BA690 ; 4x nop   (WALLRUN_LATCH_CAVE, then the handler exit)
    "E9 DE 03 00 00 90 90 90 90"
    # padding ; VZMIN = -10.0f at VA 0x8BA2B8 (file 0x4BA2B8)
    "66 90 00 00 20 C1"
)

# Stairs-jump fix: normal jumps keep a stale falling flag [vars+0x4CC] = 1, so any ground contact
# lands them, even right after take-off. The flag itself stays vanilla (clearing it moves the
# fall-start height [vars+0x204] to the apex and adds the jump rise to fall damage). Instead,
# PENDING (dword at 0xDBFCEC in the .data tail) holds the Prince data from take-off until the
# vertical velocity is <= 0, and the landing gate refuses to land while it is set.
STAIRSJUMP_CAVE = bytes.fromhex(  # at 0x8BA2C0, jumped to from the take-off handler 0x64F068
    # mov [esi+0x578],ecx   (replayed hook: launch time)
    "89 8E 78 05 00 00"
    # mov [PENDING],esi   (apex not reached yet)
    "89 35 EC FC DB 00"
    # jmp 0x64F06E   (mov/jmp only: the je there still sees the flags of cmp eax,ebp)
    "E9 9D 4D D9 FF"
)

STAIRSJUMP_APEX_CAVE = bytes.fromhex(  # at 0x8BA570, jumped to from the airborne handler 0x64C819
    # cmp [PENDING],esi ; jne vanilla
    "39 35 EC FC DB 00 75 2D"
    # sub esp,0xC ; 0x4A7980([0xD34A48], esp) velocity
    "83 EC 0C 54 FF 35 48 4A D3 00 E8 F9 D3 BE FF 83 C4 08"
    # v.z > 0 (rising) or NaN -> keep ; else PENDING = 0   (same test as the vanilla falling flag)
    "D9 EE D9 44 24 08 DF F1 DD D8 7A 0C 77 0A C7 05 EC FC DB 00 00 00 00 00"
    # add esp,0xC
    "83 C4 0C"
    # vanilla: cmp [esi+0x4CC],ebx ; jne 0x64C884 ; jmp 0x64C821   (replayed hook)
    "39 9E CC 04 00 00 0F 85 D3 22 D9 FF E9 6B 22 D9 FF"
)

STAIRSJUMP_GATE_CAVE = bytes.fromhex(  # at 0x8BA5C0, jumped to from the landing gate 0x64CDB5
    # cmp [esi+0x4CC],ebx ; je 0x64CDC1   (replayed: falling flag clear -> no landing)
    "39 9E CC 04 00 00 0F 84 F5 27 D9 FF"
    # cmp [PENDING],esi ; je 0x64CDC1   (before the apex -> no landing)
    "39 35 EC FC DB 00 0F 84 E9 27 D9 FF"
    # jmp 0x64DCC8   (landing)
    "E9 EB 36 D9 FF"
)

# Jump key: new action 0x10. Controls-menu order (24 vanilla entries at 0x8BC244 + 0x10 after
# Roll/Jump 0x00), relocated to 0x8BA2E0 because a vtable pointer follows the original array.
JUMPKEY_ORDER = bytes.fromhex(
    "27 25 28 26 2D 00 10 07 02 03 01 06 05 04 0A 08 09 2B 2C 29 2A 0C 0E 0F 0D")

JUMPKEY_LABEL = b"Jump\0"  # at 0x8BA300

JUMPKEY_LABEL_CAVE = bytes.fromhex(  # at 0x8BA310, hooked from text lookup 0x418050(&group,&key)
    # eax = key c_str   (MSVC 7.1 std::string: +4 inline buffer or pointer, +0x18 capacity)
    "8B 44 24 08 83 78 18 10 72 05 8B 40 04 EB 03 83 C0 04"
    # key == "Action_16" ? (cmp "Acti", "on_1", "6\0") ; else -> orig
    "81 38 41 63 74 69 75 19 81 78 04 6F 6E 5F 31 75 10 66 81 78 08 36 00 75 08"
    # mov eax, 0x8BA300 ("Jump") ; ret 8
    "B8 00 A3 8B 00 C2 08 00"
    # orig: mov eax,[esp+4] ; push esi ; mov esi,ecx ; jmp 0x418057   (replayed entry)
    "8B 44 24 04 56 8B F1 E9 08 DD B5 FF"
)

JUMPKEY_DEFAULTS_CAVE = bytes.fromhex(  # at 0x8BA350, hooked from the end of SetDefaultBindings
    # cmp byte [esi+8],0 ; je done   (same guard as every vanilla default)
    "80 7E 08 00 74 16"
    # 0x41B090(device 0, DIK_V 0x2F)   (free V from any other action)
    "6A 2F 6A 00 8B CE E8 2F 0D B6 FF"
    # action 0x10 slot 0 = keyboard V
    "8B 46 34 C6 40 60 00 C6 40 61 2F"
    # done: pop edi ; pop esi ; add esp,8 ; ret   (replayed epilogue)
    "5F 5E 83 C4 08 C3"
)

JUMPKEY_PAD_CAVE = bytes.fromhex(  # at 0x8BA380, hooked from the pad builder after the enable mask
    # push ecx (0x200 stays live) ; 0x41B540(0x10) -> st0
    "51 6A 10 B9 68 F0 93 00 E8 B3 11 B6 FF"
    # st0 > 0.0 ?   (same test as the vanilla bits)
    "D8 1D 28 BD 8B 00 DF E0 F6 C4 41 75 13"
    # Space enabled by mask [0x9114A8] ? -> or dword [0x93F060], 0x10001   (Space + Jump-key bit)
    "F6 05 A8 14 91 00 01 74 0A 81 0D 60 F0 93 00 01 00 01 00"
    # skip: pop ecx ; mov eax,[0x93F0E4] ; jmp 0x41DAF3   (replayed)
    "59 A1 E4 F0 93 00 E9 3B 37 B6 FF"
)

# Story-trigger fix: replaces the trigger manager's point test 0x49DE40(vol, actor) (cdecl).
# Story gates (type 5/0xD) refuse the Prince in movement mode 4 (jump) / 0x15. A gate touched in
# those modes (or jumped over: points below him down to take-off z) is latched, and reported as
# inside for HOLD manager runs once he leaves them, so it gets a fresh enter on the ground.
# Latch variables in the .data tail: LATCH_VOL 0xDBFCE0, LATCH_T 0xDBFCE4 (float), LATCH_HOLD 0xDBFCE8.
STORYTRIGGER_CAVE = bytes.fromhex(  # at 0x8BA3C0, called from 0x5CF620
    # push ebx/esi/edi/ebp ; esi = vol ; edi = actor
    "53 56 57 55 8B 74 24 14 8B 7C 24 18"
    # ebp = r = 0x49DE40(vol, actor)   (vanilla result, returned on every path but the hold)
    "57 56 E8 6D 3A BE FF 83 C4 08 89 C5"
    # actor != Prince [0xD0C414] -> ret_r
    "3B 3D 14 C4 D0 00 0F 85 9A 00 00 00"
    # vol or actor without flag bit 0 -> ret_r   (same gates as 0x7B0CA0)
    "F6 46 04 01 0F 84 90 00 00 00 F6 47 04 01 0F 84 86 00 00 00"
    # trigger type [[[vol+0x18]+4]+0x48]+0xD0 not 5/0xD (story gate) -> ret_r
    "8B 46 18 8B 40 04 8B 40 48 8B 80 D0 00 00 00 83 F8 05 74 05 83 F8 0D 75 6D"
    # ebx = Prince data ; mode [ebx+0x644] 4 or 0x15 -> in_jump
    "8B 5F 18 8B 5B 04 8B 5B 48 8B 83 44 06 00 00 83 F8 04 74 60 83 F8 15 74 5B"
    # vol != LATCH_VOL -> ret_r ; r != 0 -> clear   (inside anyway: vanilla handles it)
    "3B 35 E0 FC DB 00 75 4C 85 ED 75 3E"
    # dt = now ([0x940974] - [0xCD3318]) - LATCH_T ; dt < 0 or NaN -> expire_pop
    "D9 05 74 09 94 00 D8 25 18 33 CD 00 D8 25 E4 FC DB 00 D9 EE DF F1 77 24 7A 22"
    # dt > TMAX -> clear
    "D9 05 68 A5 8B 00 DF F1 DD D8 72 18"
    # LATCH_HOLD == 0 -> clear ; LATCH_HOLD-- ; eax = 1 (inside) ; jmp done
    "83 3D E8 FC DB 00 00 74 0F FF 0D E8 FC DB 00 B8 01 00 00 00 EB 0E"
    # expire_pop: fstp st0 ; clear: LATCH_VOL = 0 ; ret_r: eax = r ; done: pop ebp/edi/esi/ebx ; ret
    "DD D8 C7 05 E0 FC DB 00 00 00 00 00 89 E8 5D 5F 5E 5B C3"
    # in_jump: r != 0 -> latch   (inside mid-air, refused by the gate)
    "85 ED 0F 85 A9 00 00 00"
    # state [ebx+0x640] not 0x412 (jump) / 0x413 (rebound) -> ret_r
    "8B 83 40 06 00 00 3D 12 04 00 00 74 07 3D 13 04 00 00 75 DD"
    # 0x49F5D0(prince, 0x40) ground contact this frame -> ret_r
    "6A 40 57 E8 27 51 BE FF 83 C4 08 85 C0 75 CE"
    # sub esp,0x10 (p = [esp], bottom = [esp+0xC]) ; p = Prince translation [[edi+0xC]+0x30]
    "83 EC 10 8B 47 0C 8B 48 30 89 0C 24 8B 48 34 89 4C 24 04 D9 40 38 D9 54 24 08"
    # bottom = max(take-off z [ebx+0x8E4], z - DMAX)
    "D8 25 64 A5 8B 00 D9 83 E4 08 00 00 DB F1 73 02 D9 C9 D9 5C 24 0C DD D8"
    # z <= bottom (or NaN) -> no_hit
    "D9 44 24 0C D9 44 24 08 DF F1 DD D8 76 37"
    # next: p.z -= STEP, or p.z = bottom as the last sample (ebp = 1)
    "D9 44 24 08 D8 25 60 A5 8B 00 D9 44 24 0C DB F1 72 09"
    "DD D9 BD 01 00 00 00 EB 04 DD D8 31 ED D9 5C 24 08"
    # 0x7AF870(vol, &p) point in bounding volume ; hit -> hit ; not last -> next
    "89 E0 50 56 E8 54 53 EF FF 83 C4 08 85 C0 75 0E 85 ED 74 C9"
    # no_hit: add esp,0x10 ; r = 0 ; jmp ret_r
    "83 C4 10 31 ED E9 4D FF FF FF"
    # hit: add esp,0x10 ; r = 0   (the mid-air result stays vanilla)
    "83 C4 10 31 ED"
    # latch: LATCH_VOL = vol ; LATCH_T = now ; LATCH_HOLD = 10 ; jmp ret_r
    "89 35 E0 FC DB 00 D9 05 74 09 94 00 D8 25 18 33 CD 00 D9 1D E4 FC DB 00"
    "C7 05 E8 FC DB 00 0A 00 00 00 E9 21 FF FF FF"
    # padding ; STEP = 0.25f at VA 0x8BA560 ; DMAX = 3.0f at 0x8BA564 ; TMAX = 10.0f at 0x8BA568
    "8D 76 00 00 00 80 3E 00 00 40 40 00 00 20 41"
)

# Angled wall jump: the horizontal wall-run jump-off has no direction of its own; its push-off
# animation (0x78/0x79) launches relative to the Prince's facing, which is the run direction f.
# When the Jump key triggered it, the facing is turned 45 degrees toward the wall first,
# f' = cos45*f - sin45*n (n = wall normal [vars+0x61C], stored by the wall-run handler this
# frame), so the leap turns 45 degrees from straight out toward the run direction.
WALLJUMP_ANGLE_CAVE = bytes.fromhex(  # at 0x8BA5E0, jumped to from the jump-off 0x591019
    # test byte [0x93F062], 1 ; 3x nop ; jne angled   (pad bit 16 = Jump key held, set by
    # PAD_CAVE together with the Space bit, so Space alone keeps the vanilla jump-off)
    "F6 05 62 F0 93 00 01 90 90 90 75 0B"
    # mov edx,[0xD34A48] ; jmp 0x59101F   (replayed hook: vanilla jump-off)
    "8B 15 48 4A D3 00 E9 28 6A CD FF"
    # angled: pushad ; sub esp,0x18 ; mov ebx,esp   (f = [ebx], f' = [ebx+0xC])
    "60 83 EC 18 89 E3"
    # 0x490850(obj,&f)   facing
    "53 FF 35 48 4A D3 00 E8 47 62 BD FF 83 C4 08"
    # f'.x = COS45*f.x - SIN45*n.x
    "D9 05 88 A6 8B 00 D8 8E 1C 06 00 00 D9 5B 0C"
    "D9 05 84 A6 8B 00 D8 0B D8 63 0C D9 5B 0C"
    # f'.y = COS45*f.y - SIN45*n.y
    "D9 05 88 A6 8B 00 D8 8E 20 06 00 00 D9 5B 10"
    "D9 05 84 A6 8B 00 D8 4B 04 D8 63 10 D9 5B 10"
    # f'.z = 0 ; 0x47C620(&f') flatten + normalize
    "C7 43 14 00 00 00 00 8D 43 0C 50 E8 C9 1F BC FF 83 C4 04"
    # up = (0,0,1) on the stack ; 0x4902A0(obj,&f',&up)   set facing
    "68 00 00 80 3F 6A 00 6A 00 89 E0 50 8D 43 0C 50 FF 35 48 4A D3 00 E8 2B 5C BD FF"
    # add esp,0x30 ; popad ; mov edx,[0xD34A48] ; jmp 0x59101F   (replayed hook, new facing)
    "83 C4 30 61 8B 15 48 4A D3 00 E9 9B 69 CD FF"
    # COS45 = 0.707107f at VA 0x8BA684 ; SIN45 = 0.707107f at 0x8BA688
    "F3 04 35 3F F3 04 35 3F"
)

# Wall-run addon, held-button chains: a running horizontal wall run continues only while the
# wall-run latch [vars+0x13E8] is set (0x590D8B). The game sets it on a fresh press and clears it
# on release, but also clears it inside chains while the button is still held, so an air run
# started from the held button would wind down after a moment. Setting the latch when the cave
# starts a run makes it behave like a freshly pressed run; releasing still clears it.
WALLRUN_LATCH_CAVE = bytes.fromhex(  # at 0x8BA690, jumped to from WALLRUN_CAVE's started path
    # mov dword [edi+0x13E8],1   (edi = Prince data, button confirmed held this frame)
    "C7 87 E8 13 00 00 01 00 00 00"
    # add esp,0x60 ; popad ; jmp 0x64DAF7   (handler exit, wall run running)
    "83 C4 60 61 E9 54 34 D9 FF"
)

# (file offset, original bytes, new bytes)
PATCHES = [
    # Jump key: 0x4DD331 roll block entry -> jmp to the jump cave
    (0xDD331,
     bytes.fromhex("C7 85 48 04 00 00 02 00 00 00"),
     bytes.fromhex("E9 8D 73 3A 00 90 90 90 90 90")),
    # Jump key: roll/jump cave in int3 padding at 0x8846C3
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
    # Stairs-jump fix: 0x64F068 take-off handler, launch-time store -> jmp to the cave
    (0x24F068,
     bytes.fromhex("89 8E 78 05 00 00"),
     bytes.fromhex("E9 53 B2 26 00 90")),
    # Stairs-jump fix: cave in the .text slack at 0x8BA2C0, after the wall-run cave
    (0x4BA2C0, bytes(len(STAIRSJUMP_CAVE)), STAIRSJUMP_CAVE),
    # Stairs-jump fix: 0x64C819 airborne apex check -> jmp to the apex cave
    (0x24C819,
     bytes.fromhex("39 9E CC 04 00 00 75 63"),
     bytes.fromhex("E9 52 DD 26 00 90 90 90")),
    # Stairs-jump fix: 0x64CDB5 landing gate -> jmp to the gate cave
    (0x24CDB5,
     bytes.fromhex("39 9E CC 04 00 00 0F 85 07 0F 00 00"),
     bytes.fromhex("E9 06 D8 26 00 90 90 90 90 90 90 90")),
    # Stairs-jump fix: apex and gate caves in the .text slack after the story-trigger cave
    (0x4BA570, bytes(len(STAIRSJUMP_APEX_CAVE)), STAIRSJUMP_APEX_CAVE),
    (0x4BA5C0, bytes(len(STAIRSJUMP_GATE_CAVE)), STAIRSJUMP_GATE_CAVE),
    # Jump key: the 4 readers of the Controls-menu order array 0x8BC244 -> 0x8BA2E0
    (0x5A54, bytes.fromhex("8A 8C 30 44 C2 8B 00"), bytes.fromhex("8A 8C 30 E0 A2 8B 00")),
    (0x64D7, bytes.fromhex("0F B6 8C 38 44 C2 8B 00"), bytes.fromhex("0F B6 8C 38 E0 A2 8B 00")),
    (0x6626, bytes.fromhex("8A 84 3A 44 C2 8B 00"), bytes.fromhex("8A 84 3A E0 A2 8B 00")),
    (0x66A4, bytes.fromhex("8A 84 3A 44 C2 8B 00"), bytes.fromhex("8A 84 3A E0 A2 8B 00")),
    # Jump key: Controls-menu scroll limits for 25 rows (max offset 19 -> 20)
    (0x6748, bytes([0x13]), bytes([0x14])),
    (0x6A46, bytes([0x12]), bytes([0x13])),
    # Jump key: hooks -> label, defaults and pad-builder caves
    (0x18050, bytes.fromhex("8B 44 24 04 56 8B F1"), bytes.fromhex("E9 BB 22 4A 00 90 90")),
    (0x1CD60, bytes.fromhex("5F 5E 83 C4 08 C3"), bytes.fromhex("E9 EB D5 49 00 90")),
    (0x1DAEE, bytes.fromhex("A1 E4 F0 93 00"), bytes.fromhex("E9 8D C8 49 00")),
    # Jump key: data and caves in the .text slack after the stairs-jump cave
    (0x4BA2E0, bytes(len(JUMPKEY_ORDER)), JUMPKEY_ORDER),
    (0x4BA300, bytes(len(JUMPKEY_LABEL)), JUMPKEY_LABEL),
    (0x4BA310, bytes(len(JUMPKEY_LABEL_CAVE)), JUMPKEY_LABEL_CAVE),
    (0x4BA350, bytes(len(JUMPKEY_DEFAULTS_CAVE)), JUMPKEY_DEFAULTS_CAVE),
    (0x4BA380, bytes(len(JUMPKEY_PAD_CAVE)), JUMPKEY_PAD_CAVE),
    # Story-trigger fix: 0x5CF620 trigger manager point test -> call the story-trigger cave
    (0x1CF620, bytes.fromhex("E8 1B E8 EC FF"), bytes.fromhex("E8 9B AD 2E 00")),
    # Story-trigger fix: cave in the .text slack at 0x8BA3C0, after the Jump-key caves
    (0x4BA3C0, bytes(len(STORYTRIGGER_CAVE)), STORYTRIGGER_CAVE),
    # Story-trigger and stairs-jump fixes: PE header, .data VirtualSize 0x4AECD8 -> 0x4AED00 (maps
    # the latch variables at 0xDBFCE0..0xDBFCEB and PENDING at 0xDBFCEC, zero-filled, inside the
    # section's last page)
    (0x1D0,
     bytes.fromhex("D8 EC 4A 00"),
     bytes.fromhex("00 ED 4A 00")),
    # Angled wall jump: 0x591019 horizontal wall-run jump-off -> jmp to the cave
    (0x191019, bytes.fromhex("8B 15 48 4A D3 00"), bytes.fromhex("E9 C2 95 32 00 90")),
    # Angled wall jump: cave in the .text slack at 0x8BA5E0, after the stairs-jump gate cave
    (0x4BA5E0, bytes(len(WALLJUMP_ANGLE_CAVE)), WALLJUMP_ANGLE_CAVE),
    # Wall-run addon: latch cave in the .text slack at 0x8BA690, after the angled wall jump cave
    (0x4BA690, bytes(len(WALLRUN_LATCH_CAVE)), WALLRUN_LATCH_CAVE),
]

# Vertical wall runs from jumps (optional, on by default): the wall-run cave's head-on check at
# 0x8BA1EF -> nops, so a contact within 30 degrees of head-on also reaches 0x526920, which starts
# a vertical run there. Applied after PATCHES: its original bytes are the cave written by them.
VERTICAL_WALLRUN_PATCH = (
    0x4BA1EF, bytes.fromhex("0F 84 AF 00 00 00"), bytes.fromhex("90 90 90 90 90 90"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Movement patch for Prince of Persia: Warrior Within (Steam POP2.EXE).")
    parser.add_argument("input", type=Path, help="path to the original POP2.EXE")
    parser.add_argument("output", type=Path, nargs="?",
                        help="output file or folder (default: POP2_patched.EXE next to the input; "
                             "a folder gets POP2_patched.EXE inside it)")
    vertical = parser.add_mutually_exclusive_group()
    vertical.add_argument("--vertical-wallruns", dest="vertical", action="store_true",
                          help="include vertical wall runs from jumps without asking")
    vertical.add_argument("--no-vertical-wallruns", dest="vertical", action="store_false",
                          help="only horizontal wall runs from jumps, without asking")
    parser.set_defaults(vertical=None)
    return parser.parse_args()


def ask_vertical_wallruns() -> bool:
    """Ask whether to include vertical wall runs from jumps. Enter or no console means yes."""
    while True:
        try:
            answer = input("Include vertical wall runs from jumps? [Y/n] ").strip().lower()
        except EOFError:
            print()
            return True
        if answer in ("", "y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("Please answer y or n.")


def main() -> int:
    args = parse_args()
    src = args.input
    default_name = "POP2_patched.EXE"
    dst = args.output or src.with_name(default_name)
    if dst.is_dir():
        dst = dst / default_name
    if not src.is_file():
        print(f"Input not found: {src}")
        return 1
    if src.resolve() == dst.resolve():
        print("Refusing to overwrite the input file; choose a different output path.")
        return 1

    data = bytearray(src.read_bytes())
    sha = hashlib.sha256(data).hexdigest()
    if sha in (PATCHED_SHA256_VERTICAL, PATCHED_SHA256_HORIZONTAL):
        print("This file is already patched. Nothing written.")
        return 1
    if sha in KNOWN_OLDER_BUILDS:
        print(f"This is an older patched build ({KNOWN_OLDER_BUILDS[sha]}). Restore the original "
              "POP2.EXE from your backup (or Steam > Verify integrity) and run the script on that. "
              "Nothing written.")
        return 1
    if sha != ORIGINAL_SHA256:
        print("Input is not the original Steam POP2.EXE (sha256 mismatch). Nothing written.")
        return 1

    vertical = args.vertical
    if vertical is None:
        try:
            vertical = ask_vertical_wallruns()
        except KeyboardInterrupt:
            print("\nCancelled. Nothing written.")
            return 1
    patches = PATCHES + ([VERTICAL_WALLRUN_PATCH] if vertical else [])
    expected_sha = PATCHED_SHA256_VERTICAL if vertical else PATCHED_SHA256_HORIZONTAL

    for offset, original, new in patches:
        assert len(original) == len(new)
        if data[offset:offset + len(original)] != original:
            print(f"Unexpected bytes at file offset {offset:#x}. Nothing written.")
            return 1
        data[offset:offset + len(new)] = new

    if hashlib.sha256(data).hexdigest() != expected_sha:
        print("Internal error: patched result has an unexpected sha256. Nothing written.")
        return 1

    try:
        dst.write_bytes(data)
    except OSError as err:
        print(f"Could not write {dst} ({err.strerror}).")
        return 1
    if hashlib.sha256(dst.read_bytes()).hexdigest() != expected_sha:
        print(f"Verification of {dst} failed; delete it and try again.")
        return 1
    print(f"Patched copy written to {dst} ")
    print("Back up the original POP2.EXE, then replace it with the patched file.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
