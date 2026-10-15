"""Scan every message for personal data people typed into the free-text box.

Hits are hidden immediately — the safe default — and written to a report.
Review the report and `--restore` any false positive before `freeze_petition`
runs. Nothing is ever deleted here, only withheld.

Run AFTER export_newsletter. See that command's docstring for why the order
matters.

IMPORTANT: Once an applied (non-dry-run) scan has written the report, do not run
the applied scan again before restoring false positives. The report is the only
record of each message's pre-scan status, and a second applied run overwrites it
with the already-hidden state, making `--restore` a no-op. Use `--dry-run` to
re-inspect without overwriting the report.
"""

import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from petition.models import Message, ModerationStatus
from petition.pii import find_pii

FILENAME = "message-pii-report.csv"


class Command(BaseCommand):
    help = (
        "Scan all messages (published, pending and hidden) for emails, phone "
        "numbers, URLs and sign-off names. Hits are hidden and written to "
        f"{FILENAME}. Run AFTER export_newsletter. WARNING: Once applied, do not "
        "run the scan again before restoring — use --dry-run to re-inspect."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--output", default=".",
            help="Directory to write the report into (default: current directory).",
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Write the report but change no statuses.",
        )
        parser.add_argument(
            "--restore",
            help=(
                "Comma-separated message IDs to set back to published, for "
                "false positives. Skips scanning entirely."
            ),
        )

    def handle(self, *args, **options):
        if options["restore"]:
            if options["dry_run"]:
                raise CommandError("--dry-run and --restore are mutually exclusive.")
            self._restore(options["restore"], options["output"])
            return

        hits = []
        scanned = 0
        for message in Message.objects.all().order_by("id"):
            scanned += 1
            text_kinds = set(find_pii(message.text))
            recipient_kinds = set(find_pii(message.recipient))
            kinds_with_source = (
                [f"{k}" for k in sorted(text_kinds)] +
                [f"{k}(recipient)" for k in sorted(recipient_kinds)]
            )
            if text_kinds or recipient_kinds:
                hits.append((message, kinds_with_source))

        out_dir = Path(options["output"])
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / FILENAME

        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["id", "previous_status", "kinds", "recipient", "text"])
            for message, kinds_with_source in hits:
                writer.writerow(
                    [
                        message.id,
                        message.status,
                        " ".join(kinds_with_source),
                        message.recipient,
                        message.text,
                    ]
                )

        if options["dry_run"]:
            self.stdout.write(
                self.style.WARNING(
                    f"{scanned} scanned, {len(hits)} would be hidden "
                    f"(dry run, nothing changed) -> {path}"
                )
            )
            return

        hidden = 0
        for message, _kinds_with_source in hits:
            if message.status != ModerationStatus.HIDDEN:
                hidden += 1
            message.status = ModerationStatus.HIDDEN
            message.save(update_fields=["status"])

        self.stdout.write(
            self.style.SUCCESS(
                f"{scanned} scanned, {len(hits)} matched, {hidden} hidden "
                f"-> {path}"
            )
        )

    def _restore(self, raw_ids, output):
        try:
            ids = [int(part) for part in raw_ids.split(",") if part.strip()]
        except ValueError:
            raise CommandError("--restore takes comma-separated integer message IDs.")

        report_path = Path(output) / FILENAME
        if not report_path.exists():
            raise CommandError(
                f"Report file {FILENAME} not found in {output}. "
                "Run the scan first to generate the report."
            )

        id_to_status = {}
        with open(report_path, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                id_to_status[int(row["id"])] = row["previous_status"]

        # Validate all IDs exist in report
        for msg_id in ids:
            if msg_id not in id_to_status:
                raise CommandError(
                    f"Message ID {msg_id} not found in report. "
                    "Only restore IDs that were scanned and reported."
                )

        # Validate all previous_status values are recognized
        valid_statuses = set(ModerationStatus.values)
        for msg_id in ids:
            previous_status = id_to_status[msg_id]
            if previous_status not in valid_statuses:
                raise CommandError(
                    f"Invalid status '{previous_status}' for message ID {msg_id} "
                    f"in report. Valid statuses: {', '.join(sorted(valid_statuses))}"
                )

        # All validations passed, perform mutations
        updated = 0
        for msg_id in ids:
            previous_status = id_to_status[msg_id]
            count = Message.objects.filter(id=msg_id).update(status=previous_status)
            updated += count

        self.stdout.write(
            self.style.SUCCESS(f"{updated} message(s) restored to previous status.")
        )
