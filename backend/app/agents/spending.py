from datetime import timedelta
from decimal import Decimal

from backend.app.agents.base import (
    Agent,
    AgentResult,
    by_category,
    expenses,
    fmt_money,
    month_start,
    num,
    previous_month_same_period,
    total_spent,
)
from backend.app.data.snapshot import FinanceSnapshot


class SpendingAgent(Agent):
    name = "spending"
    description = "Where the money goes: month-to-date spending by category and merchant."

    def run(self, snapshot: FinanceSnapshot) -> AgentResult:
        cur = snapshot.currency
        start = month_start(snapshot.as_of)
        this_month = expenses(snapshot.transactions, start, snapshot.as_of)
        prev_start, prev_end = previous_month_same_period(snapshot.as_of)
        last_month = expenses(snapshot.transactions, prev_start, prev_end)

        spent, previous = total_spent(this_month), total_spent(last_month)
        change_pct = float((spent - previous) / previous * 100) if previous > 0 else None
        categories, prev_categories = by_category(this_month), by_category(last_month)

        increases = sorted(
            ((c, amount - prev_categories.get(c, Decimal("0"))) for c, amount in categories.items()),
            key=lambda kv: kv[1],
            reverse=True,
        )
        merchants: dict[str, Decimal] = {}
        for t in expenses(snapshot.transactions, snapshot.as_of - timedelta(days=29), snapshot.as_of):
            key = " ".join(t.description.split()).title()
            merchants[key] = merchants.get(key, Decimal("0")) - t.amount
        top_merchants = sorted(merchants.items(), key=lambda kv: kv[1], reverse=True)[:5]

        if not this_month:
            summary = "No spending recorded so far this month."
        else:
            top_cat, top_amt = next(iter(categories.items()))
            trend = (
                f", {abs(change_pct):.0f}% {'more' if change_pct >= 0 else 'less'} than the same days last month"
                if change_pct is not None
                else ""
            )
            summary = (
                f"You have spent {fmt_money(spent, cur)} in the first {snapshot.as_of.day} days of this month{trend}. "
                f"Largest category: {top_cat} ({fmt_money(top_amt, cur)})."
            )

        alerts = []
        if change_pct is not None and change_pct > 25:
            alerts.append(f"Spending is up {change_pct:.0f}% on the same period last month.")
        for category, delta in increases[:2]:
            if delta > 0 and prev_categories.get(category, Decimal("0")) > 0 and delta / prev_categories[category] > 0.5:
                alerts.append(f"{category.title()} spending rose by {fmt_money(delta, cur)} versus last month.")

        return AgentResult(
            agent=self.name,
            summary=summary,
            alerts=alerts,
            facts={
                "currency": cur,
                "period": {"start": start.isoformat(), "end": snapshot.as_of.isoformat()},
                "month_to_date_spend": num(spent),
                "previous_month_same_period_spend": num(previous),
                "change_pct": round(change_pct, 1) if change_pct is not None else None,
                "by_category": {c: num(v) for c, v in categories.items()},
                "largest_increases": [{"category": c, "increase": num(d)} for c, d in increases[:3] if d > 0],
                "top_merchants_30d": [{"description": m, "spend": num(v)} for m, v in top_merchants],
            },
        )
