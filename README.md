# Warrior Within movement mods

Movement mods for **Prince of Persia: Warrior Within** (Steam, 2004), applied as a byte patch to
`POP2.EXE`. This repository contains only the patcher script; no game files are included or
distributed. You need your own Steam copy of the game.

## What it changes

- **Jump key.** A new "Jump" action in *Options > Controls*, listed after Roll/Jump, default **V**.
  It acts like Space everywhere, except that direction + Jump is a forward jump instead of a roll.
  Space itself is unchanged (direction + Space still rolls). The key can be rebound like any other
  action (gamepad binding is untested). Existing profiles start with the new action unbound: bind
  it in the menu or choose *Default settings*.
- **Wall-run addon.** Hold the wall-run button (right mouse by default) while jumping or
  rebounding into a wall at an angle (not head-on) to start a horizontal wall run from mid-air.
  Keep holding it to chain runs.
- **Stairs-jump fix.** A normal jump can no longer land before its apex. This fixes the instant
  landing when jumping up a slope or stairs near an edge, a bug also present in the original game.

## Requirements

- The Steam version of the game, with an unmodified `POP2.EXE`
  (sha256 `5559117d013155bbad608cedc2fd0dd272f37ed92c936fc4e151287f3b5ff1cb`).
- Python 3.8 or newer. No other dependencies.

## Install

1. Back up `POP2.EXE` from the game folder.
2. Run:

   ```
   python pop2_movement_patch.py "<game folder>/POP2.EXE" [output path]
   ```

   The output defaults to `POP2_patched.EXE` next to the input. The input is never modified.
3. Replace `POP2.EXE` with the patched file (rename it to `POP2.EXE`).

The script refuses any input that is not the original Steam exe, checks every byte before changing
it, and verifies the sha256 of the result
(`88193b3d610c10c8ebe33a5cfb25fd27c59c2f27d6a6b81a92ecb676a817f926`).
If you previously applied an older version of these mods, restore the original exe first (from your
backup, or *Steam > Properties > Installed Files > Verify integrity*).

## Uninstall

Restore your backup of `POP2.EXE`, or let Steam verify the game files.

## Repository layout

| File | Purpose |
|---|---|
| `pop2_movement_patch.py` | The patcher. Use this one. |
| `patch_jump.py`, `patch_wallrun.py` | Early per-mod development scripts, kept for history. They produce the older Shift+Space jump addon and are superseded. |

## Disclaimer

Unofficial fan modification, not affiliated with or endorsed by Ubisoft. Prince of Persia is a
trademark of Ubisoft Entertainment. Use at your own risk and keep a backup.

## License

The patcher scripts are released under the [MIT License](LICENSE). This covers the scripts only,
not the game or its files.
