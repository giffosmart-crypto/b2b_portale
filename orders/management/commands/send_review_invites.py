from django.core.management.base import BaseCommand
from django.utils import timezone

from catalog.review_invites import (
    get_orders_for_first_invite,
    get_orders_for_reminder,
    send_review_invite,
    send_review_reminder,
)


class Command(BaseCommand):
    help = "Invia inviti recensione e reminder per ordini completati."

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-reminder",
            action="store_true",
            help="Invia solo i primi inviti, senza reminder.",
        )

    def handle(self, *args, **options):
        now = timezone.now()

        sent_invites = 0
        sent_reminders = 0

        # 1) PRIMI INVITI
        orders_for_invite = get_orders_for_first_invite(reference_time=now)
        for order in orders_for_invite:
            ok = send_review_invite(order)
            if ok:
                sent_invites += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Inviti recensione inviati: {sent_invites}"
            )
        )

        # 2) REMINDER (se non disattivato da opzione)
        if not options["no_reminder"]:
            orders_for_reminder = get_orders_for_reminder(reference_time=now)
            for order in orders_for_reminder:
                ok = send_review_reminder(order)
                if ok:
                    sent_reminders += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f"Reminder recensioni inviati: {sent_reminders}"
                )
            )
        else:
            self.stdout.write(
                "Esecuzione con opzione --no-reminder: nessun reminder inviato."
            )
