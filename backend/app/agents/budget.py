from decimal import Decimal

from backend.app.agents.base import (
    Agent,
    AgentResult,
    add_months,
    by_category,
    days_in_month,
    expenses,
    fmt_money,
    month_end,
    month_start,
    num,
)
from backend.app.data.snapshot import FinanceSnapshot

NEEDS = frozenset({"housing", "utilities", "groceries", "health", "transport", "education"})
WARNING_THRESHOLD = Decimal("0.8")


def budget_status(spent: Decimal, limit: Decimal) -> str:
    if spent > limit:
        return "over"
    if spent >= limit * WARNING_THRESHOLD:
        return "warning"
    return "ok"


class BudgetAgent(Agent):
    name = "budget"
    description = "Budgets versus actual spending, month-end projection and the 50/30/20 rule."

    def run(self, snapshot: FinanceSnapshot) -> AgentResult:
        cur = snapshot.currency
        today = snapshot.as_of
        spent = by_category(expenses(snapshot.transactions, month_start(today), today))
        elapsed, total_days = today.day, days_in_month(today)

        rows, alerts = [], []
        for category, limit in sorted(snapshot.budgets.items()):
            used = spent.get(category, Decimal("0"))
            projected = used / elapsed * total_days
            status = budget_status(used, limit)
            rows.append(
                {
                    "category": category,
                    "limit": num(limit),
                    "spent": num(used),
                    "percent_used": round(float(used / limit * 100), 1),
                    "projected_month_end": num(projected),
                    "status": status,
                }
            )
            if status == "over":
                alerts.append(f"{category.title()} is over budget: {fmt_money(used, cur)} of {fmt_money(limit, cur)}.")
            elif projected > limit:
                alerts.append(
                    f"{category.title()} is on course for {fmt_money(projected, cur)} this month (budget {fmt_money(limit, cur)})."
                )

        rule = self._fifty_thirty_twenty(snapshot)
        if rule and rule["wants_pct"] > 30:
            alerts.append(f"Wants took {rule['wants_pct']:.0f}% of income last month (50/30/20 guideline: 30%).")
        if rule and rule["savings_pct"] < 20:
            alerts.append(f"You saved {rule['savings_pct']:.0f}% of income last month (guideline: 20%).")

        if rows:
            over = sum(1 for r in rows if r["status"] == "over")
            warn = sum(1 for r in rows if r["status"] == "warning")
            noun = "budget" if len(rows) == 1 else "budgets"
            summary = f"{len(rows)} {noun} tracked: {over} over, {warn} close to the limit, {len(rows) - over - warn} on track."
        else:
            summary = "No budgets are set yet. Add monthly limits per category to get budget tracking."

        return AgentResult(
            agent=self.name,
            summary=summary,
            alerts=alerts,
            facts={"currency": cur, "budgets": rows, "rule_50_30_20": rule, "days_elapsed": elapsed},
        )

    @staticmethod
    def _fifty_thirty_twenty(snapshot: FinanceSnapshot) -> dict | None:
        start = add_months(month_start(snapshot.as_of), -1)
        end = month_end(start)
        month = [t for t in snapshot.transactions if start <= t.booked_on <= end]
        income = sum((t.amount for t in month if t.amount > 0 and t.category == "income"), Decimal("0"))
        if income <= 0:
            return None
        needs = sum((-t.amount for t in month if t.amount < 0 and t.category in NEEDS), Decimal("0"))
        wants = sum(
            (-t.amount for t in month if t.amount < 0 and t.category not in NEEDS | {"transfer", "savings"}),
            Decimal("0"),
        )
        savings = income - needs - wants
        return {
            "month": start.strftime("%Y-%m"),
            "income": num(income),
            "needs_pct": round(float(needs / income * 100), 1),
            "wants_pct": round(float(wants / income * 100), 1),
            "savings_pct": round(float(savings / income * 100), 1),
        }
