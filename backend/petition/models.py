from django.db import models


class ModerationStatus(models.TextChoices):
    PUBLISHED = "published", "Published"
    PENDING = "pending", "Pending"
    HIDDEN = "hidden", "Hidden"


class Signature(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    newsletter = models.BooleanField(default=False)
    anonymous = models.BooleanField(default=False)
    consent = models.BooleanField(default=False)
    name_status = models.CharField(
        max_length=20,
        choices=ModerationStatus.choices,
        default=ModerationStatus.PUBLISHED,
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} <{self.email}>"


class Message(models.Model):
    signature = models.ForeignKey(
        Signature, on_delete=models.CASCADE, related_name="messages"
    )
    recipient = models.CharField(max_length=200)
    text = models.CharField(max_length=500)
    status = models.CharField(
        max_length=20,
        choices=ModerationStatus.choices,
        default=ModerationStatus.PUBLISHED,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"To {self.recipient}: {self.text[:40]}"
