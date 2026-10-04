"""The characters' names in the port.

The original's files are named after the characters' working names; the port
uses their official names (the user's choice, TechnicalDocuments/0022). The
converter writes each character's folder, and the system file's character
list, under the official name.

Two characters the original lists but never uses (no images; built while
making it) are not converted. Their names stay in the system file's list, so
the characters after them keep their numbers.
"""

OFFICIAL = {
    "ついん": "えり",
    "みさき": "サキ",
    "ゆかり": "はるか",
    "みこ": "あやね",
}

UNUSED = {"new1", "新2"}


def official(name):
    """A character's name in the port, given the original's."""
    return OFFICIAL.get(name, name)
