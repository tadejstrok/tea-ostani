import json

import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from petition.models import Message, ModerationStatus, Signature

pytestmark = pytest.mark.django_db


@pytest.fixture
def sig():
    return Signature.objects.create(name="Ana", email="a@example.com", consent=True)


def read_json(tmp_path, name):
    with open(tmp_path / name, encoding="utf-8") as fh:
        return json.load(fh)


def test_writes_all_three_files(sig, tmp_path):
    call_command("freeze_petition", "--output", str(tmp_path))
    for name in ("count.json", "messages.json", "recipient-stats.json"):
        assert (tmp_path / name).exists()


def test_count_json_matches_the_live_endpoint(sig, tmp_path):
    api = APIClient().get("/api/signatures/count/").json()
    call_command("freeze_petition", "--output", str(tmp_path))
    assert read_json(tmp_path, "count.json") == api


def test_unreached_goal_keeps_a_null_reached_at(sig, tmp_path):
    # Review Focus 4: a dropped or coerced null makes renderCounter() draw a
    # milestone for a goal that was never met.
    call_command("freeze_petition", "--output", str(tmp_path))
    milestones = read_json(tmp_path, "count.json")["milestones"]
    assert [m["goal"] for m in milestones] == [3000, 7000, 12000, 18000]
    assert all(m["reached_at"] is None for m in milestones)


def test_messages_json_has_no_signer_name_key(sig, tmp_path):
    Message.objects.create(signature=sig, recipient="Mijič", text="Odstopi.")
    call_command("freeze_petition", "--output", str(tmp_path))
    row = read_json(tmp_path, "messages.json")["results"][0]
    assert set(row.keys()) == {"recipient", "text", "created_at"}
    assert "signer_name" not in row


def test_messages_json_excludes_non_published(sig, tmp_path):
    Message.objects.create(signature=sig, recipient="Mijič", text="visible")
    Message.objects.create(
        signature=sig, recipient="Mijič", text="held",
        status=ModerationStatus.PENDING,
    )
    Message.objects.create(
        signature=sig, recipient="Mijič", text="gone",
        status=ModerationStatus.HIDDEN,
    )
    call_command("freeze_petition", "--output", str(tmp_path))
    body = read_json(tmp_path, "messages.json")
    assert body["count"] == 1
    assert [r["text"] for r in body["results"]] == ["visible"]


def test_messages_are_newest_first(sig, tmp_path):
    Message.objects.create(signature=sig, recipient="Mijič", text="first")
    Message.objects.create(signature=sig, recipient="Mijič", text="second")
    call_command("freeze_petition", "--output", str(tmp_path))
    texts = [r["text"] for r in read_json(tmp_path, "messages.json")["results"]]
    assert texts == ["second", "first"]


def test_frozen_row_matches_the_live_endpoint_minus_signer_name(sig, tmp_path):
    # Pins the whole row - recipient, text and created_at - not just the
    # timestamp, so that an added field on PublicMessageSerializer forces a
    # decision about FrozenMessageSerializer instead of drifting silently.
    Message.objects.create(
        signature=sig, recipient="Janša", text="Sramota, čigav šport je to?"
    )
    live_row = APIClient().get("/api/messages/").json()["results"][0]
    call_command("freeze_petition", "--output", str(tmp_path))
    frozen_row = read_json(tmp_path, "messages.json")["results"][0]
    expected = {k: v for k, v in live_row.items() if k != "signer_name"}
    assert frozen_row == expected


def test_slovenian_characters_are_written_literally(sig, tmp_path):
    Message.objects.create(
        signature=sig, recipient="Janša", text="Sramota, čigav šport je to?"
    )
    call_command("freeze_petition", "--output", str(tmp_path))
    raw = (tmp_path / "messages.json").read_text(encoding="utf-8")
    # Review Focus 3: default json.dumps escapes these to \uXXXX, which still
    # renders but makes the file unreadable for human review.
    assert "čigav šport" in raw
    assert "\\u" not in raw


def test_recipient_stats_match_the_live_endpoint(sig, tmp_path):
    Message.objects.create(signature=sig, recipient="Mijič", text="a")
    Message.objects.create(signature=sig, recipient="Golob", text="b")
    api = APIClient().get("/api/messages/stats/").json()
    call_command("freeze_petition", "--output", str(tmp_path))
    assert read_json(tmp_path, "recipient-stats.json") == api


def test_empty_database_produces_valid_files(tmp_path):
    call_command("freeze_petition", "--output", str(tmp_path))
    assert read_json(tmp_path, "count.json")["count"] == 0
    assert read_json(tmp_path, "messages.json") == {"count": 0, "results": []}
    assert read_json(tmp_path, "recipient-stats.json") == []


def test_reports_what_it_wrote_to_stdout(sig, tmp_path, capsys):
    Message.objects.create(signature=sig, recipient="Mijič", text="Odstopi.")
    call_command("freeze_petition", "--output", str(tmp_path))
    out = capsys.readouterr().out
    assert "1 signature" in out
    assert "1 message" in out
