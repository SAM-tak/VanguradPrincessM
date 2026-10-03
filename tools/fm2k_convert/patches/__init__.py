"""Changes to the original data, made while converting it.

The port reproduces the original, but some of its data is changed on purpose
(a fix, an improvement the user chose, assets shared between characters).
Those changes are written here, as code that edits fm2ndparser's JSON, rather
than by hand in assets/: a conversion run would overwrite hand edits.

One module per converted file, named after the JSON's stem (キャラセレ.py for
キャラセレ.json), with

    def patch(d):  # d: the parsed JSON, edited in place
        ...

Every converter calls `apply(json_path, d)` right after loading a JSON, so the
same change reaches the LTON, the script and the assets alike.
"""

import importlib.util
from pathlib import Path

HERE = Path(__file__).parent


def apply(json_path, d):
    """Runs the patch for this JSON file, if there is one. Answers whether one ran."""
    stem = Path(json_path).stem
    module_path = HERE / (stem + ".py")
    if not module_path.exists():
        return False
    spec = importlib.util.spec_from_file_location("fm2k_patch_" + stem, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.patch(d)
    print("patched %s with %s" % (Path(json_path).name, module_path.name))
    return True


def renumber(blocks):
    """Sets each block's index to its position (after blocks were added or moved)."""
    for i, b in enumerate(blocks):
        b["index"] = i
