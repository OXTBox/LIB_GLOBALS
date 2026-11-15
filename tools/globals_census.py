#!/usr/bin/env python3
"""globals_census.py - every LiveCode global the owner's scripts declare, in one register.

    python3 -I tools/globals_census.py              scan the default places, write the register
    python3 -I tools/globals_census.py PATH...      scan these files/folders instead
    options: --out GLOBALS.md  --json globals.json  --py python/lib_globals.py

Scans *.livecodescript (and LiveCode .txt scripts in the corpus) for `global` declarations.
For each global name it records where it is declared (projects, files), whether it is written
or only read, how it is used (indexed like an array, used in arithmetic, set to true/false),
the comment beside its declaration if any, and from that a Python equivalent type. It also
checks the naming habit most of them already follow (gWhatIsIt: g + CamelCase; not yet a
written rule, the owner confirms). A name that does
not follow it gets a proposed one; two names proposing the same new name are flagged.
Identical files (same content) are counted once. Writes GLOBALS.md (for people), globals.json
(for tools) and python/lib_globals.py (the Python twin: one entry per global).

P5: the owner's first register, the GAD_Globals stack (harvest XTJSON/batch/GAD_Globals,
custom property `GAD_Globals`: 165 names with a comment each), is merged in as the "GAD" column:
its owner / type / content. The harvest's `Defined_Globals` (where the stack keeps owner/type/
content per global) holds a single record under an empty name, so for the rest the values are
the ones the stack's own PropertiesToGadGlobalsArray gives every global (owner Application,
type Integer and content 0, or Boolean/false for a name starting with b), marked "(rule)".
Its comment is used as the purpose when nothing better is known.
"""
import argparse, collections, hashlib, json, os, re, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # LIB_GLOBALS
PROJECTS = os.path.dirname(HERE)
DEFAULT_PATHS = [
    'xtalk_py/corpus',                 # the script corpus
    'XTJSON/batch',                    # the 2026-11-13 harvests (scripts/ of each stack)
    'XTJSON/GAD_WORKING_03_16_2026',
    'Vibecode3D/XTJSON/scripts',       # the Vibecode3D engine's object scripts
    'LIB_GAMES/Vibecode3D_Games',
]
LIB_GLOB = 'LIB_*/livecode'            # every library's LiveCode
GLOBAL_RE = re.compile(r'^\s*global\s+(.+?)\s*(?:(?:--|#|//)\s*(.*))?$', re.I)
DATE_ONLY = re.compile(r'^[\d/:.\s-]*(?:AM|PM)?\s*$', re.I)   # a time stamp is not a purpose
RULE = re.compile(r'^g[A-Z][A-Za-z0-9]*$')
# the owner's prefixes (2026-11-15, LIB_LLMOUT/Read/LIB_GLOBALS/Clarification_to_Fable_questions.txt):
# t = temporary, p = parameter, b = boolean, ...A = a temporary array; a global array may end in Array
BOOL_RULE = re.compile(r'^b[A-Z][A-Za-z0-9]*$')     # bSomething: a boolean global, fine as it is
LEFTOVER = re.compile(r'^[tp][A-Z][A-Za-z0-9]*$')   # tSomething / pSomething declared global: a debugging leftover
ENGINE = {'it', 'the'}                 # never globals


def strip(line):
    """a line without comments and string literals (for usage counting)"""
    line = re.sub(r'"[^"]*"', '""', line)
    return re.split(r'--|#|//', line, maxsplit=1)[0]


def files_in(paths):
    seen, out = set(), []
    for p in paths:
        p = os.path.join(PROJECTS, p) if not os.path.isabs(p) else p
        cands = [p] if os.path.isfile(p) else [os.path.join(d, f) for d, _, fs in os.walk(p) for f in fs]
        for f in cands:
            low = f.lower()
            if 'zone.identifier' in low or not (low.endswith('.livecodescript') or
                                                (low.endswith('.txt') and '/corpus/' in f)):
                continue
            try:
                data = open(f, 'rb').read()
            except OSError:
                continue
            h = hashlib.sha1(data).hexdigest()
            if h in seen:
                continue
            seen.add(h)
            out.append((f, data.decode('latin-1').replace('\r\n', '\n').replace('\r', '\n')))
    return out


def project_of(path):
    rel = os.path.relpath(path, PROJECTS).split(os.sep)
    if rel[0] == 'XTJSON' and len(rel) > 2:
        return 'XTJSON/' + (rel[2] if rel[1] == 'batch' else rel[1])
    return rel[0]


def proposed(name):
    """gWhatIsIt from any name: sGame_root -> gGameRoot, bPaused -> gPaused, CenterX -> gCenterX"""
    core = name
    if re.match(r'^[gbs][A-Z]', core):           # g/b/s prefixes already mark a kind
        core = core[1:]
    words = [w for w in re.split(r'[_\W]+|(?<=[a-z0-9])(?=[A-Z])', core) if w]
    return 'g' + ''.join(w[:1].upper() + w[1:] for w in words) if words else 'g' + name


GAD_HARVEST = os.path.join(PROJECTS, 'XTJSON', 'batch', 'GAD_Globals', 'stack_GAD_Globals.json')


def load_gad(path=GAD_HARVEST):
    """{name.lower(): dict(name, comment, owner, type, content, by_rule)} from the GAD_Globals harvest"""
    try:
        custom = json.load(open(path, encoding='utf-8')).get('custom', {})
    except (OSError, ValueError):
        return {}
    defined = {k.lower(): v for k, v in (custom.get('Defined_Globals') or {}).items() if k}
    out = {}
    for name, comment in (custom.get('GAD_Globals') or {}).items():
        comment = re.sub(r'^\s*--\s*', '', str(comment or '')).strip()
        comment = re.sub(r'\s*--\s*[\d/:.\s-]*(?:AM|PM)?\s*$', '', comment, flags=re.I).strip()  # trailing time stamp
        if DATE_ONLY.match(comment) or comment.split()[:1] == [name]:   # a stamp, or the name pasted again
            comment = ''
        d = defined.get(name.lower())
        if d:
            rec = dict(owner=d.get('owner', ''), type=d.get('type', ''), content=d.get('content', ''), by_rule=False)
        elif name[:1] == 'b':
            rec = dict(owner='Application', type='Boolean', content=False, by_rule=True)
        else:
            rec = dict(owner='Application', type='Integer', content=0, by_rule=True)
        rec.update(name=name, comment=comment)
        out[name.lower()] = rec
    return out


def gad_cell(g):
    if not g:
        return '-'
    content = str(g['content']).lower() if isinstance(g['content'], bool) else g['content']
    return '%s / %s / %s%s' % (g['owner'], g['type'], content, ' (rule)' if g['by_rule'] else '')


def census(paths):
    reg = collections.OrderedDict()
    texts = files_in(paths)
    for f, text in texts:
        names_here = {}
        for line in text.split('\n'):
            m = GLOBAL_RE.match(line)
            if not m:
                continue
            for n in [x.strip() for x in m.group(1).split(',')]:
                if not re.match(r'^[A-Za-z_][\w.]*$', n) or n.lower() in ENGINE:
                    continue
                key = n.lower()                      # LiveCode names are case-insensitive
                e = reg.setdefault(key, dict(name=n, spellings=collections.Counter(), files=[], projects=collections.Counter(),
                                             writes=0, reads=0, indexed=0, arith=0, boolean=0, comments=[]))
                e['spellings'][n] += 1
                e['files'].append(os.path.relpath(f, PROJECTS))
                e['projects'][project_of(f)] += 1
                if m.group(2) and m.group(2) not in e['comments'] and len(e['comments']) < 3 \
                        and not DATE_ONLY.match(m.group(2).strip()):
                    e['comments'].append(m.group(2).strip()[:120])
                names_here[key] = n
        if not names_here:
            continue
        # usage of the globals this file declares
        for raw in text.split('\n'):
            line = strip(raw)
            if not line.strip() or GLOBAL_RE.match(raw):
                continue
            low = line.lower()
            for key in names_here:
                if key not in low:
                    continue
                if not re.search(r'(?<![\w.])' + re.escape(key) + r'(?![\w.])', low):
                    continue
                e = reg[key]
                k = re.escape(key)
                if re.search(r'\b(?:put|add|subtract|multiply|divide)\b.*\b(?:into|to|from|by)\s+' + k + r'\b', low) or \
                   re.search(r'\b(?:put|add|subtract)\b.*\b(?:into|to|from)\s+' + k + r'\s*\[', low) or \
                   re.search(r'\b(?:delete|split|combine|sort)\b[^\n]*\b' + k + r'\b', low):
                    e['writes'] += 1
                else:
                    e['reads'] += 1
                if re.search(k + r'\s*\[', low):
                    e['indexed'] += 1
                if re.search(r'\b(?:add|subtract|multiply|divide)\b.*\b' + k + r'\b', low) or \
                   re.search(k + r'\s*[-+*/](?!\s*["&])|(?<![&"])[-+*/]\s*' + k + r'\b', low):
                    # (comparisons < > are not arithmetic: `gList > ""`, `number of lines of gList > 0`)
                    e['arith'] += 1
                if re.search(r'\bput\s+(?:true|false)\s+into\s+' + k + r'\b', low) or \
                   re.search(k + r'\s+is\s+(?:not\s+)?(?:true|false)\b', low):
                    e['boolean'] += 1
    # Python twin and naming
    props = collections.defaultdict(list)
    for key, e in reg.items():
        e['name'] = e['spellings'].most_common(1)[0][0]
        e['pytype'] = ('dict' if e['indexed'] else 'bool' if e['boolean'] and not e['arith'] else
                       'float' if e['arith'] else 'str')
        e['follows'] = bool(RULE.match(e['name']) or BOOL_RULE.match(e['name']))
        e['leftover'] = bool(LEFTOVER.match(e['name']))
        e['proposed'] = e['name'] if e['follows'] else proposed(e['name'])
        props[e['proposed'].lower()].append(e['name'])
    for key, e in reg.items():
        clash = [n for n in props[e['proposed'].lower()] if n.lower() != key]
        e['clash'] = clash
    return reg, len(texts)


def purpose_of(e, purposes, gad):
    g = gad.get(e['name'].lower())
    return purposes.get(e['name'].lower()) or '; '.join(e['comments']) or (g['comment'] if g else '')


def write_md(reg, nfiles, path, gad):
    rows = sorted(reg.values(), key=lambda e: (-sum(e['projects'].values()), e['name'].lower()))
    ok = sum(1 for e in rows if e['follows'])
    out = ['# Globals register (generated by tools/globals_census.py)', '',
           'Every `global` declared in the scanned LiveCode (%d distinct script files). %d globals; '
           '%d follow the owner\'s naming (`gWhatIsIt`, or `bWhatIsIt` for a boolean: "ok (b)"), %d do not '
           '(proposed name given; "leftover?" = a `t`/`p` name declared global, which by the owner\'s prefixes '
           '(t temporary, p parameter) is a debugging leftover: drop the global declaration and see what breaks). Python is '
           'the equivalent type in `python/lib_globals.py`, judged from use: indexed -> dict, '
           'set to true/false -> bool, arithmetic -> float, else str. "W/R" = lines writing / reading '
           'it. Purpose: the comment beside its declaration where there is one; the rest is to be '
           'written (in `PURPOSES.md`, which this tool merges in). GAD = owner / type / content in the '
           'owner\'s GAD_Globals register (%d globals there, %d of them declared in the scanned scripts; '
           '"(rule)" = the stack\'s default, not a saved value); its comment is the purpose of last resort.'
           % (nfiles, len(rows), ok, len(rows) - ok, len(gad), sum(1 for k in gad if k in reg)), '',
           '| Global | Rule | Proposed | Python | W/R | Declared in | GAD | Purpose |', '|---|---|---|---|---|---|---|---|']
    purposes = load_purposes()
    for e in rows:
        where = ', '.join('%s (%d)' % (p, n) if n > 1 else p for p, n in e['projects'].most_common(4))
        if len(e['projects']) > 4:
            where += ' +%d' % (len(e['projects']) - 4)
        purpose = purpose_of(e, purposes, gad)
        flag = ('ok (b)' if BOOL_RULE.match(e['name']) else 'ok') if e['follows'] else \
            'leftover?' if e['leftover'] else 'rename'
        prop = e['proposed'] + (' **clash: %s**' % ', '.join(e['clash']) if e['clash'] else '')
        prop_cell = '-' if e['follows'] else 'drop the global?' if e['leftover'] else '`%s`' % prop
        out.append('| `%s` | %s | %s | %s | %d/%d | %s | %s | %s |' % (e['name'], flag, prop_cell,
                                                                     e['pytype'], e['writes'], e['reads'], where,
                                                                     gad_cell(gad.get(e['name'].lower())),
                                                                     purpose.replace('|', '/')))
    missing = sorted(g['name'] for k, g in gad.items() if k not in reg)
    if missing:
        out += ['', '## In the GAD_Globals register but not declared in any scanned script (%d)' % len(missing), '',
                ', '.join('`%s`' % n for n in missing)]
    open(path, 'w', encoding='utf-8').write('\n'.join(out) + '\n')


def load_purposes():
    """PURPOSES.md lines like `gName - what it is for` (written by people, kept by the tool)"""
    p = os.path.join(HERE, 'PURPOSES.md')
    out = {}
    if os.path.exists(p):
        for line in open(p, encoding='utf-8'):
            m = re.match(r'^\s*[-*]?\s*`?(\w[\w.]*)`?\s+-\s+(.+)$', line)
            if m:
                out[m.group(1).lower()] = m.group(2).strip()
    return out


def write_json(reg, path, gad):
    data = {e['name']: dict(proposed=e['proposed'], follows=e['follows'], python=e['pytype'],
                            writes=e['writes'], reads=e['reads'], projects=dict(e['projects']),
                            files=sorted(set(e['files']))[:20], comments=e['comments'], clash=e['clash'],
                            gad=gad.get(e['name'].lower()))
            for e in sorted(reg.values(), key=lambda e: e['name'].lower())}
    json.dump(data, open(path, 'w', encoding='utf-8'), indent=1)


def write_py(reg, path, gad):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = ['"""lib_globals - the Python twin of the LiveCode globals register (generated by',
             'LIB_GLOBALS/tools/globals_census.py; do not edit by hand, edit PURPOSES.md and re-run).',
             '',
             'GLOBALS[name] = (python type, proposed gWhatIsIt name, purpose). new_state() gives a dict with',
             'every global at its empty value, the way a fresh LiveCode engine starts."""', '',
             'GLOBALS = {']
    purposes = load_purposes()
    for e in sorted(reg.values(), key=lambda e: e['name'].lower()):
        purpose = purpose_of(e, purposes, gad)
        lines.append('    %r: (%s, %r, %r),' % (e['name'], e['pytype'], e['proposed'], purpose))
    lines += ['}', '', '', 'def new_state():',
              '    """every global at its empty value (LiveCode globals start empty)"""',
              '    return {name: kind() for name, (kind, _, _) in GLOBALS.items()}', '']
    open(path, 'w', encoding='utf-8').write('\n'.join(lines))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('paths', nargs='*')
    ap.add_argument('--out', default=os.path.join(HERE, 'GLOBALS.md'))
    ap.add_argument('--json', default=os.path.join(HERE, 'globals.json'))
    ap.add_argument('--py', default=os.path.join(HERE, 'python', 'lib_globals.py'))
    a = ap.parse_args()
    paths = a.paths or DEFAULT_PATHS + sorted(os.path.relpath(p, PROJECTS) for p in
                                              __import__('glob').glob(os.path.join(PROJECTS, LIB_GLOB)))
    reg, n = census(paths)
    gad = load_gad()
    write_md(reg, n, a.out, gad)
    write_json(reg, a.json, gad)
    write_py(reg, a.py, gad)
    ok = sum(1 for e in reg.values() if e['follows'])
    print('%d script files, %d globals: %d follow the naming (gName, bName), %d to rename or drop, %d proposed-name clashes; '
          'GAD register: %d, %d declared here -> %s'
          % (n, len(reg), ok, len(reg) - ok, sum(1 for e in reg.values() if e['clash']),
             len(gad), sum(1 for k in gad if k in reg), a.out))


if __name__ == '__main__':
    sys.exit(main())
