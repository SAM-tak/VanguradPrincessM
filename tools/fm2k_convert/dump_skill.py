"""Print skills as one line per block, for reading them while porting to L^.

usage: dump_skill.py <fm2ndparser json> <skill number>...
"""

import json
import sys

# Fields that only restate other fields, or that are almost always at their default.
QUIET = {"index", "type", "blockType", "varName", "useEvenVarName",
         "in", "depthEnabled", "fails", "levelCancelCondition", "replace", "out",
         "damageRateEnabled", "aEnabled"}


def ref(v):
    if isinstance(v, dict) and "number" in v:
        s = "#%d" % v["number"]
        if "block" in v:
            s += ":%d" % v["block"]
        return s
    return v


def fmt(b):
    parts = []
    for k, v in b.items():
        if k in QUIET or v is False or v is None:
            continue
        if isinstance(v, dict) and "number" in v:
            if v["number"] == 0 and not v.get("block"):
                continue
            v = ref(v)
        elif isinstance(v, dict):
            v = {kk: vv for kk, vv in v.items() if vv}
            if not v:
                continue
        elif isinstance(v, list):
            v = len(v)
        if v is True:
            parts.append(k)
        else:
            parts.append("%s=%s" % (k, v))
    return " ".join(parts)


def main():
    d = json.load(open(sys.argv[1], encoding="utf-8-sig"))
    for n in map(int, sys.argv[2:]):
        s = d["skills"][n]
        print("== #%d %s" % (n, s["name"]))
        for i, b in enumerate(s["blocks"]):
            print("  %3d %-8s %s" % (i, b["type"], fmt(b)))


if __name__ == "__main__":
    main()
