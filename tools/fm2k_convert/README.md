# fm2k_convert

Converts the original Vanguard Princess data (FM2K `.kgt/.player/.stage/.demo`) into the port's
native assets: PNG, WAV and LTON. One-shot migration tool — the port never reads FM2K files.

Background and decisions: `TechnicalDocuments/0003-asset-pipeline-decision.md`.

## 1. Extract with fm2ndparser

[xem85/fm2ndparser](https://github.com/xem85/fm2ndparser) (MIT, .NET 10). It rejects the
game's `2DKGT2G` files as "locked"; disable that check first — the layout is identical.

```sh
git clone --depth 1 https://github.com/xem85/fm2ndparser
cd fm2ndparser
sed -i 's/if (type.StartsWith("2DKGT2G"))/if (false \&\& type.StartsWith("2DKGT2G"))/' Fm2ndParser/Parsers/BaseParser.cs
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

## Output

```text
assets/<system|characters|stages|demos>/<name>/
  data.lton           settings, commands, CPU, story, built-in skill table, ...
  images.lton         position = FM2K image number, nil^ = unused slot
  sounds.lton         position = FM2K sound number, nil^ = unused slot
  skills/NNNN.lton    100 skills per file; skill number = first + position
  images/NNNN.png     indexed: 8-bit grayscale, value = palette index
                      rgba:    sprites that carried their own palette
  palettes.png        256 x 8, one row per colour variant (index 0 transparent)
  sounds/NNNN.wav     original bytes
```

## Preview

`preview_gif.py` renders a skill's `I` (image) blocks as an animated GIF with a palette applied
(conditions are ignored; for eyeballing only). Output goes to `assets/_preview/`.

```sh
tools/fm2k_convert/.venv/Scripts/python tools/fm2k_convert/preview_gif.py assets/characters/ゆい 1 2 22 --json-dir <json dir> --palette 0 1
```

## Skills as L^ code

`gen_skills.py` writes every skill of a character as an L^ procedure
(`src/chara/<id>/skills/`, see `TechnicalDocuments/0005`). `dump_skill.py` prints skills
one block per line, for reading them.

```sh
python tools/fm2k_convert/gen_skills.py <json dir>/ゆい.json yui
python tools/fm2k_convert/dump_skill.py <json dir>/ゆい.json 1 213
```

Stages go through the same generator: their scripts are layers
(`TechnicalDocuments/0007`).

```sh
python tools/fm2k_convert/gen_skills.py <json dir>/スクール.json school --stage
```

## Checking the LTON

Check the LTON with lhat:

```sh
lhat --compile assets/characters/ゆい/skills/0600.lton -o <tmp>
```
