import pytest

from petition.models import Message, ModerationStatus, Signature
from petition.stats import GOALS, count_payload, recipient_counts

pytestmark = pytest.mark.django_db


def test_goals_are_the_four_published_goals():
    assert GOALS == [3000, 7000, 12000, 18000]


def test_count_payload_on_empty_database():
    payload = count_payload()
    assert payload["count"] == 0
    assert payload["petition_started_at"] is None
    assert [m["goal"] for m in payload["milestones"]] == GOALS
    assert all(m["reached_at"] is None for m in payload["milestones"])


def test_count_payload_returns_datetimes_not_strings():
    sig = Signature.objects.create(name="Ana", email="a@example.com", consent=True)
    payload = count_payload()
    assert payload["count"] == 1
    assert payload["petition_started_at"] == sig.created_at


def test_count_payload_marks_a_reached_goal(monkeypatch):
    monkeypatch.setattr("petition.stats.GOALS", [2])
    Signature.objects.create(name="A", email="a@example.com", consent=True)
    second = Signature.objects.create(name="B", email="b@example.com", consent=True)
    payload = count_payload()
    assert payload["milestones"] == [{"goal": 2, "reached_at": second.created_at}]


def test_recipient_counts_groups_unknown_as_drugim():
    sig = Signature.objects.create(name="Ana", email="a@example.com", consent=True)
    Message.objects.create(signature=sig, recipient="Mijič", text="a")
    Message.objects.create(signature=sig, recipient="Golob", text="b")
    Message.objects.create(signature=sig, recipient="Nekdo Drug", text="c")
    assert recipient_counts() == [
        {"recipient": "Drugim", "count": 2},
        {"recipient": "Mijič", "count": 1},
    ]


def test_recipient_counts_excludes_non_published():
    sig = Signature.objects.create(name="Ana", email="a@example.com", consent=True)
    Message.objects.create(signature=sig, recipient="Mijič", text="visible")
    Message.objects.create(
        signature=sig, recipient="Mijič", text="held",
        status=ModerationStatus.PENDING,
    )
    Message.objects.create(
        signature=sig, recipient="Mijič", text="gone",
        status=ModerationStatus.HIDDEN,
    )
    assert recipient_counts() == [{"recipient": "Mijič", "count": 1}]
