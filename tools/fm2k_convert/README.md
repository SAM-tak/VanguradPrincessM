# fm2k_convert

Converts the original Vanguard Princess data (FM2K `.kgt/.player/.stage/.demo`) into the port's
native assets: PNG, WAV and LTON. One-shot migration tool — the port never reads FM2K files.

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

## Names

Characters get their official names (`names.py`: ついん → えり, みさき → サキ, ゆかり → はるか,
みこ → あやね); new1 and 新2, unused, are not converted. When running `gen_script.py` by hand,
write to the official name's folder. See `TechnicalDocuments/0022`.

## Patches

Deliberate changes to the original data live in `patches/<json stem>.py` (`def patch(d)`, editing
the parsed JSON). `convert.py` and `gen_script.py` apply them right after loading a JSON, so never
edit `assets/` by hand: a conversion overwrites it. See `TechnicalDocuments/0019`.

## Output

```text
assets/<system|characters|stages|demos>/<name>/
  data.lton           settings, commands, CPU, story, built-in skill table, ...
  images.lton         position = FM2K image number, nil^ = unused slot
  sounds.lton         position = FM2K sound number, nil^ = unused slot
  skills/NNNN.lton    100 skills per file; skill number = first + position
  images/NNNN.dds     indexed: uncompressed single-channel DDS (R8), value = palette index
  images/NNNN.png     rgba:    sprites that carried their own palette
  palettes.png        256 x 8, one row per colour variant (index 0 transparent)
  sounds/NNNN.wav     original bytes
```

## Preview

`preview_gif.py` renders a skill's `I` (image) blocks as an animated GIF with a palette applied
(conditions are ignored; for eyeballing only). Output goes to `assets/_preview/`.

```sh
tools/fm2k_convert/.venv/Scripts/python tools/fm2k_convert/preview_gif.py assets/characters/ゆい 1 2 22 --json-dir <json dir> --palette 0 1
```

## Skills as data

`gen_script.py` writes the skills of a character, a stage or the system file as
`script.lton` in the converted folder, which `src/script.lh` runs
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

## Checking the LTON

Check the LTON with lhat:

```sh
lhat --compile assets/characters/ゆい/skills/0600.lton -o <tmp>
```
