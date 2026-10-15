"""Pattern scan for personal data people typed into the free-text message box.

`find_pii()` returns the kinds of personal data found in a string. It is a
detector, not a judge: the `scan_messages` command decides what to do with a
hit, and a human reviews the result. URL detection calls `moderation.screen()`
so the two never disagree about what a link looks like.

The sign-off detectors are deliberately calibrated for recall over precision:
a false positive hides one message out of thousands and a human reviews it
before anything is restored; a false negative publishes someone's name
forever. When in doubt, widen.
"""

import re

from .moderation import screen

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.\w{2,}")

# Slovenian forms: +386 41 234 567, 00386 1 234 56, 041 234 567, 041234567,
# 386 41 234 567, (041) 234 567, +386 (0)41 234 567.
# Requires at least seven digits, so four-digit years and goal figures
# (2026, 3000, 15458) cannot match.
PHONE_RE = re.compile(
    r"(?<![\d+])"
    r"(?:"
    r"(?:\+386|00386|386|0)\s?(?:\d{1,2}|\(0\d{1,2}\)|\(0\)\d{1,2})|"
    r"\(0\d{1,2}\)"
    r")"
    r"[\s/-]?\d{3}[\s-]?\d{2,3}(?!\d)"
)

# Uppercase/lowercase classes for a capitalised Slovenian/Bosnian/Croatian/
# Serbian given name: Č Š Ž Ć Đ and č š ž ć đ in addition to plain ASCII.
_UPPER = "A-ZČŠŽĆĐ"
_LOWER = "a-zčšžćđ"

# A closing salutation, optionally followed by a few words of filler, then a
# name of two or more letters. A bare sign-off, or one followed by a single
# initial, is not a name.
#
# Only the salutation (and filler) is case-insensitive. A global re.IGNORECASE
# would make the name class match lowercase too, flagging "Lep pozdrav,
# odstopi takoj" as a name.
#
# The filler group is bounded to three words so it cannot span an entire
# message looking for some unrelated capitalised word later on — it exists
# only to bridge things like "Hvala za vse, Marko".
SIGNOFF_RE = re.compile(
    r"\b(?i:lepo pozdravljeni|lep pozdrav|lep dan|pozdravljeni|pozdrav|lp|"
    r"hvala za|hvala|s spoštovanjem|s poštovanjem|vse dobro|srečno)\b"
    r"(?:[\s,:;!.-]+\w+){0,3}?"
    r"[\s,:;!.-]+"
    rf"[{_UPPER}][{_LOWER}]{{1,}}",
    re.UNICODE,
)

# The commonest way people sign a message: no salutation at all, just their
# name (one to three capitalised words) standing alone on the last non-empty
# line — "Odstopi takoj.\n\nAna Novak". An optional trailing "." or "!" is
# tolerated; anything else on the line (more text, a comma, a lowercase word)
# means it is not a bare signature and this rule does not fire.
#
# Only applied when the text has at least two non-empty lines: a single-line
# text that is itself one capitalised word ("Odstopi.", or a bare recipient
# field like "Mijič") is an imperative sentence or an addressee, not a
# trailing signature, and must not be flagged.
TRAILING_NAME_RE = re.compile(
    rf"^[{_UPPER}][{_LOWER}]+(?:[ -][{_UPPER}][{_LOWER}]+){{0,2}}[.!]?$",
    re.UNICODE,
)


def find_pii(text):
    """Return a sorted list of personal-data kinds found in `text`."""
    if not text:
        return []

    kinds = set()
    if EMAIL_RE.search(text):
        kinds.add("email")
    if PHONE_RE.search(text):
        kinds.add("phone")
    if screen(text):
        kinds.add("url")
    if SIGNOFF_RE.search(text):
        kinds.add("signoff")

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if len(lines) >= 2 and TRAILING_NAME_RE.match(lines[-1]):
        kinds.add("trailing-name")

    return sorted(kinds)
