"""Read what fm2ndparser leaves out about demos, straight from the game's files,
into assets/system/<game>/demos.lton:

- the game's demo assignment (the .kgt's KgtGameDemoConfig, 8 bytes): which
  demo is the title, the select screens, the continue screen, the opening;
- each demo's own settings (the last 1,033 bytes of a .demo): "skip with
  input" and its total time.

Layouts: wanwan docs/editor/system_settings.md (demoConfig at 0x0E428 of the
system data block, whose demoNames[100] of 256 bytes each start at 0x08028;
KgtDemoConfig = bgm u16, pressToSkip u8, 2 bytes, totalTime u32).
See TechnicalDocuments/0016.

usage: read_demos.py <game dir> <assets dir>
"""

import argparse
import struct
from pathlib import Path

DEMO_NAMES = 0x08028
DEMO_CONFIG = 0x0E428
# The order of KgtGameDemoConfig's bytes. The ids count from 1 (0 = none).
CONFIG_KEYS = ["title", "storySelect", "vsSelect", "teamSelect", "continueScreen", "opening", "tag1", "tag2"]


def lton_str(s):
    return '"%s"' % s.replace("\\", "\\\\").replace('"', '\\"')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("game", type=Path)
    ap.add_argument("assets", type=Path)
    args = ap.parse_args()

    kgt = next(args.game.glob("*.kgt"))
    b = kgt.read_bytes()
    names = []
    # The first demo name locates the system data block (its offset in the
    # file depends on what comes before it).
    demos = sorted(p.stem for p in args.game.glob("*.demo"))
    base = None
    for n in demos:
        i = b.find(n.encode("cp932") + b"\0")
        if i >= 0:
            # the name found may be any entry: step back to entry 0
            for k in range(100):
                start = i - DEMO_NAMES - 256 * k
                if start >= 0:
                    first = b[start + DEMO_NAMES:start + DEMO_NAMES + 32].split(b"\0")[0]
                    if first and first.decode("cp932", "replace") in demos:
                        head = [b[start + DEMO_NAMES + 256 * j:start + DEMO_NAMES + 256 * j + 32].split(b"\0")[0]
                                for j in range(len(demos))]
                        if all(h.decode("cp932", "replace") in demos for h in head):
                            base = start
                            break
            if base is not None:
                break
    if base is None:
        raise SystemExit("demo names not found in %s" % kgt)
    for j in range(100):
        n = b[base + DEMO_NAMES + 256 * j:base + DEMO_NAMES + 256 * j + 32].split(b"\0")[0].decode("cp932", "replace")
        if not n:
            break
        names.append(n)
    config = b[base + DEMO_CONFIG:base + DEMO_CONFIG + 8]

    lines = ["# Read from %s and the .demo files by tools/fm2k_convert/read_demos.py." % kgt.name,
             "# The demos the engine plays for each part of the game (TechnicalDocuments/0016)."]
    for key, idx in zip(CONFIG_KEYS, config):
        name = names[idx - 1] if 0 < idx <= len(names) else ""
        lines.append("%s = %s," % (key, lton_str(name)))
    lines.append("# Each demo: skip with a button, and its total time in frames (0: none).")
    lines.append("demos = {")
    for n in names:
        p = args.game / (n + ".demo")
        if not p.exists():
            continue
        t = p.read_bytes()[-1033:]
        skip = t[2] != 0
        time = struct.unpack("<I", t[5:9])[0]
        lines.append("    { name = %s, skip = %s, time = %d }," % (lton_str(n), "true^" if skip else "false^", time))
    lines.append("},")

    out = args.assets / "system" / kgt.stem / "demos.lton"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("->", out)


if __name__ == "__main__":
    main()
