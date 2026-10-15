from django.urls import path

from . import views

urlpatterns = [
    path("signatures/", views.SignatureListCreateView.as_view(), name="signature-list"),
    path("signatures/count/", views.SignatureCountView.as_view(), name="signature-count"),
    path("messages/", views.PublicMessageListView.as_view(), name="message-list"),
    path(
        "messages/stats/",
        views.MessageRecipientStatsView.as_view(),
        name="message-recipient-stats",
    ),
]
