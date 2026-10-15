import pytest
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import Client

from petition.models import Message, ModerationStatus, Signature

pytestmark = pytest.mark.django_db


def test_models_registered():
    assert Signature in admin.site._registry
    assert Message in admin.site._registry


def test_changelist_requires_auth():
    resp = Client().get("/admin/petition/signature/")
    assert resp.status_code == 302
    assert "/admin/login/" in resp.headers["Location"]


def test_superuser_can_view_changelist():
    get_user_model().objects.create_superuser("mod", "mod@example.com", "pw12345!")
    client = Client()
    client.login(username="mod", password="pw12345!")
    resp = client.get("/admin/petition/signature/")
    assert resp.status_code == 200


def test_hide_names_action_sets_status():
    from petition.admin import hide_names

    sig = Signature.objects.create(name="Ana", email="a@example.com", consent=True)
    hide_names(None, None, Signature.objects.all())
    sig.refresh_from_db()
    assert sig.name_status == ModerationStatus.HIDDEN


def test_hide_messages_action_sets_status():
    from petition.admin import hide_messages

    sig = Signature.objects.create(name="Ana", email="a@example.com", consent=True)
    msg = Message.objects.create(signature=sig, recipient="Mijič", text="hi")
    hide_messages(None, None, Message.objects.all())
    msg.refresh_from_db()
    assert msg.status == ModerationStatus.HIDDEN
