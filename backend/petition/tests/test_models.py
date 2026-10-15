import pytest
from django.db import IntegrityError

from petition.models import Message, ModerationStatus, Signature

pytestmark = pytest.mark.django_db


def test_signature_defaults():
    sig = Signature.objects.create(name="Ana", email="ana@example.com", consent=True)
    assert sig.newsletter is False
    assert sig.anonymous is False
    assert sig.name_status == ModerationStatus.PUBLISHED
    assert sig.ip_address is None
    assert sig.created_at is not None


def test_email_is_unique():
    Signature.objects.create(name="Ana", email="dup@example.com", consent=True)
    with pytest.raises(IntegrityError):
        Signature.objects.create(name="Bob", email="dup@example.com", consent=True)


def test_message_linked_to_signature():
    sig = Signature.objects.create(name="Ana", email="ana@example.com", consent=True)
    msg = Message.objects.create(signature=sig, recipient="Mijič", text="Odstopi.")
    assert msg.status == ModerationStatus.PUBLISHED
    assert list(sig.messages.all()) == [msg]
