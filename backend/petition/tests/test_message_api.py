import pytest
from rest_framework.test import APIClient

from petition.models import Message, ModerationStatus, Signature

pytestmark = pytest.mark.django_db


@pytest.fixture
def sig():
    return Signature.objects.create(name="Ana", email="ana@example.com", consent=True)


def test_lists_only_published_messages(sig):
    Message.objects.create(signature=sig, recipient="Mijič", text="visible")
    Message.objects.create(
        signature=sig, recipient="Mijič", text="held",
        status=ModerationStatus.PENDING,
    )
    Message.objects.create(
        signature=sig, recipient="Mijič", text="hidden",
        status=ModerationStatus.HIDDEN,
    )
    resp = APIClient().get("/api/messages/")
    assert resp.status_code == 200
    texts = [row["text"] for row in resp.json()["results"]]
    assert texts == ["visible"]


def test_message_shape(sig):
    Message.objects.create(signature=sig, recipient="Mijič", text="hi")
    row = APIClient().get("/api/messages/").json()["results"][0]
    assert set(row.keys()) == {"signer_name", "recipient", "text", "created_at"}
    assert row["signer_name"] == "Ana"


def test_anonymous_signer_name_hidden():
    anon_sig = Signature.objects.create(
        name="Bine", email="bine@example.com", consent=True, anonymous=True
    )
    Message.objects.create(signature=anon_sig, recipient="Mijič", text="hi")
    row = APIClient().get("/api/messages/").json()["results"][0]
    assert row["signer_name"] is None


def test_held_signer_name_hidden(sig):
    sig.name_status = ModerationStatus.PENDING
    sig.save()
    Message.objects.create(signature=sig, recipient="Mijič", text="hi")
    row = APIClient().get("/api/messages/").json()["results"][0]
    assert row["signer_name"] is None


def test_recipient_stats_counts_and_orders(sig):
    Message.objects.create(signature=sig, recipient="Mijič", text="a")
    Message.objects.create(signature=sig, recipient="Mijič", text="b")
    Message.objects.create(signature=sig, recipient="Janša", text="c")
    resp = APIClient().get("/api/messages/stats/")
    assert resp.status_code == 200
    assert resp.json() == [
        {"recipient": "Mijič", "count": 2},
        {"recipient": "Janša", "count": 1},
    ]


def test_recipient_stats_excludes_held_messages(sig):
    Message.objects.create(signature=sig, recipient="Mijič", text="visible")
    Message.objects.create(
        signature=sig, recipient="Mijič", text="held", status=ModerationStatus.PENDING
    )
    resp = APIClient().get("/api/messages/stats/")
    assert resp.json() == [{"recipient": "Mijič", "count": 1}]


def test_recipient_stats_groups_unknown_recipients_as_drugim(sig):
    Message.objects.create(signature=sig, recipient="Mijič", text="a")
    Message.objects.create(signature=sig, recipient="Golob", text="b")
    Message.objects.create(signature=sig, recipient="Nekdo Drug", text="c")
    resp = APIClient().get("/api/messages/stats/")
    assert resp.json() == [
        {"recipient": "Drugim", "count": 2},
        {"recipient": "Mijič", "count": 1},
    ]
