"""Shared builders for the public count and recipient-stats payloads.

Both the live API views and the `freeze_petition` management command read from
here, so the static JSON written at erasure time cannot drift from the shape the
API served. Returns raw `datetime` objects — encoding is the caller's job, and
the two callers deliberately encode differently (see the spec).
"""

from django.db.models import Count

from .models import Message, ModerationStatus, Signature

GOALS = [3000, 7000, 12000, 18000]

KNOWN_RECIPIENTS = {"Mijič", "Stevanović", "Vrtovec", "Logar", "Janša"}
OTHER_RECIPIENT_LABEL = "Drugim"


def count_payload():
    """Return the `/api/signatures/count/` body as a plain dict."""
    count = Signature.objects.count()
    ordered = Signature.objects.order_by("created_at")

    petition_started_at = None
    first = ordered.first()
    if first:
        petition_started_at = first.created_at

    milestones = []
    for goal in GOALS:
        reached_at = None
        if count >= goal:
            # The signature that tipped the count over this goal is when it was
            # "reached" — the Nth row by signup order, 0-indexed.
            reached_at = ordered[goal - 1].created_at
        milestones.append({"goal": goal, "reached_at": reached_at})

    return {
        "count": count,
        "petition_started_at": petition_started_at,
        "milestones": milestones,
    }


def recipient_counts():
    """Return the `/api/messages/stats/` body as a list of dicts."""
    rows = (
        Message.objects.filter(status=ModerationStatus.PUBLISHED)
        .values("recipient")
        .annotate(count=Count("id"))
    )
    counts = {}
    for row in rows:
        key = (
            row["recipient"]
            if row["recipient"] in KNOWN_RECIPIENTS
            else OTHER_RECIPIENT_LABEL
        )
        counts[key] = counts.get(key, 0) + row["count"]

    return sorted(
        ({"recipient": k, "count": v} for k, v in counts.items()),
        key=lambda row: -row["count"],
    )
