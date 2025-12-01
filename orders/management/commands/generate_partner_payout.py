from datetime import datetime
from django.core.management.base import BaseCommand, CommandError

from orders.services import build_partner_payouts


class Command(BaseCommand):
    help = "Genera/aggiorna i PartnerPayout per un intervallo di date (YYYY-MM-DD YYYY-MM-DD)."

    def add_arguments(self, parser):
        parser.add_argument("period_start", type=str, help="Data inizio (YYYY-MM-DD)")
        parser.add_argument("period_end", type=str, help="Data fine (YYYY-MM-DD)")

    def handle(self, *args, **options):
        try:
            period_start = datetime.strptime(options["period_start"], "%Y-%m-%d").date()
            period_end = datetime.strptime(options["period_end"], "%Y-%m-%d").date()
        except ValueError:
            raise CommandError("Formato data non valido. Usa YYYY-MM-DD.")

        payouts = build_partner_payouts(period_start, period_end)

        self.stdout.write(
            self.style.SUCCESS(
                f"Generati/aggiornati {len(payouts)} payout per il periodo {period_start} → {period_end}."
            )
        )
