from django.conf import settings
from django.db import IntegrityError
from rest_framework import generics, status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .models import Message, ModerationStatus, Signature
from .moderation import screen
from .serializers import (
    PublicMessageSerializer,
    PublicSignatureSerializer,
    SignatureCreateSerializer,
)
from .stats import count_payload, recipient_counts


def get_client_ip(request):
    if settings.USE_X_FORWARDED_FOR:
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _status_for(text):
    return ModerationStatus.PENDING if screen(text) else ModerationStatus.PUBLISHED


class SignatureListCreateView(generics.ListCreateAPIView):
    serializer_class = PublicSignatureSerializer

    def get_queryset(self):
        return Signature.objects.filter(
            anonymous=False, name_status=ModerationStatus.PUBLISHED
        )

    def list(self, request, *args, **kwargs):
        # Public name listing is gated behind a flag; POST/signing is unaffected.
        if not settings.SIGNATURE_LIST_ENABLED:
            raise NotFound()
        return super().list(request, *args, **kwargs)

    def get_throttles(self):
        if self.request.method == "POST":
            self.throttle_scope = "signature"
            return [ScopedRateThrottle()]
        return []

    def create(self, request, *args, **kwargs):
        serializer = SignatureCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Silent dedupe: never reveal whether the email already signed.
        if Signature.objects.filter(email__iexact=data["email"]).exists():
            return Response({"status": "ok"}, status=status.HTTP_201_CREATED)

        try:
            signature = Signature.objects.create(
                name=data["name"],
                email=data["email"],
                newsletter=data["newsletter"],
                anonymous=data["anonymous"],
                consent=data["consent"],
                name_status=_status_for(data["name"]),
                ip_address=get_client_ip(request),
            )
        except IntegrityError:
            # Race on the unique email — treat as the same silent no-op.
            return Response({"status": "ok"}, status=status.HTTP_201_CREATED)

        message = data.get("message")
        if message:
            signature.messages.create(
                recipient=message["recipient"],
                text=message["text"],
                status=_status_for(message["text"]),
            )
        return Response({"status": "ok"}, status=status.HTTP_201_CREATED)


class SignatureCountView(APIView):
    def get(self, request):
        return Response(count_payload())


class PublicMessageListView(generics.ListAPIView):
    serializer_class = PublicMessageSerializer

    def get_queryset(self):
        return Message.objects.filter(
            status=ModerationStatus.PUBLISHED
        ).select_related("signature")


class MessageRecipientStatsView(APIView):
    def get(self, request):
        return Response(recipient_counts())
