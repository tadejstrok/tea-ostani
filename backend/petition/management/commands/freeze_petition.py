"""Freeze the public petition data into static JSON, then the API can go away.

Writes the three files the static site reads. Shapes are produced by the same
code paths the live API used — `petition.stats` for the counts and a
ModelSerializer for the messages — so the frozen files cannot drift from what
the API served. Run AFTER export_newsletter and scan_messages.
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand
from rest_framework.utils.encoders import JSONEncoder

from petition.models import Message, ModerationStatus
from petition.serializers import FrozenMessageSerializer
from petition.stats import count_payload, recipient_counts


class Command(BaseCommand):
    help = (
        "Write count.json, messages.json and recipient-stats.json for the "
        "static site. Run AFTER export_newsletter and scan_messages."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--output", default=".",
            help="Directory to write the JSON files into (default: current directory).",
        )

    def handle(self, *args, **options):
        out_dir = Path(options["output"])
        out_dir.mkdir(parents=True, exist_ok=True)

        counts = count_payload()

        published = Message.objects.filter(
            status=ModerationStatus.PUBLISHED
        )  # Meta.ordering is ["-created_at"], so this is newest first
        rows = FrozenMessageSerializer(published, many=True).data
        messages = {"count": len(rows), "results": rows}

        stats = recipient_counts()

        self._write(out_dir / "count.json", counts)
        self._write(out_dir / "messages.json", messages)
        self._write(out_dir / "recipient-stats.json", stats)

        self.stdout.write(
            self.style.SUCCESS(
                f"Froze {counts['count']} signature(s) and "
                f"{len(rows)} message(s) -> {out_dir}"
            )
        )

    def _write(self, path, payload):
        # DRF's JSONEncoder renders datetimes exactly as the API did;
        # ensure_ascii=False keeps Slovenian characters readable.
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, cls=JSONEncoder, ensure_ascii=False)
