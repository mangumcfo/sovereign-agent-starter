#!/usr/bin/env python3
"""Join mid-sentence hard line-breaks inside ``` code/prompt blocks (the 'broken lines').
The book build uses white-space:pre-wrap, so joined long lines wrap cleanly. Bullets, headers,
blank lines, and sentence ends are preserved. Dry-run by default; --apply writes (with .bak)."""
import re, sys

def fix(text):
    lines = text.split("\n"); out=[]; infence=False; joins=0
    def is_break(line): return line.strip().startswith("```")
    def new_block(s):   # a line we must NOT join onto the previous (bullet/number/header/blank)
        return (not s.strip()) or re.match(r'^\s*([-*•]|\d+[.)]|[A-Z][A-Z /&]+:)\s', s) is not None
    for i, l in enumerate(lines):
        if is_break(l): infence = not infence; out.append(l); continue
        if not infence or not out:
            out.append(l); continue
        prev = out[-1]
        prev_open = bool(prev.strip()) and not re.search(r'[.!?:)\]]\s*$', prev) and not is_break(prev)
        cont = bool(l.strip()) and not new_block(l) and (l[:1].islower() or l.lstrip()[:1].isalnum() or l.startswith(("  ","\t")))
        if prev_open and cont:
            out[-1] = prev.rstrip() + " " + l.strip(); joins += 1
        else:
            out.append(l)
    return "\n".join(out), joins

if __name__ == "__main__":
    apply = "--apply" in sys.argv
    paths = [a for a in sys.argv[1:] if not a.startswith("--")]
    for p in paths:
        src = open(p, encoding="utf-8").read()
        fixed, n = fix(src)
        print(f"{p}: {n} mid-sentence breaks joined")
        if apply and n:
            open(p+".bak","w",encoding="utf-8").write(src)
            open(p,"w",encoding="utf-8").write(fixed)
            print(f"  applied (backup: {p}.bak)")
