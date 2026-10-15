from rest_framework import serializers

from .models import Message, ModerationStatus, Signature


class MessageInputSerializer(serializers.Serializer):
    recipient = serializers.CharField(max_length=200)
    text = serializers.CharField(max_length=500)


class SignatureCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    email = serializers.EmailField()
    newsletter = serializers.BooleanField(default=False)
    anonymous = serializers.BooleanField(default=False)
    consent = serializers.BooleanField()
    message = MessageInputSerializer(required=False)

    def validate_consent(self, value):
        if value is not True:
            raise serializers.ValidationError("Consent is required.")
        return value


class PublicSignatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Signature
        fields = ["name", "created_at"]


class PublicMessageSerializer(serializers.ModelSerializer):
    signer_name = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ["signer_name", "recipient", "text", "created_at"]

    def get_signer_name(self, obj):
        signature = obj.signature
        if signature.anonymous or signature.name_status != ModerationStatus.PUBLISHED:
            return None
        return signature.name


class FrozenMessageSerializer(serializers.ModelSerializer):
    """Public message without any signer attribution.

    `signer_name` is absent as a field rather than serialized as null: there is
    nothing left to repopulate, and a reader of the file can see at a glance
    that signer identity is not in it. Subclassing ModelSerializer keeps
    `created_at` formatting identical to what the live API served.
    """

    class Meta:
        model = Message
        fields = ["recipient", "text", "created_at"]
