"""Export newsletter-consented email addresses, before anything is deleted.

MUST run before `scan_messages`. `Message.status` carries no provenance and the
admin's bulk actions write no `django_admin_log` rows, so once the scan starts
setting `status = hidden`, moderator decisions become indistinguishable from
scan hits — and the exclusion below would silently widen to "anyone who typed a
phone number". Running first makes every hidden row moderator-hidden by
definition.
"""

import csv
from pathlib import Path

from django.core.management.base import BaseCommand

from petition.models import ModerationStatus, Signature

FILENAME = "newsletter-emails.csv"

# Statuses that remove a signer from the mailing list: `hidden` is a moderator
# takedown; `pending` was auto-flagged by screen() and never reviewed.
EXCLUDING_STATUSES = (ModerationStatus.HIDDEN, ModerationStatus.PENDING)


class Command(BaseCommand):
    help = (
        "Export emails of signatures that consented to the newsletter, "
        "excluding anyone with a hidden or pending message. Writes "
        f"{FILENAME}. Run this BEFORE scan_messages."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--output", default=".",
            help="Directory to write the CSV into (default: current directory).",
        )

    def handle(self, *args, **options):
        subscribers = Signature.objects.filter(newsletter=True)

        # exclude() on a reverse relation drops any signature having at least
        # one matching message, and leaves signatures with no messages alone.
        included = subscribers.exclude(
            messages__status__in=EXCLUDING_STATUSES
        ).order_by("created_at")

        total = subscribers.count()
        rows = list(included.values_list("email", "created_at"))
        exported = len(rows)

        out_dir = Path(options["output"])
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / FILENAME

        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["email", "created_at"])
            for email, created_at in rows:
                writer.writerow([email, created_at.isoformat()])

        self.stdout.write(
            self.style.SUCCESS(
                f"{exported} exported, {total - exported} excluded "
                f"(hidden or pending message) -> {path}"
            )
        )
