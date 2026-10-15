import csv

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from petition.models import Message, ModerationStatus, Signature

pytestmark = pytest.mark.django_db


@pytest.fixture
def sig():
    return Signature.objects.create(name="Ana", email="a@example.com", consent=True)


def read_report(tmp_path):
    with open(tmp_path / "message-pii-report.csv", newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_clean_message_is_untouched(sig, tmp_path):
    msg = Message.objects.create(signature=sig, recipient="Mijič", text="Odstopi.")
    call_command("scan_messages", "--output", str(tmp_path))
    msg.refresh_from_db()
    assert msg.status == ModerationStatus.PUBLISHED
    assert read_report(tmp_path) == []


def test_hit_is_hidden_and_reported(sig, tmp_path):
    msg = Message.objects.create(
        signature=sig, recipient="Mijič", text="pisi na ana@example.com"
    )
    call_command("scan_messages", "--output", str(tmp_path))
    msg.refresh_from_db()
    assert msg.status == ModerationStatus.HIDDEN
    row = read_report(tmp_path)[0]
    assert row["id"] == str(msg.id)
    assert row["previous_status"] == "published"
    assert row["kinds"] == "email"


def test_scans_pending_and_hidden_messages_too(sig, tmp_path):
    Message.objects.create(
        signature=sig, recipient="Mijič", text="tel 041 234 567",
        status=ModerationStatus.PENDING,
    )
    Message.objects.create(
        signature=sig, recipient="Mijič", text="mail x@example.com",
        status=ModerationStatus.HIDDEN,
    )
    call_command("scan_messages", "--output", str(tmp_path))
    statuses = sorted(r["previous_status"] for r in read_report(tmp_path))
    assert statuses == ["hidden", "pending"]
    assert Message.objects.filter(status=ModerationStatus.HIDDEN).count() == 2


def test_recipient_field_is_scanned(sig, tmp_path):
    msg = Message.objects.create(
        signature=sig, recipient="ana@example.com", text="Odstopi."
    )
    call_command("scan_messages", "--output", str(tmp_path))
    msg.refresh_from_db()
    assert msg.status == ModerationStatus.HIDDEN


def test_dry_run_reports_without_changing_anything(sig, tmp_path):
    msg = Message.objects.create(
        signature=sig, recipient="Mijič", text="mail ana@example.com"
    )
    call_command("scan_messages", "--output", str(tmp_path), "--dry-run")
    msg.refresh_from_db()
    assert msg.status == ModerationStatus.PUBLISHED
    assert len(read_report(tmp_path)) == 1


def test_text_with_commas_and_newlines_survives_the_report(sig, tmp_path):
    Message.objects.create(
        signature=sig, recipient="Mijič",
        text='Odstopi, prosim.\nLep pozdrav, Ana "A"',
    )
    call_command("scan_messages", "--output", str(tmp_path))
    row = read_report(tmp_path)[0]
    assert row["text"] == 'Odstopi, prosim.\nLep pozdrav, Ana "A"'


def test_restore_republishes_listed_ids(sig, tmp_path):
    msg = Message.objects.create(
        signature=sig, recipient="Mijič", text="mail ana@example.com"
    )
    call_command("scan_messages", "--output", str(tmp_path))
    msg.refresh_from_db()
    assert msg.status == ModerationStatus.HIDDEN

    call_command("scan_messages", "--restore", str(msg.id), "--output", str(tmp_path))
    msg.refresh_from_db()
    assert msg.status == ModerationStatus.PUBLISHED


def test_restore_accepts_several_ids(sig, tmp_path):
    first = Message.objects.create(
        signature=sig, recipient="Mijič", text="a@example.com",
    )
    second = Message.objects.create(
        signature=sig, recipient="Mijič", text="b@example.com",
    )
    call_command("scan_messages", "--output", str(tmp_path))
    first.refresh_from_db()
    second.refresh_from_db()
    assert first.status == ModerationStatus.HIDDEN
    assert second.status == ModerationStatus.HIDDEN

    call_command("scan_messages", "--restore", f"{first.id},{second.id}", "--output", str(tmp_path))
    first.refresh_from_db()
    second.refresh_from_db()
    assert first.status == ModerationStatus.PUBLISHED
    assert second.status == ModerationStatus.PUBLISHED


def test_reports_totals_to_stdout(sig, tmp_path, capsys):
    Message.objects.create(signature=sig, recipient="Mijič", text="Odstopi.")
    Message.objects.create(signature=sig, recipient="Mijič", text="a@example.com")
    call_command("scan_messages", "--output", str(tmp_path))
    out = capsys.readouterr().out
    assert "2 scanned" in out
    assert "1 hidden" in out


def test_restore_with_non_integer_segment_raises_error(sig, tmp_path):
    msg = Message.objects.create(
        signature=sig, recipient="Mijič", text="mail ana@example.com"
    )
    call_command("scan_messages", "--output", str(tmp_path))
    with pytest.raises(CommandError) as exc_info:
        call_command("scan_messages", "--restore", f"{msg.id},abc", "--output", str(tmp_path))
    assert "comma-separated integer" in str(exc_info.value)


def test_restore_with_duplicate_ids_is_harmless(sig, tmp_path):
    msg = Message.objects.create(
        signature=sig, recipient="Mijič", text="mail ana@example.com"
    )
    call_command("scan_messages", "--output", str(tmp_path))
    msg.refresh_from_db()
    assert msg.status == ModerationStatus.HIDDEN

    call_command("scan_messages", "--restore", f"{msg.id},{msg.id}", "--output", str(tmp_path))
    msg.refresh_from_db()
    assert msg.status == ModerationStatus.PUBLISHED


def test_restore_with_unknown_id_raises_error(sig, tmp_path):
    msg = Message.objects.create(
        signature=sig, recipient="Mijič", text="mail ana@example.com"
    )
    call_command("scan_messages", "--output", str(tmp_path))
    with pytest.raises(CommandError) as exc_info:
        call_command("scan_messages", "--restore", "99999", "--output", str(tmp_path))
    assert "not found in report" in str(exc_info.value)


def test_restore_pending_message_goes_back_to_pending(sig, tmp_path):
    msg = Message.objects.create(
        signature=sig, recipient="Mijič", text="mail ana@example.com",
        status=ModerationStatus.PENDING,
    )
    call_command("scan_messages", "--output", str(tmp_path))
    msg.refresh_from_db()
    assert msg.status == ModerationStatus.HIDDEN

    call_command("scan_messages", "--restore", str(msg.id), "--output", str(tmp_path))
    msg.refresh_from_db()
    assert msg.status == ModerationStatus.PENDING


def test_restore_moderator_hidden_stays_hidden(sig, tmp_path):
    msg = Message.objects.create(
        signature=sig, recipient="Mijič", text="mail ana@example.com",
        status=ModerationStatus.HIDDEN,
    )
    call_command("scan_messages", "--output", str(tmp_path))
    msg.refresh_from_db()
    assert msg.status == ModerationStatus.HIDDEN

    call_command("scan_messages", "--restore", str(msg.id), "--output", str(tmp_path))
    msg.refresh_from_db()
    assert msg.status == ModerationStatus.HIDDEN


def test_dry_run_and_restore_together_raises_error(sig, tmp_path):
    msg = Message.objects.create(
        signature=sig, recipient="Mijič", text="mail ana@example.com"
    )
    call_command("scan_messages", "--output", str(tmp_path))
    with pytest.raises(CommandError) as exc_info:
        call_command("scan_messages", "--restore", str(msg.id), "--dry-run", "--output", str(tmp_path))
    assert "mutually exclusive" in str(exc_info.value)


def test_already_hidden_message_counted_as_matched_not_newly_hidden(sig, tmp_path, capsys):
    Message.objects.create(
        signature=sig, recipient="Mijič", text="mail ana@example.com",
        status=ModerationStatus.HIDDEN,
    )
    call_command("scan_messages", "--output", str(tmp_path))
    out = capsys.readouterr().out
    assert "1 scanned" in out
    assert "1 matched" in out
    assert "0 hidden" in out


def test_restore_with_bogus_previous_status_raises_error(sig, tmp_path):
    import csv as csv_module
    msg = Message.objects.create(
        signature=sig, recipient="Mijič", text="mail ana@example.com"
    )
    call_command("scan_messages", "--output", str(tmp_path))
    msg.refresh_from_db()
    assert msg.status == ModerationStatus.HIDDEN

    # Corrupt the CSV by changing previous_status to invalid value
    report_path = tmp_path / "message-pii-report.csv"
    rows = []
    with open(report_path, newline="", encoding="utf-8") as fh:
        reader = csv_module.DictReader(fh)
        for row in reader:
            row["previous_status"] = "publishd"  # typo
            rows.append(row)

    with open(report_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv_module.DictWriter(fh, fieldnames=["id", "previous_status", "kinds", "recipient", "text"])
        writer.writeheader()
        writer.writerows(rows)

    with pytest.raises(CommandError) as exc_info:
        call_command("scan_messages", "--restore", str(msg.id), "--output", str(tmp_path))
    assert "Invalid status" in str(exc_info.value)

    # Verify message status was not changed
    msg.refresh_from_db()
    assert msg.status == ModerationStatus.HIDDEN
