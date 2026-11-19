import statistics
from datetime import timedelta
from decimal import Decimal

from backend.app.agents.base import Agent, AgentResult, expenses, fmt_money, num
from backend.app.data.snapshot import FinanceSnapshot, TransactionView

RECENT_DAYS = 30
HISTORY_DAYS = 180
ROBUST_Z_LIMIT = 3.5
MIN_HISTORY = 5
MIN_AMOUNT = Decimal("20")
DUPLICATE_WINDOW_DAYS = 3


def _normalise(description: str) -> str:
    return " ".join(description.lower().split())


class AnomalyAgent(Agent):
    name = "anomaly"
    description = "Unusually large charges (robust z-score per category) and possible duplicate payments."

    def run(self, snapshot: FinanceSnapshot) -> AgentResult:
        cur = snapshot.currency
        recent_start = snapshot.as_of - timedelta(days=RECENT_DAYS - 1)
        recent = expenses(snapshot.transactions, recent_start, snapshot.as_of)
        history = expenses(snapshot.transactions, recent_start - timedelta(days=HISTORY_DAYS), recent_start - timedelta(days=1))

        per_category: dict[str, list[float]] = {}
        for t in history:
            per_category.setdefault(t.category, []).append(float(-t.amount))

        unusual = []
        for t in sorted(recent, key=lambda tx: tx.booked_on):
            amount = -t.amount
            past = per_category.get(t.category, [])
            if amount < MIN_AMOUNT or len(past) < MIN_HISTORY:
                continue
            median = statistics.median(past)
            mad = statistics.median(abs(x - median) for x in past)
            if mad == 0:
                score = float("inf") if float(amount) > median * 2 else 0.0
            else:
                score = 0.6745 * (float(amount) - median) / mad  # Iglewicz-Hoaglin modified z-score
            if score > ROBUST_Z_LIMIT and float(amount) > median * 2:
                unusual.append((t, median, score))

        duplicates = self._duplicates(recent)

        alerts = [
            f"{t.booked_on.isoformat()}: {fmt_money(-t.amount, cur)} at '{t.description}' is far above your usual "
            f"{t.category} spend (median {fmt_money(median, cur)})."
            for t, median, _ in unusual[:5]
        ]
        alerts += [
            f"Possible duplicate: {fmt_money(-a.amount, cur)} '{a.description}' on {a.booked_on.isoformat()} "
            f"and {b.booked_on.isoformat()}."
            for a, b in duplicates[:5]
        ]
        if unusual or duplicates:
            summary = (
                f"In the last {RECENT_DAYS} days: {len(unusual)} unusually large charge(s) and "
                f"{len(duplicates)} possible duplicate payment(s)."
            )
        else:
            summary = f"Nothing unusual found in the last {RECENT_DAYS} days."

        return AgentResult(
            agent=self.name,
            summary=summary,
            alerts=alerts,
            facts={
                "currency": cur,
                "window_days": RECENT_DAYS,
                "unusual": [
                    {
                        "date": t.booked_on.isoformat(),
                        "description": t.description,
                        "category": t.category,
                        "amount": num(-t.amount),
                        "category_median": num(median),
                        "robust_z": None if score == float("inf") else round(score, 1),
                    }
                    for t, median, score in unusual
                ],
                "possible_duplicates": [
                    {
                        "description": a.description,
                        "amount": num(-a.amount),
                        "dates": [a.booked_on.isoformat(), b.booked_on.isoformat()],
                    }
                    for a, b in duplicates
                ],
            },
        )

    @staticmethod
    def _duplicates(recent: list[TransactionView]) -> list[tuple[TransactionView, TransactionView]]:
        found = []
        ordered = sorted(recent, key=lambda t: (t.booked_on, _normalise(t.description)))
        for i, a in enumerate(ordered):
            for b in ordered[i + 1 :]:
                if (b.booked_on - a.booked_on).days > DUPLICATE_WINDOW_DAYS:
                    break
                if a.amount == b.amount and a.account_id == b.account_id and _normalise(a.description) == _normalise(b.description):
                    found.append((a, b))
        return found
