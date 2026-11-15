# LIB_GLOBALS

The owner's note (`Register_and_Reuse_all_globals.txt`): register every LiveCode global name,
what it is used for and its Python equivalent, so standalone scripts can reuse them without
breaking anything when compiled together with other scripts. LIB_SYSTEM TODO A-35.

| File | What |
|---|---|
| `GLOBALS.md` | the register, for people: every global, whether it follows `gWhatIsIt`, a proposed name if not, Python type, writes/reads, where declared, purpose |
| `globals.json` | the same, for tools |
| `python/lib_globals.py` | the Python twin: `GLOBALS[name] = (type, proposed name, purpose)`, `new_state()` |
| GAD column | P5: owner / type / content from the owner's 2024 GAD_Globals stack (165 globals). Only the comments were saved per global; owner/type/content are the stack's default rule, marked "(rule)". That rule calls every name starting with b Boolean, so `buildItem` (an item number) shows Boolean: trust the comment |
| `PURPOSES.md` | purposes written by people (`gName - what it is for`); the tool keeps them |
| `tools/globals_census.py` | makes the three generated files; `--help` |

All three generated files are rebuilt by:

    python3 -I tools/globals_census.py

Sources: the script corpus (`xtalk_py/corpus`), the XTJSON harvests, the Vibecode3D engine
scripts, `LIB_GAMES/Vibecode3D_Games`, every `LIB_*/livecode`. Identical files count once.

**How it judges the Python type** (a guess from use, check before relying on it): indexed
`g[...]` → dict; set to / compared with true/false and never used in arithmetic → bool;
`add`/`subtract`/`+ - * /` → float; anything else → str (LiveCode lists are text).

**Not decided yet (owner):** `gWhatIsIt` is the habit most globals follow, not a written rule;
the 119 renames are proposals only, nothing in any script was renamed. Six proposals clash
(two old names would become one), marked **clash** in the register.
