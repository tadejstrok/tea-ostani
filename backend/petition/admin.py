from django.contrib import admin

from .models import Message, ModerationStatus, Signature


@admin.action(description="Publish selected names")
def publish_names(modeladmin, request, queryset):
    queryset.update(name_status=ModerationStatus.PUBLISHED)


@admin.action(description="Hide selected names")
def hide_names(modeladmin, request, queryset):
    queryset.update(name_status=ModerationStatus.HIDDEN)


@admin.action(description="Publish selected messages")
def publish_messages(modeladmin, request, queryset):
    queryset.update(status=ModerationStatus.PUBLISHED)


@admin.action(description="Hide selected messages")
def hide_messages(modeladmin, request, queryset):
    queryset.update(status=ModerationStatus.HIDDEN)


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    fields = ("recipient", "text", "status", "created_at")
    readonly_fields = ("created_at",)


@admin.register(Signature)
class SignatureAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "name_status", "anonymous", "newsletter", "created_at")
    list_filter = ("name_status", "anonymous", "newsletter", "created_at")
    search_fields = ("name", "email")
    readonly_fields = ("created_at", "ip_address")
    inlines = [MessageInline]
    actions = [publish_names, hide_names]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("recipient", "text", "status", "signature", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("recipient", "text")
    readonly_fields = ("created_at",)
    actions = [publish_messages, hide_messages]
