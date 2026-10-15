"""Pluggable auto-hold hook for post-moderation.

`screen()` returns True when content should be withheld (status `pending`)
until a moderator approves it. The default heuristic holds anything that
contains a URL — a common spam signal. Extend `BLOCKLIST` or replace the
body to tighten moderation without touching models or views.
"""

# Substrings (case-insensitive) that hold content for manual review.
BLOCKLIST = (
    "http://",
    "https://",
    "www.",
)


def screen(text):
    """Return True if `text` should be held for manual review."""
    if not text:
        return False
    lowered = text.lower()
    return any(term in lowered for term in BLOCKLIST)
