import statistics
from decimal import Decimal

from backend.app.agents.base import Agent, AgentResult, add_months, fmt_money, month_end, month_start, num
from backend.app.data.snapshot import FinanceSnapshot

LIQUID_ACCOUNTS = frozenset({"current", "savings", "cash"})
HISTORY_MONTHS = 6


class CashflowAgent(Agent):
    name = "cashflow"
    description = "Monthly income vs spending, savings rate, next-month projection and emergency-fund cover."

    def run(self, snapshot: FinanceSnapshot) -> AgentResult:
        cur = snapshot.currency
        months = []
        first_tx = min((t.booked_on for t in snapshot.transactions), default=None)
        for back in range(HISTORY_MONTHS, 0, -1):
            start = add_months(month_start(snapshot.as_of), -back)
            end = month_end(start)
            if first_tx is None or end < first_tx:
                continue  # no history yet for this month
            rows = [t for t in snapshot.transactions if start <= t.booked_on <= end and t.category != "transfer"]
            income = sum((t.amount for t in rows if t.amount > 0), Decimal("0"))
            spend = sum((-t.amount for t in rows if t.amount < 0 and t.category != "savings"), Decimal("0"))
            months.append({"month": start.strftime("%Y-%m"), "income": income, "spending": spend, "net": income - spend})

        liquid = sum((a.balance for a in snapshot.accounts if a.account_type in LIQUID_ACCOUNTS), Decimal("0"))
        if not months:
            return AgentResult(
                agent=self.name,
                summary="Not enough history yet: cash-flow analysis needs at least one complete month of transactions.",
                facts={"currency": cur, "months": [], "liquid_balance": num(liquid)},
            )

        avg_income = sum((m["income"] for m in months), Decimal("0")) / len(months)
        avg_spend = sum((m["spending"] for m in months), Decimal("0")) / len(months)
        savings_rate = float((avg_income - avg_spend) / avg_income * 100) if avg_income > 0 else None
        cover_months = float(liquid / avg_spend) if avg_spend > 0 else None

        projection = None
        if len(months) >= 3:
            nets = [float(m["net"]) for m in months]
            fit = statistics.linear_regression(list(range(len(nets))), nets)
            projection = fit.slope * len(nets) + fit.intercept

        alerts = []
        if savings_rate is not None and savings_rate < 0:
            alerts.append(f"On average you spent {fmt_money(avg_spend - avg_income, cur)} more than you earned per month.")
        if cover_months is not None and cover_months < 3:
            alerts.append(f"Easy-access savings cover {cover_months:.1f} months of spending (a common target is 3-6).")
        if projection is not None and projection < 0:
            alerts.append(f"The trend points to a shortfall of about {fmt_money(-projection, cur)} next month.")

        rate_text = f", saving {savings_rate:.0f}% of income" if savings_rate is not None else ""
        summary = (
            f"Over the last {len(months)} months you averaged {fmt_money(avg_income, cur)} in and "
            f"{fmt_money(avg_spend, cur)} out{rate_text}."
        )
        if cover_months is not None:
            summary += f" Easy-access money covers {cover_months:.1f} months of spending."

        return AgentResult(
            agent=self.name,
            summary=summary,
            alerts=alerts,
            facts={
                "currency": cur,
                "months": [{k: (num(v) if k != "month" else v) for k, v in m.items()} for m in months],
                "average_income": num(avg_income),
                "average_spending": num(avg_spend),
                "savings_rate_pct": round(savings_rate, 1) if savings_rate is not None else None,
                "liquid_balance": num(liquid),
                "emergency_fund_months": round(cover_months, 1) if cover_months is not None else None,
                "projected_next_month_net": round(projection, 2) if projection is not None else None,
            },
        )
