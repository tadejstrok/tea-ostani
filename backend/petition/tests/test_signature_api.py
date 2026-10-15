import pytest
from rest_framework.test import APIClient

from petition.models import Message, ModerationStatus, Signature

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    return APIClient()


def test_submit_creates_signature(client):
    resp = client.post(
        "/api/signatures/",
        {"name": "Ana", "email": "ana@example.com", "consent": True},
        format="json",
    )
    assert resp.status_code == 201
    assert resp.json() == {"status": "ok"}
    sig = Signature.objects.get()
    assert sig.name == "Ana"
    assert sig.name_status == ModerationStatus.PUBLISHED
    assert sig.ip_address is not None


def test_submit_with_message_creates_linked_message(client):
    client.post(
        "/api/signatures/",
        {
            "name": "Ana",
            "email": "ana@example.com",
            "consent": True,
            "message": {"recipient": "Mijič", "text": "Odstopi."},
        },
        format="json",
    )
    msg = Message.objects.get()
    assert msg.recipient == "Mijič"
    assert msg.status == ModerationStatus.PUBLISHED


def test_message_with_url_is_held_pending(client):
    client.post(
        "/api/signatures/",
        {
            "name": "Ana",
            "email": "ana@example.com",
            "consent": True,
            "message": {"recipient": "Mijič", "text": "glej https://spam.example"},
        },
        format="json",
    )
    assert Message.objects.get().status == ModerationStatus.PENDING


def test_duplicate_email_is_silent_noop(client):
    payload = {"name": "Ana", "email": "dup@example.com", "consent": True}
    first = client.post("/api/signatures/", payload, format="json")
    second = client.post(
        "/api/signatures/",
        {"name": "Someone Else", "email": "DUP@example.com", "consent": True,
         "message": {"recipient": "Mijič", "text": "hi"}},
        format="json",
    )
    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json() == {"status": "ok"}
    assert Signature.objects.count() == 1
    assert Message.objects.count() == 0


def test_consent_false_returns_400(client):
    resp = client.post(
        "/api/signatures/",
        {"name": "Ana", "email": "ana@example.com", "consent": False},
        format="json",
    )
    assert resp.status_code == 400
    assert "consent" in resp.json()


def test_missing_name_returns_400(client):
    resp = client.post(
        "/api/signatures/",
        {"email": "ana@example.com", "consent": True},
        format="json",
    )
    assert resp.status_code == 400
    assert "name" in resp.json()


def test_count_endpoint(client):
    Signature.objects.create(name="A", email="a@example.com", consent=True)
    Signature.objects.create(name="B", email="b@example.com", consent=True)
    resp = client.get("/api/signatures/count/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 2
    assert body["petition_started_at"] is not None
    assert body["milestones"] == [
        {"goal": 3000, "reached_at": None},
        {"goal": 7000, "reached_at": None},
        {"goal": 12000, "reached_at": None},
        {"goal": 18000, "reached_at": None},
    ]


def test_count_endpoint_no_signatures_yet(client):
    resp = client.get("/api/signatures/count/")
    body = resp.json()
    assert body["count"] == 0
    assert body["petition_started_at"] is None


def test_count_endpoint_reports_milestones_reached_at(client, monkeypatch):
    monkeypatch.setattr("petition.stats.GOALS", [3, 5])
    for i in range(5):
        Signature.objects.create(name=f"S{i}", email=f"s{i}@example.com", consent=True)
    resp = client.get("/api/signatures/count/")
    body = resp.json()
    assert body["count"] == 5

    ordered = list(Signature.objects.order_by("created_at"))
    assert body["milestones"] == [
        {
            "goal": 3,
            "reached_at": ordered[2].created_at.isoformat().replace("+00:00", "Z"),
        },
        {
            "goal": 5,
            "reached_at": ordered[4].created_at.isoformat().replace("+00:00", "Z"),
        },
    ]
    assert body["petition_started_at"] == ordered[0].created_at.isoformat().replace(
        "+00:00", "Z"
    )


def test_name_with_url_is_held_pending(client):
    client.post(
        "/api/signatures/",
        {"name": "Ana https://spam.example", "email": "ana@example.com", "consent": True},
        format="json",
    )
    assert Signature.objects.get().name_status == ModerationStatus.PENDING


def test_list_excludes_anonymous_and_non_published(client, settings):
    settings.SIGNATURE_LIST_ENABLED = True
    Signature.objects.create(name="Visible", email="v@example.com", consent=True)
    Signature.objects.create(
        name="Anon", email="anon@example.com", consent=True, anonymous=True
    )
    Signature.objects.create(
        name="Held", email="held@example.com", consent=True,
        name_status=ModerationStatus.PENDING,
    )
    resp = client.get("/api/signatures/")
    assert resp.status_code == 200
    names = [row["name"] for row in resp.json()["results"]]
    assert names == ["Visible"]


def test_list_disabled_returns_404(client, settings):
    settings.SIGNATURE_LIST_ENABLED = False
    Signature.objects.create(name="Visible", email="v@example.com", consent=True)
    resp = client.get("/api/signatures/")
    assert resp.status_code == 404


def test_post_still_works_when_list_disabled(client, settings):
    settings.SIGNATURE_LIST_ENABLED = False
    resp = client.post(
        "/api/signatures/",
        {"name": "Ana", "email": "ana@example.com", "consent": True},
        format="json",
    )
    assert resp.status_code == 201
    assert Signature.objects.filter(email="ana@example.com").exists()
