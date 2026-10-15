import random

from django.core.management.base import BaseCommand

from petition.models import Message, Signature

EMAIL_PREFIX = "test-seed-"
RECIPIENTS = ["Mijič", "Stevanović", "Logar", "Vrtovec", "Janša"]


class Command(BaseCommand):
    help = (
        "Seed (or delete) throwaway test signatures/messages for exercising "
        "pagination locally. Emails are tagged with a 'test-seed-' prefix so "
        "they're easy to find and remove afterwards."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "count", type=int, nargs="?", default=340,
            help="Number of test signatures to create (default: 340).",
        )
        parser.add_argument(
            "--delete", action="store_true",
            help="Delete all previously seeded test signatures instead of creating new ones.",
        )

    def handle(self, *args, **options):
        if options["delete"]:
            deleted, _ = Signature.objects.filter(
                email__istartswith=EMAIL_PREFIX
            ).delete()
            self.stdout.write(self.style.SUCCESS(f"Deleted {deleted} seeded rows."))
            return

        count = options["count"]
        rng = random.Random(42)  # deterministic, so repeated runs are reproducible
        created = 0

        for i in range(1, count + 1):
            anonymous = i % 5 == 0
            signature = Signature.objects.create(
                name=f"Testni Podpisnik {i}",
                email=f"{EMAIL_PREFIX}{i}@example.com",
                consent=True,
                anonymous=anonymous,
            )
            if i % 2 == 0:
                Message.objects.create(
                    signature=signature,
                    recipient=rng.choice(RECIPIENTS),
                    text=f"Testno sporočilo številka {i}, za namene preizkušanja paginacije.",
                )
            created += 1

        self.stdout.write(self.style.SUCCESS(f"Created {created} test signatures."))
