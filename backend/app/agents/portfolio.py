from decimal import Decimal

from backend.app.agents.base import Agent, AgentResult, fmt_money, num
from backend.app.data.snapshot import FinanceSnapshot

POSITION_LIMIT = Decimal("0.25")
ASSET_CLASS_LIMIT = Decimal("0.80")


class PortfolioAgent(Agent):
    name = "portfolio"
    description = "Investment value, unrealised gain, allocation and concentration risk."

    def run(self, snapshot: FinanceSnapshot) -> AgentResult:
        cur = snapshot.currency
        holdings = snapshot.holdings
        total = sum((h.market_value for h in holdings), Decimal("0"))
        if not holdings or total <= 0:
            return AgentResult(
                agent=self.name,
                summary="No investment holdings with a market value are recorded.",
                facts={"currency": cur, "holdings": 0},
            )

        cost = sum((h.cost_basis for h in holdings), Decimal("0"))
        gain = total - cost
        gain_pct = float(gain / cost * 100) if cost > 0 else None

        weights = sorted(((h.symbol, h.market_value / total) for h in holdings), key=lambda kv: kv[1], reverse=True)
        allocation: dict[str, Decimal] = {}
        for h in holdings:
            allocation[h.asset_class] = allocation.get(h.asset_class, Decimal("0")) + h.market_value / total
        hhi = sum((w * w for _, w in weights), Decimal("0"))
        effective_positions = float(1 / hhi) if hhi > 0 else 0.0

        alerts = []
        top_symbol, top_weight = weights[0]
        if len(holdings) > 1 and top_weight > POSITION_LIMIT:
            alerts.append(f"{top_symbol} is {float(top_weight) * 100:.0f}% of the portfolio (concentration risk above 25%).")
        top_class, top_class_weight = max(allocation.items(), key=lambda kv: kv[1])
        if top_class_weight > ASSET_CLASS_LIMIT:
            alerts.append(f"{float(top_class_weight) * 100:.0f}% of the portfolio is in {top_class}.")

        gain_text = f"{'up' if gain >= 0 else 'down'} {fmt_money(abs(gain), cur)}" + (
            f" ({gain_pct:+.1f}%)" if gain_pct is not None else ""
        )
        summary = (
            f"Portfolio worth {fmt_money(total, cur)} across {len(holdings)} holdings, {gain_text} on cost. "
            f"Largest position: {top_symbol} at {float(top_weight) * 100:.0f}%."
        )
        return AgentResult(
            agent=self.name,
            summary=summary,
            alerts=alerts,
            facts={
                "currency": cur,
                "holdings": len(holdings),
                "market_value": num(total),
                "cost_basis": num(cost),
                "unrealised_gain": num(gain),
                "unrealised_gain_pct": round(gain_pct, 2) if gain_pct is not None else None,
                "allocation_pct": {k: round(float(v) * 100, 1) for k, v in sorted(allocation.items())},
                "weights_pct": {s: round(float(w) * 100, 1) for s, w in weights},
                "effective_number_of_positions": round(effective_positions, 2),
            },
        )
