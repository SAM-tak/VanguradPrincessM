# fm2k_convert

Converts the original Vanguard Princess data (FM2K `.kgt/.player/.stage/.demo`) into the port's
native media and definitions. The port never reads FM2K files.

Current layout: `assets/` holds media and legacy numbered skill exports (ignored
by Git); `data/` holds generated/edited LTON definitions (tracked by Git).
`layout.py` maps an `assets` path to its sibling `data` for metadata IO. Existing
commands below still take `assets`; generated definitions go to `data`.
`data/_conversion/` holds the support extraction inputs and is not shipped.
See [0046](../../TechnicalDocuments/0046-versioned-game-data.md).

Background and decisions: `TechnicalDocuments/0003-asset-pipeline-decision.md`.

## 1. Extract with fm2ndparser

[xem85/fm2ndparser](https://github.com/xem85/fm2ndparser) (MIT, .NET 10). It rejects the
game's `2DKGT2G` files as "locked"; disable that check first — the layout is identical.
It also reads a sound's loop flag from the wrong bit; fix that too.

```sh
git clone --depth 1 https://github.com/xem85/fm2ndparser
cd fm2ndparser
sed -i 's/if (type.StartsWith("2DKGT2G"))/if (false \&\& type.StartsWith("2DKGT2G"))/' Fm2ndParser/Parsers/BaseParser.cs
# a sound's loop flag is bit 4 (0x10), not bit 5 (TechnicalDocuments/0014)
sed -i 's/var endlessLoop = isFlagOn(flags, 5);/var endlessLoop = isFlagOn(flags, 4);/' Fm2ndParser/Parsers/BaseParser.cs
dotnet build -c Release -o ../fm2nd-bin
```

Run it from an empty directory (output goes to the current directory). `-x` is not needed;
the JSON already carries the image and sound bytes.

```sh
mkdir json && cd json
../fm2nd-bin/Fm2ndParser.exe ".../vanpri108/ヴァンガードプリンセス/ヴァンガードプリンセス.kgt"
```

About 10 minutes and ~1.5 GB of JSON.

## 2. Convert

```sh
python -m venv tools/fm2k_convert/.venv
tools/fm2k_convert/.venv/Scripts/python -m pip install -r tools/fm2k_convert/requirements.txt
tools/fm2k_convert/.venv/Scripts/python tools/fm2k_convert/convert.py <json dir> assets -j 6
```

About 4 minutes. `--lton-only` rewrites just the LTON (13 s); `--only <stem>...` limits the files.

## Shared assets

After `convert.py`, gather what the characters hold in common (same bytes) into `assets/shared`:

```sh
tools/fm2k_convert/.venv/Scripts/python tools/fm2k_convert/share_assets.py assets --apply
```

The listings' entries become `shared = "images/<sha1>.png"`; the skills keep their numbers.
`--preview <dir>` writes the split for looking at instead. See `TechnicalDocuments/0020`.

Ownership corrections in `share_owners.txt` also apply to images already moved
to the shared pool: `--apply` restores the owner's numbered file, clears the
foreign slots, and deletes the pooled copy only when no manifest references it.
See `TechnicalDocuments/0034` for the additional Yui-only corrections.

`share_aliases.txt` records explicit, user-approved substitutions of different
image content with a canonical shared image (0035). `--apply` handles these
both on a fresh conversion and with an existing shared pool. This is a visual
change, not an automatic similarity-based deduplication rule.

## Support action audit

`supports.py` resolves the five supports' five regular actions from their HUD
input checks and variable-76 dispatchers. It writes a read-only report with
per-character skill numbers, input aliases/differences and Kurumi's separate
request-93 hook. It does not rewrite or unify skill bodies (TechnicalDocuments/0036).

```sh
python tools/fm2k_convert/supports.py assets --out build/support-actions.json
```

After generating each original character script, split complete owner-specific
support definitions (without normalizing them to Yui):

```sh
python tools/fm2k_convert/owner_supports.py data --apply
```

This writes `data/supports/<support>/<owner>.lton` and keeps the original
numbered conversion input in `data/_conversion`. Existing binary media and
palettes stay referenced by the owner's manifests. Boss Hilda retains her
fixed implementation; Kurumi retains her body collaboration attacks.

If restored dependencies reveal that an asset placed in one support's folder
is actually used by multiple supports, return only those assets to the pool:

```sh
python tools/fm2k_convert/organize_support_media.py assets --restore-common-only --apply
```

This updates every manifest and verifies copies before removing the old files.
Omit `--apply` to inspect the proposal. See TechnicalDocuments/0060.

## Names

Characters get their official names (`names.py`: ついん → えり, みさき → サキ, ゆかり → はるか,
みこ → あやね); new1 and 新2, unused, are not converted. When running `gen_script.py` by hand,
write to the official name's folder. See `TechnicalDocuments/0022`.

## Patches

Deliberate changes to the original data live in `patches/<json stem>.py` (`def patch(d)`, editing
the parsed JSON). `convert.py` and `gen_script.py` apply them right after loading a JSON, so never
regenerate blindly: conversion overwrites definitions. Review Git diffs in `data/`
and keep permanent conversion rules in the tools as well. See `TechnicalDocuments/0019`.

## Output

```text
assets/<system|characters|stages|demos>/<name>/
  skills/NNNN.lton    legacy extraction output, not loaded by the game
  images/NNNN.dds     palette-indexed sprites
  images/NNNN.png     RGBA sprites
  palettes.png       palette rows
  sounds/NNNN.wav     sounds

data/<system|characters|supports|stages|demos>/<name>/
  data.lton          extracted settings for tools/investigation (not shipped)
  images.lton        image references into assets/
  sounds.lton        sound references into assets/
  script.lton        executable definitions
  portrait.lton      selection portrait definitions (characters)
  cpu.lton           CPU patterns (characters)
  story.lton         story flow (characters)

data/_conversion/<characters|supports>/<name>/
  support-source.lton  normalized inputs for repeatable support extraction
```

## Preview

`preview_gif.py` renders a skill's `I` (image) blocks as an animated GIF with a palette applied
(conditions are ignored; for eyeballing only). Output goes to `assets/_preview/`.

```sh
tools/fm2k_convert/.venv/Scripts/python tools/fm2k_convert/preview_gif.py assets/characters/ゆい 1 2 22 --json-dir <json dir> --palette 0 1
```

## Skills as data

`gen_script.py` writes the skills of a character, a stage or the system file as
`script.lton` in the corresponding `data/` folder, which `src/script.lh` runs
(`TechnicalDocuments/0012`). A character's command table, hit reactions and gauge
settings go in the same file. For a character it also writes `portrait.lton`: only the
skills its select-screen face (#25) reaches, the others empty, so the select screen need
not read every whole script (`TechnicalDocuments/0023`). `dump_skill.py` prints skills one
block per line, for reading them.

```sh
python tools/fm2k_convert/gen_script.py <json dir>/ゆい.json assets/characters/ゆい
python tools/fm2k_convert/gen_script.py <json dir>/スクール.json assets/stages/スクール --layers
python tools/fm2k_convert/gen_script.py <json dir>/ヴァンガードプリンセス.json assets/system/ヴァンガードプリンセス --layers
python tools/fm2k_convert/dump_skill.py <json dir>/ゆい.json 1 213
```

`--layers` (stages and the system file's HUD scripts): a script that ends with E hides its
image; one that runs past its last block keeps showing its last image.

`gen_skills.py` writes skills as L^ procedures instead (`src/chara/<id>/skills/`,
`TechnicalDocuments/0005`): a draft to start from when rewriting a skill by hand.

## Demo assignment

`read_demos.py` reads what fm2ndparser leaves out about demos straight from the game's files:
which demo is the opening, the title screen, the select screens (the .kgt's demo config) and each
demo's "skip with input" and time (the .demo's last bytes), into
`assets/system/<game>/demos.lton` (`TechnicalDocuments/0016`).

```sh
python tools/fm2k_convert/read_demos.py vanpri108/ヴァンガードプリンセス assets
```

## Story routes and CPU patterns

`python tools/fm2k_convert/story.py` exports `story.lton` for each selectable
character and `cpu.lton` for all fighters including Hilda. Run after conversion
and shared-asset extraction. It recovers opponents discarded by fm2ndparser
directly from the original `.player` files, validates the dummy preparation
event and 7/7/11-fight routes, and exports explicit fight/demo sequences.
Difficulty and introduction are implemented in `src/story.lh`, without running
the dummy fight or interpreting story jump instructions at runtime.
These files are runtime assets and are included by `tools/dist.ps1`.

CPU command references use the original command table, which includes empty
entries. The export resolves them into skill numbers before runtime; indices
from the filtered player-input command table must not be used here.

## Owner-specific support definitions

Run `gen_script.py` against the original player JSON (with `--player` for raw
command input modes), then:

```sh
python tools/fm2k_convert/owner_supports.py data --apply
```

`share_supports.py assets --apply` is a compatibility alias for this command;
it no longer normalizes other characters to Yui. Previously normalized inputs
are rejected: recover originals from the parser JSON before first extraction.

Runtime definitions are `data/supports/{support}/{owner}.lton`, e.g.
`data/supports/えこ/ゆい.lton`. Each is a complete owner-specific definition,
not a recipe or delta. Character scripts retain 495–499 body skills. Original
conversion inputs live in `data/_conversion/characters/{owner}/support-source.lton`.
Re-extracting from those inputs is deterministic; they are excluded from distributions.

Support IDs are the support's 10000-slot bank plus the original skill number.
A support's reachable helpers are cloned into the same bank. Unreachable helper
instructions become Nop without changing block offsets; entering the middle of
an owner's helper never accidentally executes preceding voice or body code.
Kurumi's request-93 branches retain explicit connections to her body attacks.
The boss Hilda remains a separate fixed-support implementation.

Media numbers and palettes belong to the original owner. Existing image/sound
manifests still point to shared files or support-specific media folders; this
extraction never duplicates binary assets. A match loads only the selected
owner/support definition and its media. Loading without a selection (tools and
all-support tests) explicitly requests all five definitions for that owner.

The old Yui-only `supports/*/script.lton` packages are retired. See
TechnicalDocuments/0060-owner-support-packages.md for migration and verification.

## Victory demo preload lists

`gen_script.py` also generates `preload.lton` when its output directory is
`ゆい勝ち`. To regenerate just the media lists from the converted script:

```sh
python tools/fm2k_convert/victory_media.py assets/demos/ゆい勝ち
```

The ten lists specialize only winner variable 129. Opponent-dependent dialogue
and random branches retain all candidates. Runtime requests the selected list's
images and sounds through the asynchronous loader; the original demo script is
unchanged. The analyzer follows block-level control flow from every active layer,
including loops and cross-skill jumps. Unsupported instructions or writes to the
winner variable fail generation instead of silently producing incomplete lists.

## Checking the LTON

For a static VM coverage inventory (no changes to game data), run from the project root:

```sh
python tools/fm2k_convert/audit_vm.py --out build/fm2k-vm-audit.json
```

Add `--json-dir build/update-0117/new-json` to list raw blocks converted to Nop.
The report includes source locations and known ignored operands/events. Counts
are stored definitions, including owner-specific copies, not executed paths.
Nop includes intentional unreachable padding; it is not automatically a bug.
See `TechnicalDocuments/0074-fm2k-vm-coverage-audit.md` for the reviewed findings
and `tests/vm-audit.lh` for runtime diagnostic probes.

Check the LTON with lhat:

```sh
lhat --compile assets/characters/ゆい/skills/0600.lton -o <tmp>
```
