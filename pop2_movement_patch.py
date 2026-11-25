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
    when a wall run ends next to a runnable wall. Pressing C during a horizontal wall run cuts
    it into a slide, swinging onto the wall like on a curtain, once the floor is far enough
    below (2.5 units); until then he keeps running. No other slide starts when a ledge he can
    still grab is just below, or the floor is less than 2 units below. After a jump off a slide,
    a new slide waits a moment (0.6 s) and, for a short while, cannot start higher than the
    last one, so chaining slides between walls cannot gain height. If he ever gets stuck after
    a slide, or a rewind ends mid-slide with C released, he lets go.
  * Code section: the patch adds a 64 KB code section (.mods) for the mods' code; the wall slide
    uses it.

Usage: python pop2_movement_patch.py <path to original POP2.EXE> [output file or folder]
           [--vertical-wallruns | --no-vertical-wallruns] [--wall-slide | --no-wall-slide]

Without these options the script asks whether to include vertical wall runs from jumps and the
wall slide (Enter = yes; with no console to answer, yes). The output defaults to
POP2_patched.EXE next to the input. The original file is never modified. Back it up, then
replace POP2.EXE with the patched file. The script only accepts the unmodified Steam POP2.EXE
and checks every byte it changes. Requires Python 3.8+.
"""
import argparse
import hashlib
import sys
from pathlib import Path

ORIGINAL_SHA256 = "5559117d013155bbad608cedc2fd0dd272f37ed92c936fc4e151287f3b5ff1cb"
# sha256 of the output for (vertical wall runs from jumps, wall slide)
# BEGIN GENERATED patched-sha256 (tools/modbuild.py patcher; do not edit by hand)
PATCHED_SHA256 = {
    (True, False): "89815876a23200f8c3a47a752dae98d4778c2f075b09f1f7ffae740769b32c0b",
    (False, False): "ab030994cc2862e6bcd3cf4425b392e63349abcb6aa7a81943ad1b958635feeb",
    (True, True): "86f9e90e29dcc60d6ffbb1a0062066876cd4df6dfa3bd332cab9ac95050ab7e5",
    (False, True): "82f6f866098c39a61fd41594fdd351330156215b0b2ad46b61ed4a4687726c0c",
}
# END GENERATED patched-sha256

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
    # BEGIN GENERATED older-builds (tools/modbuild.py patcher; do not edit by hand)
    "cf4b50c6089071b69b8a9fd671db2314e5f267ae0a762a8ff17d67f046445f0b":
        "movement patch with vertical wall runs and the third wall slide",
    "893a1c5e70ea80afb6fb30cdab84f7f245df669d1c63073bc1d35247a2a3301a":
        "movement patch with the third wall slide, without vertical wall runs",
    "408d99fdf309904aaea63436cf33f09aa35576896fd79c803c3f48d3b2585172":
        "movement patch with vertical wall runs and the fourth wall slide",
    "aa5ee41ce87359d1ef574a44726c24392c1f524756b456dd6e11687885442d36":
        "movement patch with the fourth wall slide, without vertical wall runs",
    "60bfa426763eb7fe6b0c26dfdc06c04043d9be31f58418dd70ea863200b6f77a":
        "movement patch with vertical wall runs and the fifth wall slide",
    "3584bc9f35d4506a1ca8439b07c2b3d5b5f9c8faf77170ebd149a2e49c17fc3e":
        "movement patch with the fifth wall slide, without vertical wall runs",
    "fa6e88af8cee549379aec51cd1e87f79da047d14421b99d57f59b828a1bba895":
        "movement patch with vertical wall runs and the sixth wall slide",
    "2c7aaa72a9afcb8f73e950542ab546bc0ff4f4370e53fa899ed697c5a5e30f25":
        "movement patch with the sixth wall slide, without vertical wall runs",
    # END GENERATED older-builds
}

# BEGIN GENERATED mods (tools/modbuild.py patcher; do not edit by hand)
# Everything up to END GENERATED mods is generated by tools/modbuild.py from the mods' sources (GNU
# as, Intel syntax; one source line per line below, names as in the sources). Addresses are virtual
# addresses (VA); a patch entry is (file offset, original bytes, new bytes), with file offset = VA -
# 0x400000, except in the .mods section (file offset MODS_RAW).
MODS_RAW, MODS_SIZE = 0x547000, 0x10000

# ---- M00 shared: the .mods section and the PE header edits ----
SECTION_PATCHES = [
    # NumberOfSections 4 -> 5
    (0x86, bytes.fromhex("04 00"), bytes.fromhex("05 00")),
    # SizeOfCode 0x4C0000 -> 0x4D0000
    (0x9C, bytes.fromhex("00 00 4C 00"), bytes.fromhex("00 00 4D 00")),
    # SizeOfImage 0x9C8056 -> 0x9D9000
    (0xD0, bytes.fromhex("56 80 9C 00"), bytes.fromhex("00 90 9D 00")),
    # section table entry 5 (empty in the original): .mods, VirtualSize 0x10000, RVA 0x9C9000,
    # SizeOfRawData 0x10000, PointerToRawData 0x547000, characteristics 0x60000020
    (0x218,
     bytes.fromhex("00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 "
                   "00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 "
                   "00 00 00 00 00 00 00 00 "),
     bytes.fromhex("2E 6D 6F 64 73 00 00 00 00 00 01 00 00 90 9C 00 "
                   "00 00 01 00 00 70 54 00 00 00 00 00 00 00 00 00 "
                   "00 00 00 00 20 00 00 60 ")),
    # .text VirtualSize 0x4B9120 -> 0x4BA000: maps the slack at 0x8BA120..0x8BAFFF where the caves
    # live
    (0x180, bytes.fromhex("20 91 4B 00"), bytes.fromhex("00 A0 4B 00")),
    # .data VirtualSize 0x4AECD8 -> 0x4AED00: maps the variables in data.inc (zero-filled last page)
    (0x1D0, bytes.fromhex("D8 EC 4A 00"), bytes.fromhex("00 ED 4A 00")),
]

# ---- M01 Special Jump key ----
# A new Controls-menu action (after Roll/Jump, default V) that acts as Space everywhere, but
# direction + Special Jump is a forward jump instead of a roll.

M01_FORWARD_JUMP = bytes.fromhex(  # .m01_forward_jump at 0x8846C3, source m01_jump_key/forward_jump.s
    # m01_forward_jump:
    "F6 05 62 F0 93 00 01 "                 # test byte ptr ds:PAD_BITS_HIGH, 1   # Special Jump held?
    "74 1E "                                # je .Lroll
    "90 90 90 90 90 90 90 90 90 90 90 90 "  # .fill 12, 1, 0x90   # 12 nops: unused room (kept: the bytes must
                                            #   stay identical)
    "C7 44 24 1C 00 00 C0 40 "              # mov dword ptr [esp+0x1C], M01_JUMP_SPEED
    "BE 27 00 00 00 "                       # mov esi, M01_MOVE_JUMP
    "E9 C1 87 C5 FF "                       # jmp JUMP_FROM_ROLL
    # .Lroll:
    "C7 85 48 04 00 00 02 00 00 00 "        # mov dword ptr [ebp+0x448], 2   # replayed: the roll
    "E9 42 8C C5 FF "                       # jmp ROLL_BLOCK_NEXT
)

M01_MENU_ORDER = bytes.fromhex(  # .m01_menu_order at 0x8BA2E0, source m01_jump_key/menu_entry.s
    # m01_menu_order:
    "27 25 28 26 2D 00 10 07 02 03 01 06 "  # .byte 0x27, 0x25, 0x28, 0x26, 0x2D, 0x00, M01_ACTION, 0x07,
                                            #   0x02, 0x03, 0x01, 0x06
    "05 04 0A 08 09 2B 2C 29 2A 0C 0E 0F "  # .byte 0x05, 0x04, 0x0A, 0x08, 0x09, 0x2B, 0x2C, 0x29, 0x2A,
    "0D "                                   #   0x0C, 0x0E, 0x0F, 0x0D
)

M01_LABEL = bytes.fromhex(  # .m01_label at 0x8BA300, source m01_jump_key/menu_entry.s
    # m01_label:
    "53 70 65 63 69 61 6C 20 4A 75 6D 70 "  # .asciz "Special Jump"   # room for 15 characters before
    "00 "                                   #   m01_label_lookup
)

M01_LABEL_LOOKUP = bytes.fromhex(  # .m01_label_lookup at 0x8BA310, source m01_jump_key/menu_entry.s
    # thiscall (&group, &key), hooked at the entry of FN_TEXT_LOOKUP
    # m01_label_lookup:
    "8B 44 24 08 "                          # mov eax, [esp+8]   # &key: MSVC 7.1 std::string, characters
                                            #   inline at +4
    "83 78 18 10 "                          # cmp dword ptr [eax+0x18], 0x10   # while the capacity (+0x18) is
                                            #   below 16, else a pointer at +4
    "72 05 "                                # jb .Linline
    "8B 40 04 "                             # mov eax, [eax+4]
    "EB 03 "                                # jmp .Lkey
    # .Linline:
    "83 C0 04 "                             # add eax, 4
    # .Lkey:
    "81 38 41 63 74 69 "                    # cmp dword ptr [eax], 0x69746341   # "Acti"
    "75 19 "                                # jne .Lvanilla
    "81 78 04 6F 6E 5F 31 "                 # cmp dword ptr [eax+4], 0x315F6E6F   # "on_1"
    "75 10 "                                # jne .Lvanilla
    "66 81 78 08 36 00 "                    # .byte 0x66, 0x81, 0x78, 0x08, 0x36, 0x00   # cmp word ptr
                                            #   [eax+8], 0x0036 ("6\0"), in the imm16 form (as would pick the
                                            #   shorter imm8 form)
    "75 08 "                                # jne .Lvanilla
    "B8 00 A3 8B 00 "                       # mov eax, offset m01_label
    "C2 08 00 "                             # ret 8
    # .Lvanilla:
    "8B 44 24 04 "                          # mov eax, [esp+4]   # replayed entry
    "56 "                                   # push esi
    "8B F1 "                                # {load} mov esi, ecx   # 8B F1 (as picks 89 CE by default)
    "E9 08 DD B5 FF "                       # jmp TEXT_LOOKUP_BODY
)

M01_DEFAULT_BINDING = bytes.fromhex(  # .m01_default_binding at 0x8BA350, source m01_jump_key/menu_entry.s
    # hooked at the epilogue of SetDefaultBindings (DEFAULT_BINDINGS_END); esi = the binding table
    # m01_default_binding:
    "80 7E 08 00 "                          # cmp byte ptr [esi+8], 0   # same guard as every vanilla default
    "74 16 "                                # je .Ldone
    "6A 2F "                                # push M01_DEFAULT_KEY
    "6A 00 "                                # push M01_DEVICE_KEYBOARD
    "8B CE "                                # {load} mov ecx, esi   # 8B CE (as picks 89 F1 by default)
    "E8 2F 0D B6 FF "                       # call FN_UNBIND_KEY   # free V from any other action
    "8B 46 34 "                             # mov eax, [esi+0x34]
    "C6 40 60 00 "                          # mov byte ptr [eax+0x60], M01_DEVICE_KEYBOARD   # action 0x10,
                                            #   slot 0: device
    "C6 40 61 2F "                          # mov byte ptr [eax+0x61], M01_DEFAULT_KEY   # and key
    # .Ldone:
    "5F "                                   # pop edi   # replayed epilogue
    "5E "                                   # pop esi
    "83 C4 08 "                             # add esp, 8
    "C3 "                                   # ret
)

M01_PAD_BIT = bytes.fromhex(  # .m01_pad_bit at 0x8BA380, source m01_jump_key/pad_bit.s
    # hooked in the pad builder right after the enable mask (PAD_BUILDER_MASKED)
    # m01_pad_bit:
    "51 "                                   # push ecx   # ecx stays live in the pad builder
    "6A 10 "                                # push M01_ACTION
    "B9 68 F0 93 00 "                       # mov ecx, offset INPUT_MANAGER
    "E8 B3 11 B6 FF "                       # call FN_ACTION_VALUE   # st0 = the action's value
    "D8 1D 28 BD 8B 00 "                    # fcomp dword ptr ds:FLOAT_ZERO   # same test as the vanilla bits:
                                            #   value > 0.0
    "DF E0 "                                # fnstsw ax
    "F6 C4 41 "                             # test ah, 0x41
    "75 13 "                                # jne .Lskip
    "F6 05 A8 14 91 00 01 "                 # test byte ptr ds:INPUT_ENABLE_MASK, 1   # only while Space is
                                            #   enabled
    "74 0A "                                # je .Lskip
    "81 0D 60 F0 93 00 01 00 01 00 "        # or dword ptr ds:PAD_BITS, M01_PAD_BITS
    # .Lskip:
    "59 "                                   # pop ecx
    "A1 E4 F0 93 00 "                       # mov eax, dword ptr ds:PAD_BITS_E4   # replayed
    "E9 3B 37 B6 FF "                       # jmp PAD_BUILDER_NEXT
)

# ---- M02 Wall runs from jumps ----
# Hold the wall-run button while jumping or rebounding into a wall to start a wall run from mid-air,
# and keep holding it to chain runs. Option "vertical": head-on contacts (within 30 degrees) start
# vertical runs too.

M02_AIR_CONTACT = bytes.fromhex(  # .m02_air_contact at 0x8BA130, source m02_wall_runs/air_wallrun.s
    # m02_air_contact:
    "83 C4 08 "                             # add esp, 8   # replayed hook: no wall contact -> vanilla
    "85 C0 "                                # test eax, eax
    # m02_no_contact_je:
    "0F 84 5C 36 D9 FF "                    # je AIR_NO_CONTACT
    # m02_contact:
    "60 "                                   # pushad
    "83 EC 2C "                             # sub esp, 0x2C
    "89 E3 "                                # mov ebx, esp
    # m02_wallrun_attempt:
    "8B 3D 40 4A D3 00 "                    # mov edi, dword ptr ds:CURRENT_INST
    "8B 7F 48 "                             # mov edi, [edi+0x48]   # Prince data
    "6A 05 "                                # push M02_WALLRUN_BIT   # button held?
    "FF B7 B8 10 00 00 "                    # push dword ptr [edi+VARS_PAD_ID]
    "8D 43 24 "                             # lea eax, [ebx+M02_F_HELD]
    "50 "                                   # push eax
    "FF 35 48 4A D3 00 "                    # push dword ptr ds:CURRENT_OBJ
    "E8 EF 42 E6 FF "                       # call FN_IS_DOWN
    "83 C4 10 "                             # add esp, 0x10
    "83 7B 24 00 "                          # cmp dword ptr [ebx+M02_F_HELD], 0
    "0F 84 36 01 00 00 "                    # je .Lskip
    "8D 43 18 "                             # lea eax, [ebx+M02_F_VELOCITY]   # v.z < VZMIN -> skip
    "50 "                                   # push eax
    "FF 35 48 4A D3 00 "                    # push dword ptr ds:CURRENT_OBJ
    "E8 03 D8 BE FF "                       # call FN_GET_VELOCITY
    "83 C4 08 "                             # add esp, 8
    "D9 43 20 "                             # fld dword ptr [ebx+M02_F_VELOCITY+8]
    "D8 1D B8 A2 8B 00 "                    # fcomp dword ptr ds:M02_VZMIN
    "DF E0 "                                # fnstsw ax
    "F6 C4 01 "                             # test ah, 1
    "0F 85 10 01 00 00 "                    # jne .Lskip
    "53 "                                   # push ebx   # facing
    "FF 35 48 4A D3 00 "                    # push dword ptr ds:CURRENT_OBJ
    "E8 B0 66 BD FF "                       # call FN_GET_FACING
    "83 C4 08 "                             # add esp, 8
    "8D 43 0C "                             # lea eax, [ebx+M02_F_NORMAL]   # wall normal; none -> skip
    "50 "                                   # push eax
    "FF 35 28 BD 8B 00 "                    # push dword ptr ds:FLOAT_ZERO   # minAbsDot 0.0
    "53 "                                   # push ebx
    "68 80 00 00 00 "                       # push M02_CONTACT_WALL
    "FF 35 48 4A D3 00 "                    # push dword ptr ds:CURRENT_OBJ
    "E8 72 58 BE FF "                       # call FN_CONTACT_NORMAL
    "83 C4 14 "                             # add esp, 0x14
    "85 C0 "                                # test eax, eax
    "0F 84 DB 00 00 00 "                    # je .Lskip
    "8D 43 0C "                             # lea eax, [ebx+M02_F_NORMAL]
    "50 "                                   # push eax
    "E8 4E 24 BC FF "                       # call FN_FLATTEN_NORMALIZE
    "83 C4 04 "                             # add esp, 4
    "D9 03 "                                # fld dword ptr [ebx+M02_F_FACING]   # |facing.xy . n.xy| > cos 30
                                            #   deg -> skip (head-on)
    "D8 4B 0C "                             # fmul dword ptr [ebx+M02_F_NORMAL]
    "D9 43 04 "                             # fld dword ptr [ebx+M02_F_FACING+4]
    "D8 4B 10 "                             # fmul dword ptr [ebx+M02_F_NORMAL+4]
    "DE C1 "                                # faddp st(1), st
    "D9 E1 "                                # fabs
    "D8 1D 74 0E 8C 00 "                    # fcomp dword ptr ds:FLOAT_COS30
    "DF E0 "                                # fnstsw ax
    "F6 C4 41 "                             # test ah, 0x41
    # m02_head_on_je:
    "0F 84 AF 00 00 00 "                    # je .Lskip   # 6 bytes; the vertical option turns them into nops
    "FF B7 CC 04 00 00 "                    # push dword ptr [edi+VARS_FALLING]   # save the 13 fields
                                            #   FN_GOTO_WALLING can write before failing
    "FF B7 DC 08 00 00 "                    # push dword ptr [edi+VARS_TAKEOFF_POS]
    "FF B7 E0 08 00 00 "                    # push dword ptr [edi+VARS_TAKEOFF_POS+4]
    "FF B7 E4 08 00 00 "                    # push dword ptr [edi+VARS_TAKEOFF_Z]
    "FF B7 04 02 00 00 "                    # push dword ptr [edi+VARS_FALL_START_Z]
    "FF B7 A8 07 00 00 "                    # push dword ptr [edi+VARS_WALLRUN_SENTINEL]
    "FF B7 AC 07 00 00 "                    # push dword ptr [edi+VARS_WALLRUN_SENTINEL+4]
    "FF B7 B0 07 00 00 "                    # push dword ptr [edi+VARS_WALLRUN_SENTINEL+8]
    "FF B7 80 05 00 00 "                    # push dword ptr [edi+VARS_WALLRUN_DIR]
    "FF B7 84 05 00 00 "                    # push dword ptr [edi+VARS_WALLRUN_DIR+4]
    "FF B7 88 05 00 00 "                    # push dword ptr [edi+VARS_WALLRUN_DIR+8]
    "FF 77 60 "                             # push dword ptr [edi+VARS_WALLRUN_VERTICAL]
    "FF B7 40 08 00 00 "                    # push dword ptr [edi+VARS_WALLRUN_T0]
    "53 "                                   # push ebx   # FN_GOTO_WALLING(obj, &started, &facing)
    "8D 43 28 "                             # lea eax, [ebx+M02_F_STARTED]
    "50 "                                   # push eax
    "FF 35 48 4A D3 00 "                    # push dword ptr ds:CURRENT_OBJ
    "E8 D0 C6 C6 FF "                       # call FN_GOTO_WALLING
    "83 C4 0C "                             # add esp, 0xC
    "83 7B 28 00 "                          # cmp dword ptr [ebx+M02_F_STARTED], 0
    "75 54 "                                # jne .Lstarted
    "8F 87 40 08 00 00 "                    # pop dword ptr [edi+VARS_WALLRUN_T0]   # failed: restore the 13
                                            #   fields
    "8F 47 60 "                             # pop dword ptr [edi+VARS_WALLRUN_VERTICAL]
    "8F 87 88 05 00 00 "                    # pop dword ptr [edi+VARS_WALLRUN_DIR+8]
    "8F 87 84 05 00 00 "                    # pop dword ptr [edi+VARS_WALLRUN_DIR+4]
    "8F 87 80 05 00 00 "                    # pop dword ptr [edi+VARS_WALLRUN_DIR]
    "8F 87 B0 07 00 00 "                    # pop dword ptr [edi+VARS_WALLRUN_SENTINEL+8]
    "8F 87 AC 07 00 00 "                    # pop dword ptr [edi+VARS_WALLRUN_SENTINEL+4]
    "8F 87 A8 07 00 00 "                    # pop dword ptr [edi+VARS_WALLRUN_SENTINEL]
    "8F 87 04 02 00 00 "                    # pop dword ptr [edi+VARS_FALL_START_Z]
    "8F 87 E4 08 00 00 "                    # pop dword ptr [edi+VARS_TAKEOFF_Z]
    "8F 87 E0 08 00 00 "                    # pop dword ptr [edi+VARS_TAKEOFF_POS+4]
    "8F 87 DC 08 00 00 "                    # pop dword ptr [edi+VARS_TAKEOFF_POS]
    "8F 87 CC 04 00 00 "                    # pop dword ptr [edi+VARS_FALLING]
    # .Lskip:
    "83 C4 2C "                             # add esp, 0x2C
    "61 "                                   # popad
    "E9 0D 2C D9 FF "                       # jmp AIR_CONTACT_VANILLA
    # .Lstarted:
    "E9 DE 03 00 00 "                       # jmp m02_latch   # the 13 saved fields stay on the stack;
                                            #   m02_latch drops them
    "90 90 90 90 66 90 "                    # .byte 0x90, 0x90, 0x90, 0x90, 0x66, 0x90   # padding (4 nops and
                                            #   a 2-byte nop) up to M02_VZMIN
    # M02_VZMIN:
    "00 00 20 C1 "                          # .float -10.0
)

M02_LATCH = bytes.fromhex(  # .m02_latch at 0x8BA690, source m02_wall_runs/air_wallrun.s
    # m02_latch:
    "C7 87 E8 13 00 00 01 00 00 00 "        # mov dword ptr [edi+VARS_WALLRUN_LATCH], 1   # edi = Prince data,
                                            #   button confirmed held this frame
    "83 C4 60 "                             # add esp, 0x60   # the 13 saved fields (0x34) and the frame
                                            #   (0x2C)
    "61 "                                   # popad
    "E9 54 34 D9 FF "                       # jmp AIR_HANDLER_EXIT   # wall run running
)

# ---- M03 Stairs-jump fix ----
# A normal jump can no longer land before its apex.

M03_TAKEOFF = bytes.fromhex(  # .m03_takeoff at 0x8BA2C0, source m03_stairs_jump/stairs_jump.s
    # take-off handler (TAKEOFF_STORE); esi = Prince data, the flags of cmp eax,ebp are still live
    # m03_takeoff:
    "89 8E 78 05 00 00 "                    # mov [esi+VARS_LAUNCH_TIME], ecx   # replayed: launch time
    "89 35 EC FC DB 00 "                    # mov dword ptr ds:m03_pending, esi   # apex not reached yet
    "E9 9D 4D D9 FF "                       # jmp TAKEOFF_NEXT   # mov/jmp only: the je there still sees the
                                            #   flags
)

M03_APEX = bytes.fromhex(  # .m03_apex at 0x8BA570, source m03_stairs_jump/stairs_jump.s
    # airborne handler, before its falling-flag check (APEX_CHECK); esi = Prince data, ebx = 0
    # m03_apex:
    "39 35 EC FC DB 00 "                    # cmp dword ptr ds:m03_pending, esi
    "75 2D "                                # jne .Lvanilla
    "83 EC 0C "                             # sub esp, 0xC   # velocity
    "54 "                                   # push esp
    "FF 35 48 4A D3 00 "                    # push dword ptr ds:CURRENT_OBJ
    "E8 F9 D3 BE FF "                       # call FN_GET_VELOCITY
    "83 C4 08 "                             # add esp, 8
    "D9 EE "                                # fldz   # v.z > 0 (rising) or NaN -> keep, else clear
    "D9 44 24 08 "                          # fld dword ptr [esp+8]   # (the same test as the vanilla falling
                                            #   flag)
    "DF F1 "                                # fcomip st, st(1)
    "DD D8 "                                # fstp st(0)
    "7A 0C "                                # jp .Lkeep
    "77 0A "                                # ja .Lkeep
    "C7 05 EC FC DB 00 00 00 00 00 "        # mov dword ptr ds:m03_pending, 0
    # .Lkeep:
    "83 C4 0C "                             # add esp, 0xC
    # .Lvanilla:
    "39 9E CC 04 00 00 "                    # cmp [esi+VARS_FALLING], ebx   # replayed: cmp [esi+0x4CC],ebx ;
                                            #   jne APEX_FLAG_SET
    "0F 85 D3 22 D9 FF "                    # jne APEX_FLAG_SET
    "E9 6B 22 D9 FF "                       # jmp APEX_FLAG_CLEAR
)

M03_LANDING = bytes.fromhex(  # .m03_landing at 0x8BA5C0, source m03_stairs_jump/stairs_jump.s
    # airborne handler, landing gate (LANDING_GATE); esi = Prince data, ebx = 0
    # m03_landing:
    "39 9E CC 04 00 00 "                    # cmp [esi+VARS_FALLING], ebx   # replayed: falling flag clear ->
                                            #   no landing
    "0F 84 F5 27 D9 FF "                    # je LANDING_SKIP
    "39 35 EC FC DB 00 "                    # cmp dword ptr ds:m03_pending, esi   # before the apex -> no
                                            #   landing
    "0F 84 E9 27 D9 FF "                    # je LANDING_SKIP
    "E9 EB 36 D9 FF "                       # jmp LANDING
)

# ---- M04 Story-trigger fix ----
# Story triggers jumped through or over fire when the Prince lands.

M04_POINT_TEST = bytes.fromhex(  # .m04_point_test at 0x8BA3C0, source m04_story_trigger/story_trigger.s
    # m04_point_test:
    "53 "                                   # push ebx
    "56 "                                   # push esi
    "57 "                                   # push edi
    "55 "                                   # push ebp
    "8B 74 24 14 "                          # mov esi, [esp+0x14]   # vol
    "8B 7C 24 18 "                          # mov edi, [esp+0x18]   # actor
    "57 "                                   # push edi   # ebp = r = the vanilla result
    "56 "                                   # push esi
    "E8 6D 3A BE FF "                       # call FN_POINT_IN_TRIGGER
    "83 C4 08 "                             # add esp, 8
    "89 C5 "                                # mov ebp, eax
    "3B 3D 14 C4 D0 00 "                    # cmp edi, dword ptr ds:PRINCE_ACTOR   # not the Prince -> r
    "0F 85 9A 00 00 00 "                    # jne .Lret_r
    "F6 46 04 01 "                          # test byte ptr [esi+4], 1   # vol or actor without flag bit 0 ->
                                            #   r (as 0x7B0CA0)
    "0F 84 90 00 00 00 "                    # je .Lret_r
    "F6 47 04 01 "                          # test byte ptr [edi+4], 1
    "0F 84 86 00 00 00 "                    # je .Lret_r
    "8B 46 18 "                             # mov eax, [esi+0x18]   # trigger type [[[vol+0x18]+4]+0x48]+0xD0
    "8B 40 04 "                             # mov eax, [eax+4]
    "8B 40 48 "                             # mov eax, [eax+0x48]
    "8B 80 D0 00 00 00 "                    # mov eax, [eax+0xD0]
    "83 F8 05 "                             # cmp eax, M04_GATE_TYPE
    "74 05 "                                # je .Lgate
    "83 F8 0D "                             # cmp eax, M04_GATE_TYPE2
    "75 6D "                                # jne .Lret_r
    # .Lgate:
    "8B 5F 18 "                             # mov ebx, [edi+0x18]   # ebx = Prince data
    "8B 5B 04 "                             # mov ebx, [ebx+4]
    "8B 5B 48 "                             # mov ebx, [ebx+0x48]
    "8B 83 44 06 00 00 "                    # mov eax, [ebx+VARS_MOVE_MODE]
    "83 F8 04 "                             # cmp eax, M04_MODE_JUMP
    "74 60 "                                # je .Lin_jump
    "83 F8 15 "                             # cmp eax, M04_MODE_JUMP2
    "74 5B "                                # je .Lin_jump
    "3B 35 E0 FC DB 00 "                    # cmp esi, dword ptr ds:m04_latch_vol   # not the latched gate ->
                                            #   r
    "75 4C "                                # jne .Lret_r
    "85 ED "                                # test ebp, ebp   # inside anyway: vanilla handles it
    "75 3E "                                # jne .Lclear
    "D9 05 74 09 94 00 "                    # fld dword ptr ds:CLOCK   # dt = now - m04_latch_time; dt < 0 or
                                            #   NaN -> expire
    "D8 25 18 33 CD 00 "                    # fsub dword ptr ds:CLOCK_BASE
    "D8 25 E4 FC DB 00 "                    # fsub dword ptr ds:m04_latch_time
    "D9 EE "                                # fldz
    "DF F1 "                                # fcomip st, st(1)
    "77 24 "                                # ja .Lexpire_pop
    "7A 22 "                                # jp .Lexpire_pop
    "D9 05 68 A5 8B 00 "                    # fld dword ptr ds:M04_TMAX   # dt > TMAX -> clear
    "DF F1 "                                # fcomip st, st(1)
    "DD D8 "                                # fstp st(0)
    "72 18 "                                # jb .Lclear
    "83 3D E8 FC DB 00 00 "                 # cmp dword ptr ds:m04_latch_hold, 0   # hold used up -> clear
    "74 0F "                                # je .Lclear
    "FF 0D E8 FC DB 00 "                    # dec dword ptr ds:m04_latch_hold
    "B8 01 00 00 00 "                       # mov eax, 1   # inside
    "EB 0E "                                # jmp .Ldone
    # .Lexpire_pop:
    "DD D8 "                                # fstp st(0)
    # .Lclear:
    "C7 05 E0 FC DB 00 00 00 00 00 "        # mov dword ptr ds:m04_latch_vol, 0
    # .Lret_r:
    "89 E8 "                                # mov eax, ebp
    # .Ldone:
    "5D "                                   # pop ebp
    "5F "                                   # pop edi
    "5E "                                   # pop esi
    "5B "                                   # pop ebx
    "C3 "                                   # ret
    # .Lin_jump:
    "85 ED "                                # test ebp, ebp   # inside mid-air, refused by the gate -> latch
    "0F 85 A9 00 00 00 "                    # jne .Llatch
    "8B 83 40 06 00 00 "                    # mov eax, [ebx+VARS_STATE]   # only in a jump or a rebound
    "3D 12 04 00 00 "                       # cmp eax, M04_STATE_AIR
    "74 07 "                                # je .Lair
    "3D 13 04 00 00 "                       # cmp eax, M04_STATE_REBOUND
    "75 DD "                                # jne .Lret_r
    # .Lair:
    "6A 40 "                                # push M04_CONTACT_GROUND   # ground contact this frame -> r
    "57 "                                   # push edi
    "E8 27 51 BE FF "                       # call FN_CONTACT
    "83 C4 08 "                             # add esp, 8
    "85 C0 "                                # test eax, eax
    "75 CE "                                # jne .Lret_r
    "83 EC 10 "                             # sub esp, 0x10   # p = [esp] (3 floats), bottom = [esp+0xC]
    "8B 47 0C "                             # mov eax, [edi+0xC]   # p = the Prince's translation
                                            #   [[edi+0xC]+0x30]
    "8B 48 30 "                             # mov ecx, [eax+0x30]
    "89 0C 24 "                             # mov [esp], ecx
    "8B 48 34 "                             # mov ecx, [eax+0x34]
    "89 4C 24 04 "                          # mov [esp+4], ecx
    "D9 40 38 "                             # fld dword ptr [eax+0x38]
    "D9 54 24 08 "                          # fst dword ptr [esp+8]
    "D8 25 64 A5 8B 00 "                    # fsub dword ptr ds:M04_DMAX   # bottom = max(take-off z, z -
                                            #   DMAX)
    "D9 83 E4 08 00 00 "                    # fld dword ptr [ebx+VARS_TAKEOFF_Z]
    "DB F1 "                                # fcomi st, st(1)
    "73 02 "                                # jae .Lbottom
    "D9 C9 "                                # fxch st(1)
    # .Lbottom:
    "D9 5C 24 0C "                          # fstp dword ptr [esp+0xC]
    "DD D8 "                                # fstp st(0)
    "D9 44 24 0C "                          # fld dword ptr [esp+0xC]   # z <= bottom (or NaN) -> no hit
    "D9 44 24 08 "                          # fld dword ptr [esp+8]
    "DF F1 "                                # fcomip st, st(1)
    "DD D8 "                                # fstp st(0)
    "76 37 "                                # jbe .Lno_hit
    # .Lnext:
    "D9 44 24 08 "                          # fld dword ptr [esp+8]   # p.z -= STEP, or p.z = bottom as the
                                            #   last sample (ebp = 1)
    "D8 25 60 A5 8B 00 "                    # fsub dword ptr ds:M04_STEP
    "D9 44 24 0C "                          # fld dword ptr [esp+0xC]
    "DB F1 "                                # fcomi st, st(1)
    "72 09 "                                # jb .Lnot_last
    "DD D9 "                                # fstp st(1)
    "BD 01 00 00 00 "                       # mov ebp, 1
    "EB 04 "                                # jmp .Lsample
    # .Lnot_last:
    "DD D8 "                                # fstp st(0)
    "31 ED "                                # xor ebp, ebp
    # .Lsample:
    "D9 5C 24 08 "                          # fstp dword ptr [esp+8]
    "89 E0 "                                # mov eax, esp   # FN_POINT_IN_VOLUME(vol, &p): hit -> latch
    "50 "                                   # push eax
    "56 "                                   # push esi
    "E8 54 53 EF FF "                       # call FN_POINT_IN_VOLUME
    "83 C4 08 "                             # add esp, 8
    "85 C0 "                                # test eax, eax
    "75 0E "                                # jne .Lhit
    "85 ED "                                # test ebp, ebp   # not the last sample -> next
    "74 C9 "                                # je .Lnext
    # .Lno_hit:
    "83 C4 10 "                             # add esp, 0x10
    "31 ED "                                # xor ebp, ebp
    "E9 4D FF FF FF "                       # jmp .Lret_r
    # .Lhit:
    "83 C4 10 "                             # add esp, 0x10
    "31 ED "                                # xor ebp, ebp   # the mid-air result stays vanilla (outside)
    # .Llatch:
    "89 35 E0 FC DB 00 "                    # mov dword ptr ds:m04_latch_vol, esi
    "D9 05 74 09 94 00 "                    # fld dword ptr ds:CLOCK
    "D8 25 18 33 CD 00 "                    # fsub dword ptr ds:CLOCK_BASE
    "D9 1D E4 FC DB 00 "                    # fstp dword ptr ds:m04_latch_time
    "C7 05 E8 FC DB 00 0A 00 00 00 "        # mov dword ptr ds:m04_latch_hold, M04_HOLD_RUNS
    "E9 21 FF FF FF "                       # jmp .Lret_r
    "8D 76 00 "                             # .byte 0x8D, 0x76, 0x00   # padding (3-byte nop) up to the floats
    # M04_STEP:
    "00 00 80 3E "                          # .float 0.25   # sample step below the Prince
    # M04_DMAX:
    "00 00 40 40 "                          # .float 3.0   # sample at most this far below him
    # M04_TMAX:
    "00 00 20 41 "                          # .float 10.0   # a latch expires after this long (s)
)

# ---- M05 Diagonal wall jump ----
# Special Jump off a horizontal wall run leaps at 45 degrees toward the run direction.

M05_JUMPOFF = bytes.fromhex(  # .m05_jumpoff at 0x8BA5E0, source m05_diagonal_jump/diagonal_jump.s
    # wall-run jump-off (WALLRUN_JUMPOFF); esi = Prince data, eax free
    # m05_jumpoff:
    "A0 62 F0 93 00 "                       # mov al, byte ptr ds:PAD_BITS_HIGH   # bit 16 = Special Jump (set
                                            #   with the Space bit, so Space
    "24 01 "                                # and al, 1   # alone keeps the vanilla jump-off)
    "A2 F0 FC DB 00 "                       # mov byte ptr ds:m05_jumpoff_v, al
    "75 0B "                                # jne .Langled
    "8B 15 48 4A D3 00 "                    # mov edx, dword ptr ds:CURRENT_OBJ   # replayed: vanilla jump-off
    "E9 26 6A CD FF "                       # jmp WALLRUN_JUMPOFF_NEXT
    # .Langled:
    "60 "                                   # pushad
    "83 EC 18 "                             # sub esp, 0x18
    "89 E3 "                                # mov ebx, esp
    "53 "                                   # push ebx   # f = facing
    "FF 35 48 4A D3 00 "                    # push dword ptr ds:CURRENT_OBJ
    "E8 45 62 BD FF "                       # call FN_GET_FACING
    "83 C4 08 "                             # add esp, 8
    "D9 05 8A A6 8B 00 "                    # fld dword ptr ds:M05_SIN45   # f'.x = COS45 * f.x - SIN45 * n.x
    "D8 8E 1C 06 00 00 "                    # fmul dword ptr [esi+VARS_WALL_NORMAL]
    "D9 5B 0C "                             # fstp dword ptr [ebx+M05_F_TURNED]
    "D9 05 86 A6 8B 00 "                    # fld dword ptr ds:M05_COS45
    "D8 0B "                                # fmul dword ptr [ebx+M05_F_FACING]
    "D8 63 0C "                             # fsub dword ptr [ebx+M05_F_TURNED]
    "D9 5B 0C "                             # fstp dword ptr [ebx+M05_F_TURNED]
    "D9 05 8A A6 8B 00 "                    # fld dword ptr ds:M05_SIN45   # f'.y = COS45 * f.y - SIN45 * n.y
    "D8 8E 20 06 00 00 "                    # fmul dword ptr [esi+VARS_WALL_NORMAL+4]
    "D9 5B 10 "                             # fstp dword ptr [ebx+M05_F_TURNED+4]
    "D9 05 86 A6 8B 00 "                    # fld dword ptr ds:M05_COS45
    "D8 4B 04 "                             # fmul dword ptr [ebx+M05_F_FACING+4]
    "D8 63 10 "                             # fsub dword ptr [ebx+M05_F_TURNED+4]
    "D9 5B 10 "                             # fstp dword ptr [ebx+M05_F_TURNED+4]
    "C7 43 14 00 00 00 00 "                 # mov dword ptr [ebx+M05_F_TURNED+8], 0   # f'.z = 0, then flatten
                                            #   + normalize (safety)
    "8D 43 0C "                             # lea eax, [ebx+M05_F_TURNED]
    "50 "                                   # push eax
    "E8 C7 1F BC FF "                       # call FN_FLATTEN_NORMALIZE
    "83 C4 04 "                             # add esp, 4
    "68 00 00 80 3F "                       # push 0x3F800000   # up = (0, 0, 1.0f) on the stack
    "6A 00 "                                # push 0
    "6A 00 "                                # push 0
    "89 E0 "                                # mov eax, esp
    "50 "                                   # push eax   # FN_SET_FACING(obj, &f', &up)
    "8D 43 0C "                             # lea eax, [ebx+M05_F_TURNED]
    "50 "                                   # push eax
    "FF 35 48 4A D3 00 "                    # push dword ptr ds:CURRENT_OBJ
    "E8 29 5C BD FF "                       # call FN_SET_FACING
    "83 C4 30 "                             # add esp, 0x30   # its arguments, up and the frame
    "61 "                                   # popad
    "8B 15 48 4A D3 00 "                    # mov edx, dword ptr ds:CURRENT_OBJ   # replayed: vanilla jump-off
                                            #   with the new facing
    "E9 99 69 CD FF "                       # jmp WALLRUN_JUMPOFF_NEXT
    # M05_COS45:
    "F3 04 35 3F "                          # .float 0.70710678
    # M05_SIN45:
    "F3 04 35 3F "                          # .float 0.70710678
)

# ---- M06 Diagonal torpedo ----
# Special Jump + primary attack off a horizontal wall run dives at 45 degrees in the torpedo attack,
# with or without an enemy. Depends on M05 (m05_jumpoff_v).

M06_PRIMARY_ATTACK = bytes.fromhex(  # .m06_primary_attack at 0x8BA6B0
    # source: m06_diagonal_torpedo/diagonal_torpedo.s
    # wall-attack check, primary-attack branch (WALL_ATTACK_PRIMARY); esi = the Prince object
    # m06_primary_attack:
    "BB 02 00 00 00 "                       # mov ebx, M06_TORPEDO_KIND   # replayed: torpedo kind
    "80 3D F0 FC DB 00 00 "                 # cmp byte ptr ds:m05_jumpoff_v, 0   # not a Special Jump
                                            #   jump-off: vanilla, needs a target
    "74 1B "                                # je .Lback
    "56 "                                   # push esi
    "E8 CC D4 BD FF "                       # call FN_CURRENT_ANIM
    "83 C4 04 "                             # add esp, 4
    "83 F8 78 "                             # cmp eax, M06_ANIM_PUSHOFF   # only the horizontal wall
                                            #   jump-off's push-off, which
    "74 05 "                                # je .Lforce   # always passes m05_jumpoff first, so a stale flag
                                            #   never
    "83 F8 79 "                             # cmp eax, M06_ANIM_PUSHOFF2   # matters
    "75 08 "                                # jne .Lback
    # .Lforce:
    "C7 44 24 1C 01 00 00 00 "              # mov dword ptr [esp+0x1C], 1   # the force flag the
                                            #   secondary-attack branch sets
    # .Lback:
    "E9 E4 8B E1 FF "                       # jmp WALL_ATTACK_PRIMARY_NEXT
)

# ---- M07 Wall slide (option "slide") ----
# Hold C against a wall in the air to slide down it like on a curtain. All of it is in the .mods
# section. slide.s is the slide itself (a mode of the airborne state 0x412, run from the
# wall-contact point of M02's cave); the other parts add the entry without wall contact, the start
# gates, the watchdog, the C gate, the run cut, the curtain-like entry animations, the jump gate and
# the animation keep. The slide state is at 0xDBFD00..0xDBFD6B, in the .data page M07 maps.

M07_TUNABLES = bytes.fromhex(  # .m07_tunables at 0xDC9000, source m07_wall_slide/tunables.s
    # ---- tunables ----
    "66 66 66 3F "                          # M07_SEARCH_REACH: .float 0.9   # search ray length along the
                                            #   facing
    "00 00 80 3F "                          # M07_SEARCH_Z: .float 1.0   # search ray height above the origin
    "A4 70 FD 3E "                          # M07_SEARCH_STAND: .float 0.495   # distance from the wall after
                                            #   the snap (contact distance)
    "9A 99 99 3E "                          # M07_SEARCH_MAX_NZ: .float 0.3   # wall must be near-vertical:
                                            #   |normal z| at most this
    "9A 99 19 3F "                          # M07_LEDGE_DROP: .float 0.6   # no ledge grab until this far
                                            #   below the search start height
    "00 00 E0 40 "                          # M07_EDGE_MAX_FALL: .float 7.0   # vanilla: no ledge catch at
                                            #   this fall distance or more
    "00 00 00 00 "                          # M07_EDGE_CATCH: .float 0.0   # edge height above the feet when
                                            #   vanilla catches it (b19 logs: 0)
    "00 00 40 40 "                          # M07_EDGE_DEPTH: .float 3.0   # edge box depth below the feet, at
                                            #   most
    "00 00 00 3F "                          # M07_EDGE_TOP: .float 0.5   # edge box top above the feet (below
                                            #   the ledge dropped from)
    "CD CC CC 3E "                          # M07_EDGE_HALF_X: .float 0.4   # edge box half size, local x
    "CD CC CC 3E "                          # M07_EDGE_HALF_Y: .float 0.4   # edge box half size, local y
                                            #   (forward axis unknown)
    "00 00 00 40 "                          # M07_FLOOR_CLEAR: .float 2.0   # no slide when the floor is
                                            #   closer than this below the feet
    "00 00 20 40 "                          # M07_FLOOR_CLEAR_RUN: .float 2.5   # the same for the run cut;
                                            #   shortcut: ground runs peaked at 2.0 in the b37 test (one
                                            #   level), raise it if a ground run still cuts
    "00 00 00 3F "                          # M07_FLOOR_PROBE_Z: .float 0.5   # floor ray start above the feet
                                            #   (as the slide's floor ray)
    "00 00 40 40 "                          # M07_FLOOR_PROBE: .float 3.0   # floor ray reach below the feet
                                            #   (longer than M07_FLOOR_CLEAR: for the log)
    "00 00 00 3F "                          # M07_WD_STUCK: .float 0.5   # stuck this long (s) -> forced fall
                                            #   exit; also the retry gap
    "00 00 80 3F "                          # M07_WD_WINDOW: .float 1.0   # only if a slide frame ran at most
                                            #   this long before he stopped
    "6F 12 03 3B "                          # M07_WD_EPS: .float 0.002   # per-axis movement below this counts
                                            #   as not moving
    "00 00 00 00 8F C2 75 3E F6 28 1C 3F "  # M07_SWAY_TAU: .float 0.0, 0.24, 0.61, 1.19, 1.41   # sway
    "EC 51 98 3F E1 7A B4 3F "              #   waypoints, the anims' natural lengths
    "00 00 00 00 48 E1 FA 3F 71 3D 6A 40 "  # M07_SWAY_OFFSET: .float 0.0, 1.96, 3.66, 1.57, 1.80   # offset
    "C3 F5 C8 3F 66 66 E6 3F "              #   along the wall at k = 1 (curtainB)
    "75 03 00 00 71 03 00 00 72 03 00 00 "  # M07_ENTRY_ANIMS: .long 0x375, 0x371, 0x372, 0x373   # grab,
    "73 03 00 00 "                          #   settle, swing, swing (wall on his left)
    "74 03 00 00 6E 03 00 00 6F 03 00 00 "  # .long 0x374, 0x36E, 0x36F, 0x370   # the same, wall on his right
    "70 03 00 00 "
    "69 03 00 00 77 03 00 00 00 00 00 00 "  # .long 0x369, 0x377, 0, 0   # head-on grab and its follow-up (0 =
    "00 00 00 00 "                          #   no phase)
    "00 00 80 3E "                          # M07_ADOPT_WINDOW: .float 0.25   # a slide without a sway record
                                            #   is adopted on frames with tau below this (shortcut:
                                            #   first-frame test by time; upgrade to a "first slide frame"
                                            #   flag if a slow first frame misses it)
    "CD CC EC 40 "                          # M07_SWAY_VREF: .float 7.4   # k = 1 at this speed along the wall
                                            #   (curtainB)
    "9A 99 99 3F "                          # M07_SWAY_KMAX: .float 1.2
    "8F C2 75 3E "                          # M07_TURN_START: .float 0.24   # facing turn start (end of the
                                            #   grab anim)
    "29 5C 8F 3E "                          # M07_TURN_LENGTH: .float 0.28   # facing turn length
    "DB 0F 49 40 "                          # M07_PI: .float 3.14159265
    "00 00 00 3F "                          # M07_SWAY_HALF: .float 0.5
    "00 00 40 40 "                          # M07_SWAY_THREE: .float 3.0
    "00 00 00 40 "                          # M07_ENTRY_END: .float 2.0   # phase anims end at the latest this
                                            #   long after the start
    "17 B7 D1 38 "                          # M07_SWAY_EPS: .float 0.0001   # LAT * dz below this: no sway
                                            #   step this frame
    "9A 99 19 3F "                          # M07_JUMP_COOLDOWN: .float 0.6   # no new slide this long (s)
                                            #   after a slide jump-off
    "00 00 C0 3F "                          # M07_HEIGHT_CAP_WINDOW: .float 1.5   # height cap this long (s)
                                            #   after a slide jump-off; shortcut: a guess (one corner cycle is
                                            #   1.04 s), lengthen if a slower chain climbs
    "00 00 00 00 "                          # M07_HEIGHT_CAP_MARGIN: .float 0.0   # a new slide may start this
                                            #   far above the last start (user: 0)
)

M07_SEARCH = bytes.fromhex(  # .m07_search at 0xDC90D4, source m07_wall_slide/search.s
    # m07_search:
    "60 "                                   # pushad
    "81 EC A0 00 00 00 "                    # sub esp, M07_GF_SIZE
    "89 E7 "                                # mov edi, esp
    "8B 1D 48 4A D3 00 "                    # mov ebx, dword ptr ds:CURRENT_OBJ
    "3B 1D 14 C4 D0 00 "                    # cmp ebx, dword ptr ds:PRINCE_ACTOR
    "0F 85 D1 02 00 00 "                    # jne .Lno_slide
    "8B 35 40 4A D3 00 "                    # mov esi, dword ptr ds:CURRENT_INST
    "8B 76 48 "                             # mov esi, dword ptr [esi+0x48]
    "D9 05 74 09 94 00 "                    # fld dword ptr ds:CLOCK
    "D8 25 18 33 CD 00 "                    # fsub dword ptr ds:CLOCK_BASE
    "D9 1F "                                # fstp dword ptr [edi+M07_GF_NOW]
    # already sliding (fresh state for this Prince): the slide.s slide frame handles it
    "39 35 00 FD DB 00 "                    # cmp dword ptr ds:m07_slide_vars, esi
    "75 19 "                                # jne 1f
    "D9 07 "                                # fld dword ptr [edi+M07_GF_NOW]
    "D8 25 08 FD DB 00 "                    # fsub dword ptr ds:m07_slide_last
    "D8 1D EC 9F DC 00 "                    # fcomp dword ptr ds:M07_STALE
    "DF E0 "                                # fnstsw ax
    "F6 C4 41 "                             # test ah, 0x41   # now - tlast <= stale
    "0F 85 99 02 00 00 "                    # jnz .Lno_slide
    # 1:
    # C down, held at least HOLD
    "6A 01 "                                # push 1
    "FF B6 B8 10 00 00 "                    # push dword ptr [esi+0x10b8]
    "8D 47 08 "                             # lea eax, [edi+M07_GF_OUT]
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 17 53 95 FF "                       # call FN_IS_DOWN
    "83 C4 10 "                             # add esp, 16
    "83 7F 08 00 "                          # cmp dword ptr [edi+M07_GF_OUT], 0
    "0F 84 7A 02 00 00 "                    # je .Lno_slide
    "D9 07 "                                # fld dword ptr [edi+M07_GF_NOW]
    "D8 A6 14 07 00 00 "                    # fsub dword ptr [esi+0x714]
    "D8 1D D0 9F DC 00 "                    # fcomp dword ptr ds:M07_HOLD
    "DF E0 "                                # fnstsw ax
    "F6 C4 01 "                             # test ah, 0x01   # held < HOLD
    "0F 85 61 02 00 00 "                    # jnz .Lno_slide
    # cooldown, as the contact entry (slide.s): unsigned compare of the float bits
    "D9 07 "                                # fld dword ptr [edi+M07_GF_NOW]
    "D8 25 08 FD DB 00 "                    # fsub dword ptr ds:m07_slide_last
    "D9 5F 04 "                             # fstp dword ptr [edi+M07_GF_TMP]
    "8B 47 04 "                             # mov eax, [edi+M07_GF_TMP]
    "3B 05 E8 9F DC 00 "                    # cmp eax, dword ptr ds:M07_GRACE
    "0F 82 47 02 00 00 "                    # jb .Lno_slide
    "8B 07 "                                # mov eax, [edi+M07_GF_NOW]   # jump-off cooldown
    "E8 7A 05 00 00 "                       # call m07_jump_cooldown_check
    "0F 84 3A 02 00 00 "                    # jz .Lno_slide
    # the curtain animations the slide uses must be in the Prince's table
    "A1 1C A0 DC 00 "                       # mov eax, dword ptr ds:M07_ANIM_SLIDE
    "E8 1A 0E 00 00 "                       # call m07_has_anim
    "0F 84 2A 02 00 00 "                    # jz .Lno_slide
    "A1 24 A0 DC 00 "                       # mov eax, dword ptr ds:M07_ANIM_JUMP
    "E8 0A 0E 00 00 "                       # call m07_has_anim
    "0F 84 1A 02 00 00 "                    # jz .Lno_slide
    "A1 28 A0 DC 00 "                       # mov eax, dword ptr ds:M07_ANIM_JUMP_AIR
    "E8 FA 0D 00 00 "                       # call m07_has_anim
    "0F 84 0A 02 00 00 "                    # jz .Lno_slide
    "A1 20 A0 DC 00 "                       # mov eax, dword ptr ds:M07_ANIM_LET_GO
    "E8 EA 0D 00 00 "                       # call m07_has_anim
    "0F 84 FA 01 00 00 "                    # jz .Lno_slide
    # ray: from = pos + (0,0,RZ), delta = flat facing * REACH
    "8D 47 0C "                             # lea eax, [edi+M07_GF_FACING]
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 80 76 6C FF "                       # call FN_GET_FACING
    "83 C4 08 "                             # add esp, 8
    "C7 47 14 00 00 00 00 "                 # mov dword ptr [edi+M07_GF_FACING+8], 0
    "8D 47 0C "                             # lea eax, [edi+M07_GF_FACING]
    "50 "                                   # push eax
    "E8 3D 34 6B FF "                       # call FN_FLATTEN_NORMALIZE
    "83 C4 04 "                             # add esp, 4
    "8D 47 18 "                             # lea eax, [edi+M07_GF_POS]
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 F0 5A 6C FF "                       # call FN_GET_POSITION
    "83 C4 08 "                             # add esp, 8
    # the ray is tried along the facing, then to his right (f.y, -f.x), then to his left
    "C7 87 9C 00 00 00 00 00 00 00 "        # mov dword ptr [edi+M07_GF_RAY_SIDE], 0
    "8B 47 0C "                             # mov eax, [edi+M07_GF_FACING]
    "89 87 94 00 00 00 "                    # mov [edi+M07_GF_RAY_DIR], eax
    "8B 47 10 "                             # mov eax, [edi+M07_GF_FACING+4]
    "89 87 98 00 00 00 "                    # mov [edi+M07_GF_RAY_DIR+4], eax
    "E8 8C 03 00 00 "                       # call m07_try_ray
    "75 62 "                                # jnz .Lgot_wall
    "39 35 40 FD DB 00 "                    # cmp dword ptr ds:m07_side_rays, esi   # side rays only after a
                                            #   horizontal run
    "0F 85 9E 01 00 00 "                    # jne .Lno_slide
    "C7 87 9C 00 00 00 01 00 00 00 "        # mov dword ptr [edi+M07_GF_RAY_SIDE], 1
    "8B 47 10 "                             # mov eax, [edi+M07_GF_FACING+4]
    "89 87 94 00 00 00 "                    # mov [edi+M07_GF_RAY_DIR], eax
    "D9 47 0C "                             # fld dword ptr [edi+M07_GF_FACING]
    "D9 E0 "                                # fchs
    "D9 9F 98 00 00 00 "                    # fstp dword ptr [edi+M07_GF_RAY_DIR+4]
    "E8 5B 03 00 00 "                       # call m07_try_ray
    "75 31 "                                # jnz .Lgot_wall
    "C7 87 9C 00 00 00 02 00 00 00 "        # mov dword ptr [edi+M07_GF_RAY_SIDE], 2
    "D9 87 94 00 00 00 "                    # fld dword ptr [edi+M07_GF_RAY_DIR]
    "D9 E0 "                                # fchs
    "D9 9F 94 00 00 00 "                    # fstp dword ptr [edi+M07_GF_RAY_DIR]
    "D9 87 98 00 00 00 "                    # fld dword ptr [edi+M07_GF_RAY_DIR+4]
    "D9 E0 "                                # fchs
    "D9 9F 98 00 00 00 "                    # fstp dword ptr [edi+M07_GF_RAY_DIR+4]
    "E8 2E 03 00 00 "                       # call m07_try_ray
    "0F 84 48 01 00 00 "                    # jz .Lno_slide
    # .Lgot_wall:
    # no start above the last slide's start height within M07_HEIGHT_CAP_WINDOW of a jump-off
    "8B 07 "                                # mov eax, [edi+M07_GF_NOW]
    "E8 97 04 00 00 "                       # call m07_height_cap_check
    "0F 84 3B 01 00 00 "                    # jz .Lno_slide
    # a ledge edge vanilla could still catch below him -> no slide, let him fall
    "E8 CB 01 00 00 "                       # call m07_edge_check
    "85 C0 "                                # test eax, eax
    "79 12 "                                # jns m07_log_sedge
    # the floor too close below him -> no slide, let him land
    "8B 15 2C 90 DC 00 "                    # mov edx, dword ptr ds:M07_FLOOR_CLEAR
    "E8 7D 02 00 00 "                       # call m07_floor_check
    "73 0A "                                # jnc .Lslide
    # m07_log_sfloor:
    "E9 20 01 00 00 "                       # jmp .Lno_slide
    # m07_log_sedge:
    "E9 1B 01 00 00 "                       # jmp .Lno_slide
    # .Lslide:
    # m07_log_sslide:
    # -2 no query), M07_GF_FLOOR_CLEAR
    # snap: position = hit point + n * STAND (height kept)
    "D9 05 08 90 DC 00 "                    # fld dword ptr ds:M07_SEARCH_STAND
    "D9 C0 "                                # fld st(0)
    "D8 4F 48 "                             # fmul dword ptr [edi+M07_GF_HIT_NORMAL]
    "D8 47 3C "                             # fadd dword ptr [edi+M07_GF_HIT_POINT]
    "D9 5F 18 "                             # fstp dword ptr [edi+M07_GF_POS]
    "D8 4F 4C "                             # fmul dword ptr [edi+M07_GF_HIT_NORMAL+4]
    "D8 47 40 "                             # fadd dword ptr [edi+M07_GF_HIT_POINT+4]
    "D9 5F 1C "                             # fstp dword ptr [edi+M07_GF_POS+4]
    "8D 47 18 "                             # lea eax, [edi+M07_GF_POS]
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 E7 5C 6C FF "                       # call FN_SET_POSITION
    "83 C4 08 "                             # add esp, 8
    # a side-ray start (after a horizontal run) records the sway from the speed along t
    "83 BF 9C 00 00 00 00 "                 # cmp dword ptr [edi+M07_GF_RAY_SIDE], 0
    "74 79 "                                # je 1f
    "8D 47 3C "                             # lea eax, [edi+M07_GF_HIT_POINT]
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 A1 E6 6D FF "                       # call FN_GET_VELOCITY
    "83 C4 08 "                             # add esp, 8
    "D9 47 3C "                             # fld dword ptr [edi+M07_GF_HIT_POINT]
    "D8 4F 4C "                             # fmul dword ptr [edi+M07_GF_HIT_NORMAL+4]
    "D9 E0 "                                # fchs   # -vx * ny
    "D9 47 40 "                             # fld dword ptr [edi+M07_GF_HIT_POINT+4]
    "D8 4F 48 "                             # fmul dword ptr [edi+M07_GF_HIT_NORMAL]   # vy * nx
    "DE C1 "                                # faddp st(1), st   # v . t
    "D8 35 A4 90 DC 00 "                    # fdiv dword ptr ds:M07_SWAY_VREF
    "D9 C0 "                                # fld st(0)
    "D9 E1 "                                # fabs
    "D8 1D A8 90 DC 00 "                    # fcomp dword ptr ds:M07_SWAY_KMAX
    "DF E0 "                                # fnstsw ax
    "F6 C4 41 "                             # test ah, 0x41   # |k| <= KMAX
    "75 13 "                                # jnz 2f
    "D9 E4 "                                # ftst
    "DF E0 "                                # fnstsw ax
    "DD D8 "                                # fstp st(0)
    "D9 05 A8 90 DC 00 "                    # fld dword ptr ds:M07_SWAY_KMAX
    "F6 C4 01 "                             # test ah, 0x01
    "74 02 "                                # jz 2f
    "D9 E0 "                                # fchs
    # 2:
    "D9 1D 4C FD DB 00 "                    # fstp dword ptr ds:m07_sway_k
    # m07_log_sway:
    "8B 07 "                                # mov eax, [edi+M07_GF_NOW]
    "A3 48 FD DB 00 "                       # mov dword ptr ds:m07_sway_t0, eax
    "C7 05 58 FD DB 00 00 00 00 00 "        # mov dword ptr ds:m07_sway_phase, 0
    "C7 05 5C FD DB 00 00 00 00 00 "        # mov dword ptr ds:m07_sway_phase_set, 0
    "31 C0 "                                # xor eax, eax   # side ray 1 = wall on his right -> set 1
    "83 BF 9C 00 00 00 01 "                 # cmp dword ptr [edi+M07_GF_RAY_SIDE], 1
    "0F 94 C0 "                             # sete al
    "A3 60 FD DB 00 "                       # mov dword ptr ds:m07_anim_set, eax
    # 1:
    # velocity zero: the snap position must hold (M07_GF_HIT_NORMAL+8 is 0 after the flatten: reuse
    # M07_GF_HIT_POINT as
    # the zero vector, it is not needed any more)
    "31 C0 "                                # xor eax, eax
    "89 47 3C "                             # mov [edi+M07_GF_HIT_POINT], eax
    "89 47 40 "                             # mov [edi+M07_GF_HIT_POINT+4], eax
    "89 47 44 "                             # mov [edi+M07_GF_HIT_POINT+8], eax
    "8D 47 3C "                             # lea eax, [edi+M07_GF_HIT_POINT]
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 FD 55 84 FF "                       # call FN_SET_VELOCITY
    "83 C4 08 "                             # add esp, 8
    # slide state, as the contact entry (slide.s) sets it (m07_log_entry)
    "89 35 00 FD DB 00 "                    # mov dword ptr ds:m07_slide_vars, esi
    "8B 07 "                                # mov eax, [edi+M07_GF_NOW]
    "A3 04 FD DB 00 "                       # mov dword ptr ds:m07_slide_t0, eax
    "A3 08 FD DB 00 "                       # mov dword ptr ds:m07_slide_last, eax   # first step: no movement
    "A3 0C FD DB 00 "                       # mov dword ptr ds:m07_slide_contact, eax   # counts as contact
                                            #   for this frame (within GRACE)
    "31 C0 "                                # xor eax, eax
    "89 86 2C 03 00 00 "                    # mov [esi+0x32c], eax   # no air re-orientation toward the old
                                            #   jump direction
    "89 86 30 03 00 00 "                    # mov [esi+0x330], eax
    "89 86 34 03 00 00 "                    # mov [esi+0x334], eax
    "8B 47 48 "                             # mov eax, [edi+M07_GF_HIT_NORMAL]
    "A3 10 FD DB 00 "                       # mov dword ptr ds:m07_slide_normal, eax
    "8B 47 4C "                             # mov eax, [edi+M07_GF_HIT_NORMAL+4]
    "A3 14 FD DB 00 "                       # mov dword ptr ds:m07_slide_normal+4, eax
    "C7 05 18 FD DB 00 00 00 00 00 "        # mov dword ptr ds:m07_slide_normal+8, 0
    "8B 07 "                                # mov eax, [edi+M07_GF_NOW]
    "A3 20 FD DB 00 "                       # mov dword ptr ds:m07_search_t0, eax   # marks this slide as
                                            #   search-started (T0 is unique per slide)
    "8B 47 20 "                             # mov eax, [edi+M07_GF_POS+8]
    "A3 24 FD DB 00 "                       # mov dword ptr ds:m07_search_z, eax
    "A3 68 FD DB 00 "                       # mov dword ptr ds:m07_start_z, eax   # the height cap's reference
    # m07_log_sstart:
    "90 "                                   # nop
    # .Lno_slide:
    "81 C4 A0 00 00 00 "                    # add esp, M07_GF_SIZE
    "61 "                                   # popad
    "E9 7C 0C 00 00 "                       # jmp m07_no_contact
    # Ledge grab gate (0x64CD81). Block the probe while a search-started slide of this Prince is
    # running (fresh state, T0 == m07_search_t0) and he is less than M07_LEDGE_DROP below its start height.
    # m07_ledge_gate:
    "60 "                                   # pushad
    "83 EC 10 "                             # sub esp, 16
    "8B 1D 48 4A D3 00 "                    # mov ebx, dword ptr ds:CURRENT_OBJ
    "3B 1D 14 C4 D0 00 "                    # cmp ebx, dword ptr ds:PRINCE_ACTOR
    "75 69 "                                # jne .Lledge_probe_allowed
    "8B 35 40 4A D3 00 "                    # mov esi, dword ptr ds:CURRENT_INST
    "8B 76 48 "                             # mov esi, dword ptr [esi+0x48]
    "39 35 00 FD DB 00 "                    # cmp dword ptr ds:m07_slide_vars, esi
    "75 58 "                                # jne .Lledge_probe_allowed
    "A1 04 FD DB 00 "                       # mov eax, dword ptr ds:m07_slide_t0
    "3B 05 20 FD DB 00 "                    # cmp eax, dword ptr ds:m07_search_t0
    "75 4B "                                # jne .Lledge_probe_allowed
    "D9 05 74 09 94 00 "                    # fld dword ptr ds:CLOCK
    "D8 25 18 33 CD 00 "                    # fsub dword ptr ds:CLOCK_BASE
    "D8 25 08 FD DB 00 "                    # fsub dword ptr ds:m07_slide_last
    "D8 1D EC 9F DC 00 "                    # fcomp dword ptr ds:M07_STALE
    "DF E0 "                                # fnstsw ax
    "F6 C4 41 "                             # test ah, 0x41   # now - tlast <= stale
    "74 2C "                                # jz .Lledge_probe_allowed
    "89 E0 "                                # mov eax, esp
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 BC 58 6C FF "                       # call FN_GET_POSITION
    "83 C4 08 "                             # add esp, 8
    "D9 05 24 FD DB 00 "                    # fld dword ptr ds:m07_search_z
    "D8 64 24 08 "                          # fsub dword ptr [esp+8]   # descent since the start
    "D8 1D 10 90 DC 00 "                    # fcomp dword ptr ds:M07_LEDGE_DROP
    "DF E0 "                                # fnstsw ax
    "F6 C4 01 "                             # test ah, 0x01   # below M07_LEDGE_DROP: block
    "74 09 "                                # jz .Lledge_probe_allowed
    # m07_log_lgblock:
    "83 C4 10 "                             # add esp, 16
    "61 "                                   # popad
    "E9 59 39 88 FF "                       # jmp LEDGE_PROBE_SKIP
    # .Lledge_probe_allowed:
    "83 C4 10 "                             # add esp, 16
    "61 "                                   # popad
    "A1 48 4A D3 00 "                       # mov eax, dword ptr ds:CURRENT_OBJ   # the replaced instruction
    "E9 31 39 88 FF "                       # jmp LEDGE_PROBE_CALL
)

M07_CHECKS = bytes.fromhex(  # .m07_checks at 0xDC9455, source m07_wall_slide/checks.s
    # Edge check. In: ebx = obj, esi = vars, edi = a frame with the
    # L_ layout and M07_GF_POS filled. Out: eax = [edi+M07_GF_EDGE_INDEX] = edge index, -1 none found, -2 no
    # query
    # (nothing below can be caught any more). Fills M07_GF_EDGE_DEPTH, M07_GF_BOX_MIN/M07_GF_BOX_MAX and, for
    # a found edge, M07_GF_EDGE_FLAGS
    # and M07_GF_EDGE_POINT. Clobbers ecx, edx; the FPU stack is left empty.
    # m07_edge_check:
    "C7 47 70 FE FF FF FF "                 # mov dword ptr [edi+M07_GF_EDGE_INDEX], -2
    "D9 86 04 02 00 00 "                    # fld dword ptr [esi+VARS_FALL_START_Z]
    "D8 67 20 "                             # fsub dword ptr [edi+M07_GF_POS+8]   # fallen
    "D8 2D 14 90 DC 00 "                    # fsubr dword ptr ds:M07_EDGE_MAX_FALL
    "D8 25 18 90 DC 00 "                    # fsub dword ptr ds:M07_EDGE_CATCH   # D = 7 - fallen - catch
    "D9 05 1C 90 DC 00 "                    # fld dword ptr ds:M07_EDGE_DEPTH
    "D8 D1 "                                # fcom st(1)
    "DF E0 "                                # fnstsw ax
    "F6 C4 01 "                             # test ah, 0x01   # M07_EDGE_DEPTH < D: keep M07_EDGE_DEPTH
    "74 04 "                                # jz 1f
    "DD D9 "                                # fstp st(1)
    "EB 02 "                                # jmp 2f
    # 1:
    "DD D8 "                                # fstp st(0)
    # 2:
    "D9 57 54 "                             # fst dword ptr [edi+M07_GF_EDGE_DEPTH]
    "D9 E4 "                                # ftst
    "DF E0 "                                # fnstsw ax
    "DD D8 "                                # fstp st(0)
    "F6 C4 41 "                             # test ah, 0x41   # D <= 0: nothing below can be caught
    "75 7E "                                # jnz .Ledge_done
    "D9 05 24 90 DC 00 "                    # fld dword ptr ds:M07_EDGE_HALF_X
    "D9 57 64 "                             # fst dword ptr [edi+M07_GF_BOX_MAX]
    "D9 E0 "                                # fchs
    "D9 5F 58 "                             # fstp dword ptr [edi+M07_GF_BOX_MIN]
    "D9 05 28 90 DC 00 "                    # fld dword ptr ds:M07_EDGE_HALF_Y
    "D9 57 68 "                             # fst dword ptr [edi+M07_GF_BOX_MAX+4]
    "D9 E0 "                                # fchs
    "D9 5F 5C "                             # fstp dword ptr [edi+M07_GF_BOX_MIN+4]
    "D9 47 54 "                             # fld dword ptr [edi+M07_GF_EDGE_DEPTH]
    "D9 E0 "                                # fchs
    "D9 5F 60 "                             # fstp dword ptr [edi+M07_GF_BOX_MIN+8]
    "A1 20 90 DC 00 "                       # mov eax, dword ptr ds:M07_EDGE_TOP
    "89 47 6C "                             # mov [edi+M07_GF_BOX_MAX+8], eax
    "8D 47 64 "                             # lea eax, [edi+M07_GF_BOX_MAX]
    "50 "                                   # push eax
    "8D 47 58 "                             # lea eax, [edi+M07_GF_BOX_MIN]
    "50 "                                   # push eax
    "6A 00 "                                # push 0
    "53 "                                   # push ebx
    "E8 E0 4A 6D FF "                       # call FN_BOX_QUERY
    "83 C4 10 "                             # add esp, 16
    "68 0F F4 4F 00 "                       # push LEDGE_EDGE_MASK
    "6A 01 "                                # push LEDGE_EDGE_TYPE
    "8D 47 18 "                             # lea eax, [edi+M07_GF_POS]
    "50 "                                   # push eax
    "6A 00 "                                # push 0
    "E8 8B 4C 6D FF "                       # call FN_QUERY_NEAREST
    "83 C4 10 "                             # add esp, 16
    "89 47 70 "                             # mov [edi+M07_GF_EDGE_INDEX], eax
    "85 C0 "                                # test eax, eax
    "78 23 "                                # js .Ledge_done
    "50 "                                   # push eax
    "6A 00 "                                # push 0
    "E8 49 4C 6D FF "                       # call FN_QUERY_FLAGS
    "83 C4 08 "                             # add esp, 8
    "89 47 74 "                             # mov [edi+M07_GF_EDGE_FLAGS], eax
    "8D 47 78 "                             # lea eax, [edi+M07_GF_EDGE_POINT]
    "50 "                                   # push eax
    "8D 47 18 "                             # lea eax, [edi+M07_GF_POS]
    "50 "                                   # push eax
    "FF 77 70 "                             # push dword ptr [edi+M07_GF_EDGE_INDEX]
    "6A 00 "                                # push 0
    "E8 31 4D 6D FF "                       # call FN_QUERY_CLOSEST_POINT
    "83 C4 10 "                             # add esp, 16
    # .Ledge_done:
    "8B 47 70 "                             # mov eax, [edi+M07_GF_EDGE_INDEX]
    "C3 "                                   # ret
    # Floor check. In: ebx = obj, edi = a frame with the L_ layout and M07_GF_POS filled. Ray from
    # pos + (0,0,M07_FLOOR_PROBE_Z) along (0,0,-(M07_FLOOR_PROBE_Z+M07_FLOOR_PROBE)); M07_GF_FLOOR_CLEAR = pos
    # z - hit z (M07_FLOOR_PROBE when nothing is
    # hit), M07_GF_FLOOR_POINT = hit point (unset when nothing is hit). edx = the limit (float bits). Out:
    # CF=1 when M07_GF_FLOOR_CLEAR < limit (floor too close). Uses M07_GF_RAY_FROM/M07_GF_RAY_DELTA; clobbers
    # eax, ecx, edx; the FPU
    # stack is left empty.
    # m07_floor_check:
    "52 "                                   # push edx   # the limit, compared at [esp] below
    "8B 47 18 "                             # mov eax, [edi+M07_GF_POS]
    "89 47 24 "                             # mov [edi+M07_GF_RAY_FROM], eax
    "8B 47 1C "                             # mov eax, [edi+M07_GF_POS+4]
    "89 47 28 "                             # mov [edi+M07_GF_RAY_FROM+4], eax
    "D9 47 20 "                             # fld dword ptr [edi+M07_GF_POS+8]
    "D8 05 34 90 DC 00 "                    # fadd dword ptr ds:M07_FLOOR_PROBE_Z
    "D9 5F 2C "                             # fstp dword ptr [edi+M07_GF_RAY_FROM+8]
    "31 C0 "                                # xor eax, eax
    "89 47 30 "                             # mov [edi+M07_GF_RAY_DELTA], eax
    "89 47 34 "                             # mov [edi+M07_GF_RAY_DELTA+4], eax
    "D9 05 34 90 DC 00 "                    # fld dword ptr ds:M07_FLOOR_PROBE_Z
    "D8 05 38 90 DC 00 "                    # fadd dword ptr ds:M07_FLOOR_PROBE
    "D9 E0 "                                # fchs
    "D9 5F 38 "                             # fstp dword ptr [edi+M07_GF_RAY_DELTA+8]
    "A1 38 90 DC 00 "                       # mov eax, dword ptr ds:M07_FLOOR_PROBE
    "89 87 84 00 00 00 "                    # mov [edi+M07_GF_FLOOR_CLEAR], eax
    "6A 01 "                                # push 1
    "6A 00 "                                # push 0
    "6A 00 "                                # push 0
    "6A FF "                                # push -1
    "8D 47 30 "                             # lea eax, [edi+M07_GF_RAY_DELTA]
    "50 "                                   # push eax
    "8D 47 24 "                             # lea eax, [edi+M07_GF_RAY_FROM]
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 07 8B 6D FF "                       # call FN_RAY
    "83 C4 1C "                             # add esp, 28
    "85 C0 "                                # test eax, eax
    "74 1F "                                # jz 1f
    "8D 87 88 00 00 00 "                    # lea eax, [edi+M07_GF_FLOOR_POINT]
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 F3 91 6D FF "                       # call FN_RAY_HIT_POINT
    "83 C4 08 "                             # add esp, 8
    "D9 47 20 "                             # fld dword ptr [edi+M07_GF_POS+8]
    "D8 A7 90 00 00 00 "                    # fsub dword ptr [edi+M07_GF_FLOOR_POINT+8]
    "D9 9F 84 00 00 00 "                    # fstp dword ptr [edi+M07_GF_FLOOR_CLEAR]
    # 1:
    "D9 87 84 00 00 00 "                    # fld dword ptr [edi+M07_GF_FLOOR_CLEAR]
    "D8 1C 24 "                             # fcomp dword ptr [esp]
    "DF E0 "                                # fnstsw ax
    "9E "                                   # sahf   # CF=1: clearance < limit (unordered also sets CF: no
                                            #   slide)
    "8D 64 24 04 "                          # lea esp, [esp+4]   # keeps CF
    "C3 "                                   # ret
    # one search ray from pos + (0,0,RZ) along [edi+M07_GF_RAY_DIR] (flat unit vector) * REACH. Accepts a
    # near-vertical runnable wall whose normal is within 60 degrees of -RD: eax = 1 and ZF = 0, with
    # M07_GF_HIT_POINT, M07_GF_HIT_NORMAL (flattened) set; else eax = 0 and ZF = 1. ebx = obj, edi = the
    # search frame.
    # m07_try_ray:
    "8B 47 18 "                             # mov eax, [edi+M07_GF_POS]
    "89 47 24 "                             # mov [edi+M07_GF_RAY_FROM], eax
    "8B 47 1C "                             # mov eax, [edi+M07_GF_POS+4]
    "89 47 28 "                             # mov [edi+M07_GF_RAY_FROM+4], eax
    "D9 47 20 "                             # fld dword ptr [edi+M07_GF_POS+8]
    "D8 05 04 90 DC 00 "                    # fadd dword ptr ds:M07_SEARCH_Z
    "D9 5F 2C "                             # fstp dword ptr [edi+M07_GF_RAY_FROM+8]
    "D9 05 00 90 DC 00 "                    # fld dword ptr ds:M07_SEARCH_REACH
    "D9 C0 "                                # fld st(0)
    "D8 8F 94 00 00 00 "                    # fmul dword ptr [edi+M07_GF_RAY_DIR]
    "D9 5F 30 "                             # fstp dword ptr [edi+M07_GF_RAY_DELTA]
    "D8 8F 98 00 00 00 "                    # fmul dword ptr [edi+M07_GF_RAY_DIR+4]
    "D9 5F 34 "                             # fstp dword ptr [edi+M07_GF_RAY_DELTA+4]
    "C7 47 38 00 00 00 00 "                 # mov dword ptr [edi+M07_GF_RAY_DELTA+8], 0
    "6A 01 "                                # push 1
    "6A 00 "                                # push 0
    "6A 00 "                                # push 0
    "6A FF "                                # push -1
    "8D 47 30 "                             # lea eax, [edi+M07_GF_RAY_DELTA]
    "50 "                                   # push eax
    "8D 47 24 "                             # lea eax, [edi+M07_GF_RAY_FROM]
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 81 8A 6D FF "                       # call FN_RAY
    "83 C4 1C "                             # add esp, 28
    # m07_log_sray:
    "85 C0 "                                # test eax, eax
    "74 78 "                                # jz .Lray_miss
    "8D 47 3C "                             # lea eax, [edi+M07_GF_HIT_POINT]
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 70 91 6D FF "                       # call FN_RAY_HIT_POINT
    "83 C4 08 "                             # add esp, 8
    "8D 47 48 "                             # lea eax, [edi+M07_GF_HIT_NORMAL]
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 03 92 6D FF "                       # call FN_RAY_HIT_NORMAL
    "83 C4 08 "                             # add esp, 8
    "68 FF FF 00 00 "                       # push 0xFFFF
    "53 "                                   # push ebx
    "E8 B5 6A 6D FF "                       # call FN_SURFACE_FLAGS
    "83 C4 08 "                             # add esp, 8
    # m07_log_shit:
    "A9 00 00 03 00 "                       # test eax, SURFACE_NO_RUN_MASK
    "75 49 "                                # jnz .Lray_miss
    "D9 47 50 "                             # fld dword ptr [edi+M07_GF_HIT_NORMAL+8]
    "D9 E1 "                                # fabs
    "D8 1D 0C 90 DC 00 "                    # fcomp dword ptr ds:M07_SEARCH_MAX_NZ
    "DF E0 "                                # fnstsw ax
    "F6 C4 41 "                             # test ah, 0x41   # |nz| <= NZ
    "74 37 "                                # jz .Lray_miss
    "8D 47 48 "                             # lea eax, [edi+M07_GF_HIT_NORMAL]
    "50 "                                   # push eax
    "E8 E0 2F 6B FF "                       # call FN_FLATTEN_NORMALIZE
    "83 C4 04 "                             # add esp, 4
    # ray direction within 60 degrees of the wall: -(RD . n) >= FRONT
    "D9 87 94 00 00 00 "                    # fld dword ptr [edi+M07_GF_RAY_DIR]
    "D8 4F 48 "                             # fmul dword ptr [edi+M07_GF_HIT_NORMAL]
    "D9 87 98 00 00 00 "                    # fld dword ptr [edi+M07_GF_RAY_DIR+4]
    "D8 4F 4C "                             # fmul dword ptr [edi+M07_GF_HIT_NORMAL+4]
    "DE C1 "                                # faddp st(1), st
    "D9 E0 "                                # fchs
    "D8 1D E4 9F DC 00 "                    # fcomp dword ptr ds:M07_FRONT_COS
    "DF E0 "                                # fnstsw ax
    "F6 C4 01 "                             # test ah, 0x01   # below FRONT
    "75 08 "                                # jnz .Lray_miss
    "B8 01 00 00 00 "                       # mov eax, 1
    "85 C0 "                                # test eax, eax
    "C3 "                                   # ret
    # .Lray_miss:
    "31 C0 "                                # xor eax, eax
    "C3 "                                   # ret
)

M07_CONTACT_GATE = bytes.fromhex(  # .m07_contact_gate at 0xDC9671, source m07_wall_slide/contact_gate.s
    # Contact entry gate, called instead of .Lanims_ok from the contact entry (slide.s). Same
    # contract: ZF=1 -> no slide (vanilla contact handling). ZF=1 when the animations are missing
    # or when a catchable ledge edge is below him. ebx = obj, esi = vars (the cave's registers);
    # the cave's edi frame is kept. Clobbers edx (m07_anims_ok already did).
    # m07_contact_gate:
    "8B 15 2C 90 DC 00 "                    # mov edx, dword ptr ds:M07_FLOOR_CLEAR
    # as m07_contact_gate with edx = the floor limit (float bits); m07_run_cut passes M07_FLOOR_CLEAR_RUN.
    # m07_contact_gate_limit:
    "52 "                                   # push edx   # the limit, read back after the pushad below
    "8B 47 4C "                             # mov eax, [edi+M07_SF_NOW]   # jump-off cooldown (the cave's
                                            #   frame)
    "E8 7A 00 00 00 "                       # call m07_jump_cooldown_check
    "74 73 "                                # jz 9f
    "E8 C8 10 00 00 "                       # call m07_anims_ok
    "74 6C "                                # jz 9f
    "8B 47 4C "                             # mov eax, [edi+M07_SF_NOW]   # now, into the new frame's
                                            #   M07_GF_NOW
    "60 "                                   # pushad
    "81 EC A0 00 00 00 "                    # sub esp, M07_GF_SIZE
    "89 E7 "                                # mov edi, esp
    "89 07 "                                # mov [edi+M07_GF_NOW], eax
    "8D 47 18 "                             # lea eax, [edi+M07_GF_POS]
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 3F 56 6C FF "                       # call FN_GET_POSITION
    "83 C4 08 "                             # add esp, 8
    "8B 07 "                                # mov eax, [edi+M07_GF_NOW]   # height cap
    "E8 6B 00 00 00 "                       # call m07_height_cap_check
    "74 2C "                                # jz 2f
    "E8 A3 FD FF FF "                       # call m07_edge_check
    "85 C0 "                                # test eax, eax
    "79 18 "                                # jns m07_log_cedge
    "8B 97 C0 00 00 00 "                    # mov edx, [edi+M07_GF_SIZE+32]   # the limit pushed at entry,
                                            #   above the pushad
    "E8 55 FE FF FF "                       # call m07_floor_check
    "73 21 "                                # jnc 1f
    # m07_log_cfloor:
    "81 C4 A0 00 00 00 "                    # add esp, M07_GF_SIZE
    "61 "                                   # popad
    "39 C0 "                                # cmp eax, eax   # ZF=1: no slide
    "EB 27 "                                # jmp 9f
    # m07_log_cedge:
    "81 C4 A0 00 00 00 "                    # add esp, M07_GF_SIZE
    "61 "                                   # popad
    "39 C0 "                                # cmp eax, eax   # ZF=1: no slide
    "EB 1C "                                # jmp 9f
    # 2:
    "81 C4 A0 00 00 00 "                    # add esp, M07_GF_SIZE
    "61 "                                   # popad
    "39 C0 "                                # cmp eax, eax   # ZF=1: no slide
    "EB 11 "                                # jmp 9f
    # 1:
    # the height cap's reference. For the run cut the search's start right after writes it again.
    "8B 47 20 "                             # mov eax, [edi+M07_GF_POS+8]
    "A3 68 FD DB 00 "                       # mov dword ptr ds:m07_start_z, eax
    # m07_log_cnone:
    "81 C4 A0 00 00 00 "                    # add esp, M07_GF_SIZE
    "61 "                                   # popad
    "85 E4 "                                # test esp, esp   # ZF=0: slide may start
    # 9:
    "8D 64 24 04 "                          # lea esp, [esp+4]   # drop the limit; keeps ZF
    "C3 "                                   # ret
    # eax = now (float bits). ZF=1 while now - m07_jumpoff_time < M07_JUMP_COOLDOWN (no slide). Unsigned
    # compare
    # of the float bits: a negative difference (rewind to before the jump, reload) never blocks.
    # m07_jump_cooldown_check:
    "50 "                                   # push eax
    "D9 04 24 "                             # fld dword ptr [esp]
    "D8 25 64 FD DB 00 "                    # fsub dword ptr ds:m07_jumpoff_time
    "D9 1C 24 "                             # fstp dword ptr [esp]
    "58 "                                   # pop eax
    "3B 05 C8 90 DC 00 "                    # cmp eax, dword ptr ds:M07_JUMP_COOLDOWN
    "73 03 "                                # jae 1f
    # m07_log_jcool:
    "39 C0 "                                # cmp eax, eax   # ZF=1
    "C3 "                                   # ret
    # 1:
    "85 E4 "                                # test esp, esp   # ZF=0
    "C3 "                                   # ret
    # eax = now (float bits), edi = a frame with M07_GF_POS. ZF=1 (no slide) while now - m07_jumpoff_time <
    # M07_HEIGHT_CAP_WINDOW
    # and the feet are above m07_start_z + M07_HEIGHT_CAP_MARGIN; same unsigned compare as
    # m07_jump_cooldown_check (a clock that went
    # back never blocks). Clobbers eax; the FPU stack is left empty.
    # m07_height_cap_check:
    "50 "                                   # push eax
    "D9 04 24 "                             # fld dword ptr [esp]
    "D8 25 64 FD DB 00 "                    # fsub dword ptr ds:m07_jumpoff_time
    "D9 1C 24 "                             # fstp dword ptr [esp]
    "58 "                                   # pop eax
    "3B 05 CC 90 DC 00 "                    # cmp eax, dword ptr ds:M07_HEIGHT_CAP_WINDOW
    "73 19 "                                # jae 1f
    "D9 05 68 FD DB 00 "                    # fld dword ptr ds:m07_start_z
    "D8 05 D0 90 DC 00 "                    # fadd dword ptr ds:M07_HEIGHT_CAP_MARGIN
    "D8 5F 20 "                             # fcomp dword ptr [edi+M07_GF_POS+8]
    "DF E0 "                                # fnstsw ax
    "F6 C4 01 "                             # test ah, 0x01   # cap < z: above the cap
    "74 03 "                                # jz 1f
    # m07_log_hcap:
    "39 C0 "                                # cmp eax, eax   # ZF=1
    "C3 "                                   # ret
    # 1:
    "85 E4 "                                # test esp, esp   # ZF=0
    "C3 "                                   # ret
)

M07_WATCHDOG = bytes.fromhex(  # .m07_watchdog at 0xDC9748, source m07_wall_slide/watchdog.s
    # Stuck watchdog, hook 4 at 0x630160 (function entry). Locals at edi = esp.
    # m07_watchdog:
    "60 "                                   # pushad
    "83 EC 20 "                             # sub esp, M07_WF_SIZE
    "89 E7 "                                # mov edi, esp
    "8B 1D 48 4A D3 00 "                    # mov ebx, dword ptr ds:CURRENT_OBJ
    "3B 1D 14 C4 D0 00 "                    # cmp ebx, dword ptr ds:PRINCE_ACTOR
    "0F 85 6F 02 00 00 "                    # jne .Lout
    "8B 35 40 4A D3 00 "                    # mov esi, dword ptr ds:CURRENT_INST
    "8B 76 48 "                             # mov esi, dword ptr [esi+0x48]
    "D9 05 74 09 94 00 "                    # fld dword ptr ds:CLOCK
    "D8 25 18 33 CD 00 "                    # fsub dword ptr ds:CLOCK_BASE
    "D9 1F "                                # fstp dword ptr [edi+M07_WF_NOW]
    # side-search allowance: set on 0x420 (horizontal run), kept in 0x412, else cleared
    "8B 86 40 06 00 00 "                    # mov eax, [esi+0x640]
    "3D 20 04 00 00 "                       # cmp eax, 0x420
    "75 17 "                                # jne 1f
    "39 35 40 FD DB 00 "                    # cmp dword ptr ds:m07_side_rays, esi   # first 0x420 frame of
                                            #   this run -> m07_run_t0 = now
    "74 07 "                                # je 3f
    "8B 07 "                                # mov eax, [edi+M07_WF_NOW]
    "A3 44 FD DB 00 "                       # mov dword ptr ds:m07_run_t0, eax
    # 3:
    "89 35 40 FD DB 00 "                    # mov dword ptr ds:m07_side_rays, esi
    "EB 11 "                                # jmp 2f
    # 1:
    "3D 12 04 00 00 "                       # cmp eax, 0x412
    "74 0A "                                # je 2f
    "C7 05 40 FD DB 00 00 00 00 00 "        # mov dword ptr ds:m07_side_rays, 0
    # 2:
    # a slide of his is running and its T0 is new -> draw the sword once
    "39 35 00 FD DB 00 "                    # cmp dword ptr ds:m07_slide_vars, esi
    "75 43 "                                # jne 4f
    "A1 04 FD DB 00 "                       # mov eax, dword ptr ds:m07_slide_t0
    "3B 05 3C FD DB 00 "                    # cmp eax, dword ptr ds:m07_sword_t0
    "74 36 "                                # je 4f
    "D9 07 "                                # fld dword ptr [edi+M07_WF_NOW]
    "D8 25 08 FD DB 00 "                    # fsub dword ptr ds:m07_slide_last
    "D8 1D EC 9F DC 00 "                    # fcomp dword ptr ds:M07_STALE
    "DF E0 "                                # fnstsw ax
    "F6 C4 41 "                             # test ah, 0x41   # now - TLAST <= STALE: running
    "74 21 "                                # jz 4f
    "A1 04 FD DB 00 "                       # mov eax, dword ptr ds:m07_slide_t0
    "A3 3C FD DB 00 "                       # mov dword ptr ds:m07_sword_t0, eax
    "C7 05 40 FD DB 00 00 00 00 00 "        # mov dword ptr ds:m07_side_rays, 0   # a slide started: no side
                                            #   rays until the next run
    # m07_log_wdsword:
    "6A 03 "                                # push 3
    "6A 01 "                                # push 1
    "53 "                                   # push ebx
    "E8 BC 76 93 FF "                       # call FN_SNAP_SWORD
    "83 C4 0C "                             # add esp, 12
    # 4:
    "8D 47 04 "                             # lea eax, [edi+M07_WF_POS]
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 DF 54 6C FF "                       # call FN_GET_POSITION
    "83 C4 08 "                             # add esp, 8
    # orphaned slide animation (rewind) -> fall exit now
    "81 BE 40 06 00 00 12 04 00 00 "        # cmp dword ptr [esi+0x640], 0x412
    "0F 85 A3 00 00 00 "                    # jne 6f
    "53 "                                   # push ebx
    "E8 76 E3 6C FF "                       # call FN_CURRENT_ANIM
    "83 C4 04 "                             # add esp, 4
    "3B 05 1C A0 DC 00 "                    # cmp eax, dword ptr ds:M07_ANIM_SLIDE
    "74 2A "                                # je 8f
    "3D 74 03 00 00 "                       # cmp eax, 0x374   # the sway anims (0x36E..0x375) count as slide
                                            #   anims too
    "74 23 "                                # je 8f
    "3D 69 03 00 00 "                       # cmp eax, 0x369   # and the head-on set
    "74 1C "                                # je 8f
    "3D 77 03 00 00 "                       # cmp eax, 0x377
    "74 15 "                                # je 8f
    "3D 75 03 00 00 "                       # cmp eax, 0x375
    "74 0E "                                # je 8f
    "3D 6E 03 00 00 "                       # cmp eax, 0x36E
    "72 6F "                                # jb 6f
    "3D 73 03 00 00 "                       # cmp eax, 0x373
    "77 68 "                                # ja 6f
    # 8:
    "39 35 00 FD DB 00 "                    # cmp dword ptr ds:m07_slide_vars, esi
    "75 22 "                                # jne 5f
    "D9 07 "                                # fld dword ptr [edi+M07_WF_NOW]
    "D8 25 08 FD DB 00 "                    # fsub dword ptr ds:m07_slide_last
    "D9 E4 "                                # ftst
    "DF E0 "                                # fnstsw ax
    "F6 C4 01 "                             # test ah, 0x01   # now < TLAST: time went back, not running
    "75 0F "                                # jnz 7f
    "D8 1D EC 9F DC 00 "                    # fcomp dword ptr ds:M07_STALE
    "DF E0 "                                # fnstsw ax
    "F6 C4 41 "                             # test ah, 0x41   # now - TLAST <= STALE: the slide is running
    "75 42 "                                # jnz 6f
    "EB 02 "                                # jmp 5f
    # 7:
    "DD D8 "                                # fstp st(0)
    # 5:
    # m07_log_wdorphan:
    "8D 47 10 "                             # lea eax, [edi+M07_WF_VELOCITY]
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 CD 6F 6C FF "                       # call FN_GET_FACING
    "83 C4 08 "                             # add esp, 8
    "D9 47 10 "                             # fld dword ptr [edi+M07_WF_VELOCITY]
    "D8 0D F0 9F DC 00 "                    # fmul dword ptr ds:M07_OUT
    "D9 E0 "                                # fchs
    "D9 5F 10 "                             # fstp dword ptr [edi+M07_WF_VELOCITY]
    "D9 47 14 "                             # fld dword ptr [edi+M07_WF_VELOCITY+4]
    "D8 0D F0 9F DC 00 "                    # fmul dword ptr ds:M07_OUT
    "D9 E0 "                                # fchs
    "D9 5F 14 "                             # fstp dword ptr [edi+M07_WF_VELOCITY+4]
    "D9 05 D4 9F DC 00 "                    # fld dword ptr ds:M07_V0
    "D9 E0 "                                # fchs
    "D9 5F 18 "                             # fstp dword ptr [edi+M07_WF_VELOCITY+8]
    "E8 2C 01 00 00 "                       # call .Lfall_exit
    "E9 F9 00 00 00 "                       # jmp .Lmoved
    # 6:
    "81 BE 40 06 00 00 12 04 00 00 "        # cmp dword ptr [esi+0x640], 0x412
    "0F 85 E9 00 00 00 "                    # jne .Lmoved
    "D9 07 "                                # fld dword ptr [edi+M07_WF_NOW]
    "D8 1D 34 FD DB 00 "                    # fcomp dword ptr ds:m07_wd_moved
    "DF E0 "                                # fnstsw ax
    "F6 C4 01 "                             # test ah, 0x01   # now < m07_wd_moved: game time went back
                                            #   (rewind, reload)
    "0F 85 D6 00 00 00 "                    # jnz .Lmoved
    "31 C9 "                                # xor ecx, ecx
    # 1:
    "D9 44 8F 04 "                          # fld dword ptr [edi+M07_WF_POS+ecx*4]
    "D8 24 8D 28 FD DB 00 "                 # fsub dword ptr ds:m07_wd_pos[ecx*4]
    "D9 E1 "                                # fabs
    "D8 1D 44 90 DC 00 "                    # fcomp dword ptr ds:M07_WD_EPS
    "DF E0 "                                # fnstsw ax
    "F6 C4 41 "                             # test ah, 0x41   # |d| > EPS: moved
    "0F 84 B6 00 00 00 "                    # jz .Lmoved
    "41 "                                   # inc ecx
    "83 F9 03 "                             # cmp ecx, 3
    "72 DC "                                # jb 1b
    # not moving: stuck for at least M07_WD_STUCK?
    "D9 07 "                                # fld dword ptr [edi+M07_WF_NOW]
    "D8 25 34 FD DB 00 "                    # fsub dword ptr ds:m07_wd_moved
    "D8 1D 3C 90 DC 00 "                    # fcomp dword ptr ds:M07_WD_STUCK
    "DF E0 "                                # fnstsw ax
    "F6 C4 01 "                             # test ah, 0x01
    "0F 85 B6 00 00 00 "                    # jnz .Lout
    # retry gap since the last fire (a time that went back allows it)
    "D9 07 "                                # fld dword ptr [edi+M07_WF_NOW]
    "D8 25 38 FD DB 00 "                    # fsub dword ptr ds:m07_wd_fired
    "D9 E4 "                                # ftst
    "DF E0 "                                # fnstsw ax
    "F6 C4 01 "                             # test ah, 0x01   # now < m07_wd_fired
    "75 13 "                                # jnz 2f
    "D8 1D 3C 90 DC 00 "                    # fcomp dword ptr ds:M07_WD_STUCK
    "DF E0 "                                # fnstsw ax
    "F6 C4 01 "                             # test ah, 0x01   # now - m07_wd_fired < M07_WD_STUCK
    "0F 85 94 00 00 00 "                    # jnz .Lout
    "EB 02 "                                # jmp 3f
    # 2:
    "DD D8 "                                # fstp st(0)
    # 3:
    # only after a slide of this Prince: the state is his, it is no longer running, and its
    # last frame was at most M07_WD_WINDOW before he stopped moving
    "39 35 00 FD DB 00 "                    # cmp dword ptr ds:m07_slide_vars, esi
    "0F 85 84 00 00 00 "                    # jne .Lout
    "D9 07 "                                # fld dword ptr [edi+M07_WF_NOW]
    "D8 25 08 FD DB 00 "                    # fsub dword ptr ds:m07_slide_last
    "D8 1D EC 9F DC 00 "                    # fcomp dword ptr ds:M07_STALE
    "DF E0 "                                # fnstsw ax
    "F6 C4 41 "                             # test ah, 0x41   # now - TLAST <= STALE: still sliding
    "75 6F "                                # jnz .Lout
    "D9 05 34 FD DB 00 "                    # fld dword ptr ds:m07_wd_moved
    "D8 25 08 FD DB 00 "                    # fsub dword ptr ds:m07_slide_last
    "D8 1D 40 90 DC 00 "                    # fcomp dword ptr ds:M07_WD_WINDOW
    "DF E0 "                                # fnstsw ax
    "F6 C4 41 "                             # test ah, 0x41   # m07_wd_moved - TLAST <= WIN
    "74 56 "                                # jz .Lout
    # m07_log_wdfire:
    "8B 07 "                                # mov eax, [edi+M07_WF_NOW]
    "A3 38 FD DB 00 "                       # mov dword ptr ds:m07_wd_fired, eax
    # the slide's fall exit: v = n * OUT + (0,0,-V0)
    "D9 05 10 FD DB 00 "                    # fld dword ptr ds:m07_slide_normal
    "D8 0D F0 9F DC 00 "                    # fmul dword ptr ds:M07_OUT
    "D9 5F 10 "                             # fstp dword ptr [edi+M07_WF_VELOCITY]
    "D9 05 14 FD DB 00 "                    # fld dword ptr ds:m07_slide_normal+4
    "D8 0D F0 9F DC 00 "                    # fmul dword ptr ds:M07_OUT
    "D9 5F 14 "                             # fstp dword ptr [edi+M07_WF_VELOCITY+4]
    "D9 05 D4 9F DC 00 "                    # fld dword ptr ds:M07_V0
    "D9 E0 "                                # fchs
    "D9 5F 18 "                             # fstp dword ptr [edi+M07_WF_VELOCITY+8]
    "E8 30 00 00 00 "                       # call .Lfall_exit
    "EB 1F "                                # jmp .Lout
    # .Lmoved:
    "8B 47 04 "                             # mov eax, [edi+M07_WF_POS]
    "A3 28 FD DB 00 "                       # mov dword ptr ds:m07_wd_pos, eax
    "8B 47 08 "                             # mov eax, [edi+M07_WF_POS+4]
    "A3 2C FD DB 00 "                       # mov dword ptr ds:m07_wd_pos+4, eax
    "8B 47 0C "                             # mov eax, [edi+M07_WF_POS+8]
    "A3 30 FD DB 00 "                       # mov dword ptr ds:m07_wd_pos+8, eax
    "8B 07 "                                # mov eax, [edi+M07_WF_NOW]
    "A3 34 FD DB 00 "                       # mov dword ptr ds:m07_wd_moved, eax
    # .Lout:
    "83 C4 20 "                             # add esp, M07_WF_SIZE
    "61 "                                   # popad
    "81 EC E4 00 00 00 "                    # sub esp, 0xe4   # the replaced instruction
    "E9 88 67 86 FF "                       # jmp AIR_FRAME_HANDLER_BODY
    # the slide's fall exit with velocity [edi+M07_WF_VELOCITY] (edi = the watchdog frame, ebx = obj, esi =
    # vars)
    # .Lfall_exit:
    "31 C0 "                                # xor eax, eax
    "50 "                                   # push eax
    "6A 0A "                                # push 10
    "6A 50 "                                # push 0x50
    "FF 35 20 A0 DC 00 "                    # push dword ptr ds:M07_ANIM_LET_GO
    "50 "                                   # push eax
    "50 "                                   # push eax
    "6A 2C "                                # push 0x2C
    "53 "                                   # push ebx
    "E8 6B 1C 82 FF "                       # call FN_START_FALL
    "83 C4 20 "                             # add esp, 0x20
    "8D 47 10 "                             # lea eax, [edi+M07_WF_VELOCITY]
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 5E 4F 84 FF "                       # call FN_SET_VELOCITY
    "83 C4 08 "                             # add esp, 8
    "8B 47 0C "                             # mov eax, [edi+M07_WF_POS+8]
    "89 86 04 02 00 00 "                    # mov [esi+0x204], eax   # fall reset
    "C7 86 CC 04 00 00 01 00 00 00 "        # mov dword ptr [esi+0x4cc], 1
    "C3 "                                   # ret
)

M07_C_GATE = bytes.fromhex(  # .m07_c_gate at 0xDC9A19, source m07_wall_slide/c_gate.s
    # C gate, called instead of IsDown 0x71E450(obj, &out, pad, bit) at 0x725D9A. Same
    # arguments and results (out, eax, registers as IsDown leaves them).
    # m07_c_gate:
    "FF 74 24 10 "                          # push dword ptr [esp+16]
    "FF 74 24 10 "                          # push dword ptr [esp+16]
    "FF 74 24 10 "                          # push dword ptr [esp+16]
    "FF 74 24 10 "                          # push dword ptr [esp+16]
    "E8 22 4A 95 FF "                       # call FN_IS_DOWN
    "83 C4 10 "                             # add esp, 16
    "60 "                                   # pushad
    "8B 5C 24 24 "                          # mov ebx, [esp+36]   # obj
    "3B 1D 14 C4 D0 00 "                    # cmp ebx, dword ptr ds:PRINCE_ACTOR
    "75 32 "                                # jne 9f
    "83 7C 24 30 01 "                       # cmp dword ptr [esp+48], 1   # bit 1 = C
    "75 2B "                                # jne 9f
    "8B 54 24 28 "                          # mov edx, [esp+40]   # &out
    "83 3A 00 "                             # cmp dword ptr [edx], 0
    "74 22 "                                # je 9f
    "8B 43 18 "                             # mov eax, [ebx+0x18]   # vars, as PressedWithin finds them
    "8B 40 04 "                             # mov eax, [eax+4]
    "8B 40 48 "                             # mov eax, [eax+0x48]
    "D9 80 14 07 00 00 "                    # fld dword ptr [eax+VARS_C_PRESS_TIME]
    "D8 1D 08 FD DB 00 "                    # fcomp dword ptr ds:m07_slide_last
    "DF E0 "                                # fnstsw ax
    "F6 C4 41 "                             # test ah, 0x41   # press <= last slide frame: the slide's C
    "74 06 "                                # jz 9f
    # m07_log_cgate:
    "C7 02 00 00 00 00 "                    # mov dword ptr [edx], 0
    # 9:
    "61 "                                   # popad
    "C3 "                                   # ret
)

M07_RUN_CUT = bytes.fromhex(  # .m07_run_cut at 0xDC9A72, source m07_wall_slide/run_cut.s
    # ---- run cut (hook 6, je from 0x590FED; esi = vars, stack at handler level) ----
    # m07_run_cut:
    "60 "                                   # pushad
    "83 EC 10 "                             # sub esp, 16   # [esp] out, [esp+4] velocity (3f)
    "8B 1D 48 4A D3 00 "                    # mov ebx, dword ptr ds:CURRENT_OBJ
    "3B 1D 14 C4 D0 00 "                    # cmp ebx, dword ptr ds:PRINCE_ACTOR
    "0F 85 F1 00 00 00 "                    # jne .Lrun_continues
    "39 35 40 FD DB 00 "                    # cmp dword ptr ds:m07_side_rays, esi
    "0F 85 E5 00 00 00 "                    # jne .Lrun_continues
    "6A 01 "                                # push 1
    "FF B6 B8 10 00 00 "                    # push dword ptr [esi+0x10b8]
    "8D 44 24 08 "                          # lea eax, [esp+8]
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 A9 49 95 FF "                       # call FN_IS_DOWN
    "83 C4 10 "                             # add esp, 16
    "83 3C 24 00 "                          # cmp dword ptr [esp], 0
    "0F 84 C5 00 00 00 "                    # je .Lrun_continues
    "D9 86 14 07 00 00 "                    # fld dword ptr [esi+VARS_C_PRESS_TIME]
    "D8 1D 44 FD DB 00 "                    # fcomp dword ptr ds:m07_run_t0
    "DF E0 "                                # fnstsw ax
    "F6 C4 01 "                             # test ah, 0x01   # pressed before this run started
    "0F 85 AE 00 00 00 "                    # jnz .Lrun_continues
    "D9 05 74 09 94 00 "                    # fld dword ptr ds:CLOCK
    "D8 25 18 33 CD 00 "                    # fsub dword ptr ds:CLOCK_BASE
    "D8 A6 14 07 00 00 "                    # fsub dword ptr [esi+VARS_C_PRESS_TIME]
    "D8 1D D0 9F DC 00 "                    # fcomp dword ptr ds:M07_HOLD
    "DF E0 "                                # fnstsw ax
    "F6 C4 01 "                             # test ah, 0x01   # held < HOLD
    "0F 85 8B 00 00 00 "                    # jnz .Lrun_continues
    "A1 1C A0 DC 00 "                       # mov eax, dword ptr ds:M07_ANIM_SLIDE
    "E8 B2 04 00 00 "                       # call m07_has_anim
    "74 7F "                                # jz .Lrun_continues
    # cut only where the slide may start (m07_contact_gate reads now from [edi+M07_SF_NOW] of a frame)
    "FF B6 04 02 00 00 "                    # push dword ptr [esi+VARS_FALL_START_Z]
    "83 EC 50 "                             # sub esp, M07_SF_NOW + 4
    "89 E7 "                                # mov edi, esp
    "D9 05 74 09 94 00 "                    # fld dword ptr ds:CLOCK
    "D8 25 18 33 CD 00 "                    # fsub dword ptr ds:CLOCK_BASE
    "D9 5F 4C "                             # fstp dword ptr [edi+M07_SF_NOW]
    "57 "                                   # push edi   # position into [edi], [edi+8] = z
    "53 "                                   # push ebx
    "E8 C5 51 6C FF "                       # call FN_GET_POSITION
    "83 C4 08 "                             # add esp, 8
    "8B 47 08 "                             # mov eax, [edi+8]
    "89 86 04 02 00 00 "                    # mov [esi+VARS_FALL_START_Z], eax   # as after the cut: fallen =
                                            #   0
    "8B 15 30 90 DC 00 "                    # mov edx, dword ptr ds:M07_FLOOR_CLEAR_RUN   # the run cut's own
                                            #   floor limit
    "E8 45 FB FF FF "                       # call m07_contact_gate_limit
    "8D 64 24 50 "                          # lea esp, [esp+M07_SF_NOW+4]   # lea and pop keep ZF
    "8F 86 04 02 00 00 "                    # pop dword ptr [esi+VARS_FALL_START_Z]
    "74 3B "                                # jz .Lrun_continues
    # m07_log_runcut:
    "8D 44 24 04 "                          # lea eax, [esp+4]
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 37 DE 6D FF "                       # call FN_GET_VELOCITY
    "83 C4 08 "                             # add esp, 8
    "31 C0 "                                # xor eax, eax
    "50 "                                   # push eax
    "6A 0A "                                # push 10
    "6A 50 "                                # push 0x50
    "6A 2C "                                # push 0x2C
    "50 "                                   # push eax
    "50 "                                   # push eax
    "6A 2C "                                # push 0x2C
    "53 "                                   # push ebx
    "E8 01 1B 82 FF "                       # call FN_START_FALL
    "83 C4 20 "                             # add esp, 0x20
    "8D 44 24 04 "                          # lea eax, [esp+4]
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 F3 4D 84 FF "                       # call FN_SET_VELOCITY
    "83 C4 08 "                             # add esp, 8
    "83 C4 10 "                             # add esp, 16
    "61 "                                   # popad
    "E9 1E 75 7C FF "                       # jmp WALLRUN_JUMPOFF_TAIL
    # .Lrun_continues:
    "83 C4 10 "                             # add esp, 16
    "61 "                                   # popad
    "E9 77 8C 7C FF "                       # jmp RUN_CONTINUES
)

M07_ENTRY_ANIMS = bytes.fromhex(  # .m07_entry_anims at 0xDC9B82, source m07_wall_slide/entry_anims.s
    # ---- sway helpers (slide.s slide frame: ebx = obj, esi = vars, edi = its frame) ----
    # eax = 1 and st0 = tau when the sway of this slide is on (m07_sway_t0 = m07_slide_t0, 0 <= tau < last
    # waypoint), else eax = 0 and the FPU stack empty
    # .Lsway_active:
    "83 3D 60 FD DB 00 02 "                 # cmp dword ptr ds:m07_anim_set, 2   # head-on set has no swing
                                            #   and no turn
    "74 34 "                                # je 9f
    "A1 04 FD DB 00 "                       # mov eax, dword ptr ds:m07_slide_t0
    "3B 05 48 FD DB 00 "                    # cmp eax, dword ptr ds:m07_sway_t0
    "75 27 "                                # jne 9f
    "D9 47 4C "                             # fld dword ptr [edi+M07_SF_NOW]
    "D8 25 04 FD DB 00 "                    # fsub dword ptr ds:m07_slide_t0
    "D9 E4 "                                # ftst
    "DF E0 "                                # fnstsw ax
    "F6 C4 01 "                             # test ah, 0x01   # tau < 0
    "75 13 "                                # jnz 8f
    "D8 15 58 90 DC 00 "                    # fcom dword ptr ds:M07_SWAY_TAU+16
    "DF E0 "                                # fnstsw ax
    "F6 C4 01 "                             # test ah, 0x01   # tau < end
    "74 06 "                                # jz 8f
    "B8 01 00 00 00 "                       # mov eax, 1
    "C3 "                                   # ret
    # 8:
    "DD D8 "                                # fstp st(0)
    # 9:
    "31 C0 "                                # xor eax, eax
    "C3 "                                   # ret
    # st0 = tau -> st0 = F(tau): cosine segments through M07_SWAY_TAU / M07_SWAY_OFFSET (0 before, last after)
    # .Lsway_curve:
    "D9 E4 "                                # ftst
    "DF E0 "                                # fnstsw ax
    "F6 C4 01 "                             # test ah, 0x01
    "74 05 "                                # jz 1f
    "DD D8 "                                # fstp st(0)
    "D9 EE "                                # fldz
    "C3 "                                   # ret
    # 1:
    "31 C9 "                                # xor ecx, ecx
    # 2:
    "D9 04 8D 4C 90 DC 00 "                 # fld dword ptr ds:M07_SWAY_TAU+4[ecx*4]
    "DF F1 "                                # fcomip st, st(1)
    "77 0F "                                # ja 3f   # tau < tau_b
    "41 "                                   # inc ecx
    "83 F9 04 "                             # cmp ecx, 4
    "72 EF "                                # jb 2b
    "DD D8 "                                # fstp st(0)
    "D9 05 6C 90 DC 00 "                    # fld dword ptr ds:M07_SWAY_OFFSET+16
    "C3 "                                   # ret
    # 3:
    "D8 24 8D 48 90 DC 00 "                 # fsub dword ptr ds:M07_SWAY_TAU[ecx*4]
    "D9 04 8D 4C 90 DC 00 "                 # fld dword ptr ds:M07_SWAY_TAU+4[ecx*4]
    "D8 24 8D 48 90 DC 00 "                 # fsub dword ptr ds:M07_SWAY_TAU[ecx*4]
    "D9 1D 54 FD DB 00 "                    # fstp dword ptr ds:m07_sway_tmp2
    "D8 35 54 FD DB 00 "                    # fdiv dword ptr ds:m07_sway_tmp2   # u
    "D8 0D B4 90 DC 00 "                    # fmul dword ptr ds:M07_PI
    "D9 FF "                                # fcos
    "D8 0D B8 90 DC 00 "                    # fmul dword ptr ds:M07_SWAY_HALF
    "D9 E0 "                                # fchs
    "D8 05 B8 90 DC 00 "                    # fadd dword ptr ds:M07_SWAY_HALF   # w = (1 - cos(pi u)) / 2
    "D9 04 8D 60 90 DC 00 "                 # fld dword ptr ds:M07_SWAY_OFFSET+4[ecx*4]
    "D8 24 8D 5C 90 DC 00 "                 # fsub dword ptr ds:M07_SWAY_OFFSET[ecx*4]
    "DE C9 "                                # fmulp st(1), st
    "D8 04 8D 5C 90 DC 00 "                 # fadd dword ptr ds:M07_SWAY_OFFSET[ecx*4]
    "C3 "                                   # ret
    # hook 7 (call from m07_frame_anim_block): during this slide's sway the phase anims 0x375, 0x371, 0x372,
    # 0x373 in turn, each until it stops playing (the airborne anim-end branch replaces it), missing
    # ones skipped, and the velocity zeroed (their root motion would add to the scripted swing); then
    # and otherwise the slide loop
    # m07_entry_anim:
    "60 "                                   # pushad
    "83 EC 0C "                             # sub esp, 12   # zero vector
    "A1 04 FD DB 00 "                       # mov eax, dword ptr ds:m07_slide_t0
    "3B 05 48 FD DB 00 "                    # cmp eax, dword ptr ds:m07_sway_t0
    "0F 84 8A 00 00 00 "                    # je 1f
    # no sway record for this slide: adopt it with the head-on set on its first frames
    "D9 47 4C "                             # fld dword ptr [edi+M07_SF_NOW]
    "D8 25 04 FD DB 00 "                    # fsub dword ptr ds:m07_slide_t0
    "D9 E4 "                                # ftst
    "DF E0 "                                # fnstsw ax
    "F6 C4 01 "                             # test ah, 0x01   # tau < 0
    "75 71 "                                # jnz 2f
    "D8 1D A0 90 DC 00 "                    # fcomp dword ptr ds:M07_ADOPT_WINDOW
    "DF E0 "                                # fnstsw ax
    "F6 C4 01 "                             # test ah, 0x01   # tau >= HWIN: not a fresh slide
    "0F 84 F7 00 00 00 "                    # jz 5f
    "A1 04 FD DB 00 "                       # mov eax, dword ptr ds:m07_slide_t0
    "A3 48 FD DB 00 "                       # mov dword ptr ds:m07_sway_t0, eax
    "C7 05 60 FD DB 00 02 00 00 00 "        # mov dword ptr ds:m07_anim_set, 2
    "C7 05 4C FD DB 00 00 00 00 00 "        # mov dword ptr ds:m07_sway_k, 0
    "C7 05 5C FD DB 00 00 00 00 00 "        # mov dword ptr ds:m07_sway_phase_set, 0
    "C7 05 58 FD DB 00 00 00 00 00 "        # mov dword ptr ds:m07_sway_phase, 0
    "53 "                                   # push ebx
    "E8 E5 DE 6C FF "                       # call FN_CURRENT_ANIM
    "83 C4 04 "                             # add esp, 4
    "3B 05 1C A0 DC 00 "                    # cmp eax, dword ptr ds:M07_ANIM_SLIDE   # already in a slide
                                            #   anim: restarted at once, no re-grab
    "74 0E "                                # je 3f
    "3D 69 03 00 00 "                       # cmp eax, 0x369
    "74 07 "                                # je 3f
    "3D 77 03 00 00 "                       # cmp eax, 0x377
    "75 16 "                                # jne 1f
    # 3:
    "C7 05 58 FD DB 00 04 00 00 00 "        # mov dword ptr ds:m07_sway_phase, 4
    "E9 97 00 00 00 "                       # jmp 5f
    # 2:
    "DD D8 "                                # fstp st(0)
    "E9 90 00 00 00 "                       # jmp 5f
    # 1:
    "D9 47 4C "                             # fld dword ptr [edi+M07_SF_NOW]
    "D8 25 04 FD DB 00 "                    # fsub dword ptr ds:m07_slide_t0
    "D8 1D C0 90 DC 00 "                    # fcomp dword ptr ds:M07_ENTRY_END
    "DF E0 "                                # fnstsw ax
    "F6 C4 01 "                             # test ah, 0x01   # tau >= AEND: phases over
    "74 7A "                                # jz 5f
    # 4:
    "8B 0D 58 FD DB 00 "                    # mov ecx, dword ptr ds:m07_sway_phase
    "83 F9 04 "                             # cmp ecx, 4
    "73 6F "                                # jae 5f
    "A1 60 FD DB 00 "                       # mov eax, dword ptr ds:m07_anim_set
    "8D 04 81 "                             # lea eax, [ecx+eax*4]   # row of the wall side
    "8B 04 85 70 90 DC 00 "                 # mov eax, dword ptr ds:M07_ENTRY_ANIMS[eax*4]
    "85 C0 "                                # test eax, eax   # no anim in this phase: skip it
    "74 21 "                                # jz 3f
    "50 "                                   # push eax
    "E8 96 02 00 00 "                       # call m07_has_anim
    "58 "                                   # pop eax
    "74 18 "                                # jz 3f   # not loaded: skip the phase
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 72 DE 6C FF "                       # call FN_CURRENT_ANIM
    "83 C4 04 "                             # add esp, 4
    "59 "                                   # pop ecx   # ecx = the phase anim
    "39 C8 "                                # cmp eax, ecx
    "74 29 "                                # je 6f   # still playing
    "83 3D 5C FD DB 00 00 "                 # cmp dword ptr ds:m07_sway_phase_set, 0
    "74 12 "                                # je 7f   # not set yet: set it
    # 3:
    "FF 05 58 FD DB 00 "                    # inc dword ptr ds:m07_sway_phase   # it ended (or is missing):
                                            #   next phase
    "C7 05 5C FD DB 00 00 00 00 00 "        # mov dword ptr ds:m07_sway_phase_set, 0
    "EB AF "                                # jmp 4b
    # 7:
    "C7 05 5C FD DB 00 01 00 00 00 "        # mov dword ptr ds:m07_sway_phase_set, 1
    "89 C8 "                                # mov eax, ecx
    "EB 20 "                                # jmp 8f
    # 6:
    "31 C0 "                                # xor eax, eax
    "89 04 24 "                             # mov [esp], eax
    "89 44 24 04 "                          # mov [esp+4], eax
    "89 44 24 08 "                          # mov [esp+8], eax
    "89 E0 "                                # mov eax, esp
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 FB 4B 84 FF "                       # call FN_SET_VELOCITY
    "83 C4 08 "                             # add esp, 8
    "EB 3F "                                # jmp 9f
    # 5:
    "A1 1C A0 DC 00 "                       # mov eax, dword ptr ds:M07_ANIM_SLIDE
    # 8:
    # m07_log_swanim:
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 1A DE 6C FF "                       # call FN_CURRENT_ANIM
    "83 C4 04 "                             # add esp, 4
    "59 "                                   # pop ecx
    "39 C8 "                                # cmp eax, ecx
    "74 2B "                                # je 9f
    "51 "                                   # push ecx
    "53 "                                   # push ebx
    "E8 CB 57 84 FF "                       # call FN_SET_ANIM
    "83 C4 08 "                             # add esp, 8
    "3B 0D 1C A0 DC 00 "                    # cmp ecx, dword ptr ds:M07_ANIM_SLIDE
    "74 19 "                                # je 9f
    "31 C0 "                                # xor eax, eax   # a phase anim was just set: zero its velocity
                                            #   too
    "89 04 24 "                             # mov [esp], eax
    "89 44 24 04 "                          # mov [esp+4], eax
    "89 44 24 08 "                          # mov [esp+8], eax
    "89 E0 "                                # mov eax, esp
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 BA 4B 84 FF "                       # call FN_SET_VELOCITY
    "83 C4 08 "                             # add esp, 8
    # 9:
    "83 C4 0C "                             # add esp, 12
    "61 "                                   # popad
    "C3 "                                   # ret
    # hook 8 (call from m07_frame_face_call): face the wall as before, then during the turn window the
    # facing goes from the run direction sign(k) * t to -n (smoothstep)
    # m07_sway_face:
    "E8 26 09 00 00 "                       # call m07_face_wall
    "60 "                                   # pushad
    "83 EC 18 "                             # sub esp, 24   # [esp] dir (3f), [esp+12] up (3f)
    "E8 C6 FD FF FF "                       # call .Lsway_active
    "85 C0 "                                # test eax, eax
    "0F 84 B3 00 00 00 "                    # jz 9f
    "D8 25 AC 90 DC 00 "                    # fsub dword ptr ds:M07_TURN_START
    "D8 35 B0 90 DC 00 "                    # fdiv dword ptr ds:M07_TURN_LENGTH   # u
    "D9 E8 "                                # fld1
    "DF F1 "                                # fcomip st, st(1)
    "0F 86 9B 00 00 00 "                    # jbe 8f   # u >= 1: already facing the wall
    "D9 EE "                                # fldz
    "DF F1 "                                # fcomip st, st(1)
    "72 04 "                                # jb 1f   # u > 0
    "DD D8 "                                # fstp st(0)
    "D9 EE "                                # fldz
    # 1:
    "D9 C0 "                                # fld st(0)
    "D8 C0 "                                # fadd st, st(0)
    "D8 2D BC 90 DC 00 "                    # fsubr dword ptr ds:M07_SWAY_THREE   # 3 - 2u
    "D8 C9 "                                # fmul st, st(1)
    "DE C9 "                                # fmulp st(1), st   # w = u u (3 - 2u)
    "D9 1D 50 FD DB 00 "                    # fstp dword ptr ds:m07_sway_tmp
    "A1 4C FD DB 00 "                       # mov eax, dword ptr ds:m07_sway_k
    "A9 FF FF FF 7F "                       # test eax, 0x7FFFFFFF
    "74 73 "                                # jz 9f   # k = 0: no run direction
    # rd = sign(k) * (-n.y, n.x); dir = rd + w * (-n - rd)
    "D9 47 04 "                             # fld dword ptr [edi+M07_SF_NORMAL+4]
    "D9 E0 "                                # fchs
    "D9 07 "                                # fld dword ptr [edi+M07_SF_NORMAL]
    "85 C0 "                                # test eax, eax
    "79 08 "                                # jns 2f
    "D9 E0 "                                # fchs
    "D9 C9 "                                # fxch st(1)
    "D9 E0 "                                # fchs
    "D9 C9 "                                # fxch st(1)
    # 2:
    "D9 47 04 "                             # fld dword ptr [edi+M07_SF_NORMAL+4]
    "D9 E0 "                                # fchs
    "D8 E1 "                                # fsub st, st(1)   # -n.y - ry
    "D8 0D 50 FD DB 00 "                    # fmul dword ptr ds:m07_sway_tmp
    "D8 C1 "                                # fadd st, st(1)
    "D9 5C 24 04 "                          # fstp dword ptr [esp+4]   # dir.y
    "DD D8 "                                # fstp st(0)
    "D9 07 "                                # fld dword ptr [edi+M07_SF_NORMAL]
    "D9 E0 "                                # fchs
    "D8 E1 "                                # fsub st, st(1)   # -n.x - rx
    "D8 0D 50 FD DB 00 "                    # fmul dword ptr ds:m07_sway_tmp
    "D8 C1 "                                # fadd st, st(1)
    "D9 1C 24 "                             # fstp dword ptr [esp]   # dir.x
    "DD D8 "                                # fstp st(0)
    "31 C0 "                                # xor eax, eax
    "89 44 24 08 "                          # mov [esp+8], eax
    "89 44 24 0C "                          # mov [esp+12], eax
    "89 44 24 10 "                          # mov [esp+16], eax
    "C7 44 24 14 00 00 80 3F "              # mov dword ptr [esp+20], 0x3F800000
    "89 E0 "                                # mov eax, esp
    "50 "                                   # push eax
    "E8 C3 27 6B FF "                       # call FN_FLATTEN_NORMALIZE
    "83 C4 04 "                             # add esp, 4
    "8D 44 24 0C "                          # lea eax, [esp+12]
    "50 "                                   # push eax
    "8D 44 24 04 "                          # lea eax, [esp+4]
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 30 64 6C FF "                       # call FN_SET_FACING
    "83 C4 0C "                             # add esp, 12
    # m07_log_swface:
    "EB 02 "                                # jmp 9f
    # 8:
    "DD D8 "                                # fstp st(0)
    # 9:
    "83 C4 18 "                             # add esp, 24
    "61 "                                   # popad
    "C3 "                                   # ret
    # hook 9 (jmp from m07_frame_stick_zero): during the sway the scripted step replaces the stick
    # m07_sway_stick:
    "51 "                                   # push ecx
    "52 "                                   # push edx
    "E8 FF FC FF FF "                       # call .Lsway_active
    "85 C0 "                                # test eax, eax
    "75 0C "                                # jnz 1f
    "5A "                                   # pop edx
    "59 "                                   # pop ecx
    "D9 EE "                                # fldz
    "D9 5F 50 "                             # fstp dword ptr [edi+M07_SF_LATERAL]
    "E9 85 04 00 00 "                       # jmp m07_frame_stick
    # 1:
    "DD D8 "                                # fstp st(0)
    "85 ED "                                # test ebp, ebp
    "74 73 "                                # jz 4f   # no contact: no sideways step
    "D9 47 4C "                             # fld dword ptr [edi+M07_SF_NOW]
    "D8 25 04 FD DB 00 "                    # fsub dword ptr ds:m07_slide_t0
    "E8 1B FD FF FF "                       # call .Lsway_curve
    "D9 1D 50 FD DB 00 "                    # fstp dword ptr ds:m07_sway_tmp   # F(tau)
    "D9 87 50 01 00 00 "                    # fld dword ptr [edi+M07_SF_PREV]
    "D8 25 04 FD DB 00 "                    # fsub dword ptr ds:m07_slide_t0
    "E8 04 FD FF FF "                       # call .Lsway_curve   # F(tau_prev)
    "D8 2D 50 FD DB 00 "                    # fsubr dword ptr ds:m07_sway_tmp   # F(tau) - F(tau_prev)
    "D8 0D 4C FD DB 00 "                    # fmul dword ptr ds:m07_sway_k   # step along t
    "D9 05 E0 9F DC 00 "                    # fld dword ptr ds:M07_LAT
    "D8 8F 44 01 00 00 "                    # fmul dword ptr [edi+M07_SF_DZ]
    "D9 C0 "                                # fld st(0)
    "D9 E1 "                                # fabs
    "D8 1D C4 90 DC 00 "                    # fcomp dword ptr ds:M07_SWAY_EPS
    "DF E0 "                                # fnstsw ax
    "F6 C4 41 "                             # test ah, 0x41   # LAT * dz <= EPS
    "75 21 "                                # jnz 3f
    "D9 1D 50 FD DB 00 "                    # fstp dword ptr ds:m07_sway_tmp
    "D8 35 50 FD DB 00 "                    # fdiv dword ptr ds:m07_sway_tmp   # s = step / (LAT * dz)
    "D9 57 50 "                             # fst dword ptr [edi+M07_SF_LATERAL]
    # m07_log_sws:
    "D9 E4 "                                # ftst
    "DF E0 "                                # fnstsw ax
    "DD D8 "                                # fstp st(0)
    "F6 C4 40 "                             # test ah, 0x40
    "75 0B "                                # jnz 4f
    "5A "                                   # pop edx
    "59 "                                   # pop ecx
    "E9 5A 04 00 00 "                       # jmp m07_frame_corner
    # 3:
    "DD D8 "                                # fstp st(0)
    "DD D8 "                                # fstp st(0)
    # 4:
    "D9 EE "                                # fldz
    "D9 5F 50 "                             # fstp dword ptr [edi+M07_SF_LATERAL]
    "5A "                                   # pop edx
    "59 "                                   # pop ecx
    "E9 DA 04 00 00 "                       # jmp m07_frame_no_lateral
)

M07_JUMP_GATE = bytes.fromhex(  # .m07_jump_gate at 0xDC9F18, source m07_wall_slide/jump_gate.s
    # hook 10 (call from m07_jump_call, the slide frame: edi = its frame), cdecl as PressedWithin
    # (obj, &out, pad, bit, seconds): during the entry phases out = 0, else PressedWithin itself
    # m07_jump_gate:
    "8B 0D 48 FD DB 00 "                    # mov ecx, dword ptr ds:m07_sway_t0
    "D9 47 4C "                             # fld dword ptr [edi+M07_SF_NOW]
    "D8 25 04 FD DB 00 "                    # fsub dword ptr ds:m07_slide_t0
    "D9 E4 "                                # ftst
    "DF E0 "                                # fnstsw ax
    "F6 C4 01 "                             # test ah, 0x01
    "75 4A "                                # jnz 8f   # tau < 0: time went back, vanilla
    "3B 0D 04 FD DB 00 "                    # cmp ecx, dword ptr ds:m07_slide_t0
    "74 0F "                                # je 2f
    "D8 1D A0 90 DC 00 "                    # fcomp dword ptr ds:M07_ADOPT_WINDOW   # no record yet:
                                            #   m07_entry_anim adopts it while tau < HWIN
    "DF E0 "                                # fnstsw ax
    "F6 C4 01 "                             # test ah, 0x01
    "75 2A "                                # jnz 7f
    "EB 35 "                                # jmp 6f
    # 2:
    "D8 1D C0 90 DC 00 "                    # fcomp dword ptr ds:M07_ENTRY_END
    "DF E0 "                                # fnstsw ax
    "F6 C4 01 "                             # test ah, 0x01   # tau >= AEND: phases over
    "74 28 "                                # jz 6f
    "B8 01 00 00 00 "                       # mov eax, 1   # entry phases: 1 (sway sets), 2 (head-on set)
    "83 3D 60 FD DB 00 02 "                 # cmp dword ptr ds:m07_anim_set, 2
    "75 05 "                                # jne 3f
    "B8 02 00 00 00 "                       # mov eax, 2
    # 3:
    "39 05 58 FD DB 00 "                    # cmp dword ptr ds:m07_sway_phase, eax
    "73 0D "                                # jae 6f
    # 7:
    "8B 44 24 08 "                          # mov eax, [esp+8]
    "C7 00 00 00 00 00 "                    # mov dword ptr [eax], 0
    # m07_log_jgate:
    "C3 "                                   # ret
    # 8:
    "DD D8 "                                # fstp st(0)
    # 6:
    "FF 74 24 14 "                          # push dword ptr [esp+20]   # seconds
    "FF 74 24 14 "                          # push dword ptr [esp+20]   # bit
    "FF 74 24 14 "                          # push dword ptr [esp+20]   # pad
    "FF 74 24 14 "                          # push dword ptr [esp+20]   # &out
    "FF 74 24 14 "                          # push dword ptr [esp+20]   # obj
    "E8 2B B1 93 FF "                       # call FN_PRESSED_WITHIN
    "83 C4 14 "                             # add esp, 20
    "8B 44 24 08 "                          # mov eax, [esp+8]
    "83 38 00 "                             # cmp dword ptr [eax], 0
    "74 08 "                                # je 1f
    "8B 47 4C "                             # mov eax, [edi+M07_SF_NOW]
    # m07_log_jrec:
    "A3 64 FD DB 00 "                       # mov dword ptr ds:m07_jumpoff_time, eax
    # 1:
    "C3 "                                   # ret
    # eax = animation id; ZF=1 if its slot in the Prince's table is empty or out of range
)

M07_ANIM_TABLE = bytes.fromhex(  # .m07_anim_table at 0xDC9FAA, source m07_wall_slide/anim_table.s
    # (as .Lhas_anim in slide.s). anim = [[obj+0x14]], table = [anim+0x30]
    # m07_has_anim:
    "8B 4B 14 "                             # mov ecx, [ebx+0x14]
    "8B 09 "                                # mov ecx, [ecx]
    "8B 49 30 "                             # mov ecx, [ecx+0x30]
    "0F B7 11 "                             # movzx edx, word ptr [ecx]
    "39 D0 "                                # cmp eax, edx
    "73 06 "                                # jae 1f
    "83 7C 81 08 00 "                       # cmp dword ptr [ecx+eax*4+8], 0
    "C3 "                                   # ret
    # 1:
    "31 C0 "                                # xor eax, eax
    "C3 "                                   # ret
    # m07_mods_end:
)

M07_SLIDE_TUNABLES = bytes.fromhex(  # .m07_slide_tunables at 0xDC9FD0, source m07_wall_slide/slide_tunables.s
    # ---- tunables (read-only; stage 3 tunes these in place) ----
    "CD CC 4C 3E "                          # M07_HOLD: .float 0.2   # C held at least this long (s) to start
    "00 00 10 40 "                          # M07_V0: .float 2.25   # descent speed at the start (units/s)
    "00 00 40 40 "                          # M07_ACC: .float 3.0   # descent acceleration (units/s^2)
    "00 00 A0 40 "                          # M07_VMAX: .float 5.0   # descent speed cap (units/s)
    "00 00 40 3F "                          # M07_LAT: .float 0.75   # sideways speed at full stick, as a
                                            #   fraction of the descent speed
    "00 00 00 3F "                          # M07_FRONT_COS: .float 0.5   # wall check: |ref . n| above this
                                            #   (cos 60 deg); 0x49FA30 minimum
    "CD CC CC 3D "                          # M07_GRACE: .float 0.1   # contact may drop out this long (s)
                                            #   before he falls
    "00 00 80 3E "                          # M07_STALE: .float 0.25   # slide state older than this (s) is
                                            #   ignored
    "00 00 80 3F "                          # M07_OUT: .float 1.0   # outward speed when he lets go
    "66 66 E6 3E "                          # M07_CORNER_LOOK: .float 0.45   # corner probe: sideways offset
    "00 00 80 3F "                          # M07_CORNER_REACH: .float 1.0   # corner probe: length into the
                                            #   wall
    "00 00 80 3F "                          # M07_CORNER_Z: .float 1.0   # corner probe: height above the
                                            #   origin
    "00 00 80 3E "                          # M07_STICK_MIN: .float 0.25   # minimum stick magnitude
    "00 00 00 3F "                          # M07_JUMP_SIDE_MIN: .float 0.5   # V jump: minimum sideways share
                                            #   of the stick
    "F3 04 35 3F "                          # M07_COS45: .float 0.70710678
    "CD CC 4C 3E "                          # M07_JUMP_WINDOW: .float 0.2   # jump press window (s), as the
                                            #   curtain
    "00 00 00 3F "                          # M07_FLOOR_RAY_Z: .float 0.5   # floor ray: start height above
                                            #   the feet
    "CD CC CC 3E "                          # M07_SIDE_CLEARANCE: .float 0.4   # sideways ray: clearance
                                            #   beyond this frame's step
    "00 00 00 3F "                          # M07_HALF: .float 0.5
    "6C 03 00 00 "                          # M07_ANIM_SLIDE: .long 0x36C   # slide animation (curtain loop)
    "6D 03 00 00 "                          # M07_ANIM_LET_GO: .long 0x36D   # animation when he lets go
                                            #   (curtain let-go)
    "79 03 00 00 "                          # M07_ANIM_JUMP: .long 0x379   # jump-off animation (curtain)
    "78 03 00 00 "                          # M07_ANIM_JUMP_AIR:.long 0x378   # animation the airborne handler
                                            #   sets after the jump-off
    "69 03 00 00 "                          # M07_KEEP_FIRST: .long 0x369   # first curtain animation kept in
                                            #   the table
    "11 00 00 00 "                          # M07_KEEP_COUNT: .long 17   # 0x369..0x379
)

M07_SLIDE = bytes.fromhex(  # .m07_slide at 0xDCA040, source m07_wall_slide/slide.s
    # ---- entry points ----
    # m07_contact:
    "60 "                                   # pusha
    "BD 01 00 00 00 "                       # mov ebp, 1
    "EB 03 "                                # jmp m07_main
    # m07_no_contact:
    "60 "                                   # pusha
    "31 ED "                                # xor ebp, ebp
    # m07_main:
    "81 EC 60 01 00 00 "                    # sub esp, M07_SF_SIZE
    "89 E7 "                                # mov edi, esp
    "8B 1D 48 4A D3 00 "                    # mov ebx, dword ptr ds:CURRENT_OBJ
    "8B 35 40 4A D3 00 "                    # mov esi, dword ptr ds:CURRENT_INST
    "8B 76 48 "                             # mov esi, dword ptr [esi+0x48]
    "D9 05 74 09 94 00 "                    # fld dword ptr ds:CLOCK
    "D8 25 18 33 CD 00 "                    # fsub dword ptr ds:CLOCK_BASE
    "D9 5F 4C "                             # fstp dword ptr [edi+M07_SF_NOW]
    "31 C0 "                                # xor eax, eax
    "89 47 30 "                             # mov [edi+M07_SF_UP], eax
    "89 47 34 "                             # mov [edi+M07_SF_UP+4], eax
    "C7 47 38 00 00 80 3F "                 # mov dword ptr [edi+M07_SF_UP+8], 0x3F800000
    "89 47 78 "                             # mov [edi+M07_SF_ZERO], eax
    "89 47 7C "                             # mov [edi+M07_SF_ZERO+4], eax
    "89 87 80 00 00 00 "                    # mov [edi+M07_SF_ZERO+8], eax
    "39 35 00 FD DB 00 "                    # cmp dword ptr ds:m07_slide_vars, esi
    "75 24 "                                # jne .Lnotsliding
    "D9 47 4C "                             # fld dword ptr [edi+M07_SF_NOW]
    "D8 25 08 FD DB 00 "                    # fsub dword ptr ds:m07_slide_last
    "D8 1D EC 9F DC 00 "                    # fcomp dword ptr ds:M07_STALE
    "DF E0 "                                # fnstsw ax
    "F6 C4 41 "                             # test ah, 0x41   # now - tlast <= stale
    "0F 85 FF 00 00 00 "                    # jnz .Lsliding
    "C7 05 00 FD DB 00 00 00 00 00 "        # mov dword ptr ds:m07_slide_vars, 0
    # ---- not sliding: entry check ----
    # m07_entry:
    # .Lnotsliding:
    "85 ED "                                # test ebp, ebp
    "0F 84 B4 03 00 00 "                    # jz .Lvanilla_nocontact
    "E8 90 05 00 00 "                       # call .Lc_down
    "0F 84 B5 03 00 00 "                    # jz .Lvanilla_contact
    "D9 47 4C "                             # fld dword ptr [edi+M07_SF_NOW]
    "D8 A6 14 07 00 00 "                    # fsub dword ptr [esi+0x714]   # press time of pad bit 1 (C)
    "D8 1D D0 9F DC 00 "                    # fcomp dword ptr ds:M07_HOLD
    "DF E0 "                                # fnstsw ax
    "F6 C4 01 "                             # test ah, 0x01   # held < HOLD
    "0F 85 9B 03 00 00 "                    # jnz .Lvanilla_contact
    # cooldown: no new slide within GRACE of the last slide frame (else a land exit just above
    # the floor restarts the slide before vanilla lands him). Unsigned compare of the float bits:
    # a negative difference (game time reset) is huge as unsigned, so it never blocks.
    "D9 47 4C "                             # fld dword ptr [edi+M07_SF_NOW]
    "D8 25 08 FD DB 00 "                    # fsub dword ptr ds:m07_slide_last
    "D9 5F 24 "                             # fstp dword ptr [edi+M07_SF_TMP]
    "8B 47 24 "                             # mov eax, [edi+M07_SF_TMP]
    "3B 05 E8 9F DC 00 "                    # cmp eax, dword ptr ds:M07_GRACE
    "0F 82 80 03 00 00 "                    # jb .Lvanilla_contact
    # m07_entry_anim_call:
    "E8 4A 06 00 00 "                       # call .Lanims_ok   # the curtain animations must be in the table
    "0F 84 75 03 00 00 "                    # jz .Lvanilla_contact
    "8D 47 24 "                             # lea eax, [edi+M07_SF_TMP]
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 3B 67 6C FF "                       # call FN_GET_FACING
    "83 C4 08 "                             # add esp, 8
    "E8 52 05 00 00 "                       # call .Lget_normal
    "0F 84 5D 03 00 00 "                    # jz .Lvanilla_contact
    # orient n out of the wall: sum over contact points of (pos - p) . n must be > 0
    "8D 47 54 "                             # lea eax, [edi+M07_SF_POS]
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 B3 4B 6C FF "                       # call FN_GET_POSITION
    "83 C4 08 "                             # add esp, 8
    "68 80 00 00 00 "                       # push 0x80
    "6A 0F "                                # push 15
    "8D 87 90 00 00 00 "                    # lea eax, [edi+M07_SF_POINTS]
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 8C 5B 6D FF "                       # call FN_CONTACT_POINTS
    "83 C4 10 "                             # add esp, 16
    "89 C1 "                                # mov ecx, eax
    "8D 97 90 00 00 00 "                    # lea edx, [edi+M07_SF_POINTS]
    "D9 EE "                                # fldz
    # .Lsum_points:
    "85 C9 "                                # test ecx, ecx
    "7E 1A "                                # jle .Lsum_done
    "D9 47 54 "                             # fld dword ptr [edi+M07_SF_POS]
    "D8 22 "                                # fsub dword ptr [edx]
    "D8 0F "                                # fmul dword ptr [edi+M07_SF_NORMAL]
    "D9 47 58 "                             # fld dword ptr [edi+M07_SF_POS+4]
    "D8 62 04 "                             # fsub dword ptr [edx+4]
    "D8 4F 04 "                             # fmul dword ptr [edi+M07_SF_NORMAL+4]
    "DE C1 "                                # faddp st(1), st
    "DE C1 "                                # faddp st(1), st
    "83 C2 0C "                             # add edx, 12
    "49 "                                   # dec ecx
    "EB E2 "                                # jmp .Lsum_points
    # .Lsum_done:
    "D9 E4 "                                # ftst
    "DF E0 "                                # fnstsw ax
    "DD D8 "                                # fstp st(0)
    "F6 C4 01 "                             # test ah, 0x01   # sum < 0 -> flip
    "74 05 "                                # jz 1f
    "E8 36 05 00 00 "                       # call .Lneg_n
    # 1:
    # m07_log_entry:
    "89 35 00 FD DB 00 "                    # mov dword ptr ds:m07_slide_vars, esi
    "8B 47 4C "                             # mov eax, [edi+M07_SF_NOW]
    "A3 04 FD DB 00 "                       # mov dword ptr ds:m07_slide_t0, eax
    "A3 08 FD DB 00 "                       # mov dword ptr ds:m07_slide_last, eax   # first step: no movement
    "A3 0C FD DB 00 "                       # mov dword ptr ds:m07_slide_contact, eax
    "31 C0 "                                # xor eax, eax
    "89 86 2C 03 00 00 "                    # mov [esi+0x32c], eax   # no air re-orientation toward the old
                                            #   jump direction
    "89 86 30 03 00 00 "                    # mov [esi+0x330], eax
    "89 86 34 03 00 00 "                    # mov [esi+0x334], eax
    "EB 53 "                                # jmp .Lstore_n
    # ---- sliding ----
    # m07_sliding:
    # .Lsliding:
    "85 ED "                                # test ebp, ebp
    "74 6A "                                # jz .Lno_contact
    # reference = facing = -m07_slide_normal
    "D9 05 10 FD DB 00 "                    # fld dword ptr ds:m07_slide_normal
    "D9 E0 "                                # fchs
    "D9 5F 24 "                             # fstp dword ptr [edi+M07_SF_TMP]
    "D9 05 14 FD DB 00 "                    # fld dword ptr ds:m07_slide_normal+4
    "D9 E0 "                                # fchs
    "D9 5F 28 "                             # fstp dword ptr [edi+M07_SF_TMP+4]
    "C7 47 2C 00 00 00 00 "                 # mov dword ptr [edi+M07_SF_TMP+8], 0
    "E8 9C 04 00 00 "                       # call .Lget_normal
    "74 44 "                                # jz .Lcontact_unusable
    # keep the orientation of the previous frame
    "D9 07 "                                # fld dword ptr [edi+M07_SF_NORMAL]
    "D8 0D 10 FD DB 00 "                    # fmul dword ptr ds:m07_slide_normal
    "D9 47 04 "                             # fld dword ptr [edi+M07_SF_NORMAL+4]
    "D8 0D 14 FD DB 00 "                    # fmul dword ptr ds:m07_slide_normal+4
    "DE C1 "                                # faddp st(1), st
    "D9 E4 "                                # ftst
    "DF E0 "                                # fnstsw ax
    "DD D8 "                                # fstp st(0)
    "F6 C4 01 "                             # test ah, 0x01
    "74 05 "                                # jz 1f
    "E8 BD 04 00 00 "                       # call .Lneg_n
    # 1:
    "8B 47 4C "                             # mov eax, [edi+M07_SF_NOW]
    "A3 0C FD DB 00 "                       # mov dword ptr ds:m07_slide_contact, eax
    # .Lstore_n:
    "8B 07 "                                # mov eax, [edi+M07_SF_NORMAL]
    "A3 10 FD DB 00 "                       # mov dword ptr ds:m07_slide_normal, eax
    "8B 47 04 "                             # mov eax, [edi+M07_SF_NORMAL+4]
    "A3 14 FD DB 00 "                       # mov dword ptr ds:m07_slide_normal+4, eax
    "8B 47 08 "                             # mov eax, [edi+M07_SF_NORMAL+8]
    "A3 18 FD DB 00 "                       # mov dword ptr ds:m07_slide_normal+8, eax
    "EB 33 "                                # jmp .Lchecks
    # .Lcontact_unusable:
    "31 ED "                                # xor ebp, ebp   # unusable contact counts as none
    # .Lno_contact:
    "D9 47 4C "                             # fld dword ptr [edi+M07_SF_NOW]
    "D8 25 0C FD DB 00 "                    # fsub dword ptr ds:m07_slide_contact
    "D8 1D E8 9F DC 00 "                    # fcomp dword ptr ds:M07_GRACE
    "DF E0 "                                # fnstsw ax
    "F6 C4 41 "                             # test ah, 0x41   # now - tcont <= grace
    "0F 84 69 02 00 00 "                    # jz .Lfall_exit
    "A1 10 FD DB 00 "                       # mov eax, dword ptr ds:m07_slide_normal
    "89 07 "                                # mov [edi+M07_SF_NORMAL], eax
    "A1 14 FD DB 00 "                       # mov eax, dword ptr ds:m07_slide_normal+4
    "89 47 04 "                             # mov [edi+M07_SF_NORMAL+4], eax
    "A1 18 FD DB 00 "                       # mov eax, dword ptr ds:m07_slide_normal+8
    "89 47 08 "                             # mov [edi+M07_SF_NORMAL+8], eax
    # .Lchecks:
    "E8 FE 04 00 00 "                       # call .Lanims_ok
    "0F 84 47 02 00 00 "                    # jz .Lfall_exit
    "E8 F9 03 00 00 "                       # call .Lc_down
    "0F 84 3C 02 00 00 "                    # jz .Lfall_exit
    "FF 35 0C A0 DC 00 "                    # push dword ptr ds:M07_JUMP_WINDOW
    "6A 00 "                                # push 0
    "FF B6 B8 10 00 00 "                    # push dword ptr [esi+0x10b8]
    "8D 47 48 "                             # lea eax, [edi+M07_SF_OUT]
    "50 "                                   # push eax
    "53 "                                   # push ebx
    # m07_jump_call:
    "E8 46 AE 93 FF "                       # call FN_PRESSED_WITHIN
    "83 C4 14 "                             # add esp, 20
    "83 7F 48 00 "                          # cmp dword ptr [edi+M07_SF_OUT], 0
    "0F 85 AC 02 00 00 "                    # jne .Ljump_exit
    # m07_frame:
    # ---- slide frame ----
    "A1 08 FD DB 00 "                       # mov eax, dword ptr ds:m07_slide_last
    "89 87 50 01 00 00 "                    # mov [edi+M07_SF_PREV], eax
    "8B 47 4C "                             # mov eax, [edi+M07_SF_NOW]
    "A3 08 FD DB 00 "                       # mov dword ptr ds:m07_slide_last, eax
    "D9 47 4C "                             # fld dword ptr [edi+M07_SF_NOW]
    "D8 A7 50 01 00 00 "                    # fsub dword ptr [edi+M07_SF_PREV]
    "D9 9F 48 01 00 00 "                    # fstp dword ptr [edi+M07_SF_DT]
    # descent this frame dz = d(now - T0) - d(prev - T0), exact at any frame rate;
    # computed first: the sideways step is LAT*dz
    "D9 47 4C "                             # fld dword ptr [edi+M07_SF_NOW]
    "D8 25 04 FD DB 00 "                    # fsub dword ptr ds:m07_slide_t0
    "E8 22 05 00 00 "                       # call .Ldistance
    "D9 9F 44 01 00 00 "                    # fstp dword ptr [edi+M07_SF_DZ]
    "D9 87 50 01 00 00 "                    # fld dword ptr [edi+M07_SF_PREV]
    "D8 25 04 FD DB 00 "                    # fsub dword ptr ds:m07_slide_t0
    "E8 0B 05 00 00 "                       # call .Ldistance
    "D8 AF 44 01 00 00 "                    # fsubr dword ptr [edi+M07_SF_DZ]
    "D9 9F 44 01 00 00 "                    # fstp dword ptr [edi+M07_SF_DZ]
    # m07_frame_anim_block:
    "53 "                                   # push ebx
    "E8 B0 D8 6C FF "                       # call FN_CURRENT_ANIM
    "83 C4 04 "                             # add esp, 4
    "3B 05 1C A0 DC 00 "                    # cmp eax, dword ptr ds:M07_ANIM_SLIDE
    "74 0F "                                # je 1f
    "FF 35 1C A0 DC 00 "                    # push dword ptr ds:M07_ANIM_SLIDE
    "53 "                                   # push ebx
    "E8 59 52 84 FF "                       # call FN_SET_ANIM
    "83 C4 08 "                             # add esp, 8
    # 1:
    # m07_frame_face_call:
    "E8 DA 03 00 00 "                       # call .Lface_wall   # facing = -n, M07_SF_TMP = -n
    "E8 FD 03 00 00 "                       # call .Lfall_reset   # also M07_SF_POS = position
    "C7 86 CC 04 00 00 01 00 00 00 "        # mov dword ptr [esi+0x4cc], 1
    "E8 B1 03 00 00 "                       # call .Ltangent
    # lateral factor s = (stick_world . t) * min(mag, 1); 0 if the stick is idle or no contact
    # m07_frame_stick_zero:
    "D9 EE "                                # fldz
    "D9 5F 50 "                             # fstp dword ptr [edi+M07_SF_LATERAL]
    # m07_frame_stick:
    "85 ED "                                # test ebp, ebp
    "0F 84 D2 00 00 00 "                    # jz .Lnolat
    "D9 86 78 0E 00 00 "                    # fld dword ptr [esi+0xe78]
    "D8 1D 00 A0 DC 00 "                    # fcomp dword ptr ds:M07_STICK_MIN
    "DF E0 "                                # fnstsw ax
    "F6 C4 01 "                             # test ah, 0x01
    "0F 85 BB 00 00 00 "                    # jnz .Lnolat
    "E8 DC 03 00 00 "                       # call .Lstick_side   # st0 = stick_world . t
    "D9 86 78 0E 00 00 "                    # fld dword ptr [esi+0xe78]
    "D9 E8 "                                # fld1
    "DB F1 "                                # fcomi st, st(1)
    "72 04 "                                # jb 1f
    "DD D8 "                                # fstp st(0)   # mag <= 1: keep mag
    "EB 02 "                                # jmp 2f
    # 1:
    "DD D9 "                                # fstp st(1)   # mag > 1: keep 1
    # 2:
    "DE C9 "                                # fmulp st(1), st
    "D9 57 50 "                             # fst dword ptr [edi+M07_SF_LATERAL]
    "D9 E4 "                                # ftst
    "DF E0 "                                # fnstsw ax
    "DD D8 "                                # fstp st(0)
    "F6 C4 40 "                             # test ah, 0x40   # s == 0
    "0F 85 90 00 00 00 "                    # jnz .Lnolat
    # m07_frame_corner:
    # corner probe: from = pos + (0,0,PZ) + t*sign(s)*LOOK, delta = -n*REACH;
    # no hit or a non-runnable hit -> the wall ends sideways
    "D9 05 F4 9F DC 00 "                    # fld dword ptr ds:M07_CORNER_LOOK
    "E8 43 04 00 00 "                       # call .Lside_from   # M07_SF_RAY_FROM = pos + (0,0,PZ) +
                                            #   t*sign(s)*LOOK
    "D9 05 F8 9F DC 00 "                    # fld dword ptr ds:M07_CORNER_REACH
    "D9 E0 "                                # fchs
    "D9 C0 "                                # fld st(0)
    "D8 0F "                                # fmul dword ptr [edi+M07_SF_NORMAL]
    "D9 5F 6C "                             # fstp dword ptr [edi+M07_SF_RAY_DELTA]
    "D8 4F 04 "                             # fmul dword ptr [edi+M07_SF_NORMAL+4]
    "D9 5F 70 "                             # fstp dword ptr [edi+M07_SF_RAY_DELTA+4]
    "C7 47 74 00 00 00 00 "                 # mov dword ptr [edi+M07_SF_RAY_DELTA+8], 0
    "E8 08 04 00 00 "                       # call .Lcast_ray
    "85 C0 "                                # test eax, eax
    "74 59 "                                # jz .Lcorner
    "68 FF FF 00 00 "                       # push 0xFFFF
    "53 "                                   # push ebx
    "E8 33 5D 6D FF "                       # call FN_SURFACE_FLAGS
    "83 C4 08 "                             # add esp, 8
    "A9 00 00 03 00 "                       # test eax, SURFACE_NO_RUN_MASK
    "75 44 "                                # jnz .Lcorner
    # sideways clearance: from = pos + (0,0,PZ), delta = t*sign(s)*(BODY + |s|*LAT*dz);
    # a hit (a wall across the path) stops the sideways movement
    "D9 EE "                                # fldz
    "E8 02 04 00 00 "                       # call .Lside_from   # M07_SF_RAY_FROM = pos + (0,0,PZ)
    "D9 47 50 "                             # fld dword ptr [edi+M07_SF_LATERAL]
    "D9 E1 "                                # fabs
    "D8 0D E0 9F DC 00 "                    # fmul dword ptr ds:M07_LAT
    "D8 8F 44 01 00 00 "                    # fmul dword ptr [edi+M07_SF_DZ]
    "D8 05 14 A0 DC 00 "                    # fadd dword ptr ds:M07_SIDE_CLEARANCE
    "F6 47 53 80 "                          # test byte ptr [edi+M07_SF_LATERAL+3], 0x80
    "74 02 "                                # jz 1f
    "D9 E0 "                                # fchs
    # 1:
    "D9 C0 "                                # fld st(0)
    "D8 4F 0C "                             # fmul dword ptr [edi+M07_SF_TANGENT]
    "D9 5F 6C "                             # fstp dword ptr [edi+M07_SF_RAY_DELTA]
    "D8 4F 10 "                             # fmul dword ptr [edi+M07_SF_TANGENT+4]
    "D9 5F 70 "                             # fstp dword ptr [edi+M07_SF_RAY_DELTA+4]
    "C7 47 74 00 00 00 00 "                 # mov dword ptr [edi+M07_SF_RAY_DELTA+8], 0
    "E8 AF 03 00 00 "                       # call .Lcast_ray
    "85 C0 "                                # test eax, eax
    "74 07 "                                # jz .Lnolat
    # m07_log_corner:
    # .Lcorner:
    "C7 47 50 00 00 00 00 "                 # mov dword ptr [edi+M07_SF_LATERAL], 0
    # .Lnolat:
    # m07_frame_no_lateral:
    # floor: from = pos + (0,0,FZ), delta = (0,0,-(FZ+dz)); a hit -> he lands (land exit)
    "8B 47 54 "                             # mov eax, [edi+M07_SF_POS]
    "89 47 60 "                             # mov [edi+M07_SF_RAY_FROM], eax
    "8B 47 58 "                             # mov eax, [edi+M07_SF_POS+4]
    "89 47 64 "                             # mov [edi+M07_SF_RAY_FROM+4], eax
    "D9 47 5C "                             # fld dword ptr [edi+M07_SF_POS+8]
    "D8 05 10 A0 DC 00 "                    # fadd dword ptr ds:M07_FLOOR_RAY_Z
    "D9 5F 68 "                             # fstp dword ptr [edi+M07_SF_RAY_FROM+8]
    "31 C0 "                                # xor eax, eax
    "89 47 6C "                             # mov [edi+M07_SF_RAY_DELTA], eax
    "89 47 70 "                             # mov [edi+M07_SF_RAY_DELTA+4], eax
    "D9 05 10 A0 DC 00 "                    # fld dword ptr ds:M07_FLOOR_RAY_Z
    "D8 87 44 01 00 00 "                    # fadd dword ptr [edi+M07_SF_DZ]
    "D9 E0 "                                # fchs
    "D9 5F 74 "                             # fstp dword ptr [edi+M07_SF_RAY_DELTA+8]
    "E8 6E 03 00 00 "                       # call .Lcast_ray
    # m07_log_slg:
    "85 C0 "                                # test eax, eax
    "75 66 "                                # jnz .Lland_exit
    # pos += t*(s*LAT*dz) - (0,0,dz)
    "D9 47 50 "                             # fld dword ptr [edi+M07_SF_LATERAL]
    "D8 0D E0 9F DC 00 "                    # fmul dword ptr ds:M07_LAT
    "D8 8F 44 01 00 00 "                    # fmul dword ptr [edi+M07_SF_DZ]
    "D9 C0 "                                # fld st(0)
    "D8 4F 0C "                             # fmul dword ptr [edi+M07_SF_TANGENT]
    "D8 47 54 "                             # fadd dword ptr [edi+M07_SF_POS]
    "D9 5F 54 "                             # fstp dword ptr [edi+M07_SF_POS]
    "D8 4F 10 "                             # fmul dword ptr [edi+M07_SF_TANGENT+4]
    "D8 47 58 "                             # fadd dword ptr [edi+M07_SF_POS+4]
    "D9 5F 58 "                             # fstp dword ptr [edi+M07_SF_POS+4]
    "D9 47 5C "                             # fld dword ptr [edi+M07_SF_POS+8]
    "D8 A7 44 01 00 00 "                    # fsub dword ptr [edi+M07_SF_DZ]
    "D9 5F 5C "                             # fstp dword ptr [edi+M07_SF_POS+8]
    "8D 47 54 "                             # lea eax, [edi+M07_SF_POS]
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 4B 4B 6C FF "                       # call FN_SET_POSITION
    "83 C4 08 "                             # add esp, 8
    # m07_exits:
    # .Ldone:
    "81 C4 60 01 00 00 "                    # add esp, M07_SF_SIZE
    "61 "                                   # popa
    "E9 DB 39 88 FF "                       # jmp AIR_HANDLER_FRAME_END
    # ---- exits ----
    # .Lvanilla_nocontact:
    "81 C4 60 01 00 00 "                    # add esp, M07_SF_SIZE
    "61 "                                   # popa
    "E9 17 33 88 FF "                       # jmp AIR_NO_CONTACT
    # m07_log_reject:
    # .Lvanilla_contact:
    "81 C4 60 01 00 00 "                    # add esp, M07_SF_SIZE
    "61 "                                   # popa
    "60 "                                   # pusha   # the 3 instructions replaced at m02_contact
    "83 EC 2C "                             # sub esp, 0x2c
    "89 E3 "                                # mov ebx, esp
    "E9 AF FC AE FF "                       # jmp m02_wallrun_attempt
    # m07_fall:
    # Let go (C released, or the wall ended): outward speed OUT, the current descent speed, fall
    # animation. Land (floor ray hit): the same without the outward speed.
    # m07_log_land:
    # .Lland_exit:
    "C7 87 4C 01 00 00 00 00 00 00 "        # mov dword ptr [edi+M07_SF_EXIT_K], 0
    "EB 0B "                                # jmp 1f
    # m07_log_fall:
    # .Lfall_exit:
    "A1 F0 9F DC 00 "                       # mov eax, dword ptr ds:M07_OUT
    "89 87 4C 01 00 00 "                    # mov [edi+M07_SF_EXIT_K], eax
    # 1:
    "C7 05 00 FD DB 00 00 00 00 00 "        # mov dword ptr ds:m07_slide_vars, 0
    "D9 05 10 FD DB 00 "                    # fld dword ptr ds:m07_slide_normal
    "D8 8F 4C 01 00 00 "                    # fmul dword ptr [edi+M07_SF_EXIT_K]
    "D9 5F 18 "                             # fstp dword ptr [edi+M07_SF_VELOCITY]
    "D9 05 14 FD DB 00 "                    # fld dword ptr ds:m07_slide_normal+4
    "D8 8F 4C 01 00 00 "                    # fmul dword ptr [edi+M07_SF_EXIT_K]
    "D9 5F 1C "                             # fstp dword ptr [edi+M07_SF_VELOCITY+4]
    # vz = -(V0 + ACC*tau_c) = -min(V0 + ACC*(now - T0), VMAX)
    "D9 47 4C "                             # fld dword ptr [edi+M07_SF_NOW]
    "D8 25 04 FD DB 00 "                    # fsub dword ptr ds:m07_slide_t0
    "E8 FA 02 00 00 "                       # call .Ldistance   # leaves tau_c in M07_SF_DIST_TMP
    "DD D8 "                                # fstp st(0)
    "D9 87 54 01 00 00 "                    # fld dword ptr [edi+M07_SF_DIST_TMP]
    "D8 0D D8 9F DC 00 "                    # fmul dword ptr ds:M07_ACC
    "D8 05 D4 9F DC 00 "                    # fadd dword ptr ds:M07_V0
    "D9 E0 "                                # fchs
    "D9 5F 20 "                             # fstp dword ptr [edi+M07_SF_VELOCITY+8]
    # as the curtain's bottom exit (0x594A41..0x594A82): start-fall with the let-go animation
    # (mode 4, dyn flag 0x40000000 cleared, state 0x412), then the velocity
    "31 C0 "                                # xor eax, eax
    "50 "                                   # push eax
    "6A 0A "                                # push 10
    "6A 50 "                                # push 0x50
    "FF 35 20 A0 DC 00 "                    # push dword ptr ds:M07_ANIM_LET_GO
    "50 "                                   # push eax
    "50 "                                   # push eax
    "6A 2C "                                # push 0x2C
    "53 "                                   # push ebx
    "E8 51 11 82 FF "                       # call FN_START_FALL
    "83 C4 20 "                             # add esp, 0x20
    "8D 47 18 "                             # lea eax, [edi+M07_SF_VELOCITY]
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 44 44 84 FF "                       # call FN_SET_VELOCITY
    "83 C4 08 "                             # add esp, 8
    "E8 DD 01 00 00 "                       # call .Lfall_reset
    "C7 86 CC 04 00 00 01 00 00 00 "        # mov dword ptr [esi+0x4cc], 1
    "E9 35 FF FF FF "                       # jmp .Ldone
    # m07_jump:
    # Space: the curtain jump-off sequence (0x5947xx). V + side: 45 degrees toward the stick side.
    # .Ljump_exit:
    "C7 05 00 FD DB 00 00 00 00 00 "        # mov dword ptr ds:m07_slide_vars, 0
    "E8 82 01 00 00 "                       # call .Ltangent
    # M07_SF_TMP = facing for the jump = -n (the airborne handler flips it and jumps along +n)
    "D9 07 "                                # fld dword ptr [edi+M07_SF_NORMAL]
    "D9 E0 "                                # fchs
    "D9 5F 24 "                             # fstp dword ptr [edi+M07_SF_TMP]
    "D9 47 04 "                             # fld dword ptr [edi+M07_SF_NORMAL+4]
    "D9 E0 "                                # fchs
    "D9 5F 28 "                             # fstp dword ptr [edi+M07_SF_TMP+4]
    "C7 47 2C 00 00 00 00 "                 # mov dword ptr [edi+M07_SF_TMP+8], 0
    # m07_jump_v_test:
    "F6 05 62 F0 93 00 01 "                 # test byte ptr ds:PAD_BITS_HIGH, 0x01
    "74 67 "                                # jz .Ljump_facing_set
    "D9 86 78 0E 00 00 "                    # fld dword ptr [esi+0xe78]
    "D8 1D 00 A0 DC 00 "                    # fcomp dword ptr ds:M07_STICK_MIN
    "DF E0 "                                # fnstsw ax
    "F6 C4 01 "                             # test ah, 0x01
    "75 54 "                                # jnz .Ljump_facing_set
    "E8 9F 01 00 00 "                       # call .Lstick_side   # st0 = stick_world . t (uses M07_SF_TMP =
                                            #   -n)
    "D9 C0 "                                # fld st(0)
    "D9 E1 "                                # fabs
    "D8 1D 04 A0 DC 00 "                    # fcomp dword ptr ds:M07_JUMP_SIDE_MIN
    "DF E0 "                                # fnstsw ax
    "F6 C4 01 "                             # test ah, 0x01
    "74 04 "                                # jz 1f
    "DD D8 "                                # fstp st(0)   # mostly forward/back: straight jump
    "EB 3A "                                # jmp .Ljump_facing_set
    # 1:
    # facing = -(n*C45 + t*sign(s)*C45)
    "D9 E4 "                                # ftst
    "DF E0 "                                # fnstsw ax
    "DD D8 "                                # fstp st(0)
    "D9 05 08 A0 DC 00 "                    # fld dword ptr ds:M07_COS45
    "F6 C4 01 "                             # test ah, 0x01
    "74 02 "                                # jz 2f
    "D9 E0 "                                # fchs   # st0 = sign(s)*C45
    # 2:
    "D9 C0 "                                # fld st(0)
    "D8 4F 0C "                             # fmul dword ptr [edi+M07_SF_TANGENT]
    "D9 07 "                                # fld dword ptr [edi+M07_SF_NORMAL]
    "D8 0D 08 A0 DC 00 "                    # fmul dword ptr ds:M07_COS45
    "DE C1 "                                # faddp st(1), st
    "D9 E0 "                                # fchs
    "D9 5F 24 "                             # fstp dword ptr [edi+M07_SF_TMP]
    "D8 4F 10 "                             # fmul dword ptr [edi+M07_SF_TANGENT+4]
    "D9 47 04 "                             # fld dword ptr [edi+M07_SF_NORMAL+4]
    "D8 0D 08 A0 DC 00 "                    # fmul dword ptr ds:M07_COS45
    "DE C1 "                                # faddp st(1), st
    "D9 E0 "                                # fchs
    "D9 5F 28 "                             # fstp dword ptr [edi+M07_SF_TMP+4]
    # .Ljump_facing_set:
    "8D 47 30 "                             # lea eax, [edi+M07_SF_UP]
    "50 "                                   # push eax
    "8D 47 24 "                             # lea eax, [edi+M07_SF_TMP]
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 CA 5C 6C FF "                       # call FN_SET_FACING
    "83 C4 0C "                             # add esp, 12
    "C7 86 88 09 00 00 00 00 00 00 "        # mov dword ptr [esi+0x988], 0
    "FF 35 24 A0 DC 00 "                    # push dword ptr ds:M07_ANIM_JUMP
    "53 "                                   # push ebx
    "E8 91 34 81 FF "                       # call FN_JUMP_ANIM
    "83 C4 08 "                             # add esp, 8
    "8D 47 54 "                             # lea eax, [edi+M07_SF_POS]
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 E4 46 6C FF "                       # call FN_GET_POSITION
    "83 C4 08 "                             # add esp, 8
    "8B 47 54 "                             # mov eax, [edi+M07_SF_POS]
    "89 86 DC 08 00 00 "                    # mov [esi+0x8dc], eax
    "8B 47 58 "                             # mov eax, [edi+M07_SF_POS+4]
    "89 86 E0 08 00 00 "                    # mov [esi+0x8e0], eax
    "8B 47 5C "                             # mov eax, [edi+M07_SF_POS+8]
    "89 86 E4 08 00 00 "                    # mov [esi+0x8e4], eax
    "89 86 04 02 00 00 "                    # mov [esi+0x204], eax
    "C7 86 CC 04 00 00 00 00 00 00 "        # mov dword ptr [esi+0x4cc], 0
    "6A 00 "                                # push 0
    "6A 13 "                                # push 0x13
    "53 "                                   # push ebx
    "E8 DC 38 6D FF "                       # call FN_49DF10
    "83 C4 0C "                             # add esp, 12
    "68 9A 99 19 3E "                       # push 0x3E19999A   # 0.15f
    "8D 47 78 "                             # lea eax, [edi+M07_SF_ZERO]
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 3A 0B 88 FF "                       # call FN_START_AIRBORNE
    "83 C4 0C "                             # add esp, 12
    "81 C4 60 01 00 00 "                    # add esp, M07_SF_SIZE
    "61 "                                   # popa
    "E9 EE 37 88 FF "                       # jmp AIR_HANDLER_SWITCHED
    # m07_helpers:
    # ---- helpers (called with one return address on the stack: locals at [esp+4+...]
    # are still addressed through edi) ----
    # ZF=1 if C (pad bit 1) is not down.
    # .Lc_down:
    "6A 01 "                                # push 1
    "FF B6 B8 10 00 00 "                    # push dword ptr [esi+0x10b8]
    "8D 47 48 "                             # lea eax, [edi+M07_SF_OUT]
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 E9 3D 95 FF "                       # call FN_IS_DOWN
    "83 C4 10 "                             # add esp, 16
    "83 7F 48 00 "                          # cmp dword ptr [edi+M07_SF_OUT], 0
    "C3 "                                   # ret
    # M07_SF_NORMAL = flattened contact normal of a runnable wall, using M07_SF_TMP as reference. ZF=1 if
    # none.
    # 0x49FA30 returns the first wall contact with |ref . n| > the minimum; M07_FRONT_COS = cos 60 deg, so
    # the wall must be within 60 degrees of the facing (entry) or of the current wall (sliding).
    # .Lget_normal:
    "8D 07 "                                # lea eax, [edi+M07_SF_NORMAL]
    "50 "                                   # push eax
    "FF 35 E4 9F DC 00 "                    # push dword ptr ds:M07_FRONT_COS
    "8D 47 24 "                             # lea eax, [edi+M07_SF_TMP]
    "50 "                                   # push eax
    "68 80 00 00 00 "                       # push 0x80
    "53 "                                   # push ebx
    "E8 A9 53 6D FF "                       # call FN_CONTACT_NORMAL
    "83 C4 14 "                             # add esp, 20
    "85 C0 "                                # test eax, eax
    "74 26 "                                # jz 9f
    "68 80 00 00 00 "                       # push 0x80
    "53 "                                   # push ebx
    "E8 37 5A 6D FF "                       # call FN_SURFACE_FLAGS
    "83 C4 08 "                             # add esp, 8
    "A9 00 00 03 00 "                       # test eax, SURFACE_NO_RUN_MASK
    "75 0F "                                # jnz 8f
    "8D 07 "                                # lea eax, [edi+M07_SF_NORMAL]
    "50 "                                   # push eax
    "E8 75 1F 6B FF "                       # call FN_FLATTEN_NORMALIZE
    "83 C4 04 "                             # add esp, 4
    "83 C8 01 "                             # or eax, 1   # ZF=0
    "C3 "                                   # ret
    # 8:
    "31 C0 "                                # xor eax, eax   # ZF=1
    # 9:
    "C3 "                                   # ret
    # .Lneg_n:
    "D9 07 "                                # fld dword ptr [edi+M07_SF_NORMAL]
    "D9 E0 "                                # fchs
    "D9 1F "                                # fstp dword ptr [edi+M07_SF_NORMAL]
    "D9 47 04 "                             # fld dword ptr [edi+M07_SF_NORMAL+4]
    "D9 E0 "                                # fchs
    "D9 5F 04 "                             # fstp dword ptr [edi+M07_SF_NORMAL+4]
    "C3 "                                   # ret
    # M07_SF_TANGENT = (-n.y, n.x, 0)
    # .Ltangent:
    "D9 47 04 "                             # fld dword ptr [edi+M07_SF_NORMAL+4]
    "D9 E0 "                                # fchs
    "D9 5F 0C "                             # fstp dword ptr [edi+M07_SF_TANGENT]
    "8B 07 "                                # mov eax, [edi+M07_SF_NORMAL]
    "89 47 10 "                             # mov [edi+M07_SF_TANGENT+4], eax
    "C7 47 14 00 00 00 00 "                 # mov dword ptr [edi+M07_SF_TANGENT+8], 0
    "C3 "                                   # ret
    # facing = M07_SF_TMP = -n
    # .Lface_wall:
    # m07_face_wall:
    "D9 07 "                                # fld dword ptr [edi+M07_SF_NORMAL]
    "D9 E0 "                                # fchs
    "D9 5F 24 "                             # fstp dword ptr [edi+M07_SF_TMP]
    "D9 47 04 "                             # fld dword ptr [edi+M07_SF_NORMAL+4]
    "D9 E0 "                                # fchs
    "D9 5F 28 "                             # fstp dword ptr [edi+M07_SF_TMP+4]
    "C7 47 2C 00 00 00 00 "                 # mov dword ptr [edi+M07_SF_TMP+8], 0
    "8D 47 30 "                             # lea eax, [edi+M07_SF_UP]
    "50 "                                   # push eax
    "8D 47 24 "                             # lea eax, [edi+M07_SF_TMP]
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 A3 5B 6C FF "                       # call FN_SET_FACING
    "83 C4 0C "                             # add esp, 12
    "C3 "                                   # ret
    # +0x204 (fall start height) = current z
    # .Lfall_reset:
    "8D 47 54 "                             # lea eax, [edi+M07_SF_POS]
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 D5 45 6C FF "                       # call FN_GET_POSITION
    "83 C4 08 "                             # add esp, 8
    "8B 47 5C "                             # mov eax, [edi+M07_SF_POS+8]
    "89 86 04 02 00 00 "                    # mov [esi+0x204], eax
    "C3 "                                   # ret
    # st0 = (stick direction in world space) . t; the stick direction is the facing M07_SF_TMP rotated
    # by -stick angle about up, exactly as the jump executor builds it (0x5DD736).
    # .Lstick_side:
    "D9 86 44 0A 00 00 "                    # fld dword ptr [esi+0xa44]
    "D9 E0 "                                # fchs
    "D9 9F 84 00 00 00 "                    # fstp dword ptr [edi+M07_SF_ANGLE]
    "8D 47 3C "                             # lea eax, [edi+M07_SF_STICK]
    "50 "                                   # push eax
    "FF B7 84 00 00 00 "                    # push dword ptr [edi+M07_SF_ANGLE]
    "8D 47 30 "                             # lea eax, [edi+M07_SF_UP]
    "50 "                                   # push eax
    "8D 47 24 "                             # lea eax, [edi+M07_SF_TMP]
    "50 "                                   # push eax
    "E8 93 39 6B FF "                       # call FN_ROTATE
    "83 C4 10 "                             # add esp, 16
    "D9 47 3C "                             # fld dword ptr [edi+M07_SF_STICK]
    "D8 4F 0C "                             # fmul dword ptr [edi+M07_SF_TANGENT]
    "D9 47 40 "                             # fld dword ptr [edi+M07_SF_STICK+4]
    "D8 4F 10 "                             # fmul dword ptr [edi+M07_SF_TANGENT+4]
    "DE C1 "                                # faddp st(1), st
    "C3 "                                   # ret
    # ZF=1 unless the slide animation and both jump-off animations are in the Prince's table.
    # m07_anims_ok:
    # .Lanims_ok:
    "A1 1C A0 DC 00 "                       # mov eax, dword ptr ds:M07_ANIM_SLIDE
    "E8 25 00 00 00 "                       # call .Lhas_anim
    "74 22 "                                # jz 9f
    "A1 24 A0 DC 00 "                       # mov eax, dword ptr ds:M07_ANIM_JUMP
    "E8 19 00 00 00 "                       # call .Lhas_anim
    "74 16 "                                # jz 9f
    "A1 28 A0 DC 00 "                       # mov eax, dword ptr ds:M07_ANIM_JUMP_AIR
    "E8 0D 00 00 00 "                       # call .Lhas_anim
    "74 0A "                                # jz 9f
    "A1 20 A0 DC 00 "                       # mov eax, dword ptr ds:M07_ANIM_LET_GO
    "E8 01 00 00 00 "                       # call .Lhas_anim
    # 9:
    "C3 "                                   # ret
    # eax = animation id; ZF=1 if its slot in the Prince's table is empty or out of range.
    # anim = [[obj+0x14]], table = [anim+0x30], word [table] = count, slot = [table+8+id*4]
    # .Lhas_anim:
    "8B 4B 14 "                             # mov ecx, [ebx+0x14]
    "8B 09 "                                # mov ecx, [ecx]
    "8B 49 30 "                             # mov ecx, [ecx+0x30]
    "0F B7 11 "                             # movzx edx, word ptr [ecx]
    "39 D0 "                                # cmp eax, edx
    "73 06 "                                # jae 1f
    "83 7C 81 08 00 "                       # cmp dword ptr [ecx+eax*4+8], 0
    "C3 "                                   # ret
    # 1:
    "31 C0 "                                # xor eax, eax
    "C3 "                                   # ret
    # ray from M07_SF_RAY_FROM along M07_SF_RAY_DELTA; eax = hit
    # .Lcast_ray:
    "6A 01 "                                # push 1
    "6A 00 "                                # push 0
    "6A 00 "                                # push 0
    "6A FF "                                # push -1
    "8D 47 6C "                             # lea eax, [edi+M07_SF_RAY_DELTA]
    "50 "                                   # push eax
    "8D 47 60 "                             # lea eax, [edi+M07_SF_RAY_FROM]
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 C4 78 6D FF "                       # call FN_RAY
    "83 C4 1C "                             # add esp, 28
    "C3 "                                   # ret
    # st0 = sideways offset k (popped): M07_SF_RAY_FROM = pos + (0,0,PZ) + t*sign(s)*k
    # .Lside_from:
    "F6 47 53 80 "                          # test byte ptr [edi+M07_SF_LATERAL+3], 0x80
    "74 02 "                                # jz 1f
    "D9 E0 "                                # fchs
    # 1:
    "D9 C0 "                                # fld st(0)
    "D8 4F 0C "                             # fmul dword ptr [edi+M07_SF_TANGENT]
    "D8 47 54 "                             # fadd dword ptr [edi+M07_SF_POS]
    "D9 5F 60 "                             # fstp dword ptr [edi+M07_SF_RAY_FROM]
    "D8 4F 10 "                             # fmul dword ptr [edi+M07_SF_TANGENT+4]
    "D8 47 58 "                             # fadd dword ptr [edi+M07_SF_POS+4]
    "D9 5F 64 "                             # fstp dword ptr [edi+M07_SF_RAY_FROM+4]
    "D9 47 5C "                             # fld dword ptr [edi+M07_SF_POS+8]
    "D8 05 FC 9F DC 00 "                    # fadd dword ptr ds:M07_CORNER_Z
    "D9 5F 68 "                             # fstp dword ptr [edi+M07_SF_RAY_FROM+8]
    "C3 "                                   # ret
    # st0 = tau (time since the start) -> st0 = distance descended:
    # tc = (VMAX - V0)/ACC, tau_c = min(tau, tc), d = tau_c*(V0 + ACC*tau_c/2) + VMAX*(tau - tau_c)
    # .Ldistance:
    "D9 05 DC 9F DC 00 "                    # fld dword ptr ds:M07_VMAX
    "D8 25 D4 9F DC 00 "                    # fsub dword ptr ds:M07_V0
    "D8 35 D8 9F DC 00 "                    # fdiv dword ptr ds:M07_ACC   # st0 = tc, st1 = tau
    "DB F1 "                                # fcomi st, st(1)
    "72 04 "                                # jb 1f   # tc < tau: tau_c = tc
    "DD D8 "                                # fstp st(0)
    "D9 C0 "                                # fld st(0)   # tau_c = tau
    # 1:
    "D9 9F 54 01 00 00 "                    # fstp dword ptr [edi+M07_SF_DIST_TMP]   # tau_c
    "D8 A7 54 01 00 00 "                    # fsub dword ptr [edi+M07_SF_DIST_TMP]   # st0 = tau - tau_c
    "D8 0D DC 9F DC 00 "                    # fmul dword ptr ds:M07_VMAX
    "D9 87 54 01 00 00 "                    # fld dword ptr [edi+M07_SF_DIST_TMP]
    "D8 0D D8 9F DC 00 "                    # fmul dword ptr ds:M07_ACC
    "D8 0D 18 A0 DC 00 "                    # fmul dword ptr ds:M07_HALF
    "D8 05 D4 9F DC 00 "                    # fadd dword ptr ds:M07_V0
    "D8 8F 54 01 00 00 "                    # fmul dword ptr [edi+M07_SF_DIST_TMP]
    "DE C1 "                                # faddp st(1), st
    "C3 "                                   # ret
)

M07_ANIM_KEEP = bytes.fromhex(  # .m07_anim_keep at 0xDCA830, source m07_wall_slide/anim_keep.s
    # ---- m07_keep: hook at the start of the "remove animation set" function 0x497F20(dst, src).
    # For the Prince, the curtain animations (M07_KEEP_FIRST, M07_KEEP_COUNT of them, both arrays of the
    # table)
    # get one extra reference before the original runs; afterwards every slot it emptied gets its
    # old pointer back (the table now owns that reference), and the extra reference on a slot it
    # left alone is released again. The next "add set" releases the slot and installs its own,
    # so the counts stay balanced.
    # m07_keep:
    "8B 44 24 04 "                          # mov eax, [esp+4]
    "3B 05 14 C4 D0 00 "                    # cmp eax, dword ptr ds:PRINCE_ACTOR
    "74 0C "                                # je 1f
    # m07_keep_vanilla:
    "8B 44 24 04 "                          # mov eax, [esp+4]   # the two replaced instructions
    "8B 48 14 "                             # mov ecx, [eax+0x14]
    "E9 DF D6 6C FF "                       # jmp ANIM_REMOVE_SET_BODY
    # 1:
    "60 "                                   # pusha
    "81 EC 90 00 00 00 "                    # sub esp, M07_KF_SIZE
    "89 E7 "                                # mov edi, esp
    "8B 70 14 "                             # mov esi, [eax+0x14]
    "8B 36 "                                # mov esi, [esi]
    "8B 76 30 "                             # mov esi, [esi+0x30]   # table
    "31 ED "                                # xor ebp, ebp   # j = 0 .. 2*KEEPN-1
    # .Lbefore_loop:
    "E8 67 00 00 00 "                       # call .Lslot_address
    "74 02 "                                # jz 1f
    "8B 01 "                                # mov eax, [ecx]
    # 1:
    "89 04 AF "                             # mov [edi+ebp*4], eax
    "85 C0 "                                # test eax, eax
    "74 09 "                                # jz 2f
    "50 "                                   # push eax
    "E8 7F D0 6C FF "                       # call FN_ANIM_ADDREF
    "83 C4 04 "                             # add esp, 4
    # 2:
    "E8 7F 00 00 00 "                       # call .Lnext_index
    "72 E0 "                                # jb .Lbefore_loop
    # the original function, with the caller's two arguments
    "FF B4 24 B8 00 00 00 "                 # push dword ptr [esp+M07_KF_SIZE+0x20+8]
    "FF B4 24 B8 00 00 00 "                 # push dword ptr [esp+M07_KF_SIZE+0x20+8]
    "E8 AE FF FF FF "                       # call m07_keep_vanilla
    "83 C4 08 "                             # add esp, 8
    "31 ED "                                # xor ebp, ebp
    # .Lafter_loop:
    "E8 2F 00 00 00 "                       # call .Lslot_address
    "74 1E "                                # jz 2f
    "8B 04 AF "                             # mov eax, [edi+ebp*4]
    "85 C0 "                                # test eax, eax
    "74 17 "                                # jz 2f
    "83 39 00 "                             # cmp dword ptr [ecx], 0
    "75 04 "                                # jne 1f
    "89 01 "                                # mov [ecx], eax   # emptied: put it back (the table keeps our
                                            #   reference)
    "EB 0E "                                # jmp 2f
    # 1:
    "8D 04 AF "                             # lea eax, [edi+ebp*4]   # left alone: release our extra reference
    "6A 00 "                                # push 0
    "50 "                                   # push eax
    "E8 CB D0 6C FF "                       # call FN_ANIM_RELEASE
    "83 C4 08 "                             # add esp, 8
    # 2:
    "E8 3B 00 00 00 "                       # call .Lnext_index
    "72 D4 "                                # jb .Lafter_loop
    # m07_log_keepdone:
    "81 C4 90 00 00 00 "                    # add esp, M07_KF_SIZE
    "61 "                                   # popa
    "C3 "                                   # ret
    # j = ebp -> ecx = &slot (j < KEEPN: table slot of KEEP0+j; else second-array slot of
    # KEEP0+j-KEEPN); eax = 0 and ZF=1 if out of range or there is no second array
    # .Lslot_address:
    "89 E8 "                                # mov eax, ebp
    "8D 4E 08 "                             # lea ecx, [esi+8]
    "3B 05 30 A0 DC 00 "                    # cmp eax, dword ptr ds:M07_KEEP_COUNT
    "72 09 "                                # jb 1f
    "2B 05 30 A0 DC 00 "                    # sub eax, dword ptr ds:M07_KEEP_COUNT
    "8B 4E 04 "                             # mov ecx, [esi+4]
    # 1:
    "03 05 2C A0 DC 00 "                    # add eax, dword ptr ds:M07_KEEP_FIRST
    "0F B7 16 "                             # movzx edx, word ptr [esi]
    "39 D0 "                                # cmp eax, edx
    "73 0B "                                # jae 2f
    "85 C9 "                                # test ecx, ecx
    "74 07 "                                # jz 2f
    "8D 0C 81 "                             # lea ecx, [ecx+eax*4]
    "31 C0 "                                # xor eax, eax
    "40 "                                   # inc eax   # ZF=0
    "C3 "                                   # ret
    # 2:
    "31 C0 "                                # xor eax, eax   # ZF=1
    "C3 "                                   # ret
    # ebp += 1; CF=1 while ebp < 2*KEEPN
    # .Lnext_index:
    "45 "                                   # inc ebp
    "A1 30 A0 DC 00 "                       # mov eax, dword ptr ds:M07_KEEP_COUNT
    "01 C0 "                                # add eax, eax
    "39 C5 "                                # cmp ebp, eax
    "C3 "                                   # ret
    # m07_slide_end:
)

# The mods' code and data, then their hooks, in the order they are applied
PATCHES = [
    # ---- M01 Special Jump key ----
    # .m01_forward_jump at 0x8846C3
    (0x4846C3, b"\xCC" * len(M01_FORWARD_JUMP), M01_FORWARD_JUMP),
    # .m01_menu_order at 0x8BA2E0
    (0x4BA2E0, bytes(len(M01_MENU_ORDER)), M01_MENU_ORDER),
    # .m01_label at 0x8BA300
    (0x4BA300, bytes(len(M01_LABEL)), M01_LABEL),
    # .m01_label_lookup at 0x8BA310
    (0x4BA310, bytes(len(M01_LABEL_LOOKUP)), M01_LABEL_LOOKUP),
    # .m01_default_binding at 0x8BA350
    (0x4BA350, bytes(len(M01_DEFAULT_BINDING)), M01_DEFAULT_BINDING),
    # .m01_pad_bit at 0x8BA380
    (0x4BA380, bytes(len(M01_PAD_BIT)), M01_PAD_BIT),
    # roll block entry (mov dword [ebp+0x448],2) -> jmp m01_forward_jump
    (0xDD331, bytes.fromhex("C7 85 48 04 00 00 02 00 00 00"), bytes.fromhex("E9 8D 73 3A 00 90 90 90 90 90")),
    # menu order reader -> m01_menu_order
    (0x5A54, bytes.fromhex("8A 8C 30 44 C2 8B 00"), bytes.fromhex("8A 8C 30 E0 A2 8B 00")),
    # menu order reader -> m01_menu_order
    (0x64D7, bytes.fromhex("0F B6 8C 38 44 C2 8B 00"), bytes.fromhex("0F B6 8C 38 E0 A2 8B 00")),
    # menu order reader -> m01_menu_order
    (0x6626, bytes.fromhex("8A 84 3A 44 C2 8B 00"), bytes.fromhex("8A 84 3A E0 A2 8B 00")),
    # menu order reader -> m01_menu_order
    (0x66A4, bytes.fromhex("8A 84 3A 44 C2 8B 00"), bytes.fromhex("8A 84 3A E0 A2 8B 00")),
    # Controls menu scroll limit for 25 rows (max offset 19 -> 20)
    (0x6748, bytes.fromhex("13"), bytes.fromhex("14")),
    # Controls menu scroll limit for 25 rows (18 -> 19)
    (0x6A46, bytes.fromhex("12"), bytes.fromhex("13")),
    # text lookup entry -> jmp m01_label_lookup
    (0x18050, bytes.fromhex("8B 44 24 04 56 8B F1"), bytes.fromhex("E9 BB 22 4A 00 90 90")),
    # SetDefaultBindings epilogue -> jmp m01_default_binding
    (0x1CD60, bytes.fromhex("5F 5E 83 C4 08 C3"), bytes.fromhex("E9 EB D5 49 00 90")),
    # pad builder after the enable mask (mov eax,[0x93F0E4]) -> jmp m01_pad_bit
    (0x1DAEE, bytes.fromhex("A1 E4 F0 93 00"), bytes.fromhex("E9 8D C8 49 00")),

    # ---- M02 Wall runs from jumps ----
    # .m02_air_contact at 0x8BA130
    (0x4BA130, bytes(len(M02_AIR_CONTACT)), M02_AIR_CONTACT),
    # .m02_latch at 0x8BA690
    (0x4BA690, bytes(len(M02_LATCH)), M02_LATCH),
    # airborne wall-contact test (add esp,8 ; test eax,eax ; je no contact) -> jmp m02_air_contact
    (0x24CEAF,
     bytes.fromhex("83 C4 08 85 C0 0F 84 DD 08 00 00 "),
     bytes.fromhex("E9 7C D2 26 00 90 90 90 90 90 90 ")),

    # ---- M03 Stairs-jump fix ----
    # .m03_takeoff at 0x8BA2C0
    (0x4BA2C0, bytes(len(M03_TAKEOFF)), M03_TAKEOFF),
    # .m03_apex at 0x8BA570
    (0x4BA570, bytes(len(M03_APEX)), M03_APEX),
    # .m03_landing at 0x8BA5C0
    (0x4BA5C0, bytes(len(M03_LANDING)), M03_LANDING),
    # take-off handler, launch-time store -> jmp m03_takeoff
    (0x24F068, bytes.fromhex("89 8E 78 05 00 00"), bytes.fromhex("E9 53 B2 26 00 90")),
    # airborne handler, falling-flag check -> jmp m03_apex
    (0x24C819, bytes.fromhex("39 9E CC 04 00 00 75 63"), bytes.fromhex("E9 52 DD 26 00 90 90 90")),
    # airborne handler, landing gate -> jmp m03_landing
    (0x24CDB5,
     bytes.fromhex("39 9E CC 04 00 00 0F 85 07 0F 00 00 "),
     bytes.fromhex("E9 06 D8 26 00 90 90 90 90 90 90 90 ")),

    # ---- M04 Story-trigger fix ----
    # .m04_point_test at 0x8BA3C0
    (0x4BA3C0, bytes(len(M04_POINT_TEST)), M04_POINT_TEST),
    # trigger manager: call FN_POINT_IN_TRIGGER -> call m04_point_test
    (0x1CF620, bytes.fromhex("E8 1B E8 EC FF"), bytes.fromhex("E8 9B AD 2E 00")),

    # ---- M05 Diagonal wall jump ----
    # .m05_jumpoff at 0x8BA5E0
    (0x4BA5E0, bytes(len(M05_JUMPOFF)), M05_JUMPOFF),
    # horizontal wall-run jump-off (mov edx,[0xD34A48]) -> jmp m05_jumpoff
    (0x191019, bytes.fromhex("8B 15 48 4A D3 00"), bytes.fromhex("E9 C2 95 32 00 90")),

    # ---- M06 Diagonal torpedo ----
    # .m06_primary_attack at 0x8BA6B0
    (0x4BA6B0, bytes(len(M06_PRIMARY_ATTACK)), M06_PRIMARY_ATTACK),
    # wall-attack check, primary-attack branch (mov ebx,2) -> jmp m06_primary_attack
    (0x2D32BD, bytes.fromhex("BB 02 00 00 00"), bytes.fromhex("E9 EE 73 1E 00")),
]

# ---- option: vertical wall runs from jumps ----
# Applied after PATCHES: the original bytes are the cave code written there.
VERTICAL_WALLRUN_PATCHES = [
    # m02_head_on_je -> nops: a head-on contact also reaches FN_GOTO_WALLING, which starts a
    # vertical run there
    (0x4BA1EF, bytes.fromhex("0F 84 AF 00 00 00"), bytes.fromhex("90 90 90 90 90 90")),
]

# ---- option: the wall slide ----
# Applied after PATCHES and the vertical wall runs; hooks inside M02's cave edit the bytes written
# there.
WALLSLIDE_PATCHES = [
    # ---- M07 Wall slide (option "slide") ----
    # .m07_tunables at 0xDC9000
    (MODS_RAW, b"\xCC" * len(M07_TUNABLES), M07_TUNABLES),
    # .m07_search at 0xDC90D4
    (0x5470D4, b"\xCC" * len(M07_SEARCH), M07_SEARCH),
    # .m07_checks at 0xDC9455
    (0x547455, b"\xCC" * len(M07_CHECKS), M07_CHECKS),
    # .m07_contact_gate at 0xDC9671
    (0x547671, b"\xCC" * len(M07_CONTACT_GATE), M07_CONTACT_GATE),
    # .m07_watchdog at 0xDC9748
    (0x547748, b"\xCC" * len(M07_WATCHDOG), M07_WATCHDOG),
    # .m07_c_gate at 0xDC9A19
    (0x547A19, b"\xCC" * len(M07_C_GATE), M07_C_GATE),
    # .m07_run_cut at 0xDC9A72
    (0x547A72, b"\xCC" * len(M07_RUN_CUT), M07_RUN_CUT),
    # .m07_entry_anims at 0xDC9B82
    (0x547B82, b"\xCC" * len(M07_ENTRY_ANIMS), M07_ENTRY_ANIMS),
    # .m07_jump_gate at 0xDC9F18
    (0x547F18, b"\xCC" * len(M07_JUMP_GATE), M07_JUMP_GATE),
    # .m07_anim_table at 0xDC9FAA
    (0x547FAA, b"\xCC" * len(M07_ANIM_TABLE), M07_ANIM_TABLE),
    # .m07_slide_tunables at 0xDC9FD0
    (0x547FD0, b"\xCC" * len(M07_SLIDE_TUNABLES), M07_SLIDE_TUNABLES),
    # .m07_slide at 0xDCA040
    (0x548040, b"\xCC" * len(M07_SLIDE), M07_SLIDE),
    # .m07_anim_keep at 0xDCA830
    (0x548830, b"\xCC" * len(M07_ANIM_KEEP), M07_ANIM_KEEP),
    # M02 m02_contact pushad / sub esp,0x2C / mov ebx,esp -> jmp m07_contact ; nop (the cave replays
    # the three instructions when the slide does not apply)
    (0x4BA13B, bytes.fromhex("60 83 EC 2C 89 E3"), bytes.fromhex("E9 00 FF 50 00 90")),
    # remove animation set 0x497F20: mov eax,[esp+4] / mov ecx,[eax+0x14] -> jmp m07_keep ; nop ;
    # nop (the cave replays the two instructions)
    (0x97F20, bytes.fromhex("8B 44 24 04 8B 48 14"), bytes.fromhex("E9 0B 29 93 00 90 90")),
    # PE header, .data VirtualSize 0x4AED00 -> 0x4AEE00 (maps the slide state at 0xDBFD00..,
    # zero-filled, inside the section's last page)
    (0x1D0, bytes.fromhex("00 ED 4A 00"), bytes.fromhex("00 EE 4A 00")),
    # hook 1: M02 m02_no_contact_je ("no wall contact" je 0x64D797) -> je m07_search
    (0x4BA135, bytes.fromhex("0F 84 5C 36 D9 FF"), bytes.fromhex("0F 84 99 EF 50 00")),
    # hook 2: 0x64CD81 mov eax,[0xD34A48] (before the ledge probe 0x546850) -> jmp m07_ledge_gate
    (0x24CD81, bytes.fromhex("A1 48 4A D3 00"), bytes.fromhex("E9 46 C6 77 00")),
    # hook 3: slide contact entry call (animation check) -> call m07_contact_gate
    (0x548100, bytes.fromhex("E8 4A 06 00 00"), bytes.fromhex("E8 6C F5 FF FF")),
    # hook 4: 0x630160 sub esp,0xe4 (per-frame airborne handler) -> jmp m07_watchdog ; nop
    (0x230160, bytes.fromhex("81 EC E4 00 00 00"), bytes.fromhex("E9 E3 95 79 00 90")),
    # slide jump exit V test (test byte [0x93F062],1 ; jz) -> nops: Space + side = 45 deg
    (0x548558, bytes.fromhex("F6 05 62 F0 93 00 01 74 67"), bytes.fromhex("90 90 90 90 90 90 90 90 90")),
    # hook 5: 0x725D9A call IsDown 0x71E450 (C held -> secondary-weapon throw) -> call m07_c_gate
    (0x325D9A, bytes.fromhex("E8 B1 86 FF FF"), bytes.fromhex("E8 7A 3C 6A 00")),
    # hook 6: 0x590FED run-continues branch -> je m07_run_cut (C during a horizontal run)
    (0x190FED, bytes.fromhex("0F 84 06 18 00 00"), bytes.fromhex("0F 84 7F 8A 83 00")),
    # hook 7: slide frame anim block (32 bytes) -> call m07_entry_anim + nops
    (0x5482DA,
     bytes.fromhex("53 E8 B0 D8 6C FF 83 C4 04 3B 05 1C A0 DC 00 74 "
                   "0F FF 35 1C A0 DC 00 53 E8 59 52 84 FF 83 C4 08 "),
     bytes.fromhex("E8 5C F9 FF FF 90 90 90 90 90 90 90 90 90 90 90 "
                   "90 90 90 90 90 90 90 90 90 90 90 90 90 90 90 90 ")),
    # hook 8: slide frame face-the-wall call -> call m07_sway_face
    (0x5482FA, bytes.fromhex("E8 DA 03 00 00"), bytes.fromhex("E8 AF FA FF FF")),
    # hook 9: slide frame fldz ; fstp [M07_SF_LATERAL] -> jmp m07_sway_stick
    (0x548313, bytes.fromhex("D9 EE D9 5F 50"), bytes.fromhex("E9 64 FB FF FF")),
    # hook 10: slide Space test call PressedWithin 0x7050C0 -> call m07_jump_gate
    (0x548275, bytes.fromhex("E8 46 AE 93 FF"), bytes.fromhex("E8 9E FC FF FF")),
]
# END GENERATED mods


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
    patches = (SECTION_PATCHES + PATCHES + (VERTICAL_WALLRUN_PATCHES if vertical else [])
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
