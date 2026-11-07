"""Prince of Persia: Warrior Within (Steam, POP2.EXE) movement patch.

Changes:
  * Special Jump key: a new "Special Jump" action in the Controls menu (after Roll/Jump,
    default V). It acts as Space everywhere, but direction + Special Jump is a forward jump
    instead of a roll.
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
  * Angled wall jump: jump off a horizontal wall run with the Special Jump key (V by default)
    to leap 45 degrees toward the running direction. Space still jumps straight out.
  * Wall torpedo: jump off a horizontal wall run with Special Jump + primary attack (V + left
    click by default) to dive at 45 degrees in the torpedo attack, with or without an enemy.
  * Wall slide (optional, the script asks): hold Drop (C by default) for a moment while jumping
    into a wall that allows wall runs, and the Prince slides down it like on a curtain, steered
    left/right with the direction keys. He stops sideways at corners, drops where the wall ends
    or when C is released, grabs ledges on the way and lands softly. He draws his swords as the
    slide starts, like on a curtain. Space jumps off; Space + left/right jumps off at 45 degrees.
    Holding C down to the floor no longer throws the secondary weapon. It uses the curtain
    animations, so it works from the first area with a curtain onward (the game loads them
    there; the patch keeps them).
    Holding C also starts a slide without touching the wall: after dropping from a ledge or
    when a wall run ends next to a runnable wall. No slide starts when a ledge he can still
    grab is just below, or the floor is less than 1 unit below. If he ever gets stuck after a
    slide, or a rewind ends mid-slide with C released, he lets go.
  * Code section: the patch adds a 64 KB code section (.mods) for the mods' code; the wall slide
    uses it.

Usage: python pop2_movement_patch.py <path to original POP2.EXE> [output file or folder]
           [--vertical-wallruns | --no-vertical-wallruns] [--wall-slide | --no-wall-slide]

Without these options the script asks whether to include vertical wall runs from jumps and the
wall slide (Enter = yes; with no console to answer, yes). The output defaults to POP2_patched.EXE next to the input. The original file is never
modified. Back it up, then replace POP2.EXE with the patched file. The script only accepts
the unmodified Steam POP2.EXE and checks every byte it changes. Requires Python 3.8+.
"""
import argparse
import hashlib
import sys
from pathlib import Path

ORIGINAL_SHA256 = "5559117d013155bbad608cedc2fd0dd272f37ed92c936fc4e151287f3b5ff1cb"
# sha256 of the output for (vertical wall runs from jumps, wall slide)
PATCHED_SHA256 = {
    (True, False): "89815876a23200f8c3a47a752dae98d4778c2f075b09f1f7ffae740769b32c0b",
    (False, False): "ab030994cc2862e6bcd3cf4425b392e63349abcb6aa7a81943ad1b958635feeb",
    (True, True): "cf4b50c6089071b69b8a9fd671db2314e5f267ae0a762a8ff17d67f046445f0b",
    (False, True): "893a1c5e70ea80afb6fb30cdab84f7f245df669d1c63073bc1d35247a2a3301a",
}

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
    "d938ffb98c67a49d30a41130a876b7fedda2eaf5e9dee9570cbe945fe54b025a":
        "jump key + wall-run addon with vertical runs + angled wall jump + stairs-jump and "
        "story-trigger fixes",
    "3245e9119059103d989e168dd98ee4ef9c065914c3f6f87547ff751b28c6a412":
        "jump key + wall-run addon + angled wall jump + stairs-jump and story-trigger fixes",
    "e13659e0fecebc8d4d259be90f2271515bd63e82b9dad34696fb732c49475587":
        "movement patch with vertical wall runs, without the code section",
    "968fd715b305148ec8c634d8ebfbdb20a241529b985e61259a84530e0374c5bc":
        "movement patch without vertical wall runs, without the code section",
    "d679e1ea8617167104aa8772109cc12c3bbd488f829115768dd80f8b1a7bbc9d":
        "movement patch with vertical wall runs and the first wall slide",
    "5ad99a5088b160a08438f00f92bad4041938aebfb5f8c8116e4e5c825e716258":
        "movement patch with the first wall slide, without vertical wall runs",
    "603d39971f178a6bf3eebb33a8d72c9a804c38d72fe362aef00c76e034a8827c":
        "movement patch with vertical wall runs and the second wall slide",
    "3c6426a962ca8e0f42fbd81979e874cce22a5228d118534f4fdfa798c295df2b":
        "movement patch with the second wall slide, without vertical wall runs",
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

JUMPKEY_LABEL = b"Special Jump\0"  # at 0x8BA300 (room for 15 characters before the label cave)

JUMPKEY_LABEL_CAVE = bytes.fromhex(  # at 0x8BA310, hooked from text lookup 0x418050(&group,&key)
    # eax = key c_str   (MSVC 7.1 std::string: +4 inline buffer or pointer, +0x18 capacity)
    "8B 44 24 08 83 78 18 10 72 05 8B 40 04 EB 03 83 C0 04"
    # key == "Action_16" ? (cmp "Acti", "on_1", "6\0") ; else -> orig
    "81 38 41 63 74 69 75 19 81 78 04 6F 6E 5F 31 75 10 66 81 78 08 36 00 75 08"
    # mov eax, 0x8BA300 (JUMPKEY_LABEL) ; ret 8
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
# Every jump-off also stores whether it was a Jump-key jump-off in V_JUMPOFF (byte at 0xDBFCF0),
# for the wall torpedo below: its attack check runs when the push-off animation ends, when a
# quick V tap may already be released (and pad bit 16 has no press-time slot).
WALLJUMP_ANGLE_CAVE = bytes.fromhex(  # at 0x8BA5E0, jumped to from the jump-off 0x591019
    # mov al,[0x93F062] ; and al,1 ; mov [0xDBFCF0],al ; jne angled   (pad bit 16 = Jump key
    # held, set by PAD_CAVE together with the Space bit, so Space alone keeps the vanilla
    # jump-off; eax is free here, 0x59101F pushes and then calls)
    "A0 62 F0 93 00 24 01 A2 F0 FC DB 00 75 0B"
    # mov edx,[0xD34A48] ; jmp 0x59101F   (replayed hook: vanilla jump-off)
    "8B 15 48 4A D3 00 E9 26 6A CD FF"
    # angled: pushad ; sub esp,0x18 ; mov ebx,esp   (f = [ebx], f' = [ebx+0xC])
    "60 83 EC 18 89 E3"
    # 0x490850(obj,&f)   facing
    "53 FF 35 48 4A D3 00 E8 45 62 BD FF 83 C4 08"
    # f'.x = COS45*f.x - SIN45*n.x
    "D9 05 8A A6 8B 00 D8 8E 1C 06 00 00 D9 5B 0C"
    "D9 05 86 A6 8B 00 D8 0B D8 63 0C D9 5B 0C"
    # f'.y = COS45*f.y - SIN45*n.y
    "D9 05 8A A6 8B 00 D8 8E 20 06 00 00 D9 5B 10"
    "D9 05 86 A6 8B 00 D8 4B 04 D8 63 10 D9 5B 10"
    # f'.z = 0 ; 0x47C620(&f') flatten + normalize
    "C7 43 14 00 00 00 00 8D 43 0C 50 E8 C7 1F BC FF 83 C4 04"
    # up = (0,0,1) on the stack ; 0x4902A0(obj,&f',&up)   set facing
    "68 00 00 80 3F 6A 00 6A 00 89 E0 50 8D 43 0C 50 FF 35 48 4A D3 00 E8 29 5C BD FF"
    # add esp,0x30 ; popad ; mov edx,[0xD34A48] ; jmp 0x59101F   (replayed hook, new facing)
    "83 C4 30 61 8B 15 48 4A D3 00 E9 99 69 CD FF"
    # COS45 = 0.707107f at VA 0x8BA686 ; SIN45 = 0.707107f at 0x8BA68A
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

# Wall torpedo: when the wall jump-off's push-off animation ends, 0x6D3190 picks an attack from
# the recent presses. Primary attack picks the torpedo (move 0x273), but only with a target;
# secondary attack picks the spin and forces it after a horizontal wall jump-off ([esp+0x1C]).
# After a Jump-key jump-off, primary attack sets that same force flag, so the torpedo launches
# without a target along the facing, which is then the 45 degree flight direction.
WALLTORPEDO_CAVE = bytes.fromhex(  # at 0x8BA6B0, jumped to from the primary-attack branch 0x6D32BD
    # mov ebx,2   (replayed: torpedo kind)
    "BB 02 00 00 00"
    # cmp byte [0xDBFCF0],0 ; je back   (not a Jump-key jump-off: vanilla, needs a target)
    "80 3D F0 FC DB 00 00 74 1B"
    # push esi ; call 0x497B90 ; add esp,4   (current animation)
    "56 E8 CC D4 BD FF 83 C4 04"
    # cmp eax,0x78 ; je force ; cmp eax,0x79 ; jne back   (only the horizontal wall jump-off's
    # push-off, which always passes the angle cave first, so a stale flag never matters)
    "83 F8 78 74 05 83 F8 79 75 08"
    # force: mov dword [esp+0x1C],1   (the force flag the secondary-attack branch sets)
    "C7 44 24 1C 01 00 00 00"
    # back: jmp 0x6D32C2
    "E9 E4 8B E1 FF"
)

# Wall slide: a mode of the airborne handler's normal state 0x412, run from the wall-contact point
# (after the handler's ledge/curtain probes and landing check, so those keep working). Each frame
# with C held it sets the curtain animation, the facing into the wall and the fall height, and
# moves the Prince by position (the curtain animations freeze his physics): sideways from the
# stick at a fixed fraction of the descent speed, an accelerating descent computed from the
# elapsed time (the same at any frame rate), with rays for corners, walls across the path and
# the floor. Exits are the curtain jump-off (Space), a fall (C released, wall ended), a landing,
# or whatever the earlier checks start; a new slide needs 0.1 s since the last slide frame.
# The fall and landing exits use the curtain's own bottom exit (let-go animation, then the
# velocity). Only a wall within 60 degrees of his facing (or of the wall he slides on) counts,
# so a side wall at an inside corner is never taken.
# The curtain animations are loaded only with curtain areas: a hook on the "remove animation
# set" function keeps the Prince's copies (reference counted), and the slide starts only when
# they are present.
# State: 0xDBFD00 Prince data, 0xDBFD04 start time, 0xDBFD08 last slide frame, 0xDBFD0C last
# contact, 0xDBFD10 wall normal (3 floats).
WALLSLIDE_CAVE = bytes.fromhex(  # at 0x8BA6E0, jumped to from WALLRUN_CAVE (0x8BA135, 0x8BA13B) and from 0x497F20
    # tunables (floats unless noted): HOLD 0.2 s, V0 2.25, ACC 3.0, VMAX 5.0, LAT 0.75 (x descent),
    # FRONT 0.5 (cos 60 deg, wall check), GRACE 0.1 s, STALE 0.25 s, OUT 1.0, LOOK 0.45,
    # REACH 1.0, PZ 1.0, STICK 0.25, SIDE 0.5, C45 0.7071, JWIN 0.2 s, FZ 0.5, BODY 0.4,
    # HALF 0.5; dwords: ANIM 0x36C, FALLA 0x36D, JANIM 0x379, JANIM2 0x378, KEEP0 0x369,
    # KEEPN 17
    "CD CC 4C 3E 00 00 10 40 00 00 40 40 00 00 A0 40 00 00 40 3F 00 00 00 3F CD CC CC 3D 00 00 80 3E"
    "00 00 80 3F 66 66 E6 3E 00 00 80 3F 00 00 80 3F 00 00 80 3E 00 00 00 3F F3 04 35 3F CD CC 4C 3E"
    "00 00 00 3F CD CC CC 3E 00 00 00 3F 6C 03 00 00 6D 03 00 00 79 03 00 00 78 03 00 00 69 03 00 00"
    "11 00 00 00"
    # SL_CONTACT: pushad, ebp = 1 (wall contact) / SL_NOCONTACT: pushad, ebp = 0; main:
    # locals, now = [0x940974] - [0xCD3318]; sliding = SL_VARS == Prince data and the
    # last slide frame is not older than STALE
    "60 BD 01 00 00 00 EB 03 60 31 ED 81 EC 60 01 00 00 89 E7 8B 1D 48 4A D3 00 8B 35 40 4A D3 00 8B"
    "76 48 D9 05 74 09 94 00 D8 25 18 33 CD 00 D9 5F 4C 31 C0 89 47 30 89 47 34 C7 47 38 00 00 80 3F"
    "89 47 78 89 47 7C 89 87 80 00 00 00 39 35 00 FD DB 00 75 24 D9 47 4C D8 25 08 FD DB 00 D8 1D FC"
    "A6 8B 00 DF E0 F6 C4 41 0F 85 FF 00 00 00 C7 05 00 FD DB 00 00 00 00 00"
    # not sliding: needs contact, C down for HOLD, GRACE since the last slide frame, the
    # curtain animations in the table, a contact normal and no no-run flags 0x30000;
    # orients the normal out of the wall from the contact points, then starts the slide
    "85 ED 0F 84 B4 03 00 00 E8 90 05 00 00 0F 84 B5 03 00 00 D9 47 4C D8 A6 14 07 00 00 D8 1D E0 A6"
    "8B 00 DF E0 F6 C4 01 0F 85 9B 03 00 00 D9 47 4C D8 25 08 FD DB 00 D9 5F 24 8B 47 24 3B 05 F8 A6"
    "8B 00 0F 82 80 03 00 00 E8 4A 06 00 00 0F 84 75 03 00 00 8D 47 24 50 53 E8 37 60 BD FF 83 C4 08"
    "E8 52 05 00 00 0F 84 5D 03 00 00 8D 47 54 50 53 E8 AF 44 BD FF 83 C4 08 68 80 00 00 00 6A 0F 8D"
    "87 90 00 00 00 50 53 E8 88 54 BE FF 83 C4 10 89 C1 8D 97 90 00 00 00 D9 EE 85 C9 7E 1A D9 47 54"
    "D8 22 D8 0F D9 47 58 D8 62 04 D8 4F 04 DE C1 DE C1 83 C2 0C 49 EB E2 D9 E4 DF E0 DD D8 F6 C4 01"
    "74 05 E8 36 05 00 00 89 35 00 FD DB 00 8B 47 4C A3 04 FD DB 00 A3 08 FD DB 00 A3 0C FD DB 00 31"
    "C0 89 86 2C 03 00 00 89 86 30 03 00 00 89 86 34 03 00 00 EB 53"
    # sliding: refresh the normal (same side as last frame); without a usable contact, GRACE
    # then fall; animations gone or C up -> fall exit; jump within JWIN -> jump exit
    "85 ED 74 6A D9 05 10 FD DB 00 D9 E0 D9 5F 24 D9 05 14 FD DB 00 D9 E0 D9 5F 28 C7 47 2C 00 00 00"
    "00 E8 9C 04 00 00 74 44 D9 07 D8 0D 10 FD DB 00 D9 47 04 D8 0D 14 FD DB 00 DE C1 D9 E4 DF E0 DD"
    "D8 F6 C4 01 74 05 E8 BD 04 00 00 8B 47 4C A3 0C FD DB 00 8B 07 A3 10 FD DB 00 8B 47 04 A3 14 FD"
    "DB 00 8B 47 08 A3 18 FD DB 00 EB 33 31 ED D9 47 4C D8 25 0C FD DB 00 D8 1D F8 A6 8B 00 DF E0 F6"
    "C4 41 0F 84 69 02 00 00 A1 10 FD DB 00 89 07 A1 14 FD DB 00 89 47 04 A1 18 FD DB 00 89 47 08 E8"
    "FE 04 00 00 0F 84 47 02 00 00 E8 F9 03 00 00 0F 84 3C 02 00 00 FF 35 1C A7 8B 00 6A 00 FF B6 B8"
    "10 00 00 8D 47 48 50 53 E8 42 A7 E4 FF 83 C4 14 83 7F 48 00 0F 85 AC 02 00 00"
    # slide frame: animation, facing into the wall, fall height reset; sideways from the stick
    # (LAT x the descent step; stopped by the corner and clearance rays); descent
    # d(now) - d(prev) (frame-rate independent); floor ray -> land exit; else the new
    # position is set (0x48EFB0)
    "A1 08 FD DB 00 89 87 50 01 00 00 8B 47 4C A3 08 FD DB 00 D9 47 4C D8 A7 50 01 00 00 D9 9F 48 01"
    "00 00 D9 47 4C D8 25 04 FD DB 00 E8 22 05 00 00 D9 9F 44 01 00 00 D9 87 50 01 00 00 D8 25 04 FD"
    "DB 00 E8 0B 05 00 00 D8 AF 44 01 00 00 D9 9F 44 01 00 00 53 E8 AC D1 BD FF 83 C4 04 3B 05 2C A7"
    "8B 00 74 0F FF 35 2C A7 8B 00 53 E8 55 4B D5 FF 83 C4 08 E8 DA 03 00 00 E8 FD 03 00 00 C7 86 CC"
    "04 00 00 01 00 00 00 E8 B1 03 00 00 D9 EE D9 5F 50 85 ED 0F 84 D2 00 00 00 D9 86 78 0E 00 00 D8"
    "1D 10 A7 8B 00 DF E0 F6 C4 01 0F 85 BB 00 00 00 E8 DC 03 00 00 D9 86 78 0E 00 00 D9 E8 DB F1 72"
    "04 DD D8 EB 02 DD D9 DE C9 D9 57 50 D9 E4 DF E0 DD D8 F6 C4 40 0F 85 90 00 00 00 D9 05 04 A7 8B"
    "00 E8 43 04 00 00 D9 05 08 A7 8B 00 D9 E0 D9 C0 D8 0F D9 5F 6C D8 4F 04 D9 5F 70 C7 47 74 00 00"
    "00 00 E8 08 04 00 00 85 C0 74 59 68 FF FF 00 00 53 E8 2F 56 BE FF 83 C4 08 A9 00 00 03 00 75 44"
    "D9 EE E8 02 04 00 00 D9 47 50 D9 E1 D8 0D F0 A6 8B 00 D8 8F 44 01 00 00 D8 05 24 A7 8B 00 F6 47"
    "53 80 74 02 D9 E0 D9 C0 D8 4F 0C D9 5F 6C D8 4F 10 D9 5F 70 C7 47 74 00 00 00 00 E8 AF 03 00 00"
    "85 C0 74 07 C7 47 50 00 00 00 00 8B 47 54 89 47 60 8B 47 58 89 47 64 D9 47 5C D8 05 20 A7 8B 00"
    "D9 5F 68 31 C0 89 47 6C 89 47 70 D9 05 20 A7 8B 00 D8 87 44 01 00 00 D9 E0 D9 5F 74 E8 6E 03 00"
    "00 85 C0 75 66 D9 47 50 D8 0D F0 A6 8B 00 D8 8F 44 01 00 00 D9 C0 D8 4F 0C D8 47 54 D9 5F 54 D8"
    "4F 10 D8 47 58 D9 5F 58 D9 47 5C D8 A7 44 01 00 00 D9 5F 5C 8D 47 54 50 53 E8 47 44 BD FF 83 C4"
    "08"
    # exits: frame end 0x64DE4F; vanilla no-contact 0x64D797; vanilla wall-run attempt
    # 0x8BA141 (replays the 3 replaced instructions)
    "81 C4 60 01 00 00 61 E9 D7 32 D9 FF 81 C4 60 01 00 00 61 E9 13 2C D9 FF 81 C4 60 01 00 00 61 60"
    "83 EC 2C 89 E3 E9 AB F5 FF FF"
    # land / fall exit, as the curtain bottom exit: start-fall 0x5EB660 with the let-go
    # animation 0x36D, then the velocity 0x60E960 (outward 0 / OUT, current descent
    # speed), fall height reset, slide off
    "C7 87 4C 01 00 00 00 00 00 00 EB 0B A1 00 A7 8B 00 89 87 4C 01 00 00 C7 05 00 FD DB 00 00 00 00"
    "00 D9 05 10 FD DB 00 D8 8F 4C 01 00 00 D9 5F 18 D9 05 14 FD DB 00 D8 8F 4C 01 00 00 D9 5F 1C D9"
    "47 4C D8 25 04 FD DB 00 E8 FA 02 00 00 DD D8 D9 87 54 01 00 00 D8 0D E8 A6 8B 00 D8 05 E4 A6 8B"
    "00 D9 E0 D9 5F 20 31 C0 50 6A 0A 6A 50 FF 35 30 A7 8B 00 50 50 6A 2C 53 E8 4D 0A D3 FF 83 C4 20"
    "8D 47 18 50 53 E8 40 3D D5 FF 83 C4 08 E8 DD 01 00 00 C7 86 CC 04 00 00 01 00 00 00 E9 35 FF FF"
    "FF"
    # jump exit: the curtain jump-off (anim 0x379, 0x49DF10, 0x64B180); with Special Jump and
    # a sideways stick the facing is turned 45 degrees toward the stick side; exit 0x64DE43
    "C7 05 00 FD DB 00 00 00 00 00 E8 82 01 00 00 D9 07 D9 E0 D9 5F 24 D9 47 04 D9 E0 D9 5F 28 C7 47"
    "2C 00 00 00 00 F6 05 62 F0 93 00 01 74 67 D9 86 78 0E 00 00 D8 1D 10 A7 8B 00 DF E0 F6 C4 01 75"
    "54 E8 9F 01 00 00 D9 C0 D9 E1 D8 1D 14 A7 8B 00 DF E0 F6 C4 01 74 04 DD D8 EB 3A D9 E4 DF E0 DD"
    "D8 D9 05 18 A7 8B 00 F6 C4 01 74 02 D9 E0 D9 C0 D8 4F 0C D9 07 D8 0D 18 A7 8B 00 DE C1 D9 E0 D9"
    "5F 24 D8 4F 10 D9 47 04 D8 0D 18 A7 8B 00 DE C1 D9 E0 D9 5F 28 8D 47 30 50 8D 47 24 50 53 E8 C6"
    "55 BD FF 83 C4 0C C7 86 88 09 00 00 00 00 00 00 FF 35 34 A7 8B 00 53 E8 8D 2D D2 FF 83 C4 08 8D"
    "47 54 50 53 E8 E0 3F BD FF 83 C4 08 8B 47 54 89 86 DC 08 00 00 8B 47 58 89 86 E0 08 00 00 8B 47"
    "5C 89 86 E4 08 00 00 89 86 04 02 00 00 C7 86 CC 04 00 00 00 00 00 00 6A 00 6A 13 53 E8 D8 31 BE"
    "FF 83 C4 0C 68 9A 99 19 3E 8D 47 78 50 53 E8 36 04 D9 FF 83 C4 0C 81 C4 60 01 00 00 61 E9 EA 30"
    "D9 FF"
    # helpers: C down, contact normal, negate, tangent, face the wall, fall reset, stick .
    # tangent, animations present (0x36C, 0x378, 0x379, 0x36D), ray, sideways origin,
    # descent distance
    "6A 01 FF B6 B8 10 00 00 8D 47 48 50 53 E8 E5 36 E6 FF 83 C4 10 83 7F 48 00 C3 8D 07 50 FF 35 F4"
    "A6 8B 00 8D 47 24 50 68 80 00 00 00 53 E8 A5 4C BE FF 83 C4 14 85 C0 74 26 68 80 00 00 00 53 E8"
    "33 53 BE FF 83 C4 08 A9 00 00 03 00 75 0F 8D 07 50 E8 71 18 BC FF 83 C4 04 83 C8 01 C3 31 C0 C3"
    "D9 07 D9 E0 D9 1F D9 47 04 D9 E0 D9 5F 04 C3 D9 47 04 D9 E0 D9 5F 0C 8B 07 89 47 10 C7 47 14 00"
    "00 00 00 C3 D9 07 D9 E0 D9 5F 24 D9 47 04 D9 E0 D9 5F 28 C7 47 2C 00 00 00 00 8D 47 30 50 8D 47"
    "24 50 53 E8 9F 54 BD FF 83 C4 0C C3 8D 47 54 50 53 E8 D1 3E BD FF 83 C4 08 8B 47 5C 89 86 04 02"
    "00 00 C3 D9 86 44 0A 00 00 D9 E0 D9 9F 84 00 00 00 8D 47 3C 50 FF B7 84 00 00 00 8D 47 30 50 8D"
    "47 24 50 E8 8F 32 BC FF 83 C4 10 D9 47 3C D8 4F 0C D9 47 40 D8 4F 10 DE C1 C3 A1 2C A7 8B 00 E8"
    "25 00 00 00 74 22 A1 34 A7 8B 00 E8 19 00 00 00 74 16 A1 38 A7 8B 00 E8 0D 00 00 00 74 0A A1 30"
    "A7 8B 00 E8 01 00 00 00 C3 8B 4B 14 8B 09 8B 49 30 0F B7 11 39 D0 73 06 83 7C 81 08 00 C3 31 C0"
    "C3 6A 01 6A 00 6A 00 6A FF 8D 47 6C 50 8D 47 60 50 53 E8 C0 71 BE FF 83 C4 1C C3 F6 47 53 80 74"
    "02 D9 E0 D9 C0 D8 4F 0C D8 47 54 D9 5F 60 D8 4F 10 D8 47 58 D9 5F 64 D9 47 5C D8 05 0C A7 8B 00"
    "D9 5F 68 C3 D9 05 EC A6 8B 00 D8 25 E4 A6 8B 00 D8 35 E8 A6 8B 00 DB F1 72 04 DD D8 D9 C0 D9 9F"
    "54 01 00 00 D8 A7 54 01 00 00 D8 0D EC A6 8B 00 D9 87 54 01 00 00 D8 0D E8 A6 8B 00 D8 0D 28 A7"
    "8B 00 D8 05 E4 A6 8B 00 D8 8F 54 01 00 00 DE C1 C3"
    # SL_KEEP, hooked at 0x497F20 (remove animation set): for the Prince, the curtain
    # animations 0x369..0x379 get an extra reference before the original runs; emptied
    # slots get their pointer back afterwards, others release the extra reference
    "8B 44 24 04 3B 05 14 C4 D0 00 74 0C 8B 44 24 04 8B 48 14 E9 E5 CF BD FF 60 81 EC 90 00 00 00 89"
    "E7 8B 70 14 8B 36 8B 76 30 31 ED E8 67 00 00 00 74 02 8B 01 89 04 AF 85 C0 74 09 50 E8 85 C9 BD"
    "FF 83 C4 04 E8 7F 00 00 00 72 E0 FF B4 24 B8 00 00 00 FF B4 24 B8 00 00 00 E8 AE FF FF FF 83 C4"
    "08 31 ED E8 2F 00 00 00 74 1E 8B 04 AF 85 C0 74 17 83 39 00 75 04 89 01 EB 0E 8D 04 AF 6A 00 50"
    "E8 D1 C9 BD FF 83 C4 08 E8 3B 00 00 00 72 D4 81 C4 90 00 00 00 61 C3 89 E8 8D 4E 08 3B 05 40 A7"
    "8B 00 72 09 2B 05 40 A7 8B 00 8B 4E 04 03 05 3C A7 8B 00 0F B7 16 39 D0 73 0B 85 C9 74 07 8D 0C"
    "81 31 C0 40 C3 31 C0 C3 45 A1 40 A7 8B 00 01 C0 39 C5 C3"
)

MODS_CODE = bytes.fromhex(  # at 0xDC9000 (.mods), wall slide additions
    # tunables (floats): search REACH 0.9, RZ 1.0, STAND 0.495, NZ 0.3; ledge gate DROP 0.6;
    # edge check MAXFALL 7.0, CATCH 0.0, DMAX 3.0, TOP 0.5, HX 0.4, HY 0.4; floor check
    # CLEAR 1.0, FZ 0.5, PROBE 3.0; watchdog STUCK 0.5 s, WIN 1.0 s, EPS 0.002
    "66 66 66 3F 00 00 80 3F A4 70 FD 3E 9A 99 99 3E 9A 99 19 3F 00 00 E0 40 00 00 00 00 00 00 40 40"
    "00 00 00 3F CD CC CC 3E CD CC CC 3E 00 00 80 3F 00 00 00 3F 00 00 40 40 00 00 00 3F 00 00 80 3F"
    "6F 12 03 3B"
    # SEARCH, from WALLRUN_CAVE 0x8BA135 on frames without wall contact: with C held for HOLD,
    # the cooldown passed and the curtain animations loaded, one ray along the facing; a
    # near-vertical runnable wall within REACH, faced within 60 degrees, and no catchable
    # ledge or close floor below -> snap to STAND from it, velocity 0, slide state set
    "60 81 EC 94 00 00 00 89 E7 8B 1D 48 4A D3 00 3B 1D 14 C4 D0 00 0F 85 6F 02 00 00 8B 35 40 4A D3"
    "00 8B 76 48 D9 05 74 09 94 00 D8 25 18 33 CD 00 D9 1F 39 35 00 FD DB 00 75 19 D9 07 D8 25 08 FD"
    "DB 00 D8 1D FC A6 8B 00 DF E0 F6 C4 41 0F 85 37 02 00 00 6A 01 FF B6 B8 10 00 00 8D 47 08 50 53"
    "E8 A7 53 95 FF 83 C4 10 83 7F 08 00 0F 84 18 02 00 00 D9 07 D8 A6 14 07 00 00 D8 1D E0 A6 8B 00"
    "DF E0 F6 C4 01 0F 85 FF 01 00 00 D9 07 D8 25 08 FD DB 00 D9 5F 04 8B 47 04 3B 05 F8 A6 8B 00 0F"
    "82 E5 01 00 00 A1 2C A7 8B 00 E8 C1 06 00 00 0F 84 D5 01 00 00 A1 34 A7 8B 00 E8 B1 06 00 00 0F"
    "84 C5 01 00 00 A1 38 A7 8B 00 E8 A1 06 00 00 0F 84 B5 01 00 00 A1 30 A7 8B 00 E8 91 06 00 00 0F"
    "84 A5 01 00 00 8D 47 0C 50 53 E8 1D 77 6C FF 83 C4 08 C7 47 14 00 00 00 00 8D 47 0C 50 E8 DA 34"
    "6B FF 83 C4 04 8D 47 18 50 53 E8 8D 5B 6C FF 83 C4 08 8B 47 18 89 47 24 8B 47 1C 89 47 28 D9 47"
    "20 D8 05 04 90 DC 00 D9 5F 2C D9 05 00 90 DC 00 D9 C0 D8 4F 0C D9 5F 30 D8 4F 10 D9 5F 34 C7 47"
    "38 00 00 00 00 6A 01 6A 00 6A 00 6A FF 8D 47 30 50 8D 47 24 50 53 E8 D1 8E 6D FF 83 C4 1C 85 C0"
    "0F 84 24 01 00 00 8D 47 3C 50 53 E8 BC 95 6D FF 83 C4 08 8D 47 48 50 53 E8 4F 96 6D FF 83 C4 08"
    "68 FF FF 00 00 53 E8 01 6F 6D FF 83 C4 08 A9 00 00 03 00 0F 85 F1 00 00 00 D9 47 50 D9 E1 D8 1D"
    "0C 90 DC 00 DF E0 F6 C4 41 0F 84 DB 00 00 00 8D 47 48 50 E8 24 34 6B FF 83 C4 04 D9 47 0C D8 4F"
    "48 D9 47 10 D8 4F 4C DE C1 D9 E0 D8 1D F4 A6 8B 00 DF E0 F6 C4 01 0F 85 AE 00 00 00 E8 3E 01 00"
    "00 85 C0 79 0C E8 F6 01 00 00 73 0A E9 99 00 00 00 E9 94 00 00 00 D9 05 08 90 DC 00 D9 C0 D8 4F"
    "48 D8 47 3C D9 5F 18 D8 4F 4C D8 47 40 D9 5F 1C 8D 47 18 50 53 E8 52 5D 6C FF 83 C4 08 31 C0 89"
    "47 3C 89 47 40 89 47 44 8D 47 3C 50 53 E8 EA 56 84 FF 83 C4 08 89 35 00 FD DB 00 8B 07 A3 04 FD"
    "DB 00 A3 08 FD DB 00 A3 0C FD DB 00 31 C0 89 86 2C 03 00 00 89 86 30 03 00 00 89 86 34 03 00 00"
    "8B 47 48 A3 10 FD DB 00 8B 47 4C A3 14 FD DB 00 C7 05 18 FD DB 00 00 00 00 00 8B 07 A3 20 FD DB"
    "00 8B 47 20 A3 24 FD DB 00 90 81 C4 94 00 00 00 61 E9 72 14 AF FF"
    # LG_GATE, from 0x64CD81: skips the vanilla ledge probe during a search-started slide until
    # he is DROP below its start (no re-grab of the ledge he dropped from)
    "60 83 EC 10 8B 1D 48 4A D3 00 3B 1D 14 C4 D0 00 75 69 8B 35 40 4A D3 00 8B 76 48 39 35 00 FD DB"
    "00 75 58 A1 04 FD DB 00 3B 05 20 FD DB 00 75 4B D9 05 74 09 94 00 D8 25 18 33 CD 00 D8 25 08 FD"
    "DB 00 D8 1D FC A6 8B 00 DF E0 F6 C4 41 74 2C 89 E0 50 53 E8 AE 59 6C FF 83 C4 08 D9 05 24 FD DB"
    "00 D8 64 24 08 D8 1D 10 90 DC 00 DF E0 F6 C4 01 74 09 83 C4 10 61 E9 4B 3A 88 FF 83 C4 10 61 A1"
    "48 4A D3 00 E9 23 3A 88 FF"
    # EDGE_CHECK: box query below the feet (vanilla ledge edges, mask 0x4FF40F), depth
    # min(DMAX, MAXFALL - fallen - CATCH); an edge found -> no slide
    "C7 47 70 FE FF FF FF D9 86 04 02 00 00 D8 67 20 D8 2D 14 90 DC 00 D8 25 18 90 DC 00 D9 05 1C 90"
    "DC 00 D8 D1 DF E0 F6 C4 01 74 04 DD D9 EB 02 DD D8 D9 57 54 D9 E4 DF E0 DD D8 F6 C4 41 75 7E D9"
    "05 24 90 DC 00 D9 57 64 D9 E0 D9 5F 58 D9 05 28 90 DC 00 D9 57 68 D9 E0 D9 5F 5C D9 47 54 D9 E0"
    "D9 5F 60 A1 20 90 DC 00 89 47 6C 8D 47 64 50 8D 47 58 50 6A 00 53 E8 D2 4B 6D FF 83 C4 10 68 0F"
    "F4 4F 00 6A 01 8D 47 18 50 6A 00 E8 7D 4D 6D FF 83 C4 10 89 47 70 85 C0 78 23 50 6A 00 E8 3B 4D"
    "6D FF 83 C4 08 89 47 74 8D 47 78 50 8D 47 18 50 FF 77 70 6A 00 E8 23 4E 6D FF 83 C4 10 8B 47 70"
    "C3"
    # FLOOR_CHECK: ray straight down; floor closer than CLEAR below the feet -> no slide
    "8B 47 18 89 47 24 8B 47 1C 89 47 28 D9 47 20 D8 05 30 90 DC 00 D9 5F 2C 31 C0 89 47 30 89 47 34"
    "D9 05 30 90 DC 00 D8 05 34 90 DC 00 D9 E0 D9 5F 38 A1 34 90 DC 00 89 87 84 00 00 00 6A 01 6A 00"
    "6A 00 6A FF 8D 47 30 50 8D 47 24 50 53 E8 FA 8B 6D FF 83 C4 1C 85 C0 74 1F 8D 87 88 00 00 00 50"
    "53 E8 E6 92 6D FF 83 C4 08 D9 47 20 D8 A7 90 00 00 00 D9 9F 84 00 00 00 D9 87 84 00 00 00 D8 1D"
    "2C 90 DC 00 DF E0 9E C3"
    # CE_GATE, called from the slide's contact entry (0x8BA804): animation check, then the edge
    # and floor checks
    "E8 A2 19 AF FF 74 43 60 81 EC 94 00 00 00 89 E7 8D 47 18 50 53 E8 1A 58 6C FF 83 C4 08 E8 95 FE"
    "FF FF 85 C0 79 11 E8 4D FF FF FF 73 14 81 C4 94 00 00 00 61 39 C0 C3 81 C4 94 00 00 00 61 39 C0"
    "C3 81 C4 94 00 00 00 61 85 E4 C3"
    # WATCHDOG, from 0x630160 (per-frame airborne handler): draws the sword once per new
    # slide (fn_SnapSword 0x700EB0, as the curtain); in 0x412 with the slide animation and
    # no running slide (after a rewind) -> the slide's fall exit; not moving for STUCK
    # within WIN after a slide -> the same exit, retried every STUCK
    "60 83 EC 20 89 E7 8B 1D 48 4A D3 00 3B 1D 14 C4 D0 00 0F 85 02 02 00 00 8B 35 40 4A D3 00 8B 76"
    "48 D9 05 74 09 94 00 D8 25 18 33 CD 00 D9 1F 39 35 00 FD DB 00 75 39 A1 04 FD DB 00 3B 05 3C FD"
    "DB 00 74 2C D9 07 D8 25 08 FD DB 00 D8 1D FC A6 8B 00 DF E0 F6 C4 41 74 17 A1 04 FD DB 00 A3 3C"
    "FD DB 00 6A 03 6A 01 53 E8 4C 79 93 FF 83 C4 0C 8D 47 04 50 53 E8 6F 57 6C FF 83 C4 08 81 BE 40"
    "06 00 00 12 04 00 00 75 79 53 E8 0A E6 6C FF 83 C4 04 3B 05 2C A7 8B 00 75 68 39 35 00 FD DB 00"
    "75 22 D9 07 D8 25 08 FD DB 00 D9 E4 DF E0 F6 C4 01 75 0F D8 1D FC A6 8B 00 DF E0 F6 C4 41 75 42"
    "EB 02 DD D8 8D 47 10 50 53 E8 8B 72 6C FF 83 C4 08 D9 47 10 D8 0D 00 A7 8B 00 D9 E0 D9 5F 10 D9"
    "47 14 D8 0D 00 A7 8B 00 D9 E0 D9 5F 14 D9 05 E4 A6 8B 00 D9 E0 D9 5F 18 E8 2C 01 00 00 E9 F9 00"
    "00 00 81 BE 40 06 00 00 12 04 00 00 0F 85 E9 00 00 00 D9 07 D8 1D 34 FD DB 00 DF E0 F6 C4 01 0F"
    "85 D6 00 00 00 31 C9 D9 44 8F 04 D8 24 8D 28 FD DB 00 D9 E1 D8 1D 40 90 DC 00 DF E0 F6 C4 41 0F"
    "84 B6 00 00 00 41 83 F9 03 72 DC D9 07 D8 25 34 FD DB 00 D8 1D 38 90 DC 00 DF E0 F6 C4 01 0F 85"
    "B6 00 00 00 D9 07 D8 25 38 FD DB 00 D9 E4 DF E0 F6 C4 01 75 13 D8 1D 38 90 DC 00 DF E0 F6 C4 01"
    "0F 85 94 00 00 00 EB 02 DD D8 39 35 00 FD DB 00 0F 85 84 00 00 00 D9 07 D8 25 08 FD DB 00 D8 1D"
    "FC A6 8B 00 DF E0 F6 C4 41 75 6F D9 05 34 FD DB 00 D8 25 08 FD DB 00 D8 1D 3C 90 DC 00 DF E0 F6"
    "C4 41 74 56 8B 07 A3 38 FD DB 00 D9 05 10 FD DB 00 D8 0D 00 A7 8B 00 D9 5F 10 D9 05 14 FD DB 00"
    "D8 0D 00 A7 8B 00 D9 5F 14 D9 05 E4 A6 8B 00 D9 E0 D9 5F 18 E8 30 00 00 00 EB 1F 8B 47 04 A3 28"
    "FD DB 00 8B 47 08 A3 2C FD DB 00 8B 47 0C A3 30 FD DB 00 8B 07 A3 34 FD DB 00 83 C4 20 61 81 EC"
    "E4 00 00 00 E9 46 6A 86 FF 31 C0 50 6A 0A 6A 50 FF 35 30 A7 8B 00 50 50 6A 2C 53 E8 29 1F 82 FF"
    "83 C4 20 8D 47 10 50 53 E8 1C 52 84 FF 83 C4 08 8B 47 0C 89 86 04 02 00 00 C7 86 CC 04 00 00 01"
    "00 00 00 C3"
    # C_GATE, called instead of IsDown at 0x725D9A (the landing's throw check): C held since
    # the slide (press time <= last slide frame) counts as not down; then the
    # animation-table helper
    "FF 74 24 10 FF 74 24 10 FF 74 24 10 FF 74 24 10 E8 E0 4C 95 FF 83 C4 10 60 8B 5C 24 24 3B 1D 14"
    "C4 D0 00 75 32 83 7C 24 30 01 75 2B 8B 54 24 28 83 3A 00 74 22 8B 43 18 8B 40 04 8B 40 48 D9 80"
    "14 07 00 00 D8 1D 08 FD DB 00 DF E0 F6 C4 41 74 06 C7 02 00 00 00 00 61 C3 8B 4B 14 8B 09 8B 49"
    "30 0F B7 11 39 D0 73 06 83 7C 81 08 00 C3 31 C0 C3"
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
    # Wall torpedo: 0x6D32BD primary-attack branch of the wall-attack check -> jmp to the cave
    (0x2D32BD, bytes.fromhex("BB 02 00 00 00"), bytes.fromhex("E9 EE 73 1E 00")),
    # Wall torpedo: cave in the .text slack at 0x8BA6B0, after the latch cave
    (0x4BA6B0, bytes(len(WALLTORPEDO_CAVE)), WALLTORPEDO_CAVE),
]

# Code section (always): a new last section .mods (VA 0xDC9000, RVA 0x9C9000, file offset 0x547000,
# 0x10000 bytes of int3, code | execute | read). The original file ends at 0x547000 (no overlay);
# the bytes are appended before these header edits are applied.
MODS_RAW, MODS_SIZE = 0x547000, 0x10000
SECTION_PATCHES = [
    # PE header: NumberOfSections 4 -> 5
    (0x86, bytes.fromhex("04 00"), bytes.fromhex("05 00")),
    # PE header: SizeOfCode 0x4C0000 -> 0x4D0000
    (0x9C, bytes.fromhex("00 00 4C 00"), bytes.fromhex("00 00 4D 00")),
    # PE header: SizeOfImage 0x9C8056 -> 0x9D9000
    (0xD0, bytes.fromhex("56 80 9C 00"), bytes.fromhex("00 90 9D 00")),
    # section table entry 5 (empty in the original): .mods, VirtualSize 0x10000, RVA 0x9C9000,
    # SizeOfRawData 0x10000, PointerToRawData 0x547000, characteristics 0x60000020
    (0x218, bytes(40), b".mods\0\0\0" + bytes.fromhex(
        "00 00 01 00 00 90 9C 00 00 00 01 00 00 70 54 00 00 00 00 00 00 00 00 00 00 00 00 00"
        "20 00 00 60")),
]

# Vertical wall runs from jumps (optional, on by default): the wall-run cave's head-on check at
# 0x8BA1EF -> nops, so a contact within 30 degrees of head-on also reaches 0x526920, which starts
# a vertical run there. Applied after PATCHES: its original bytes are the cave written by them.
VERTICAL_WALLRUN_PATCH = (
    0x4BA1EF, bytes.fromhex("0F 84 AF 00 00 00"), bytes.fromhex("90 90 90 90 90 90"))

# Wall slide (optional, on by default). Applied after PATCHES: the hooks edit WALLRUN_CAVE and the
# header value written by them.
WALLSLIDE_PATCHES = [
    # WALLRUN_CAVE 0x8BA13B pushad / sub esp,0x2C / mov ebx,esp -> jmp SL_CONTACT 0x8BA744 ; nop
    # (the cave replays the three instructions when the slide does not apply)
    (0x4BA13B, bytes.fromhex("60 83 EC 2C 89 E3"), bytes.fromhex("E9 04 06 00 00 90")),
    # remove animation set 0x497F20: mov eax,[esp+4] / mov ecx,[eax+0x14] -> jmp SL_KEEP 0x8BAF2A ;
    # nop ; nop (the cave replays the two instructions)
    (0x97F20, bytes.fromhex("8B 44 24 04 8B 48 14"), bytes.fromhex("E9 05 30 42 00 90 90")),
    # cave in the .text slack at 0x8BA6E0, after the wall torpedo cave
    (0x4BA6E0, bytes(len(WALLSLIDE_CAVE)), WALLSLIDE_CAVE),
    # PE header, .data VirtualSize 0x4AED00 -> 0x4AEE00 (maps the state at 0xDBFD00..0xDBFD1B,
    # zero-filled, inside the section's last page)
    (0x1D0, bytes.fromhex("00 ED 4A 00"), bytes.fromhex("00 EE 4A 00")),
    # .mods code at 0xDC9000 (SEARCH, LG_GATE, EDGE_CHECK, FLOOR_CHECK, CE_GATE, WATCHDOG, C_GATE);
    # its state is at 0xDBFD20..0xDBFD3F, in the .data page mapped above
    (MODS_RAW, b"\xCC" * len(MODS_CODE), MODS_CODE),
    # hooks into it (the contact entry call is inside WALLSLIDE_CAVE, written above)
    # WALLRUN_CAVE 0x8BA135 "no wall contact" je 0x64D797 -> je SEARCH
    (0x4BA135, bytes.fromhex("0F 84 5C 36 D9 FF"), bytes.fromhex("0F 84 09 EF 50 00")),
    # 0x64CD81 mov eax,[0xD34A48] (before the ledge probe 0x546850) -> jmp LG_GATE
    (0x24CD81, bytes.fromhex("A1 48 4A D3 00"), bytes.fromhex("E9 54 C5 77 00")),
    # slide contact entry 0x8ba804 call (animation check) -> call CE_GATE
    (0x4BA804, bytes.fromhex("E8 4A 06 00 00"), bytes.fromhex("E8 A3 EC 50 00")),
    # 0x630160 sub esp,0xe4 (per-frame airborne handler) -> jmp WATCHDOG ; nop
    (0x230160, bytes.fromhex("81 EC E4 00 00 00"), bytes.fromhex("E9 92 93 79 00 90")),
    # 0x725D9A call IsDown 0x71E450 (C held -> secondary-weapon throw) -> call C_GATE
    (0x325D9A, bytes.fromhex("E8 B1 86 FF FF"), bytes.fromhex("E8 BC 39 6A 00")),
    # slide jump exit 0x8bac5c: test byte [0x93F062],1 ; jz (Special Jump test) -> nops,
    # so Space + a sideways stick jumps off at 45 degrees
    (0x4BAC5C, bytes.fromhex("F6 05 62 F0 93 00 01 74 67"), bytes.fromhex("90 90 90 90 90 90 90 90 90")),
]


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
    slide = parser.add_mutually_exclusive_group()
    slide.add_argument("--wall-slide", dest="slide", action="store_true",
                       help="include the wall slide without asking")
    slide.add_argument("--no-wall-slide", dest="slide", action="store_false",
                       help="leave out the wall slide without asking")
    parser.set_defaults(vertical=None, slide=None)
    return parser.parse_args()


def ask_yes_no(question: str) -> bool:
    """Ask a [Y/n] question. Enter or no console means yes."""
    while True:
        try:
            answer = input(f"{question} [Y/n] ").strip().lower()
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
    if sha in PATCHED_SHA256.values():
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

    vertical, slide = args.vertical, args.slide
    try:
        if vertical is None:
            vertical = ask_yes_no("Include vertical wall runs from jumps?")
        if slide is None:
            slide = ask_yes_no("Include the wall slide (hold C against a wall)?")
    except KeyboardInterrupt:
        print("\nCancelled. Nothing written.")
        return 1
    if len(data) != MODS_RAW:
        print("Unexpected file size. Nothing written.")
        return 1
    data += b"\xCC" * MODS_SIZE
    patches = (SECTION_PATCHES + PATCHES + ([VERTICAL_WALLRUN_PATCH] if vertical else [])
               + (WALLSLIDE_PATCHES if slide else []))
    expected_sha = PATCHED_SHA256[(vertical, slide)]

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
