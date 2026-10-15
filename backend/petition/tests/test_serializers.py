from petition.serializers import SignatureCreateSerializer


def test_valid_payload_without_message():
    s = SignatureCreateSerializer(
        data={"name": "Ana", "email": "ana@example.com", "consent": True}
    )
    assert s.is_valid(), s.errors
    assert s.validated_data["newsletter"] is False
    assert s.validated_data["anonymous"] is False
    assert "message" not in s.validated_data


def test_valid_payload_with_message():
    s = SignatureCreateSerializer(
        data={
            "name": "Ana",
            "email": "ana@example.com",
            "consent": True,
            "message": {"recipient": "Mijič", "text": "Odstopi."},
        }
    )
    assert s.is_valid(), s.errors
    assert s.validated_data["message"]["recipient"] == "Mijič"


def test_consent_must_be_true():
    s = SignatureCreateSerializer(
        data={"name": "Ana", "email": "ana@example.com", "consent": False}
    )
    assert not s.is_valid()
    assert "consent" in s.errors


def test_message_requires_recipient_and_text():
    s = SignatureCreateSerializer(
        data={
            "name": "Ana",
            "email": "ana@example.com",
            "consent": True,
            "message": {"text": "Odstopi."},
        }
    )
    assert not s.is_valid()
    assert "message" in s.errors


def test_message_text_max_length():
    s = SignatureCreateSerializer(
        data={
            "name": "Ana",
            "email": "ana@example.com",
            "consent": True,
            "message": {"recipient": "Mijič", "text": "x" * 501},
        }
    )
    assert not s.is_valid()
    assert "message" in s.errors
