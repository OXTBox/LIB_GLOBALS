#!/usr/bin/env python3
"""LIB_GLOBALS's check that runs without LiveCode (A-50): the census on two small scripts made in a
temporary folder (declarations, writes and reads, the Python type guess, the gWhatIsIt rule and a
proposed name). It writes to the temporary folder only, never GLOBALS.md.

    python3 -I tests/run_tests.py
"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import tempfile
import globals_census as gc                   # noqa: E402

CHECKS, FAILS = [0], []


def check(name, ok, got=None):
    CHECKS[0] += 1
    if not ok:
        FAILS.append(name)
        print("FAIL  %s%s" % (name, "" if got is None else "  (got %r)" % (got,)))
    else:
        print("ok    %s" % name)


def done():
    print("\n%d of %d passed" % (CHECKS[0] - len(FAILS), CHECKS[0]))
    return 1 if FAILS else 0


A = """global gScore, bPaused -- the score; paused flag
global sGame_root
on mouseUp
   add 10 to gScore
   put true into bPaused
   put "x" into sGame_root
end mouseUp
"""
B = """global gScore
global gGrid
on draw
   put gScore into field 1
   put 1 into gGrid[2]
end draw
"""


def main():
    with tempfile.TemporaryDirectory() as root:
        for name, text in (('a.livecodescript', A), ('b.livecodescript', B), ('c.livecodescript', A)):
            open(os.path.join(root, name), 'w').write(text)
        reg, n = gc.census([root])
        check('identical files count once', n == 2, n)
        check('four globals found', sorted(reg) == ['bpaused', 'ggrid', 'gscore', 'sgame_root'], sorted(reg))
        check('gScore: arithmetic -> float', reg['gscore']['pytype'] == 'float', reg['gscore']['pytype'])
        check('bPaused: true/false -> bool', reg['bpaused']['pytype'] == 'bool', reg['bpaused']['pytype'])
        check('gGrid: indexed -> dict', reg['ggrid']['pytype'] == 'dict', reg['ggrid']['pytype'])
        check('gScore is written and read', reg['gscore']['writes'] >= 1 and reg['gscore']['reads'] >= 1)
        check('sGame_root breaks the rule, proposed gGameRoot', not reg['sgame_root']['follows']
              and reg['sgame_root']['proposed'] == 'gGameRoot', reg['sgame_root']['proposed'])
        check('the declaration comment is kept', reg['gscore']['comments'][:1] == ['the score; paused flag'], reg['gscore']['comments'])
        out = os.path.join(root, 'G.md')
        gc.write_md(reg, n, out, {})
        check('the register is written', '| `gScore` | ok |' in open(out).read())
    return done()


if __name__ == '__main__':
    sys.exit(main())
