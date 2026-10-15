import csv

import pytest
from django.core.management import call_command

from petition.models import Message, ModerationStatus, Signature

pytestmark = pytest.mark.django_db


def make_signature(email, newsletter=True, **kwargs):
    return Signature.objects.create(
        name="Ana", email=email, consent=True, newsletter=newsletter, **kwargs
    )


def read_export(tmp_path):
    with open(tmp_path / "newsletter-emails.csv", newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_header_and_columns(tmp_path):
    make_signature("a@example.com")
    call_command("export_newsletter", "--output", str(tmp_path))
    rows = read_export(tmp_path)
    assert list(rows[0].keys()) == ["email", "created_at"]


def test_subscriber_with_no_message_is_included(tmp_path):
    # Review Focus 1: most signatures have no message at all. An exclusion
    # written as a join would silently drop the bulk of the mailing list.
    make_signature("nomessage@example.com")
    call_command("export_newsletter", "--output", str(tmp_path))
    assert [r["email"] for r in read_export(tmp_path)] == ["nomessage@example.com"]


def test_non_subscriber_is_excluded(tmp_path):
    make_signature("no@example.com", newsletter=False)
    call_command("export_newsletter", "--output", str(tmp_path))
    assert read_export(tmp_path) == []


def test_published_message_does_not_exclude(tmp_path):
    sig = make_signature("yes@example.com")
    Message.objects.create(signature=sig, recipient="Mijič", text="Odstopi.")
    call_command("export_newsletter", "--output", str(tmp_path))
    assert [r["email"] for r in read_export(tmp_path)] == ["yes@example.com"]


def test_hidden_message_excludes(tmp_path):
    sig = make_signature("hidden@example.com")
    Message.objects.create(
        signature=sig, recipient="Mijič", text="x", status=ModerationStatus.HIDDEN
    )
    call_command("export_newsletter", "--output", str(tmp_path))
    assert read_export(tmp_path) == []


def test_pending_message_excludes(tmp_path):
    sig = make_signature("pending@example.com")
    Message.objects.create(
        signature=sig, recipient="Mijič", text="x", status=ModerationStatus.PENDING
    )
    call_command("export_newsletter", "--output", str(tmp_path))
    assert read_export(tmp_path) == []


def test_mixed_messages_exclude_if_any_is_hidden(tmp_path):
    # Review Focus 2: the rule is "any hidden message", and the schema allows
    # several messages per signature even though the form submits one.
    sig = make_signature("mixed@example.com")
    Message.objects.create(signature=sig, recipient="Mijič", text="fine")
    Message.objects.create(
        signature=sig, recipient="Mijič", text="bad", status=ModerationStatus.HIDDEN
    )
    call_command("export_newsletter", "--output", str(tmp_path))
    assert read_export(tmp_path) == []


def test_hidden_name_does_not_exclude(tmp_path):
    # A rejected *name* is not grounds for removal from the mailing list.
    make_signature("namehidden@example.com", name_status=ModerationStatus.HIDDEN)
    call_command("export_newsletter", "--output", str(tmp_path))
    assert [r["email"] for r in read_export(tmp_path)] == ["namehidden@example.com"]


def test_reports_counts_to_stdout(tmp_path, capsys):
    make_signature("in@example.com")
    excluded = make_signature("out@example.com")
    Message.objects.create(
        signature=excluded, recipient="Mijič", text="x",
        status=ModerationStatus.HIDDEN,
    )
    call_command("export_newsletter", "--output", str(tmp_path))
    out = capsys.readouterr().out
    assert "1 exported" in out
    assert "1 excluded" in out


def test_multiple_published_messages_yields_single_row(tmp_path):
    # A signature with multiple non-excluding messages must appear exactly once.
    # This catches a potential bug if the exclusion is later rewritten as a
    # filter/join instead of exclude(), which would duplicate rows.
    sig = make_signature("multi@example.com")
    Message.objects.create(signature=sig, recipient="Mijič", text="first")
    Message.objects.create(signature=sig, recipient="Mijič", text="second")
    call_command("export_newsletter", "--output", str(tmp_path))
    rows = read_export(tmp_path)
    assert len([r for r in rows if r["email"] == "multi@example.com"]) == 1


def test_nested_output_directory_is_created(tmp_path):
    # The --output path may not exist. mkdir(parents=True) must create it.
    # pytest's tmp_path fixture pre-creates its directory, so we must test
    # with a nested non-existent path to exercise the mkdir() code path.
    nested = tmp_path / "does-not-exist" / "nested"
    make_signature("nested@example.com")
    call_command("export_newsletter", "--output", str(nested))
    rows = read_export(nested)
    assert [r["email"] for r in rows] == ["nested@example.com"]
