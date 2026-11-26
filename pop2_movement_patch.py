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
    (True, True): "6680492e745bf20e7a21c87fdfb24a141aa7373bb8f664f6d0760e3bbde79e1a",
    (False, True): "0c95b5b7a7b2a7e406695123ec0b34c70db683e17cbf88599ed7234f1c50e258",
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
    "86f9e90e29dcc60d6ffbb1a0062066876cd4df6dfa3bd332cab9ac95050ab7e5":
        "movement patch with vertical wall runs and the seventh wall slide",
    "82f6f866098c39a61fd41594fdd351330156215b0b2ad46b61ed4a4687726c0c":
        "movement patch with the seventh wall slide, without vertical wall runs",
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
# section. slide.s is the slide itself (a mode of the airborne state 0x412, run from M02's cave: its
# wall-contact point and its no-contact je), with the entry from wall contact and the entry without
# it (the search); the other parts add the start gates below the Prince, the ledge gate, the
# watchdog, the C gate, the run cut, the curtain-like entry animations and the animation keep. The
# slide state and the watchdog's scratch are at 0xDBFD00..0xDBFD8F, in the .data page M07 maps.

M07_TUNABLES = bytes.fromhex(  # .m07_tunables at 0xDC9000, source m07_wall_slide/tunables.s
    # ---- tunables (the checks read them as disp8 from ebp = M07_TB, slide.inc) ----
    # M07_TUNABLES:
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
    "EC 51 98 3F E1 7A B4 3F "              #   waypoints, the anims' natural lengths (shortcut: the oblique
                                            #   sets reuse them, the length of their grab 0x36A/0x36B is not
                                            #   measured; measure it from an SWA log if the swing looks out of
                                            #   step with the animation)
    "00 00 00 00 48 E1 FA 3F 71 3D 6A 40 "  # M07_SWAY_OFFSET: .float 0.0, 1.96, 3.66, 1.57, 1.80   # offset
    "C3 F5 C8 3F 66 66 E6 3F "              #   along the wall at k = 1 (curtainB)
    "75 03 00 00 71 03 00 00 72 03 00 00 "  # M07_ENTRY_ANIMS: .long 0x375, 0x371, 0x372, 0x373   # grab,
    "73 03 00 00 "                          #   settle, swing, swing (wall on his left)
    "74 03 00 00 6E 03 00 00 6F 03 00 00 "  # .long 0x374, 0x36E, 0x36F, 0x370   # the same, wall on his right
    "70 03 00 00 "
    "69 03 00 00 77 03 00 00 00 00 00 00 "  # .long 0x369, 0x377, 0, 0   # head-on grab and its follow-up (0 =
    "00 00 00 00 "                          #   no phase)
    "6A 03 00 00 71 03 00 00 72 03 00 00 "  # .long 0x36A, 0x371, 0x372, 0x373   # oblique grab (curtain
    "73 03 00 00 "                          #   0x51CB13), the left-wall swing (0x594D58)
    "6B 03 00 00 6E 03 00 00 6F 03 00 00 "  # .long 0x36B, 0x36E, 0x36F, 0x370   # oblique grab (0x51CB78),
    "70 03 00 00 "                          #   the right-wall swing (0x594D51)
    "9A 99 19 3F "                          # M07_JUMP_COOLDOWN: .float 0.6   # no new slide this long (s)
                                            #   after a slide jump-off
    "00 00 C0 3F "                          # M07_HEIGHT_CAP_WINDOW: .float 1.5   # height cap this long (s)
                                            #   after a slide jump-off; shortcut: a guess (one corner cycle is
                                            #   1.04 s), lengthen if a slower chain climbs
    "00 00 00 00 "                          # M07_HEIGHT_CAP_MARGIN: .float 0.0   # a new slide may start this
                                            #   far above the last start (user: 0)
    # the offsets from M07_TB that slide.inc gives checks.s (ebp = M07_TB)
)

M07_SEARCH = bytes.fromhex(  # .m07_search at 0xDC90BC, source m07_wall_slide/search.s
    # Ledge grab gate (0x64CD81). Block the probe while a search-started slide of this Prince is
    # running (fresh state, T0 == m07_search_t0) and he is less than M07_LEDGE_DROP below its start height.
    # m07_ledge_gate:
    "60 "                                   # pushad
    "83 EC 10 "                             # sub esp, 16
    "E8 68 0A 00 00 "                       # call m07_obj_now   # (slide.s) ebx = obj, esi = vars, ZF=1: his
                                            #   slide is running
    "75 41 "                                # jnz .Lledge_probe_allowed
    "3B 1D 14 C4 D0 00 "                    # cmp ebx, dword ptr ds:PRINCE_ACTOR
    "75 39 "                                # jne .Lledge_probe_allowed
    "A1 04 FD DB 00 "                       # mov eax, dword ptr ds:m07_slide_t0
    "3B 05 20 FD DB 00 "                    # cmp eax, dword ptr ds:m07_search_t0
    "75 2C "                                # jne .Lledge_probe_allowed
    "89 E0 "                                # mov eax, esp
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 FB 5B 6C FF "                       # call FN_GET_POSITION
    "83 C4 08 "                             # add esp, 8
    "D9 05 24 FD DB 00 "                    # fld dword ptr ds:m07_search_z
    "D8 64 24 08 "                          # fsub dword ptr [esp+8]   # descent since the start
    "D8 1D 00 90 DC 00 "                    # fcomp dword ptr ds:M07_LEDGE_DROP
    "DF E0 "                                # fnstsw ax
    "F6 C4 01 "                             # test ah, 0x01   # below M07_LEDGE_DROP: block
    "74 09 "                                # jz .Lledge_probe_allowed
    # m07_log_lgblock:
    "83 C4 10 "                             # add esp, 16
    "61 "                                   # popad
    "E9 98 3C 88 FF "                       # jmp LEDGE_PROBE_SKIP
    # .Lledge_probe_allowed:
    "83 C4 10 "                             # add esp, 16
    "61 "                                   # popad
    "A1 48 4A D3 00 "                       # mov eax, dword ptr ds:CURRENT_OBJ   # the replaced instruction
    "E9 70 3C 88 FF "                       # jmp LEDGE_PROBE_CALL
)

M07_CHECKS = bytes.fromhex(  # .m07_checks at 0xDC9116, source m07_wall_slide/checks.s
    # The checks below the Prince for a start m07_start_ok allowed: the height cap, then the edge check,
    # then the floor check (each runs only when the ones before it pass). Called by the contact entry
    # and the search (slide.s: ebp = m07_slide_vars, never 0) with the floor limit M07_FLOOR_CLEAR and
    # the fall start as it is, and by the run cut (ebp = 0) with M07_FLOOR_CLEAR_RUN and fallen 0 (the
    # fall start taken as his height z, as the cut's start-fall sets it).
    # In: eax = now (float bits), ebx = obj, esi = vars, ebp. Out: CF=1 (no slide) when he is above the
    # height cap, a ledge edge vanilla could still catch is below him or the floor is closer than the
    # limit below his feet; CF=0 the slide may start, m07_start_z = z. Keeps every register; the FPU
    # stack is left empty. The gate frame (edi, slide.inc) gets M07_GF_EDGE_DEPTH, M07_GF_EDGE_INDEX (-2
    # no query, -1 none found, else the edge), for a found edge M07_GF_EDGE_FLAGS and
    # M07_GF_EDGE_POINT, else M07_GF_FLOOR_CLEAR (M07_FLOOR_PROBE when nothing is hit) and, on a hit,
    # M07_GF_FLOOR_POINT (for the log). The calls' arguments stay on the stack until the exit.
    # m07_contact_gate:
    "60 "                                   # pushad
    "83 EC 74 "                             # sub esp, M07_GF_SIZE
    "89 E7 "                                # mov edi, esp
    "89 07 "                                # mov [edi+M07_GF_NOW], eax
    "8D 47 24 "                             # lea eax, [edi+M07_GF_POS]
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 B8 5B 6C FF "                       # call FN_GET_POSITION
    "85 ED "                                # test ebp, ebp   # 0: the run cut
    "BD 80 90 DC 00 "                       # mov ebp, offset M07_TB   # tunables as disp8 (slide.inc)
    "8B 55 9C "                             # mov edx, [ebp+M07_T_FLOOR_CLEAR]
    "75 09 "                                # jnz 1f
    "8B 55 A0 "                             # mov edx, [ebp+M07_T_FLOOR_CLEAR_RUN]
    "8D B7 28 FE FF FF "                    # lea esi, [edi+M07_GF_POS+8-VARS_FALL_START_Z]   # esi is read
                                            #   only for the fall start:
    # 1:
    # height cap: blocked while now - m07_jumpoff_time < M07_HEIGHT_CAP_WINDOW (compared as unsigned
    # float bits: a clock that went back never blocks) and the feet are above m07_start_z +
    # M07_HEIGHT_CAP_MARGIN
    "D9 07 "                                # fld dword ptr [edi+M07_GF_NOW]
    "D8 25 64 FD DB 00 "                    # fsub dword ptr ds:m07_jumpoff_time
    "50 "                                   # push eax
    "D9 1C 24 "                             # fstp dword ptr [esp]
    "58 "                                   # pop eax
    "3B 45 34 "                             # cmp eax, [ebp+M07_T_HEIGHT_CAP_WINDOW]
    "73 16 "                                # jae 1f
    "D9 05 68 FD DB 00 "                    # fld dword ptr ds:m07_start_z
    "D8 45 38 "                             # fadd dword ptr [ebp+M07_T_HEIGHT_CAP_MARGIN]
    "D8 5F 2C "                             # fcomp dword ptr [edi+M07_GF_POS+8]
    "DF E0 "                                # fnstsw ax
    "9E "                                   # sahf   # CF=1: cap < z (or unordered), above the cap
    "73 05 "                                # jnc 1f
    # m07_log_hcap:
    "E9 C7 00 00 00 "                       # jmp .Lgate_out   # CF=1
    # 1:
    "52 "                                   # push edx   # the limit, at [edi-12]
    "6A FE "                                # push -2
    "58 "                                   # pop eax
    "89 47 04 "                             # mov [edi+M07_GF_EDGE_INDEX], eax
    "D9 86 04 02 00 00 "                    # fld dword ptr [esi+VARS_FALL_START_Z]
    "D8 67 2C "                             # fsub dword ptr [edi+M07_GF_POS+8]   # fallen
    "D8 6D 84 "                             # fsubr dword ptr [ebp+M07_T_EDGE_MAX_FALL]
    "D8 65 88 "                             # fsub dword ptr [ebp+M07_T_EDGE_CATCH]   # D = 7 - fallen - catch
    "D9 45 8C "                             # fld dword ptr [ebp+M07_T_EDGE_DEPTH]
    "DB F1 "                                # fcomi st, st(1)
    "DB C1 "                                # fcmovnb st, st(1)   # min(M07_EDGE_DEPTH, D); M07_EDGE_DEPTH
                                            #   when D is NaN
    "DD D9 "                                # fstp st(1)
    "D9 57 60 "                             # fst dword ptr [edi+M07_GF_EDGE_DEPTH]
    "D9 EE "                                # fldz
    "DF F1 "                                # fcomip st, st(1)
    "73 65 "                                # jae .Lno_query   # depth <= 0: nothing below can be caught
                                            #   (never NaN: min keeps M07_EDGE_DEPTH for a NaN D)
    "D9 E0 "                                # fchs
    "D9 5F 38 "                             # fstp dword ptr [edi+M07_GF_BOX_MIN+8]
    "D9 45 94 "                             # fld dword ptr [ebp+M07_T_EDGE_HALF_X]
    "D9 57 3C "                             # fst dword ptr [edi+M07_GF_BOX_MAX]
    "D9 E0 "                                # fchs
    "D9 5F 30 "                             # fstp dword ptr [edi+M07_GF_BOX_MIN]
    "D9 45 98 "                             # fld dword ptr [ebp+M07_T_EDGE_HALF_Y]
    "D9 57 40 "                             # fst dword ptr [edi+M07_GF_BOX_MAX+4]
    "D9 E0 "                                # fchs
    "D9 5F 34 "                             # fstp dword ptr [edi+M07_GF_BOX_MIN+4]
    "8B 45 90 "                             # mov eax, dword ptr [ebp+M07_T_EDGE_TOP]
    "89 47 44 "                             # mov [edi+M07_GF_BOX_MAX+8], eax
    "8D 47 3C "                             # lea eax, [edi+M07_GF_BOX_MAX]
    "50 "                                   # push eax
    "8D 47 30 "                             # lea eax, [edi+M07_GF_BOX_MIN]
    "50 "                                   # push eax
    "6A 00 "                                # push 0
    "53 "                                   # push ebx
    "E8 F2 4D 6D FF "                       # call FN_BOX_QUERY
    "68 0F F4 4F 00 "                       # push LEDGE_EDGE_MASK
    "6A 01 "                                # push LEDGE_EDGE_TYPE
    "8D 47 24 "                             # lea eax, [edi+M07_GF_POS]
    "50 "                                   # push eax
    "6A 00 "                                # push 0
    "E8 A0 4F 6D FF "                       # call FN_QUERY_NEAREST
    "89 47 04 "                             # mov [edi+M07_GF_EDGE_INDEX], eax
    "85 C0 "                                # test eax, eax
    "78 1D "                                # js .Lfloor
    "8D 4F 68 "                             # lea ecx, [edi+M07_GF_EDGE_POINT]
    "51 "                                   # push ecx
    "8D 4F 24 "                             # lea ecx, [edi+M07_GF_POS]
    "51 "                                   # push ecx
    "50 "                                   # push eax
    "6A 00 "                                # push 0
    "E8 59 4F 6D FF "                       # call FN_QUERY_FLAGS
    "89 47 64 "                             # mov [edi+M07_GF_EDGE_FLAGS], eax
    "E8 51 50 6D FF "                       # call FN_QUERY_CLOSEST_POINT   # (0, index, &pos, &point): the
                                            #   same arguments, 0x49E140 leaves them
    # m07_log_bedge:
    "F9 "                                   # stc
    "EB 3A "                                # jmp .Lgate_out
    # .Lno_query:
    "DD D8 "                                # fstp st(0)
    # .Lfloor:
    # one ray from pos + (0,0,M07_FLOOR_PROBE_Z) along (0,0,-(M07_FLOOR_PROBE_Z+M07_FLOOR_PROBE))
    "D9 45 A8 "                             # fld dword ptr [ebp+M07_T_FLOOR_PROBE]
    "D9 45 A4 "                             # fld dword ptr [ebp+M07_T_FLOOR_PROBE_Z]
    "E8 34 0B 00 00 "                       # call m07_ray_down   # (slide.s)
    "74 12 "                                # jz 1f
    "8D 47 68 "                             # lea eax, [edi+M07_GF_FLOOR_POINT]
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 65 95 6D FF "                       # call FN_RAY_HIT_POINT
    "D9 47 2C "                             # fld dword ptr [edi+M07_GF_POS+8]
    "D8 67 70 "                             # fsub dword ptr [edi+M07_GF_FLOOR_POINT+8]
    "EB 03 "                                # jmp 2f
    # 1:
    "D9 45 A8 "                             # fld dword ptr [ebp+M07_T_FLOOR_PROBE]
    # 2:
    "D9 5F 08 "                             # fstp dword ptr [edi+M07_GF_FLOOR_CLEAR]
    "D9 47 08 "                             # fld dword ptr [edi+M07_GF_FLOOR_CLEAR]   # compared as stored (a
                                            #   float)
    # m07_log_bfloor:
    "D8 5F F4 "                             # fcomp dword ptr [edi-12]
    "DF E0 "                                # fnstsw ax
    "9E "                                   # sahf   # CF=1: clearance < limit (unordered also sets CF: no
                                            #   slide)
    "72 08 "                                # jc .Lgate_out
    # m07_log_cnone:
    # the height cap's reference. For the run cut the search's start right after writes it again.
    "8B 47 2C "                             # mov eax, [edi+M07_GF_POS+8]
    "A3 68 FD DB 00 "                       # mov dword ptr ds:m07_start_z, eax
    # .Lgate_out:
    "8D 67 74 "                             # lea esp, [edi+M07_GF_SIZE]   # (keeps CF)
    "61 "                                   # popad
    "C3 "                                   # ret
    # One search ray of the search (slide.s .Lsearch) from pos + (0,0,M07_SEARCH_Z) along
    # [edi+M07_SF_RAY_DIR] (flat unit vector) * M07_SEARCH_REACH. Accepts a near-vertical runnable wall
    # whose normal is within 60 degrees of -RD: CF=0, with M07_SF_HIT_POINT, M07_SF_HIT_NORMAL
    # (flattened) set; else CF=1. ebx = obj, edi = the slide frame (its tunables: [edi+M07_F_*]). The
    # calls' arguments stay on the stack until the exit (ebp frames it). Clobbers eax, ecx, edx; the
    # FPU stack is left empty.
    # m07_try_ray:
    "55 "                                   # push ebp
    "89 E5 "                                # mov ebp, esp
    "D9 47 C8 "                             # fld dword ptr [edi+M07_F_SEARCH_Z]
    "E8 CF 0A 00 00 "                       # call m07_from0   # (slide.s)
    "D9 EE "                                # fldz
    "D9 47 C4 "                             # fld dword ptr [edi+M07_F_SEARCH_REACH]
    "8D 57 18 "                             # lea edx, [edi+M07_SF_RAY_DIR]
    "E8 FC 0A 00 00 "                       # call m07_ray_k   # (slide.s)
    # m07_log_sray:
    "74 51 "                                # jz .Lray_miss
    "8D 47 0C "                             # lea eax, [edi+M07_SF_HIT_POINT]
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 1B 95 6D FF "                       # call FN_RAY_HIT_POINT
    "8D 07 "                                # lea eax, [edi+M07_SF_HIT_NORMAL]
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 B2 95 6D FF "                       # call FN_RAY_HIT_NORMAL
    "68 FF FF 00 00 "                       # push 0xFFFF
    "53 "                                   # push ebx
    "E8 67 6E 6D FF "                       # call FN_SURFACE_FLAGS
    # m07_log_shit:
    "A9 00 00 03 00 "                       # test eax, SURFACE_NO_RUN_MASK
    "75 2C "                                # jnz .Lray_miss
    "D9 47 08 "                             # fld dword ptr [edi+M07_SF_HIT_NORMAL+8]
    "D9 E1 "                                # fabs
    "D8 5F D0 "                             # fcomp dword ptr [edi+M07_F_SEARCH_MAX_NZ]
    "DF E0 "                                # fnstsw ax
    "9E "                                   # sahf
    "77 1F "                                # ja .Lray_miss   # |nz| > NZ (unordered passes, as before: the
                                            #   front test rejects it)
    "8D 07 "                                # lea eax, [edi+M07_SF_HIT_NORMAL]
    "50 "                                   # push eax
    "E8 9B 33 6B FF "                       # call FN_FLATTEN_NORMALIZE
    # ray direction within 60 degrees of the wall: -(RD . n) >= FRONT
    "D9 47 18 "                             # fld dword ptr [edi+M07_SF_RAY_DIR]
    "D8 0F "                                # fmul dword ptr [edi+M07_SF_HIT_NORMAL]
    "D9 47 1C "                             # fld dword ptr [edi+M07_SF_RAY_DIR+4]
    "D8 4F 04 "                             # fmul dword ptr [edi+M07_SF_HIT_NORMAL+4]
    "DE C1 "                                # faddp st(1), st
    "D9 E0 "                                # fchs
    "D8 5F 90 "                             # fcomp dword ptr [edi+M07_F_FRONT_COS]
    "DF E0 "                                # fnstsw ax
    "9E "                                   # sahf   # CF=1: below FRONT (or unordered)
    "73 01 "                                # jnc .Lray_out
    # .Lray_miss:
    "F9 "                                   # stc
    # .Lray_out:
    "C9 "                                   # leave   # drops the arguments; keeps CF
    "C3 "                                   # ret
)

M07_WATCHDOG = bytes.fromhex(  # .m07_watchdog at 0xDC929F, source m07_wall_slide/watchdog.s
    # m07_watchdog:
    "81 EC E4 00 00 00 "                    # sub esp, 0xe4   # the replaced instruction, replayed first
    "60 "                                   # pushad
    "BD 40 FD DB 00 "                       # mov ebp, M07_STATE
    "89 65 4C "                             # mov [ebp+M07_W_ESP], esp
    "E8 7A 08 00 00 "                       # call m07_obj_now   # (slide.s) ebx = obj, esi = vars, eax = now,
                                            #   edx = d, ZF=1: running
    "89 DF "                                # mov edi, ebx
    "89 45 38 "                             # mov [ebp+M07_W_NOW], eax
    "0F 94 C7 "                             # setz bh
    "B3 00 "                                # mov bl, 0
    "39 75 C0 "                             # cmp [ebp+M07_VARS], esi
    "75 09 "                                # jne 2f
    "3B 15 20 97 DC 00 "                    # cmp edx, dword ptr ds:M07_STALE   # his: d > STALE signed: not
                                            #   running (d < 0: neither)
    "0F 9F C3 "                             # setg bl
    # 2:
    "3B 3D 14 C4 D0 00 "                    # cmp edi, dword ptr ds:PRINCE_ACTOR
    "75 5A "                                # jne .Lout
    # a slide of his is running and its T0 is new -> draw the sword once
    "84 FF "                                # test bh, bh
    "74 19 "                                # jz 4f
    "8B 45 C4 "                             # mov eax, [ebp+M07_T0]
    "3B 45 FC "                             # cmp eax, [ebp+M07_SWORD_T0]
    "74 11 "                                # je 4f
    "89 45 FC "                             # mov [ebp+M07_SWORD_T0], eax
    "83 65 00 00 "                          # and dword ptr [ebp+M07_SIDE], 0   # a slide started: no side
                                            #   rays until the next run
    # m07_log_wdsword:
    "6A 03 "                                # push 3
    "6A 01 "                                # push 1
    "57 "                                   # push edi
    "E8 C0 7B 93 FF "                       # call FN_SNAP_SWORD
    # 4:
    "8D 45 2C "                             # lea eax, [ebp+M07_W_POS]
    "50 "                                   # push eax
    "57 "                                   # push edi
    "E8 E6 59 6C FF "                       # call FN_GET_POSITION
    # side-search allowance: vars on 0x420, kept in 0x412, else 0 (m07_run_t0 = now when it changes)
    "8B 86 40 06 00 00 "                    # mov eax, [esi+0x640]
    "66 2D 12 04 "                          # sub ax, 0x412   # states are below 0x10000
    "74 7B "                                # je .L412
    "31 C9 "                                # xor ecx, ecx
    "83 F8 0E "                             # cmp eax, 0x420 - 0x412
    "0F 44 CE "                             # cmove ecx, esi
    "39 4D 00 "                             # cmp [ebp+M07_SIDE], ecx
    "74 09 "                                # je .Lmoved
    "89 4D 00 "                             # mov [ebp+M07_SIDE], ecx
    "8B 45 38 "                             # mov eax, [ebp+M07_W_NOW]
    "89 45 04 "                             # mov [ebp+M07_RUN_T0], eax
    # .Lmoved:
    "8B 45 38 "                             # mov eax, [ebp+M07_W_NOW]
    "89 45 F8 "                             # mov [ebp+M07_WD_MOVED], eax
    # .Lcopy:
    "8D 75 2C "                             # lea esi, [ebp+M07_W_POS]   # m07_wd_pos = pos, m07_wd_timer =
                                            #   now (adjacent in both)
    "8D 7D E8 "                             # lea edi, [ebp+M07_WD_POS]
    "6A 04 "                                # push 4
    "59 "                                   # pop ecx
    "F3 A5 "                                # rep movsd
    # .Lout:
    "8B 65 4C "                             # mov esp, [ebp+M07_W_ESP]
    "61 "                                   # popad
    "E9 30 6E 86 FF "                       # jmp AIR_FRAME_HANDLER_BODY
    # .Lstuck:
    # stuck: d = now - m07_wd_timer; any axis moved more than WD_EPS, or d < 0 -> .Lmoved;
    # d < WD_STUCK -> out
    "D9 45 38 "                             # fld dword ptr [ebp+M07_W_NOW]
    "D8 65 F4 "                             # fsub dword ptr [ebp+M07_WD_TIMER]
    "D9 5D 48 "                             # fstp dword ptr [ebp+M07_W_TMP]
    "6A 03 "                                # push 3
    "59 "                                   # pop ecx
    # 1:
    "D9 44 8D 28 "                          # fld dword ptr [ebp+ecx*4+M07_W_POS-4]
    "D8 64 8D E4 "                          # fsub dword ptr [ebp+ecx*4+M07_WD_POS-4]
    "D9 E1 "                                # fabs
    "D8 1D 34 90 DC 00 "                    # fcomp dword ptr ds:M07_WD_EPS
    "DF E0 "                                # fnstsw ax
    "9E "                                   # sahf
    "77 C5 "                                # ja .Lmoved
    "E2 E9 "                                # loop 1b
    "A1 2C 90 DC 00 "                       # mov eax, dword ptr ds:M07_WD_STUCK
    "39 45 48 "                             # cmp [ebp+M07_W_TMP], eax
    "72 CA "                                # jb .Lout   # 0 <= d < WD_STUCK
    "7C B7 "                                # jl .Lmoved   # d < 0: game time went back (rewind, reload)
    # only after a slide of his that is no longer running and whose last frame was at most
    # WD_WINDOW before he stopped moving
    "84 DB "                                # test bl, bl
    "74 C4 "                                # jz .Lout
    "D9 45 F8 "                             # fld dword ptr [ebp+M07_WD_MOVED]
    "D8 65 C8 "                             # fsub dword ptr [ebp+M07_LAST]
    "D8 1D 30 90 DC 00 "                    # fcomp dword ptr ds:M07_WD_WINDOW
    "DF E0 "                                # fnstsw ax
    "9E "                                   # sahf
    "77 B3 "                                # ja .Lout
    # m07_log_wdfire:
    "D9 E8 "                                # fld1
    "8D 5D D0 "                             # lea ebx, [ebp+M07_NORMAL]
    "EB 33 "                                # jmp .Lfall_exit
    # .L412:
    # orphaned slide animation (rewind) -> fall exit now
    "84 FF "                                # test bh, bh
    "75 B1 "                                # jnz .Lstuck
    "57 "                                   # push edi
    "E8 05 E8 6C FF "                       # call FN_CURRENT_ANIM
    "3B 05 0C 97 DC 00 "                    # cmp eax, dword ptr ds:M07_ANIM_SLIDE
    "74 13 "                                # je 8f
    "66 2D 69 03 "                          # sub ax, 0x369   # the head-on set 0x369/0x377, the oblique grabs
                                            #   0x36A/0x36B
    "83 F8 0E "                             # cmp eax, 0x377 - 0x369   # and the sway sets 0x36E..0x375
    "77 9A "                                # ja .Lstuck
    "BA E7 5F 00 00 "                       # mov edx, 0x5FE7   # bits 0..2, 5..12, 14
    "0F A3 C2 "                             # bt edx, eax
    "73 90 "                                # jnc .Lstuck
    # 8:
    # m07_log_wdorphan:
    "8D 5D 3C "                             # lea ebx, [ebp+M07_W_VEL]
    "53 "                                   # push ebx
    "57 "                                   # push edi
    "E8 A0 74 6C FF "                       # call FN_GET_FACING
    "D9 E8 "                                # fld1
    "D9 E0 "                                # fchs
    # the slide's fall exit: v = (s * OUT * [ebx], s * OUT * [ebx+4], -V0), s = st(0)
    # .Lfall_exit:
    "D8 0D A8 96 DC 00 "                    # fmul dword ptr ds:M07_OUT
    "D9 C0 "                                # fld st(0)
    "D8 0B "                                # fmul dword ptr [ebx]
    "D9 5D 3C "                             # fstp dword ptr [ebp+M07_W_VEL]
    "D8 4B 04 "                             # fmul dword ptr [ebx+4]
    "D9 5D 40 "                             # fstp dword ptr [ebp+M07_W_VEL+4]
    "D9 05 90 96 DC 00 "                    # fld dword ptr ds:M07_V0
    "D9 E0 "                                # fchs
    "D9 5D 44 "                             # fstp dword ptr [ebp+M07_W_VEL+8]
    "89 FB "                                # mov ebx, edi
    "8D 55 3C "                             # lea edx, [ebp+M07_W_VEL]
    "E8 2A 07 00 00 "                       # call m07_let_go   # start-fall with the let-go animation, then
                                            #   the velocity (slide.s)
    "8B 45 34 "                             # mov eax, [ebp+M07_W_POS+8]
    "89 86 04 02 00 00 "                    # mov [esi+0x204], eax   # fall reset
    "6A 01 "                                # push 1
    "8F 86 CC 04 00 00 "                    # pop dword ptr [esi+0x4cc]
    "E9 30 FF FF FF "                       # jmp .Lcopy   # m07_wd_pos = pos, m07_wd_timer = now
)

M07_C_GATE = bytes.fromhex(  # .m07_c_gate at 0xDC93F2, source m07_wall_slide/c_gate.s
    # C gate, called instead of IsDown 0x71E450(obj, &out, pad, bit) at 0x725D9A (its only caller).
    # Same arguments and results (out, eax, registers as IsDown leaves them; flags clobbered: the
    # caller reloads out and compares). Drops hook 5's return address and calls IsDown with the
    # caller's arguments in place (IsDown writes only its own local and *out, never its argument
    # slots, so &out and bit are read back from them), then jumps back to C_GATE_RET.
    # The call site's registers: ebp = obj (the action handler 0x725180 loads it once from its
    # argument and passes it as IsDown's obj) and esi = its vars ([[[obj+0x18]+4]+0x48], set in the
    # handler's prologue and reloaded from [esp+0x24] after its two rep movs; vanilla reads this
    # call's pad from [esi+0x10B8]).
    # m07_c_gate:
    "83 C4 04 "                             # add esp, 4   # [esp] = obj, &out, pad, bit (the hook's
                                            #   arguments)
    "E8 56 50 95 FF "                       # call FN_IS_DOWN
    "60 "                                   # pushad
    "3B 2D 14 C4 D0 00 "                    # cmp ebp, dword ptr ds:PRINCE_ACTOR
    "75 1F "                                # jne 9f
    "83 7C 24 2C 01 "                       # cmp dword ptr [esp+44], 1   # bit 1 = C
    "75 18 "                                # jne 9f
    "D9 86 14 07 00 00 "                    # fld dword ptr [esi+VARS_C_PRESS_TIME]
    "D8 1D 08 FD DB 00 "                    # fcomp dword ptr ds:m07_slide_last
    "DF E0 "                                # fnstsw ax
    "9E "                                   # sahf
    "77 07 "                                # ja 9f   # press > last slide frame: a fresh press (unordered:
                                            #   the slide's)
    "8B 54 24 24 "                          # mov edx, [esp+36]   # &out
    # m07_log_cgate:
    "83 22 00 "                             # and dword ptr [edx], 0   # the slide's C (pressed at or before
                                            #   its last frame): not down
    # 9:
    "61 "                                   # popad
    "E9 77 C9 95 FF "                       # jmp C_GATE_RET
)

M07_RUN_CUT = bytes.fromhex(  # .m07_run_cut at 0xDC9428, source m07_wall_slide/run_cut.s
    # ---- run cut (hook 6, je from 0x590FED; esi = vars, stack at handler level) ----
    # m07_run_cut:
    "60 "                                   # pushad
    "8B 1D 48 4A D3 00 "                    # mov ebx, dword ptr ds:CURRENT_OBJ
    "3B 1D 14 C4 D0 00 "                    # cmp ebx, dword ptr ds:PRINCE_ACTOR
    "75 4D "                                # jne .Lrun_continues
    "39 35 40 FD DB 00 "                    # cmp dword ptr ds:m07_side_rays, esi
    "75 45 "                                # jne .Lrun_continues
    "D9 86 14 07 00 00 "                    # fld dword ptr [esi+VARS_C_PRESS_TIME]
    "D8 1D 44 FD DB 00 "                    # fcomp dword ptr ds:m07_run_t0
    "DF E0 "                                # fnstsw ax
    "9E "                                   # sahf
    "72 34 "                                # jb .Lrun_continues   # pressed before this run started
                                            #   (unordered too)
    "E8 E7 06 00 00 "                       # call m07_now   # (slide.s) eax = now
    "E8 14 07 00 00 "                       # call m07_start_ok   # (slide.s) keeps eax
    "74 28 "                                # jz .Lrun_continues
    "31 ED "                                # xor ebp, ebp   # m07_contact_gate for the run cut: fallen 0,
                                            #   M07_FLOOR_CLEAR_RUN
    "E8 B3 FC FF FF "                       # call m07_contact_gate
    "72 1F "                                # jc .Lrun_continues
    # m07_log_runcut:
    "50 "                                   # push eax
    "50 "                                   # push eax
    "50 "                                   # push eax   # the velocity (3 floats)
    "54 "                                   # push esp
    "53 "                                   # push ebx
    "E8 11 E5 6D FF "                       # call FN_GET_VELOCITY
    "59 "                                   # pop ecx
    "59 "                                   # pop ecx
    "6A 2C "                                # push 0x2C   # start-fall with animation 0x2C, then the run's
                                            #   velocity (slide.s)
    "59 "                                   # pop ecx
    "89 E2 "                                # mov edx, esp
    "E8 91 06 00 00 "                       # call m07_start_fall
    "83 C4 0C "                             # add esp, 12
    "61 "                                   # popad
    "E9 13 7C 7C FF "                       # jmp WALLRUN_JUMPOFF_TAIL
    # .Lrun_continues:
    "61 "                                   # popad
    "E9 6F 93 7C FF "                       # jmp RUN_CONTINUES
)

M07_ENTRY_ANIMS = bytes.fromhex(  # .m07_entry_anims at 0xDC948A, source m07_wall_slide/entry_anims.s
    # ebx = obj, edi = the slide frame with n (flat, unit, out of the wall) at M07_SF_NORMAL, ebp =
    # m07_slide_vars; called by both start paths (slide.s) before anything
    # zeroes his velocity or turns him: m07_sway_k = (v . t) / M07_SWAY_VREF clamped to +-M07_SWAY_KMAX,
    # t = (-n.y, n.x); m07_sway_f0 = his flat facing. Read by the sway (side-ray record, search.s) and
    # the adoption (m07_entry_anim). Clobbers eax, ecx, edx.
    # m07_sway_measure:
    "8D 47 30 "                             # lea eax, [edi+M07_SF_VELOCITY]   # (free at both starts: the
                                            #   frame's rays write it next)
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 EC E4 6D FF "                       # call FN_GET_VELOCITY
    "D9 47 34 "                             # fld dword ptr [edi+M07_SF_VELOCITY+4]
    "D8 0F "                                # fmul dword ptr [edi+M07_SF_NORMAL]   # vy * nx
    "D9 47 30 "                             # fld dword ptr [edi+M07_SF_VELOCITY]
    "D8 4F 04 "                             # fmul dword ptr [edi+M07_SF_NORMAL+4]   # vx * ny
    "DE E9 "                                # fsubp st(1), st   # v . t
    "D8 77 DC "                             # fdiv dword ptr [edi+M07_F_SWAY_VREF]
    # clamp to +-KMAX; a NaN k stays NaN (unordered compares keep k)
    "D9 47 E0 "                             # fld dword ptr [edi+M07_F_SWAY_KMAX]
    "DB F1 "                                # fcomi st, st(1)
    "DB C1 "                                # fcmovnb st, st(1)   # KMAX >= k: k
    "DA D9 "                                # fcmovu st, st(1)   # unordered: k
    "DD D9 "                                # fstp st(1)   # min(k, KMAX)
    "D9 47 E0 "                             # fld dword ptr [edi+M07_F_SWAY_KMAX]
    "D9 E0 "                                # fchs
    "DB F1 "                                # fcomi st, st(1)
    "DA D1 "                                # fcmovbe st, st(1)   # -KMAX <= k or unordered: k
    "DD D9 "                                # fstp st(1)   # max(k, -KMAX)
    "D9 5D 4C "                             # fstp dword ptr [ebp+W_K]
    "8D 45 54 "                             # lea eax, [ebp+W_F0]
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 89 73 6C FF "                       # call FN_GET_FACING
    "58 "                                   # pop eax
    "E8 53 31 6B FF "                       # call FN_FLATTEN_NORMALIZE   # (&m07_sway_f0 still pushed)
    # m07_log_sway:
    "83 C4 0C "                             # add esp, 12
    "C3 "                                   # ret
    # edi = slide frame, ebp = m07_slide_vars: m07_sway_tmp = tau = now - T0 and edx = its bits (as
    # unsigned they order a tau >= 0 as the floats; a negative tau is above any bound), eax = T0;
    # ZF=1 when this slide has the sway record (m07_sway_t0 = T0). Used by m07_entry_anim,
    # .Lsway_active and the jump gate (m07_jump_gate, slide.s).
    # m07_entry_tau:
    "D9 47 48 "                             # fld dword ptr [edi+M07_SF_NOW]
    "D8 65 04 "                             # fsub dword ptr [ebp+W_SLIDE_T0]
    "D9 5D 50 "                             # fstp dword ptr [ebp+W_TMP]
    "8B 55 50 "                             # mov edx, [ebp+W_TMP]
    "8B 45 04 "                             # mov eax, [ebp+W_SLIDE_T0]
    "3B 45 48 "                             # cmp eax, [ebp+W_T0]
    "C3 "                                   # ret
    # ZF=0 and st0 = tau when the sway of this slide is on (its record, a sway set, 0 <= tau < the
    # last waypoint), else ZF=1 and the FPU stack empty. Clobbers eax, edx, m07_sway_tmp.
    # .Lsway_active:
    "E8 E8 FF FF FF "                       # call m07_entry_tau
    "75 12 "                                # jne 9f
    "83 7D 60 02 "                          # cmp dword ptr [ebp+W_SET], 2   # head-on set: no swing, no turn
    "74 0C "                                # je 9f
    "3B 15 48 90 DC 00 "                    # cmp edx, dword ptr ds:M07_SWAY_TAU+16
    "73 04 "                                # jae 9f   # tau < 0 or tau >= end
    "D9 45 50 "                             # fld dword ptr [ebp+W_TMP]
    "C3 "                                   # ret   # ZF=0 (below)
    # 9:
    "31 D2 "                                # xor edx, edx   # ZF=1
    "C3 "                                   # ret
    # st0 = tau -> st0 = F(tau): cosine segments through M07_SWAY_TAU / M07_SWAY_OFFSET (F(0) = 0).
    # tau must be below the last waypoint, so the segment search ends inside the table: the callers
    # pass tau and tau_prev <= tau from .Lsway_active (and tau_prev >= 0: m07_slide_last >= T0; a
    # negative tau would mirror the first segment). Clobbers edx.
    # .Lsway_curve:
    "BA 38 90 DC 00 "                       # mov edx, offset M07_SWAY_TAU
    # 1:
    "83 C2 04 "                             # add edx, 4
    "D9 02 "                                # fld dword ptr [edx]
    "DF F1 "                                # fcomip st, st(1)
    "76 F7 "                                # jbe 1b   # tau >= tau_b: next segment
    "D8 62 FC "                             # fsub dword ptr [edx-4]
    "D9 02 "                                # fld dword ptr [edx]
    "D8 62 FC "                             # fsub dword ptr [edx-4]
    "D8 C0 "                                # fadd st, st(0)
    "DE F9 "                                # fdivp st(1), st   # u / 2, u = (tau - tau_a) / (tau_b - tau_a)
    "D8 4F EC "                             # fmul dword ptr [edi+M07_F_PI]
    "D9 FE "                                # fsin
    "D8 C8 "                                # fmul st, st(0)   # w = sin(pi u / 2)^2 = (1 - cos(pi u)) / 2
    "D9 42 14 "                             # fld dword ptr [edx+20]   # the offsets follow the waypoints
                                            #   (mod.py checks)
    "D8 62 10 "                             # fsub dword ptr [edx+16]
    "DE C9 "                                # fmulp st(1), st
    "D8 42 10 "                             # fadd dword ptr [edx+16]
    "C3 "                                   # ret
    # called by the slide frame (slide.s) with M07_SF_TMP = -n (z 0); sets the facing (jumps to
    # m07_set_facing). Animations: during this slide's entry the phase anims in turn (0x375, 0x371,
    # 0x372, 0x373 for the wall on his left), each until it stops playing (the airborne anim-end
    # branch replaces it), missing ones skipped, and the velocity zeroed (their root motion would add
    # to the scripted swing); then and otherwise the slide loop. Facing: -n, during the turn window of
    # a sway from his facing at the start (m07_sway_f0) to -n (smoothstep).
    # m07_entry_anim:
    "60 "                                   # pushad
    "53 "                                   # push ebx
    "E8 5C E6 6C FF "                       # call FN_CURRENT_ANIM
    "59 "                                   # pop ecx
    "96 "                                   # xchg esi, eax   # esi = his animation (the vars are not needed
                                            #   here)
    "E8 96 FF FF FF "                       # call m07_entry_tau   # edx = tau bits (0: the slide's first
                                            #   frame), eax = T0
    "74 55 "                                # je 3f   # this slide's sway record: its phases
    # no record: adopt it on its first frames, head-on or oblique set
    "3B 57 D8 "                             # cmp edx, dword ptr [edi+M07_F_ADOPT_WINDOW]
    "73 4B "                                # jae .Lloop   # tau < 0 or tau >= HWIN: not a fresh slide
    "89 45 48 "                             # mov [ebp+W_T0], eax
    "C6 45 60 02 "                          # mov byte ptr [ebp+W_SET], 2   # (the dwords of the sway state
                                            #   hold small values; m07_sway_k
    "31 D2 "                                # xor edx, edx   # is not read while the set is 2)
    "89 55 1C "                             # mov [ebp+W_PHASE], edx   # phase 0 begins (edx = 0: below
                                            #   M07_ENTRY_END at 3f)
    "3B 77 FC "                             # cmp esi, dword ptr [edi+M07_F_ANIM_SLIDE]   # already in a slide
                                            #   anim: restarted at once, no re-grab
    "74 36 "                                # je 1f
    "81 FE 69 03 00 00 "                    # cmp esi, 0x369
    "74 2E "                                # je 1f
    "81 FE 77 03 00 00 "                    # cmp esi, 0x377
    "74 26 "                                # je 1f
    "D9 45 54 "                             # fld dword ptr [ebp+W_F0]
    "D8 4F 18 "                             # fmul dword ptr [edi+M07_SF_TMP]
    "D9 45 58 "                             # fld dword ptr [ebp+W_F0+4]
    "D8 4F 1C "                             # fmul dword ptr [edi+M07_SF_TMP+4]
    "DE C1 "                                # faddp st(1), st   # cos = f0 . (-n)
    "D8 5F D4 "                             # fcomp dword ptr [edi+M07_F_OBLIQUE_COS]
    "DF E0 "                                # fnstsw ax
    "9E "                                   # sahf
    "73 19 "                                # jae 3f   # within 35 deg of -n: head-on
    "8B 45 4C "                             # mov eax, [ebp+W_K]
    "01 C0 "                                # add eax, eax   # CF = sign of k
    "74 12 "                                # jz 3f   # k = 0: no swing, head-on
    "B0 03 "                                # mov al, 3
    "14 00 "                                # adc al, 0   # k > 0 (wall on his left): set 3, k < 0: set 4
    "88 45 60 "                             # mov [ebp+W_SET], al
    "EB 09 "                                # jmp 3f
    # 1:
    "C6 45 1C 04 "                          # mov byte ptr [ebp+W_PHASE], 4   # (falls into the slide loop)
    # .Lloop:
    "8B 47 FC "                             # mov eax, dword ptr [edi+M07_F_ANIM_SLIDE]
    "EB 34 "                                # jmp .Lwant
    # the phases: edx = tau bits on the first pass, 0 when a phase begins (below M07_ENTRY_END)
    # 3:
    "3B 57 F4 "                             # cmp edx, dword ptr [edi+M07_F_ENTRY_END]
    "73 F6 "                                # jae .Lloop   # tau < 0 or tau >= AEND: phases over
    "8B 4D 1C "                             # mov ecx, [ebp+W_PHASE]
    "83 F9 04 "                             # cmp ecx, 4
    "73 EE "                                # jae .Lloop
    "8B 45 60 "                             # mov eax, [ebp+W_SET]
    "8D 04 81 "                             # lea eax, [ecx+eax*4]   # row of the wall side
    "8B 04 85 60 90 DC 00 "                 # mov eax, dword ptr ds:M07_ENTRY_ANIMS[eax*4]
    "85 C0 "                                # test eax, eax   # no anim in this phase: skip it
    "74 0F "                                # jz 4f
    "E8 BD 00 00 00 "                       # call m07_has_anim   # keeps eax when ZF=0, and edx
    "74 08 "                                # jz 4f   # not loaded: skip the phase
    "39 F0 "                                # cmp eax, esi
    "74 0B "                                # je .Lwant   # still playing
    "85 D2 "                                # test edx, edx
    "74 07 "                                # jz .Lwant   # the phase begins (edx = 0): set its anim
    # 4:
    "FF 45 1C "                             # inc dword ptr [ebp+W_PHASE]   # it ended (or is missing): next
                                            #   phase, which begins now
    "31 D2 "                                # xor edx, edx
    "EB CC "                                # jmp 3b
    # .Lwant:
    # m07_log_swanim:
    "39 F0 "                                # cmp eax, esi
    "74 09 "                                # je 5f
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 7F 5F 84 FF "                       # call FN_SET_ANIM
    "59 "                                   # pop ecx
    "58 "                                   # pop eax
    # 5:
    "3B 47 FC "                             # cmp eax, dword ptr [edi+M07_F_ANIM_SLIDE]
    "74 0C "                                # je 6f
    "8D 47 60 "                             # lea eax, [edi+M07_SF_ZERO]   # a phase anim: zero velocity
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 7E 53 84 FF "                       # call FN_SET_VELOCITY
    "59 "                                   # pop ecx
    "59 "                                   # pop ecx
    # 6:
    # facing: M07_SF_TMP = rd + w * (-n - rd), rd = m07_sway_f0, w = u u (3 - 2u),
    # u = (tau - TURN_START) / TURN_LENGTH clamped to >= 0; u >= 1 or no sway: -n
    "E8 FB FE FF FF "                       # call .Lsway_active
    "74 4B "                                # jz 9f
    "D8 67 E4 "                             # fsub dword ptr [edi+M07_F_TURN_START]
    "D8 77 E8 "                             # fdiv dword ptr [edi+M07_F_TURN_LENGTH]   # u
    "D9 E8 "                                # fld1
    "DF F1 "                                # fcomip st, st(1)
    "76 3D "                                # jbe 8f   # u >= 1: already facing the wall
    "D9 EE "                                # fldz
    "DB F1 "                                # fcomi st, st(1)
    "DA C1 "                                # fcmovb st, st(1)
    "DD D9 "                                # fstp st(1)   # max(u, 0)
    "D9 C0 "                                # fld st(0)
    "D8 C0 "                                # fadd st, st(0)
    "D8 6F F0 "                             # fsubr dword ptr [edi+M07_F_SWAY_THREE]   # 3 - 2u
    "D8 C9 "                                # fmul st, st(1)
    "DE C9 "                                # fmulp st(1), st   # w
    # rd = m07_sway_f0, his facing at the start
    "D9 45 54 "                             # fld dword ptr [ebp+W_F0]
    "D9 45 58 "                             # fld dword ptr [ebp+W_F0+4]   # st0 = rd.y, st1 = rd.x, st2 = w
    "D9 47 1C "                             # fld dword ptr [edi+M07_SF_TMP+4]
    "D8 E1 "                                # fsub st, st(1)
    "D8 CB "                                # fmul st, st(3)
    "DE C1 "                                # faddp st(1), st
    "D9 5F 1C "                             # fstp dword ptr [edi+M07_SF_TMP+4]
    "D9 47 18 "                             # fld dword ptr [edi+M07_SF_TMP]
    "D8 E1 "                                # fsub st, st(1)
    "DE CA "                                # fmulp st(2), st
    "DE C1 "                                # faddp st(1), st
    "D9 5F 18 "                             # fstp dword ptr [edi+M07_SF_TMP]
    "8D 47 18 "                             # lea eax, [edi+M07_SF_TMP]
    "50 "                                   # push eax
    "E8 EF 2F 6B FF "                       # call FN_FLATTEN_NORMALIZE
    "58 "                                   # pop eax
    # m07_log_swface:
    "EB 02 "                                # jmp 9f
    # 8:
    "DD D8 "                                # fstp st(0)
    # 9:
    "61 "                                   # popad
    "E9 07 06 00 00 "                       # jmp m07_set_facing
    # called by the slide frame (slide.s .Llateral) on frames with contact: ZF=1 (and the FPU stack
    # empty) when this slide's sway is not on; else ZF=0 and the scripted step replaces the stick:
    # M07_SF_LATERAL = s, left as it is (0) when LAT * dz <= M07_SWAY_EPS (dz >= 0: tau_prev <= tau
    # and both >= 0). Clobbers eax, edx, m07_sway_tmp.
    # m07_sway_stick:
    "E8 A3 FE FF FF "                       # call .Lsway_active
    "74 2E "                                # jz 9f
    "E8 B8 FE FF FF "                       # call .Lsway_curve   # F(tau)
    "D9 47 54 "                             # fld dword ptr [edi+M07_SF_PREV]
    "D8 65 04 "                             # fsub dword ptr [ebp+W_SLIDE_T0]
    "E8 AD FE FF FF "                       # call .Lsway_curve   # F(tau_prev)
    "DE E9 "                                # fsubp st(1), st
    "D8 4D 4C "                             # fmul dword ptr [ebp+W_K]   # step along t
    "D9 47 8C "                             # fld dword ptr [edi+M07_F_LAT]
    "D8 4F 50 "                             # fmul dword ptr [edi+M07_SF_DZ]
    "D8 57 F8 "                             # fcom dword ptr [edi+M07_F_SWAY_EPS]
    "DF E0 "                                # fnstsw ax
    "9E "                                   # sahf
    "76 07 "                                # jbe 1f   # LAT * dz <= EPS: no step
    "DE F9 "                                # fdivp st(1), st   # s = step / (LAT * dz)
    "D9 57 4C "                             # fst dword ptr [edi+M07_SF_LATERAL]
    "D9 EE "                                # fldz
    # m07_log_sws:
    # 1:
    "DE D9 "                                # fcompp
    "85 E4 "                                # test esp, esp   # ZF=0
    # 9:
    "C3 "                                   # ret
)

M07_ANIM_TABLE = bytes.fromhex(  # .m07_anim_table at 0xDC9672, source m07_wall_slide/anim_table.s
    # eax = animation id; ZF=1 if its slot in the Prince's table is empty or out of range.
    # anim = [[obj+0x14]], table = [anim+0x30], word [table] = count, slot = [table+8+id*4].
    # Clobbers ecx (and eax = 0 when out of range); keeps edx (m07_anims_ok counts in it, m07_entry_anim
    # keeps its phase-begins flag there) and, with ZF=0, eax (m07_entry_anim).
    # m07_has_anim:
    "8B 4B 14 "                             # mov ecx, [ebx+0x14]
    "8B 09 "                                # mov ecx, [ecx]
    "8B 49 30 "                             # mov ecx, [ecx+0x30]
    "66 3B 01 "                             # cmp ax, [ecx]   # count (ids are below 0x10000)
    "73 06 "                                # jae 1f
    "83 7C 81 08 00 "                       # cmp dword ptr [ecx+eax*4+8], 0
    "C3 "                                   # ret
    # 1:
    "31 C0 "                                # xor eax, eax
    "C3 "                                   # ret
    # m07_mods_end:
)

M07_SLIDE_TUNABLES = bytes.fromhex(  # .m07_slide_tunables at 0xDC9690, source m07_wall_slide/slide_tunables.s
    # ---- copied into the slide frame by the slide entry (slide.s): M07_F_COUNT dwords from
    # M07_FRAME_TUNABLES to M07_SF_TUNABLES, so the slide's code reads them as [edi+M07_F_*]
    # (slide.inc). The other code reads these addresses. Checked against slide.inc below. ----
    # M07_FRAME_TUNABLES:
    "00 00 10 40 "                          # M07_V0: .float 2.25   # descent speed at the start (units/s)
    "00 00 40 40 "                          # M07_ACC: .float 3.0   # descent acceleration (units/s^2)
    "00 00 A0 40 "                          # M07_VMAX: .float 5.0   # descent speed cap (units/s)
    "00 00 40 3F "                          # M07_LAT: .float 0.75   # sideways speed at full stick, as a
                                            #   fraction of the descent speed
    "00 00 00 3F "                          # M07_FRONT_COS: .float 0.5   # wall check: |ref . n| above this
                                            #   (cos 60 deg); 0x49FA30 minimum
    "CD CC CC 3D "                          # M07_GRACE: .float 0.1   # contact may drop out this long (s)
                                            #   before he falls
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
    "66 66 66 3F "                          # M07_SEARCH_REACH: .float 0.9   # search ray length along the
                                            #   facing
    "00 00 80 3F "                          # M07_SEARCH_Z: .float 1.0   # search ray height above the origin
    "A4 70 FD 3E "                          # M07_SEARCH_STAND: .float 0.495   # distance from the wall after
                                            #   the snap (contact distance)
    "9A 99 99 3E "                          # M07_SEARCH_MAX_NZ: .float 0.3   # wall must be near-vertical:
                                            #   |normal z| at most this
    "F3 B3 51 3F "                          # M07_OBLIQUE_COS: .float 0.81915204   # cos 35 deg: facing
                                            #   further than this from the wall at the start -> oblique set
                                            #   (user, 2026-11-26; the curtain splits at 45 deg, 0x51CAD4, but
                                            #   our V jump-off meets a wall at about 45 deg)
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
    "00 00 40 40 "                          # M07_SWAY_THREE: .float 3.0
    "00 00 00 40 "                          # M07_ENTRY_END: .float 2.0   # phase anims end at the latest this
                                            #   long after the start
    "17 B7 D1 38 "                          # M07_SWAY_EPS: .float 0.0001   # LAT * dz below this: no sway
                                            #   step this frame
    "6C 03 00 00 "                          # M07_ANIM_SLIDE: .long 0x36C   # slide animation (curtain loop)
    # ---- not copied (M07_ANIM_LET_GO, M07_ANIM_JUMP, M07_ANIM_JUMP_AIR follow M07_ANIM_SLIDE: mod.py checks)
    # ----
    "6D 03 00 00 "                          # M07_ANIM_LET_GO: .long 0x36D   # animation when he lets go
                                            #   (curtain let-go)
    "79 03 00 00 "                          # M07_ANIM_JUMP: .long 0x379   # jump-off animation (curtain)
    "78 03 00 00 "                          # M07_ANIM_JUMP_AIR:.long 0x378   # animation the airborne handler
                                            #   sets after the jump-off
    "CD CC 4C 3E "                          # M07_HOLD: .float 0.2   # C held at least this long (s) to start
    "00 00 80 3E "                          # M07_STALE: .float 0.25   # slide state older than this (s) is
                                            #   ignored
    "69 03 00 00 "                          # M07_KEEP_FIRST: .long 0x369   # first curtain animation kept in
                                            #   the table
    "11 00 00 00 "                          # M07_KEEP_COUNT: .long 17   # 0x369..0x379
    # the frame offsets in slide.inc
)

M07_SLIDE = bytes.fromhex(  # .m07_slide at 0xDC9730, source m07_wall_slide/slide.s
    # ---- exit to vanilla (before the entry: within short jumps of the contact entry) ----
    # m07_log_reject:
    # .Lvanilla_contact:
    "8D 5F 44 "                             # lea ebx, [edi+M07_SF_SIZE-0x2c]   # (pushad of the entry
                                            #   registers, sub esp,0x2c, ebx = esp); M02's
    "89 DC "                                # mov esp, ebx   # wall-run attempt reads no other register before
                                            #   its popad
    "E9 07 0A AF FF "                       # jmp m02_wallrun_attempt
    # ---- entry: eax = the wall contact result at m02_contact (non-zero), or 0 at M02's "no wall
    # contact" je (hook 1, m07_search) ----
    # m07_search:
    # m07_contact:
    "60 "                                   # pusha
    "BD 00 FD DB 00 "                       # mov ebp, m07_slide_vars
    "68 00 00 80 3F "                       # push 0x3F800000   # M07_SF_UP = (0, 0, 1), M07_SF_ZERO = (0, 0,
                                            #   0)
    "6A 00 "                                # push 0
    "6A 00 "                                # push 0
    "6A 00 "                                # push 0
    "81 EC E0 00 00 00 "                    # sub esp, M07_SF_PUSHED - M07_SF_TUNABLES
    "89 E7 "                                # mov edi, esp   # the tunables the slide reads, below the frame
                                            #   (slide.inc)
    "BE 90 96 DC 00 "                       # mov esi, offset M07_FRAME_TUNABLES
    "6A 20 "                                # push M07_F_COUNT
    "59 "                                   # pop ecx
    "F3 A5 "                                # rep movsd   # edi = the frame
    "91 "                                   # xchg ecx, eax   # ecx = contact (0: none), until the dispatch
                                            #   below
    "E8 CA 03 00 00 "                       # call m07_obj_now   # ebx = obj, esi = vars, eax = now, ZF=1: his
                                            #   slide is running
    "89 47 48 "                             # mov [edi+M07_SF_NOW], eax
    "0F 84 5E 01 00 00 "                    # jz .Lsliding
    "39 75 00 "                             # cmp [ebp+S_VARS], esi
    "75 04 "                                # jne .Lnotsliding
    "83 65 00 00 "                          # and dword ptr [ebp+S_VARS], 0   # his slide state is stale, or
                                            #   from the future (rewind): dropped
    # ---- not sliding: entry check (contact) or the search (no contact) ----
    # m07_entry:
    # .Lnotsliding:
    "E3 7A "                                # jecxz .Lsearch
    "E8 F2 03 00 00 "                       # call m07_start_ok   # (eax = now)
    "74 B2 "                                # jz .Lvanilla_contact
    "E8 93 F9 FF FF "                       # call m07_contact_gate   # height cap, edge, floor (checks.s; eax
                                            #   = now, ebp != 0)
    "72 AB "                                # jc .Lvanilla_contact
    "8D 47 18 "                             # lea eax, [edi+M07_SF_TMP]
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 C1 70 6C FF "                       # call FN_GET_FACING
    "E8 3D 04 00 00 "                       # call .Lget_normal
    "74 9A "                                # jz .Lvanilla_contact
    # orient n out of the wall: sum over contact points of (pos - p) . n must be >= 0
    "8D 47 24 "                             # lea eax, [edi+M07_SF_POS]
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 40 55 6C FF "                       # call FN_GET_POSITION
    "81 EC B4 00 00 00 "                    # sub esp, 15*12
    "89 E2 "                                # mov edx, esp
    "68 80 00 00 00 "                       # push 0x80
    "6A 0F "                                # push 15
    "52 "                                   # push edx
    "53 "                                   # push ebx
    "E8 1A 65 6D FF "                       # call FN_CONTACT_POINTS
    "91 "                                   # xchg ecx, eax
    "8D 54 24 10 "                          # lea edx, [esp+16]
    "D9 EE "                                # fldz
    # 1:
    "49 "                                   # dec ecx
    "78 19 "                                # js 2f
    "D9 47 24 "                             # fld dword ptr [edi+M07_SF_POS]
    "D8 22 "                                # fsub dword ptr [edx]
    "D8 0F "                                # fmul dword ptr [edi+M07_SF_NORMAL]
    "D9 47 28 "                             # fld dword ptr [edi+M07_SF_POS+4]
    "D8 62 04 "                             # fsub dword ptr [edx+4]
    "D8 4F 04 "                             # fmul dword ptr [edi+M07_SF_NORMAL+4]
    "DE C1 "                                # faddp st(1), st
    "DE C1 "                                # faddp st(1), st
    "83 C2 0C "                             # add edx, 12
    "EB E4 "                                # jmp 1b
    # 2:
    "E8 2E 04 00 00 "                       # call .Lflip_if_neg
    "E8 A7 FC FF FF "                       # call m07_sway_measure   # speed along the wall and his facing,
                                            #   before the slide frame
    # m07_log_entry:
    "E9 C8 00 00 00 "                       # jmp .Lstart
    # ---- the search (no wall contact): on a frame of state 0x412 without wall contact, when the
    # Prince is not sliding and m07_start_ok lets a slide start, one ray along the flat facing (in a
    # fall straight from a horizontal wall run, m07_side_rays, also to his right and to his left: a
    # run ends with the wall at his side). A near-vertical, wall-runnable wall within
    # M07_SEARCH_REACH whose normal is within 60 degrees of the reversed ray direction starts the
    # slide if m07_contact_gate allows it: he is moved to M07_SEARCH_STAND from the wall (where the
    # game reports contact) and his velocity is zeroed (else the fall's leftover velocity moves him
    # out of contact range after the snap). Then the slide state is set as for the contact entry and
    # this frame runs as the first slide frame (no movement), which turns him to face the wall.
    # The search fields of the slide frame (slide.inc): M07_SF_HIT_NORMAL, M07_SF_HIT_POINT,
    # M07_SF_RAY_DIR (the flat facing, turned for the side rays), M07_SF_RAY_SIDE. ----
    # .Lvanilla_nocontact:
    "8D 67 70 "                             # lea esp, [edi+M07_SF_SIZE]
    "61 "                                   # popa
    "E9 A6 3F 88 FF "                       # jmp AIR_NO_CONTACT
    # .Lsearch:
    "3B 1D 14 C4 D0 00 "                    # cmp ebx, dword ptr ds:PRINCE_ACTOR
    "75 EF "                                # jne .Lvanilla_nocontact
    "E8 70 03 00 00 "                       # call m07_start_ok   # (eax = now) C held long enough, re-entry
                                            #   and jump-off cooldowns, animations
    "74 E8 "                                # jz .Lvanilla_nocontact
    "8D 47 18 "                             # lea eax, [edi+M07_SF_RAY_DIR]   # ray direction = flat facing
                                            #   (0x47C620 sets z = 0 itself)
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 46 70 6C FF "                       # call FN_GET_FACING
    "8D 47 18 "                             # lea eax, [edi+M07_SF_RAY_DIR]
    "50 "                                   # push eax
    "E8 0D 2E 6B FF "                       # call FN_FLATTEN_NORMALIZE
    "8D 47 24 "                             # lea eax, [edi+M07_SF_POS]
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 C3 54 6C FF "                       # call FN_GET_POSITION
    "83 67 20 00 "                          # and dword ptr [edi+M07_SF_RAY_SIDE], 0   # 0 forward, 1 right, 2
                                            #   left
    "E8 0B FA FF FF "                       # call m07_try_ray   # (checks.s)
    "73 31 "                                # jnc .Lgot_wall
    "39 75 40 "                             # cmp [ebp+m07_side_rays-m07_slide_vars], esi   # side rays only
                                            #   after a horizontal run
    "75 BB "                                # jne .Lvanilla_nocontact
    "FE 47 20 "                             # inc byte ptr [edi+M07_SF_RAY_SIDE]
    "D9 47 18 "                             # fld dword ptr [edi+M07_SF_RAY_DIR]   # to his right: (f.y, -f.x)
    "8B 47 1C "                             # mov eax, [edi+M07_SF_RAY_DIR+4]
    "89 47 18 "                             # mov [edi+M07_SF_RAY_DIR], eax
    "D9 E0 "                                # fchs
    "D9 5F 1C "                             # fstp dword ptr [edi+M07_SF_RAY_DIR+4]
    "E8 EE F9 FF FF "                       # call m07_try_ray
    "73 14 "                                # jnc .Lgot_wall
    "FE 47 20 "                             # inc byte ptr [edi+M07_SF_RAY_SIDE]
    "0F BA 7F 18 1F "                       # btc dword ptr [edi+M07_SF_RAY_DIR], 31   # to his left: (-f.y,
                                            #   f.x)
    "0F BA 7F 1C 1F "                       # btc dword ptr [edi+M07_SF_RAY_DIR+4], 31
    "E8 DA F9 FF FF "                       # call m07_try_ray
    "72 8F "                                # jc .Lvanilla_nocontact
    # .Lgot_wall:
    "8B 47 48 "                             # mov eax, [edi+M07_SF_NOW]
    "E8 B5 F8 FF FF "                       # call m07_contact_gate   # height cap, edge, floor (checks.s;
                                            #   logged there)
    "72 85 "                                # jc .Lvanilla_nocontact
    # snap: position = hit point + n * STAND (height kept)
    "D9 47 CC "                             # fld dword ptr [edi+M07_F_SEARCH_STAND]
    "D9 C0 "                                # fld st(0)
    "D8 0F "                                # fmul dword ptr [edi+M07_SF_HIT_NORMAL]
    "D8 47 0C "                             # fadd dword ptr [edi+M07_SF_HIT_POINT]
    "D9 5F 24 "                             # fstp dword ptr [edi+M07_SF_POS]
    "D8 4F 04 "                             # fmul dword ptr [edi+M07_SF_HIT_NORMAL+4]
    "D8 47 10 "                             # fadd dword ptr [edi+M07_SF_HIT_POINT+4]
    "D9 5F 28 "                             # fstp dword ptr [edi+M07_SF_POS+4]
    "8D 47 24 "                             # lea eax, [edi+M07_SF_POS]
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 2D 57 6C FF "                       # call FN_SET_POSITION
    # every start: the speed along the wall and his facing, before the velocity zero (entry_anims.s)
    "E8 02 FC FF FF "                       # call m07_sway_measure
    # velocity zero: the snap position must hold
    "8D 47 60 "                             # lea eax, [edi+M07_SF_ZERO]
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 CE 50 84 FF "                       # call FN_SET_VELOCITY
    # marks: this slide is search-started (T0 is unique per slide), its start height; a side-ray
    # start (after a horizontal run) records the sway, the slide frame adopts the others
    "8B 47 48 "                             # mov eax, [edi+M07_SF_NOW]
    "89 45 20 "                             # mov [ebp+m07_search_t0-m07_slide_vars], eax
    "8B 4F 20 "                             # mov ecx, [edi+M07_SF_RAY_SIDE]
    "E3 0D "                                # jecxz 1f
    "89 45 48 "                             # mov [ebp+S_SWAY_T0], eax
    "83 65 1C 00 "                          # and dword ptr [ebp+S_PHASE], 0   # its animation is set on the
                                            #   first slide frame (tau = 0)
    "83 E1 01 "                             # and ecx, 1   # side ray 1 = wall on his right -> set 1, 2 -> set
                                            #   0
    "89 4D 60 "                             # mov [ebp+S_SET], ecx
    # 1:
    "8B 47 2C "                             # mov eax, [edi+M07_SF_POS+8]
    "89 45 24 "                             # mov [ebp+m07_search_z-m07_slide_vars], eax
    # m07_log_sstart:
    # ---- both starts (n in the frame): m07_slide_vars = esi, m07_slide_t0 = m07_slide_last (first
    # step: no movement) = m07_slide_contact = now, m07_slide_normal = n; +0x32C..+0x334 = 0 (no air
    # re-orientation toward the old jump direction). This frame runs as the first slide frame. ----
    # .Lstart:
    "8B 47 48 "                             # mov eax, [edi+M07_SF_NOW]
    "57 "                                   # push edi
    "89 EF "                                # mov edi, ebp
    "96 "                                   # xchg eax, esi
    "AB "                                   # stosd   # vars
    "96 "                                   # xchg eax, esi
    "AB "                                   # stosd   # T0
    "AB "                                   # stosd   # last
    "AB "                                   # stosd   # contact
    "31 C0 "                                # xor eax, eax
    "8D BE 2C 03 00 00 "                    # lea edi, [esi+0x32c]
    "AB "                                   # stosd
    "AB "                                   # stosd
    "AB "                                   # stosd
    "5F "                                   # pop edi
    "EB 29 "                                # jmp .Lstore_n
    # ---- sliding ----
    # m07_sliding:
    # .Lsliding:
    "E3 2E "                                # jecxz .Lno_contact
    "8D 55 10 "                             # lea edx, [ebp+S_NORMAL]   # reference = facing =
                                            #   -m07_slide_normal
    "E8 5B 03 00 00 "                       # call .Lneg_to_tmp
    "E8 F8 02 00 00 "                       # call .Lget_normal
    "74 1F "                                # jz .Lno_contact   # unusable contact counts as none
    # keep the orientation of the previous frame
    "D9 07 "                                # fld dword ptr [edi+M07_SF_NORMAL]
    "D8 4D 10 "                             # fmul dword ptr [ebp+S_NORMAL]
    "D9 47 04 "                             # fld dword ptr [edi+M07_SF_NORMAL+4]
    "D8 4D 14 "                             # fmul dword ptr [ebp+S_NORMAL+4]
    "DE C1 "                                # faddp st(1), st
    "E8 1F 03 00 00 "                       # call .Lflip_if_neg
    "8B 47 48 "                             # mov eax, [edi+M07_SF_NOW]
    "89 45 0C "                             # mov [ebp+S_CONTACT], eax   # the frame takes now ==
                                            #   m07_slide_contact as "contact"
    # .Lstore_n:
    "DF 2F "                                # fild qword ptr [edi+M07_SF_NORMAL]
    "DF 7D 10 "                             # fistp qword ptr [ebp+S_NORMAL]
    "EB 05 "                                # jmp .Lchecked
    # .Lno_contact:
    "DF 6D 10 "                             # fild qword ptr [ebp+S_NORMAL]   # n = the stored normal (x, y;
                                            #   bit-exact copy)
    "DF 3F "                                # fistp qword ptr [edi+M07_SF_NORMAL]
    # .Lchecked:
    "E8 07 01 00 00 "                       # call .Lchecks   # returns only when the slide goes on
    # m07_frame:
    # ---- slide frame ----
    "8B 45 08 "                             # mov eax, [ebp+S_LAST]
    "89 47 54 "                             # mov [edi+M07_SF_PREV], eax
    "8B 47 48 "                             # mov eax, [edi+M07_SF_NOW]
    "89 45 08 "                             # mov [ebp+S_LAST], eax
    "83 67 4C 00 "                          # and dword ptr [edi+M07_SF_LATERAL], 0
    # descent this frame dz = d(now - T0) - d(prev - T0), exact at any frame rate
    "D9 47 48 "                             # fld dword ptr [edi+M07_SF_NOW]
    "E8 55 04 00 00 "                       # call .Ldistance
    "D9 47 54 "                             # fld dword ptr [edi+M07_SF_PREV]
    "E8 4D 04 00 00 "                       # call .Ldistance
    "DE E9 "                                # fsubp st(1), st
    "D9 5F 50 "                             # fstp dword ptr [edi+M07_SF_DZ]
    "E8 FF 02 00 00 "                       # call .Lneg_n   # M07_SF_TMP = -n
    "E8 FA FB FF FF "                       # call m07_entry_anim   # entry phase animations, else the slide
                                            #   loop; facing = M07_SF_TMP (-n, turned during a sway)
    "E8 1D 03 00 00 "                       # call .Lfall_reset   # also M07_SF_POS = position
    "E8 E2 02 00 00 "                       # call .Ltangent
    "E8 70 03 00 00 "                       # call .Llateral   # s = |s|, t = sign(s) * t
    "74 51 "                                # jz .Lnolat
    # m07_frame_corner:
    # corner probe: from = pos + (0,0,PZ) + t*LOOK, delta = -n*REACH;
    # no hit or a non-runnable hit -> the wall ends sideways
    "D9 47 A4 "                             # fld dword ptr [edi+M07_F_CORNER_Z]
    "D9 47 9C "                             # fld dword ptr [edi+M07_F_CORNER_LOOK]
    "E8 C7 03 00 00 "                       # call .Lfrom
    "D9 EE "                                # fldz
    "D9 47 A0 "                             # fld dword ptr [edi+M07_F_CORNER_REACH]
    "D9 E0 "                                # fchs
    "89 FA "                                # mov edx, edi   # n
    "E8 E8 03 00 00 "                       # call .Lray_k
    "74 32 "                                # jz .Lcorner
    "68 FF FF 00 00 "                       # push 0xFFFF
    "53 "                                   # push ebx
    "E8 66 67 6D FF "                       # call FN_SURFACE_FLAGS
    "A9 00 00 03 00 "                       # test eax, SURFACE_NO_RUN_MASK
    "75 20 "                                # jnz .Lcorner
    # sideways clearance: from = pos + (0,0,PZ), delta = t*(BODY + s*LAT*dz);
    # a hit (a wall across the path) stops the sideways movement
    "D9 47 A4 "                             # fld dword ptr [edi+M07_F_CORNER_Z]
    "E8 92 03 00 00 "                       # call m07_from0
    "D9 EE "                                # fldz
    "D9 47 4C "                             # fld dword ptr [edi+M07_SF_LATERAL]
    "D8 4F 8C "                             # fmul dword ptr [edi+M07_F_LAT]
    "D8 4F 50 "                             # fmul dword ptr [edi+M07_SF_DZ]
    "D8 47 BC "                             # fadd dword ptr [edi+M07_F_SIDE_CLEARANCE]
    "8D 57 0C "                             # lea edx, [edi+M07_SF_TANGENT]
    "E8 B6 03 00 00 "                       # call .Lray_k
    "74 04 "                                # jz .Lnolat
    # m07_log_corner:
    # .Lcorner:
    "83 67 4C 00 "                          # and dword ptr [edi+M07_SF_LATERAL], 0
    # .Lnolat:
    # m07_frame_no_lateral:
    # floor: from = pos + (0,0,FZ), delta = (0,0,-(FZ+dz)); a hit -> he lands (land exit)
    "D9 47 50 "                             # fld dword ptr [edi+M07_SF_DZ]
    "D9 47 B8 "                             # fld dword ptr [edi+M07_F_FLOOR_RAY_Z]
    "E8 93 03 00 00 "                       # call m07_ray_down
    # m07_log_slg:
    "75 29 "                                # jnz .Lland_exit
    # pos += t*(s*LAT*dz) - (0,0,dz)
    "D9 47 50 "                             # fld dword ptr [edi+M07_SF_DZ]
    "D9 E0 "                                # fchs
    "D9 47 4C "                             # fld dword ptr [edi+M07_SF_LATERAL]
    "D8 4F 8C "                             # fmul dword ptr [edi+M07_F_LAT]
    "D8 4F 50 "                             # fmul dword ptr [edi+M07_SF_DZ]
    "8D 4F 24 "                             # lea ecx, [edi+M07_SF_POS]
    "E8 61 03 00 00 "                       # call .Lpos_plus
    "8D 47 24 "                             # lea eax, [edi+M07_SF_POS]
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 EE 55 6C FF "                       # call FN_SET_POSITION
    # m07_exits:
    # .Ldone:
    "8D 67 70 "                             # lea esp, [edi+M07_SF_SIZE]
    "61 "                                   # popa
    "E9 84 44 88 FF "                       # jmp AIR_HANDLER_FRAME_END
    # m07_fall:
    # Let go (C released, or the wall ended): outward speed OUT, the current descent speed, fall
    # animation. Land (floor ray hit): the same without the outward speed.
    # m07_log_land:
    # .Lland_exit:
    "D9 EE "                                # fldz
    "EB 03 "                                # jmp 1f
    # m07_log_fall:
    # .Lfall_exit:
    "D9 47 98 "                             # fld dword ptr [edi+M07_F_OUT]
    # 1:
    "83 65 00 00 "                          # and dword ptr [ebp+S_VARS], 0
    "D9 C0 "                                # fld st(0)
    "D8 4D 10 "                             # fmul dword ptr [ebp+S_NORMAL]
    "D9 5F 30 "                             # fstp dword ptr [edi+M07_SF_VELOCITY]
    "D8 4D 14 "                             # fmul dword ptr [ebp+S_NORMAL+4]
    "D9 5F 34 "                             # fstp dword ptr [edi+M07_SF_VELOCITY+4]
    # vz = -(V0 + ACC*tau_c) = -min(V0 + ACC*(now - T0), VMAX)
    "D9 47 48 "                             # fld dword ptr [edi+M07_SF_NOW]
    "E8 85 03 00 00 "                       # call .Ldistance   # leaves tau_c in M07_SF_DIST_TMP
    "DD D8 "                                # fstp st(0)
    "D9 47 58 "                             # fld dword ptr [edi+M07_SF_DIST_TMP]
    "D8 4F 84 "                             # fmul dword ptr [edi+M07_F_ACC]
    "D8 47 80 "                             # fadd dword ptr [edi+M07_F_V0]
    "D9 E0 "                                # fchs
    "D9 5F 38 "                             # fstp dword ptr [edi+M07_SF_VELOCITY+8]
    # as the curtain's bottom exit (0x594A41..0x594A82): start-fall with the let-go animation
    # (mode 4, dyn flag 0x40000000 cleared, state 0x412), then the velocity
    "8D 57 30 "                             # lea edx, [edi+M07_SF_VELOCITY]
    "E8 02 01 00 00 "                       # call m07_let_go
    "E8 4C 02 00 00 "                       # call .Lfall_reset
    "EB B7 "                                # jmp .Ldone
    # The slide goes on unless (then the exit, with this call's return address left on the stack):
    # - no usable contact for more than M07_GRACE (the paths with contact set m07_slide_contact = now),
    # an animation is missing or C is up: fall exit;
    # - Space (the jump gate below): jump exit.
    # .Lchecks:
    "D9 47 48 "                             # fld dword ptr [edi+M07_SF_NOW]
    "D8 65 0C "                             # fsub dword ptr [ebp+S_CONTACT]
    "D8 5F 94 "                             # fcomp dword ptr [edi+M07_F_GRACE]
    "DF E0 "                                # fnstsw ax
    "9E "                                   # sahf
    "77 B6 "                                # ja .Lfall_exit   # now - tcont > grace
    "E8 D5 02 00 00 "                       # call m07_anims_ok
    "74 AF "                                # jz .Lfall_exit
    "E8 93 01 00 00 "                       # call m07_c_down
    "74 A8 "                                # jz .Lfall_exit
    # Jump gate (the slide's Space test, instead of PressedWithin(jump, 0.2 s)), the vanilla rule (the
    # curtain's jump test at 0x5947xx needs phase >= 1 and an animation other than 0x376/0x377): calls
    # PressedWithin itself and reports "not pressed" (the slide goes on) while this slide's entry
    # phases run: grab (phase 0) of the sway sets (wall-run and oblique), grab + 0x377 (phases 0-1) of
    # the head-on set, and a fresh slide not adopted yet (tau < M07_ADOPT_WINDOW). Phases advance only
    # when their animation ends, so missing animations block nothing; tau < 0 (rewind) or >=
    # M07_ENTRY_END -> vanilla. A press in the last 0.2 s of the entry still fires when it ends (the
    # vanilla window). A press (the slide always jumps off then) records m07_jumpoff_time = now and
    # goes on to the jump exit. Clobbers eax, ecx, edx, m07_sway_tmp.
    # m07_jump_gate:
    "E8 A5 FA FF FF "                       # call m07_entry_tau   # edx = tau bits, ZF=1: this slide's sway
                                            #   record (entry_anims.s)
    "74 06 "                                # je 2f
    "3B 57 D8 "                             # cmp edx, dword ptr [edi+M07_F_ADOPT_WINDOW]   # no record yet:
                                            #   m07_entry_anim adopts it while 0 <= tau < HWIN
    "73 14 "                                # jae 6f
    # m07_log_jgate:
    "C3 "                                   # ret
    # 2:
    "3B 57 F4 "                             # cmp edx, dword ptr [edi+M07_F_ENTRY_END]
    "73 0E "                                # jae 6f   # tau < 0 (time went back) or tau >= AEND: phases over,
                                            #   vanilla
    "83 7D 1C 01 "                          # cmp dword ptr [ebp+S_PHASE], 1   # entry phases: 0 for every
                                            #   set, 1 for the head-on set 2 too
    "72 F4 "                                # jb m07_log_jgate
    "77 06 "                                # ja 6f
    "80 7D 60 02 "                          # cmp byte ptr [ebp+S_SET], 2
    "74 EC "                                # je m07_log_jgate
    # 6:
    "50 "                                   # push eax
    "89 E0 "                                # mov eax, esp
    "FF 77 B4 "                             # push dword ptr [edi+M07_F_JUMP_WINDOW]
    "6A 00 "                                # push 0
    "FF B6 B8 10 00 00 "                    # push dword ptr [esi+VARS_PAD_ID]
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 64 B6 93 FF "                       # call FN_PRESSED_WITHIN
    "83 C4 14 "                             # add esp, 20
    "58 "                                   # pop eax
    "85 C0 "                                # test eax, eax
    "75 01 "                                # jnz 1f
    "C3 "                                   # ret   # not pressed: the slide goes on
    # 1:
    "8B 47 48 "                             # mov eax, [edi+M07_SF_NOW]
    # m07_log_jrec:
    "89 45 64 "                             # mov [ebp+S_JUMPOFF], eax
    # m07_jump:
    # Space: the curtain jump-off sequence (0x5947xx). Space + side: 45 degrees toward the stick side.
    # .Ljump_exit:
    "83 65 00 00 "                          # and dword ptr [ebp+S_VARS], 0
    "E8 AB 01 00 00 "                       # call .Ltangent
    "E8 B4 01 00 00 "                       # call .Lneg_n   # M07_SF_TMP = facing for the jump = -n (the
                                            #   airborne handler flips it and jumps along +n)
    "E8 F5 01 00 00 "                       # call .Lstick_side   # M07_SF_LATERAL = stick_world . t (uses
                                            #   M07_SF_TMP = -n)
    "72 2C "                                # jb .Ljump_facing_set
    "E8 57 02 00 00 "                       # call .Labs_lat   # eax = |s| (float bits: ordered as the floats)
    "3B 47 AC "                             # cmp eax, dword ptr [edi+M07_F_JUMP_SIDE_MIN]
    "72 22 "                                # jb .Ljump_facing_set   # mostly forward/back: straight jump
    # facing = -(t*C45 + n*C45) = (-C45)*t + n*(-C45), t = sign(s) * t
    "D9 47 B0 "                             # fld dword ptr [edi+M07_F_COS45]
    "D9 E0 "                                # fchs
    "D9 C0 "                                # fld st(0)
    "D8 4F 0C "                             # fmul dword ptr [edi+M07_SF_TANGENT]
    "D9 07 "                                # fld dword ptr [edi+M07_SF_NORMAL]
    "D8 CA "                                # fmul st, st(2)
    "DE C1 "                                # faddp st(1), st
    "D9 5F 18 "                             # fstp dword ptr [edi+M07_SF_TMP]
    "D9 C0 "                                # fld st(0)
    "D8 4F 10 "                             # fmul dword ptr [edi+M07_SF_TANGENT+4]
    "D9 47 04 "                             # fld dword ptr [edi+M07_SF_NORMAL+4]
    "DE CA "                                # fmulp st(2), st
    "DE C1 "                                # faddp st(1), st
    "D9 5F 1C "                             # fstp dword ptr [edi+M07_SF_TMP+4]
    # .Ljump_facing_set:
    "E8 92 01 00 00 "                       # call .Lset_facing
    "83 A6 88 09 00 00 00 "                 # and dword ptr [esi+0x988], 0
    "FF 35 14 97 DC 00 "                    # push dword ptr ds:M07_ANIM_JUMP
    "53 "                                   # push ebx
    "E8 BC 3F 81 FF "                       # call FN_JUMP_ANIM
    "8D 86 DC 08 00 00 "                    # lea eax, [esi+VARS_TAKEOFF_POS]   # take-off position = position
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 0F 52 6C FF "                       # call FN_GET_POSITION
    "8B 86 E4 08 00 00 "                    # mov eax, [esi+VARS_TAKEOFF_Z]
    "89 86 04 02 00 00 "                    # mov [esi+VARS_FALL_START_Z], eax
    "83 A6 CC 04 00 00 00 "                 # and dword ptr [esi+VARS_FALLING], 0
    "6A 00 "                                # push 0
    "6A 13 "                                # push 0x13
    "53 "                                   # push ebx
    "E8 22 44 6D FF "                       # call FN_49DF10
    "68 9A 99 19 3E "                       # push 0x3E19999A   # 0.15f
    "8D 47 60 "                             # lea eax, [edi+M07_SF_ZERO]
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 83 16 88 FF "                       # call FN_START_AIRBORNE
    "8D 67 70 "                             # lea esp, [edi+M07_SF_SIZE]
    "61 "                                   # popa
    "E9 3D 43 88 FF "                       # jmp AIR_HANDLER_SWITCHED
    # m07_helpers:
    # ---- helpers (called with one return address on the stack; locals are addressed through edi,
    # the slide state through ebp) ----
    # ebx = obj, ecx = animation, edx = &velocity: start-fall 0x5EB660(obj, 0x2C, 0, 0, anim, 0x50, 10, 0)
    # (mode 4, dyn flag 0x40000000 cleared, state 0x412), then the velocity 0x60E960(obj, &v): the
    # curtain's bottom exit. Used by the slide's fall exits, the watchdog and the run cut. Clobbers
    # eax, ecx, edx.
    # m07_let_go:
    "8B 0D 10 97 DC 00 "                    # mov ecx, dword ptr ds:M07_ANIM_LET_GO
    # m07_start_fall:
    "52 "                                   # push edx
    "53 "                                   # push ebx
    "6A 00 "                                # push 0
    "6A 0A "                                # push 10
    "6A 50 "                                # push 0x50
    "51 "                                   # push ecx
    "6A 00 "                                # push 0
    "6A 00 "                                # push 0
    "6A 2C "                                # push 0x2C
    "53 "                                   # push ebx
    "E8 3F 1B 82 FF "                       # call FN_START_FALL
    "83 C4 20 "                             # add esp, 32
    "E8 37 4E 84 FF "                       # call FN_SET_VELOCITY
    "83 C4 08 "                             # add esp, 8
    "C3 "                                   # ret
    # ebx = the current object, esi = its vars ([[CURRENT_INST]+0x48]), then as m07_now. Used by the
    # slide entry and the ledge gate.
    # m07_obj_now:
    "8B 1D 48 4A D3 00 "                    # mov ebx, dword ptr ds:CURRENT_OBJ
    "8B 35 40 4A D3 00 "                    # mov esi, dword ptr ds:CURRENT_INST
    "8B 76 48 "                             # mov esi, dword ptr [esi+0x48]
    # eax = now = CLOCK - CLOCK_BASE rounded to a float (bits), as every slide time is stored; then as
    # m07_running. Used through m07_obj_now and by the watchdog and the run cut (which needs only
    # eax). Clobbers edx.
    # m07_now:
    "50 "                                   # push eax
    "D9 05 74 09 94 00 "                    # fld dword ptr ds:CLOCK
    "D8 25 18 33 CD 00 "                    # fsub dword ptr ds:CLOCK_BASE
    "D9 1C 24 "                             # fstp dword ptr [esp]
    "58 "                                   # pop eax
    # eax = now (float bits), esi = vars: edx = d = now - m07_slide_last (float bits) and ZF=1 when the
    # slide of esi is running: m07_slide_vars = esi and 0 <= d <= M07_STALE. Game time behind the last
    # slide frame (rewind, reload) is not running, as in the watchdog. d is compared as an int32 bit
    # pattern, unsigned: for d >= 0 that is the floats' order, a negative d is above any positive bound.
    # now is a rounded float, as stored in m07_slide_last: the unrounded now of a slide frame's own
    # call can be below its stored float (FPU above 24-bit precision), which read as game time behind
    # the slide (b43/b44: a search start dropped on its first frame). Used through m07_now and by
    # m07_start_ok. Keeps eax; clobbers edx.
    # m07_running:
    "50 "                                   # push eax
    "D9 04 24 "                             # fld dword ptr [esp]
    "D8 25 08 FD DB 00 "                    # fsub dword ptr ds:m07_slide_last
    "D9 1C 24 "                             # fstp dword ptr [esp]
    "5A "                                   # pop edx
    "39 35 00 FD DB 00 "                    # cmp dword ptr ds:m07_slide_vars, esi
    "75 0A "                                # jne 9f   # ZF=0
    "3B 15 20 97 DC 00 "                    # cmp edx, dword ptr ds:M07_STALE
    "77 02 "                                # ja 9f   # ZF=0
    "39 C0 "                                # cmp eax, eax   # ZF=1
    # 9:
    "C3 "                                   # ret
    # eax = now (float bits). ZF=1 (no start) unless M07_GRACE has passed since the last slide frame
    # (else a land exit just above the floor restarts the slide before vanilla lands him; unsigned
    # compare of the float bits: a negative difference, game time reset, never blocks), C is down and
    # held at least M07_HOLD, the jump-off cooldown has passed (now - m07_jumpoff_time >=
    # M07_JUMP_COOLDOWN, the same unsigned compare: a rewind to before the jump-off never blocks) and
    # the slide's animations are loaded; tested in this order. Used by the contact entry, the search
    # and the run cut. Keeps eax; clobbers ecx, edx.
    # m07_start_ok:
    "50 "                                   # push eax   # [esp] = now
    "E8 D9 FF FF FF "                       # call m07_running   # edx = now - m07_slide_last
    "3B 15 A4 96 DC 00 "                    # cmp edx, dword ptr ds:M07_GRACE
    "72 38 "                                # jb 8f
    "E8 37 00 00 00 "                       # call m07_c_down
    "74 33 "                                # jz 9f
    "D9 04 24 "                             # fld dword ptr [esp]
    "D8 A6 14 07 00 00 "                    # fsub dword ptr [esi+VARS_C_PRESS_TIME]
    "D8 1D 1C 97 DC 00 "                    # fcomp dword ptr ds:M07_HOLD
    "DF E0 "                                # fnstsw ax
    "9E "                                   # sahf
    "72 1D "                                # jb 8f   # held < HOLD
    "D9 04 24 "                             # fld dword ptr [esp]
    "D8 25 64 FD DB 00 "                    # fsub dword ptr ds:m07_jumpoff_time
    "50 "                                   # push eax
    "D9 1C 24 "                             # fstp dword ptr [esp]
    "58 "                                   # pop eax
    # m07_log_jcool:
    "3B 05 B0 90 DC 00 "                    # cmp eax, dword ptr ds:M07_JUMP_COOLDOWN
    "72 07 "                                # jb 8f
    "E8 41 01 00 00 "                       # call m07_anims_ok
    "58 "                                   # pop eax   # keeps ZF
    "C3 "                                   # ret
    # 8:
    "39 C0 "                                # cmp eax, eax   # ZF=1
    # 9:
    "58 "                                   # pop eax
    "C3 "                                   # ret
    # ZF=1 if C (pad bit 1) is not down (ebx = obj, esi = vars). Clobbers eax, ecx, edx.
    # m07_c_down:
    "50 "                                   # push eax   # out
    "89 E0 "                                # mov eax, esp
    "6A 01 "                                # push 1
    "FF B6 B8 10 00 00 "                    # push dword ptr [esi+VARS_PAD_ID]
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 86 48 95 FF "                       # call FN_IS_DOWN
    "83 C4 10 "                             # add esp, 16
    "58 "                                   # pop eax
    "85 C0 "                                # test eax, eax
    "C3 "                                   # ret
    # M07_SF_NORMAL = flattened contact normal of a runnable wall, using M07_SF_TMP as reference. ZF=1 if
    # none.
    # 0x49FA30 returns the first wall contact with |ref . n| > the minimum; M07_FRONT_COS = cos 60 deg, so
    # the wall must be within 60 degrees of the facing (entry) or of the current wall (sliding).
    # .Lget_normal:
    "57 "                                   # push edi   # &M07_SF_NORMAL
    "FF 77 90 "                             # push dword ptr [edi+M07_F_FRONT_COS]
    "8D 47 18 "                             # lea eax, [edi+M07_SF_TMP]
    "50 "                                   # push eax
    "68 80 00 00 00 "                       # push 0x80
    "53 "                                   # push ebx
    "E8 4C 5E 6D FF "                       # call FN_CONTACT_NORMAL
    "83 C4 14 "                             # add esp, 20
    "85 C0 "                                # test eax, eax
    "74 20 "                                # jz 9f
    "68 80 00 00 00 "                       # push 0x80
    "53 "                                   # push ebx
    "E8 DA 64 6D FF "                       # call FN_SURFACE_FLAGS
    "59 "                                   # pop ecx
    "59 "                                   # pop ecx
    "A9 00 00 03 00 "                       # test eax, SURFACE_NO_RUN_MASK
    "75 0A "                                # jnz 8f
    "57 "                                   # push edi
    "E8 1B 2A 6B FF "                       # call FN_FLATTEN_NORMALIZE
    "59 "                                   # pop ecx
    "85 E4 "                                # test esp, esp   # ZF=0
    "C3 "                                   # ret
    # 8:
    "39 C0 "                                # cmp eax, eax   # ZF=1
    # 9:
    "C3 "                                   # ret
    # st0 (popped) < 0 -> n = -n
    # .Lflip_if_neg:
    "D9 E4 "                                # ftst
    "DF E0 "                                # fnstsw ax
    "DD D8 "                                # fstp st(0)
    "9E "                                   # sahf
    "73 09 "                                # jae 1f
    "0F BA 3F 1F "                          # btc dword ptr [edi+M07_SF_NORMAL], 31
    "0F BA 7F 04 1F "                       # btc dword ptr [edi+M07_SF_NORMAL+4], 31
    # 1:
    "C3 "                                   # ret
    # M07_SF_TANGENT = (-n.y, n.x)
    # .Ltangent:
    "D9 47 04 "                             # fld dword ptr [edi+M07_SF_NORMAL+4]
    "D9 E0 "                                # fchs
    "D9 5F 0C "                             # fstp dword ptr [edi+M07_SF_TANGENT]
    "8B 07 "                                # mov eax, [edi+M07_SF_NORMAL]
    "89 47 10 "                             # mov [edi+M07_SF_TANGENT+4], eax
    "C3 "                                   # ret
    # M07_SF_TMP = -n; .Lneg_to_tmp: edx = &v: M07_SF_TMP = (-v.x, -v.y, 0)
    # .Lneg_n:
    "89 FA "                                # mov edx, edi
    # .Lneg_to_tmp:
    "D9 02 "                                # fld dword ptr [edx]
    "D9 E0 "                                # fchs
    "D9 5F 18 "                             # fstp dword ptr [edi+M07_SF_TMP]
    "D9 42 04 "                             # fld dword ptr [edx+4]
    "D9 E0 "                                # fchs
    "D9 5F 1C "                             # fstp dword ptr [edi+M07_SF_TMP+4]
    "83 67 20 00 "                          # and dword ptr [edi+M07_SF_TMP+8], 0
    "C3 "                                   # ret
    # facing = M07_SF_TMP (m07_entry_anim jumps here at its end). Clobbers eax, ecx, edx.
    # m07_set_facing:
    # .Lset_facing:
    "8D 47 64 "                             # lea eax, [edi+M07_SF_UP]
    "50 "                                   # push eax
    "8D 47 18 "                             # lea eax, [edi+M07_SF_TMP]
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 4F 66 6C FF "                       # call FN_SET_FACING
    "83 C4 0C "                             # add esp, 12
    "C3 "                                   # ret
    # +0x204 (fall start height) = current z (M07_SF_POS = position), +0x4CC (falling) = 1
    # .Lfall_reset:
    "8D 47 24 "                             # lea eax, [edi+M07_SF_POS]
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 81 50 6C FF "                       # call FN_GET_POSITION
    "59 "                                   # pop ecx
    "59 "                                   # pop ecx
    "8B 47 2C "                             # mov eax, [edi+M07_SF_POS+8]
    "89 86 04 02 00 00 "                    # mov [esi+VARS_FALL_START_Z], eax
    "6A 01 "                                # push 1
    "8F 86 CC 04 00 00 "                    # pop dword ptr [esi+VARS_FALLING]
    "C3 "                                   # ret
    # CF=1 if the stick is below M07_STICK_MIN; else M07_SF_LATERAL = (stick direction in world space) . t,
    # CF=0. The stick direction is the facing M07_SF_TMP rotated by -stick angle about up, exactly as
    # the jump executor builds it (0x5DD736).
    # .Lstick_side:
    "D9 86 78 0E 00 00 "                    # fld dword ptr [esi+0xe78]
    "D8 5F A8 "                             # fcomp dword ptr [edi+M07_F_STICK_MIN]
    "DF E0 "                                # fnstsw ax
    "9E "                                   # sahf
    "72 30 "                                # jb 9f
    "8D 47 3C "                             # lea eax, [edi+M07_SF_STICK]
    "50 "                                   # push eax
    "8B 86 44 0A 00 00 "                    # mov eax, [esi+0xa44]
    "0F BA F8 1F "                          # btc eax, 31   # -angle
    "50 "                                   # push eax
    "8D 47 64 "                             # lea eax, [edi+M07_SF_UP]
    "50 "                                   # push eax
    "8D 47 18 "                             # lea eax, [edi+M07_SF_TMP]
    "50 "                                   # push eax
    "E8 33 44 6B FF "                       # call FN_ROTATE
    "83 C4 10 "                             # add esp, 16
    "D9 47 3C "                             # fld dword ptr [edi+M07_SF_STICK]
    "D8 4F 0C "                             # fmul dword ptr [edi+M07_SF_TANGENT]
    "D9 47 40 "                             # fld dword ptr [edi+M07_SF_STICK+4]
    "D8 4F 10 "                             # fmul dword ptr [edi+M07_SF_TANGENT+4]
    "DE C1 "                                # faddp st(1), st
    "D9 5F 4C "                             # fstp dword ptr [edi+M07_SF_LATERAL]   # CF=0 from the add esp
                                            #   above
    # 9:
    "C3 "                                   # ret
    # lateral factor s (M07_SF_LATERAL, 0 on entry): the sway's scripted step, else
    # (stick_world . t) * min(mag, 1); 0 without contact this frame or with the stick idle. Then as .Labs_lat.
    # .Llateral:
    "8B 47 48 "                             # mov eax, [edi+M07_SF_NOW]
    "3B 45 0C "                             # cmp eax, [ebp+S_CONTACT]
    "75 22 "                                # jne .Labs_lat
    "E8 7D F9 FF FF "                       # call m07_sway_stick
    "75 1B "                                # jnz .Labs_lat
    "E8 AD FF FF FF "                       # call .Lstick_side
    "72 14 "                                # jb .Labs_lat
    "D9 E8 "                                # fld1
    "D9 86 78 0E 00 00 "                    # fld dword ptr [esi+0xe78]
    "DB F1 "                                # fcomi st, st(1)
    "DB C1 "                                # fcmovnb st, st(1)   # min(mag, 1)
    "DD D9 "                                # fstp st(1)
    "D8 4F 4C "                             # fmul dword ptr [edi+M07_SF_LATERAL]
    "D9 5F 4C "                             # fstp dword ptr [edi+M07_SF_LATERAL]
    # M07_SF_LATERAL = |s| and M07_SF_TANGENT = sign(s) * t (the products s*t stay bit-exact);
    # ZF=1 if s = +-0
    # .Labs_lat:
    "8B 47 4C "                             # mov eax, [edi+M07_SF_LATERAL]
    "01 C0 "                                # add eax, eax
    "73 0A "                                # jnc 1f
    "0F BA 7F 0C 1F "                       # btc dword ptr [edi+M07_SF_TANGENT], 31
    "0F BA 7F 10 1F "                       # btc dword ptr [edi+M07_SF_TANGENT+4], 31
    # 1:
    "D1 E8 "                                # shr eax, 1
    "89 47 4C "                             # mov [edi+M07_SF_LATERAL], eax
    "C3 "                                   # ret
    # ZF=1 unless the slide animation, the let-go animation and both jump-off animations are in the
    # Prince's table (M07_ANIM_SLIDE, M07_ANIM_LET_GO, M07_ANIM_JUMP, M07_ANIM_JUMP_AIR: consecutive
    # in slide_tunables.s, checked by mod.py). Clobbers eax, ecx, edx.
    # m07_anims_ok:
    "BA F4 FF FF FF "                       # mov edx, -12
    # 1:
    "8B 82 18 97 DC 00 "                    # mov eax, [M07_ANIM_SLIDE+12+edx]
    "E8 6F F9 FF FF "                       # call m07_has_anim   # keeps edx
    "74 05 "                                # jz 9f
    "83 C2 04 "                             # add edx, 4
    "7E EE "                                # jle 1b   # leaves with ZF=0 (edx = 4)
    # 9:
    "C3 "                                   # ret
    # st0 = z offset (popped): M07_SF_RAY_FROM = pos (x, y; bit-exact copy), pos.z + z offset.
    # Clobbers ecx. Also used by checks.s (its gate frame has M07_SF_POS and M07_SF_RAY_FROM).
    # m07_from0:
    "DF 6F 24 "                             # fild qword ptr [edi+M07_SF_POS]
    "DF 7F 30 "                             # fistp qword ptr [edi+M07_SF_RAY_FROM]
    "8D 4F 30 "                             # lea ecx, [edi+M07_SF_RAY_FROM]
    "EB 16 "                                # jmp .Lfrom_z
    # st0 = k, st1 = z offset (both popped): [ecx] = pos + k*t (x, y), pos.z + z offset;
    # .Lfrom: into M07_SF_RAY_FROM
    # .Lfrom:
    "8D 4F 30 "                             # lea ecx, [edi+M07_SF_RAY_FROM]
    # .Lpos_plus:
    "D9 C0 "                                # fld st(0)
    "D8 4F 0C "                             # fmul dword ptr [edi+M07_SF_TANGENT]
    "D8 47 24 "                             # fadd dword ptr [edi+M07_SF_POS]
    "D9 19 "                                # fstp dword ptr [ecx]
    "D8 4F 10 "                             # fmul dword ptr [edi+M07_SF_TANGENT+4]
    "D8 47 28 "                             # fadd dword ptr [edi+M07_SF_POS+4]
    "D9 59 04 "                             # fstp dword ptr [ecx+4]
    # .Lfrom_z:
    "D8 47 2C "                             # fadd dword ptr [edi+M07_SF_POS+8]
    "D9 59 08 "                             # fstp dword ptr [ecx+8]
    "C3 "                                   # ret
    # st0 = h, st1 = e (both popped): ray from pos + (0,0,h) straight down to e below pos, delta
    # (+0, +0, -(h + e)); eax = hit, ZF=1 if none. Clobbers ecx, edx. Also used by checks.s (gate frame).
    # m07_ray_down:
    "D9 C0 "                                # fld st(0)
    "E8 D1 FF FF FF "                       # call m07_from0   # pops the copy of h
    "DE C1 "                                # faddp st(1), st   # h + e
    "D9 E0 "                                # fchs
    "D9 EE "                                # fldz   # k = 0: x, y = +0 (v = M07_V0, M07_ACC: positive)
    "BA 90 96 DC 00 "                       # mov edx, offset M07_V0
    # st0 = k, st1 = z (both popped), edx = &v: ray from M07_SF_RAY_FROM along (k*v.x, k*v.y, z);
    # eax = hit, ZF=1 if none. Clobbers ecx, edx. Also used by checks.s (gate frame).
    # m07_ray_k:
    # .Lray_k:
    "D9 C0 "                                # fld st(0)
    "D8 0A "                                # fmul dword ptr [edx]
    "D9 5F 3C "                             # fstp dword ptr [edi+M07_SF_RAY_DELTA]
    "D8 4A 04 "                             # fmul dword ptr [edx+4]
    "D9 5F 40 "                             # fstp dword ptr [edi+M07_SF_RAY_DELTA+4]
    "D9 5F 44 "                             # fstp dword ptr [edi+M07_SF_RAY_DELTA+8]
    "6A 01 "                                # push 1
    "6A 00 "                                # push 0
    "6A 00 "                                # push 0
    "6A FF "                                # push -1
    "8D 47 3C "                             # lea eax, [edi+M07_SF_RAY_DELTA]
    "50 "                                   # push eax
    "8D 47 30 "                             # lea eax, [edi+M07_SF_RAY_FROM]
    "50 "                                   # push eax
    "53 "                                   # push ebx
    "E8 05 83 6D FF "                       # call FN_RAY
    "83 C4 1C "                             # add esp, 28
    "85 C0 "                                # test eax, eax
    "C3 "                                   # ret
    # st0 = time -> st0 = distance descended by then since T0 (tau = time - T0):
    # tc = (VMAX - V0)/ACC, tau_c = min(tau, tc), d = tau_c*(V0 + ACC*tau_c/2) + VMAX*(tau - tau_c)
    # .Ldistance:
    "D8 65 04 "                             # fsub dword ptr [ebp+S_T0]
    "D9 47 88 "                             # fld dword ptr [edi+M07_F_VMAX]
    "D8 67 80 "                             # fsub dword ptr [edi+M07_F_V0]
    "D8 77 84 "                             # fdiv dword ptr [edi+M07_F_ACC]   # st0 = tc, st1 = tau
    "DB F1 "                                # fcomi st, st(1)
    "DB C1 "                                # fcmovnb st, st(1)   # tau_c = min(tau, tc)
    "D9 5F 58 "                             # fstp dword ptr [edi+M07_SF_DIST_TMP]   # tau_c
    "D8 67 58 "                             # fsub dword ptr [edi+M07_SF_DIST_TMP]   # st0 = tau - tau_c
    "D8 4F 88 "                             # fmul dword ptr [edi+M07_F_VMAX]
    "D9 47 58 "                             # fld dword ptr [edi+M07_SF_DIST_TMP]
    "D8 4F 84 "                             # fmul dword ptr [edi+M07_F_ACC]
    "D8 4F C0 "                             # fmul dword ptr [edi+M07_F_HALF]
    "D8 47 80 "                             # fadd dword ptr [edi+M07_F_V0]
    "D8 4F 58 "                             # fmul dword ptr [edi+M07_SF_DIST_TMP]
    "DE C1 "                                # faddp st(1), st
    "C3 "                                   # ret
)

M07_ANIM_KEEP = bytes.fromhex(  # .m07_anim_keep at 0xDC9DA0, source m07_wall_slide/anim_keep.s
    # ---- m07_keep: hook at the start of the "remove animation set" function 0x497F20(dst, src).
    # For the Prince, the curtain animations (M07_KEEP_FIRST, M07_KEEP_COUNT of them, both arrays of the
    # table;
    # ids at or above the table's count are left to vanilla) get one extra reference before the
    # original runs; afterwards every slot it emptied gets its old pointer back (the table now owns
    # that reference), and the extra reference on a slot it left alone is released again. The next
    # "add set" releases the slot and installs its own, so the counts stay balanced.
    # shortcut: M07_KEEP_COUNT >= 1 (the id loop counts down to 0 after its first id), fine for the
    # 17 curtain ids.
    # 3:
    # m07_keep:
    "8B 44 24 04 "                          # mov eax, [esp+4]   # the first replaced instruction
    "3B 05 14 C4 D0 00 "                    # cmp eax, dword ptr ds:PRINCE_ACTOR
    "74 08 "                                # je 1f
    # m07_keep_vanilla:
    "8B 48 14 "                             # mov ecx, [eax+0x14]
    "E9 73 E1 6C FF "                       # jmp ANIM_REMOVE_SET_BODY
    # 1:
    "60 "                                   # pushad
    "89 E5 "                                # mov ebp, esp   # the pairs go below it; dst at [ebp+0x24], src
                                            #   at [ebp+0x28]
    "8B 70 14 "                             # mov esi, [eax+0x14]
    "8B 36 "                                # mov esi, [esi]
    "8B 76 30 "                             # mov esi, [esi+0x30]   # table: word count, +4 second array (or
                                            #   0), +8 first array
    "8B 3D 24 97 DC 00 "                    # mov edi, dword ptr ds:M07_KEEP_FIRST
    "8B 1D 28 97 DC 00 "                    # mov ebx, dword ptr ds:M07_KEEP_COUNT
    # .Lkeep_id:
    "66 3B 3E "                             # cmp di, [esi]   # (ids are below 0x10000)
    "73 28 "                                # jae .Lkeep_call   # this id and the ones after it are beyond the
                                            #   table
    "8D 44 BE 08 "                          # lea eax, [esi+edi*4+8]
    "8B 08 E3 07 50 51 E8 11 DB 6C FF "     # KEEP_SLOT
    "8B 46 04 "                             # mov eax, [esi+4]
    "85 C0 "                                # test eax, eax
    "74 0E "                                # jz 2f
    "8D 04 B8 "                             # lea eax, [eax+edi*4]
    "8B 08 E3 07 50 51 E8 FC DA 6C FF "     # KEEP_SLOT
    # 2:
    "47 "                                   # inc edi
    "4B "                                   # dec ebx
    "75 D3 "                                # jnz .Lkeep_id
    # .Lkeep_call:
    "8B 45 24 "                             # mov eax, [ebp+0x24]
    "FF 75 28 "                             # push dword ptr [ebp+0x28]
    "50 "                                   # push eax
    "E8 A8 FF FF FF "                       # call m07_keep_vanilla
    "59 "                                   # pop ecx
    "59 "                                   # pop ecx
    # .Lkeep_restore:
    "39 EC "                                # cmp esp, ebp
    "74 18 "                                # je m07_log_keepdone
    "58 "                                   # pop eax   # pointer
    "59 "                                   # pop ecx   # slot
    "87 01 "                                # xchg eax, [ecx]   # the slot holds the pointer again; eax = what
                                            #   vanilla left there:
    "85 C0 "                                # test eax, eax   # 0 = emptied (the table keeps our reference),
                                            #   else the pointer
    "74 F4 "                                # jz .Lkeep_restore   # itself (vanilla only writes zeros)
    "50 "                                   # push eax   # left alone: release our extra reference (&pointer,
                                            #   0)
    "89 E0 "                                # mov eax, esp
    "6A 00 "                                # push 0
    "50 "                                   # push eax
    "E8 63 DB 6C FF "                       # call FN_ANIM_RELEASE
    "83 C4 0C "                             # add esp, 12
    "EB E4 "                                # jmp .Lkeep_restore
    # m07_log_keepdone:
    "61 "                                   # popad
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
    # .m07_search at 0xDC90BC
    (0x5470BC, b"\xCC" * len(M07_SEARCH), M07_SEARCH),
    # .m07_checks at 0xDC9116
    (0x547116, b"\xCC" * len(M07_CHECKS), M07_CHECKS),
    # .m07_watchdog at 0xDC929F
    (0x54729F, b"\xCC" * len(M07_WATCHDOG), M07_WATCHDOG),
    # .m07_c_gate at 0xDC93F2
    (0x5473F2, b"\xCC" * len(M07_C_GATE), M07_C_GATE),
    # .m07_run_cut at 0xDC9428
    (0x547428, b"\xCC" * len(M07_RUN_CUT), M07_RUN_CUT),
    # .m07_entry_anims at 0xDC948A
    (0x54748A, b"\xCC" * len(M07_ENTRY_ANIMS), M07_ENTRY_ANIMS),
    # .m07_anim_table at 0xDC9672
    (0x547672, b"\xCC" * len(M07_ANIM_TABLE), M07_ANIM_TABLE),
    # .m07_slide_tunables at 0xDC9690
    (0x547690, b"\xCC" * len(M07_SLIDE_TUNABLES), M07_SLIDE_TUNABLES),
    # .m07_slide at 0xDC9730
    (0x547730, b"\xCC" * len(M07_SLIDE), M07_SLIDE),
    # .m07_anim_keep at 0xDC9DA0
    (0x547DA0, b"\xCC" * len(M07_ANIM_KEEP), M07_ANIM_KEEP),
    # M02 m02_contact pushad / sub esp,0x2C / mov ebx,esp -> jmp m07_contact ; nop (the cave replays
    # the three instructions when the slide does not apply)
    (0x4BA13B, bytes.fromhex("60 83 EC 2C 89 E3"), bytes.fromhex("E9 FA F5 50 00 90")),
    # remove animation set 0x497F20: mov eax,[esp+4] / mov ecx,[eax+0x14] -> jmp m07_keep ; nop ;
    # nop (the cave replays the two instructions)
    (0x97F20, bytes.fromhex("8B 44 24 04 8B 48 14"), bytes.fromhex("E9 7B 1E 93 00 90 90")),
    # PE header, .data VirtualSize 0x4AED00 -> 0x4AEE00 (maps the slide state at 0xDBFD00..,
    # zero-filled, inside the section's last page)
    (0x1D0, bytes.fromhex("00 ED 4A 00"), bytes.fromhex("00 EE 4A 00")),
    # hook 1: M02 m02_no_contact_je ("no wall contact" je 0x64D797) -> je m07_search
    (0x4BA135, bytes.fromhex("0F 84 5C 36 D9 FF"), bytes.fromhex("0F 84 FF F5 50 00")),
    # hook 2: 0x64CD81 mov eax,[0xD34A48] (before the ledge probe 0x546850) -> jmp m07_ledge_gate
    (0x24CD81, bytes.fromhex("A1 48 4A D3 00"), bytes.fromhex("E9 36 C3 77 00")),
    # hook 4: 0x630160 sub esp,0xe4 (per-frame airborne handler) -> jmp m07_watchdog ; nop
    (0x230160, bytes.fromhex("81 EC E4 00 00 00"), bytes.fromhex("E9 3A 91 79 00 90")),
    # hook 5: 0x725D9A call IsDown 0x71E450 (C held -> secondary-weapon throw) -> call m07_c_gate
    (0x325D9A, bytes.fromhex("E8 B1 86 FF FF"), bytes.fromhex("E8 53 36 6A 00")),
    # hook 6: 0x590FED run-continues branch -> je m07_run_cut (C during a horizontal run)
    (0x190FED, bytes.fromhex("0F 84 06 18 00 00"), bytes.fromhex("0F 84 35 84 83 00")),
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
