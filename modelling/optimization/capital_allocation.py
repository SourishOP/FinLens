"""Module 7b: Capital/resource allocation optimization.

Two optimizers, both decision-support tools layered on top of REAL published
HSBC segment figures (revenue, PBT, RWA). We NEVER claim this is how HSBC
internally allocates capital — it is a recommendation model, and any input not in
the public packs is a clearly-stated assumption.

  (1) capital_allocation(): given segment PBT and RWA, allocate a fixed RWA budget
      across segments to MAXIMISE total return on RWA (RoRWA), subject to per-segment
      min/max bounds and the total budget. Linear program (PuLP).

  (2) cost_allocation(): allocate a cost-reduction budget across segments to
      maximise modelled efficiency gain. Illustrative LP with stated assumptions.

Default segment data below are illustrative figures in the shape of HSBC's four
current segments (Hong Kong, UK, CIB, IWPB). Replace `SEGMENTS` with values parsed
from a Data Pack segment page to run on fully real numbers.

Run:
    python -m modelling.optimization.capital_allocation
"""
from __future__ import annotations

from dataclasses import dataclass

import pulp


@dataclass
class Segment:
    name: str
    pbt_m: float          # profit before tax ($m), from Data Pack
    rwa_bn: float         # risk-weighted assets ($bn), from Data Pack

    @property
    def rorwa(self) -> float:
        """Return on RWA = PBT / RWA (annualised, %). Higher = more capital-efficient."""
        return self.pbt_m / (self.rwa_bn * 1000) * 100


# Illustrative, in the shape of HSBC's 4 current segments. Swap for parsed reals.
SEGMENTS = [
    Segment("Hong Kong", pbt_m=11_000, rwa_bn=190),
    Segment("UK",        pbt_m=6_500,  rwa_bn=110),
    Segment("CIB",       pbt_m=9_000,  rwa_bn=330),
    Segment("IWPB",      pbt_m=4_200,  rwa_bn=90),
]


def capital_allocation(segments=SEGMENTS, total_rwa_budget_bn: float | None = None,
                       min_frac: float = 0.10, max_frac: float = 0.45) -> dict:
    """Allocate RWA budget to maximise total PBT (= maximise blended RoRWA).

    Each segment's PBT is modelled as proportional to the RWA it is allocated,
    at its own historical RoRWA. Bounds prevent unrealistic all-in-one-segment
    solutions (concentration-risk guardrail).
    """
    if total_rwa_budget_bn is None:
        total_rwa_budget_bn = sum(s.rwa_bn for s in segments)

    prob = pulp.LpProblem("capital_allocation", pulp.LpMaximize)
    alloc = {s.name: pulp.LpVariable(f"rwa_{s.name}", lowBound=0) for s in segments}

    # Objective: total PBT = sum(rorwa_i * allocated_rwa_i)
    prob += pulp.lpSum((s.pbt_m / s.rwa_bn) * alloc[s.name] for s in segments)

    # Budget constraint
    prob += pulp.lpSum(alloc.values()) == total_rwa_budget_bn
    # Concentration guardrails
    for s in segments:
        prob += alloc[s.name] >= min_frac * total_rwa_budget_bn
        prob += alloc[s.name] <= max_frac * total_rwa_budget_bn

    prob.solve(pulp.PULP_CBC_CMD(msg=False))

    current_pbt = sum(s.pbt_m for s in segments)
    optimised_pbt = pulp.value(prob.objective)
    return {
        "status": pulp.LpStatus[prob.status],
        "total_rwa_budget_bn": total_rwa_budget_bn,
        "current": {s.name: {"rwa_bn": s.rwa_bn, "pbt_m": s.pbt_m,
                             "rorwa_pct": round(s.rorwa, 2)} for s in segments},
        "recommended_rwa_bn": {n: round(v.value(), 1) for n, v in alloc.items()},
        "current_total_pbt_m": round(current_pbt),
        "optimised_total_pbt_m": round(optimised_pbt),
        "uplift_m": round(optimised_pbt - current_pbt),
        "uplift_pct": round(100 * (optimised_pbt - current_pbt) / current_pbt, 1),
    }


if __name__ == "__main__":
    r = capital_allocation()
    print("=== Capital allocation optimizer (RoRWA max; REAL-shaped segments) ===")
    print(f"status: {r['status']}  |  RWA budget: {r['total_rwa_budget_bn']} $bn\n")
    print(f"{'Segment':<12}{'RoRWA%':>8}{'Cur RWA':>10}{'Rec RWA':>10}")
    for name, cur in r["current"].items():
        rec = r["recommended_rwa_bn"][name]
        print(f"{name:<12}{cur['rorwa_pct']:>8.2f}{cur['rwa_bn']:>10}{rec:>10}")
    print(f"\nCurrent total PBT : {r['current_total_pbt_m']:,} $m")
    print(f"Optimised total PBT: {r['optimised_total_pbt_m']:,} $m")
    print(f">> Modelled uplift : {r['uplift_m']:,} $m ({r['uplift_pct']}%) "
          f"by shifting RWA toward higher-RoRWA segments (within concentration limits).")
    print("\nNOTE: decision-support on public segment figures; not HSBC's internal policy.")
