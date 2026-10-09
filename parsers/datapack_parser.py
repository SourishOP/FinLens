"""Parse HSBC Data Pack PDFs into a tidy quarterly financial time series.

Focus: the Group consolidated income statement (the cleanest, most continuous
series across quarters). The table has labelled rows and dated quarterly columns
like '31-Dec-24', '30-Sep-24', ... which we reshape to long format:

    period_end | metric | value_m   (values in $m)

We extract a curated set of headline metrics (NII, net operating income, ECL,
operating expenses, PBT, PAT) which feed the financials-forecast and risk modules.

Number formatting handled:
  * '8,185'      -> 8185.0
  * '(1,362)'    -> -1362.0   (parentheses = negative)
  * '—' / '-'    -> 0.0       (em-dash = nil)

Usage:
    python -m parsers.datapack_parser
"""
from __future__ import annotations

import io
import re
from pathlib import Path

import pandas as pd
import requests

try:
    import pdfplumber
except ImportError:  # pragma: no cover
    pdfplumber = None

_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = _ROOT / "data" / "financials"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; HSBC-FinOps-Project/1.0)"}

# Row label (as it appears in the PDF)  ->  tidy metric name.
# Matching is done on a normalised, lower-cased prefix so minor spacing/wording
# differences across quarters still match.
METRIC_ROWS = {
    "net interest income": "net_interest_income",
    "net fee income": "net_fee_income",
    "net operating income before change in expected credit losses": "net_operating_income",
    "change in expected credit losses": "expected_credit_losses",
    "total operating expenses": "total_operating_expenses",
    "profit/(loss) before tax": "profit_before_tax",
    "profit/(loss) after tax": "profit_after_tax",
}

_DATE_RE = re.compile(r"\d{1,2}[\u2010\-]\w{3}[\u2010\-]\d{2}")  # 31-Dec-24
_NUM_RE = re.compile(r"\(?-?[\d,]+\)?|[\u2014\-]")               # 8,185 / (1,362) / —


def _to_float(token: str) -> float | None:
    token = token.strip()
    if token in {"\u2014", "-", "", "—"}:
        return 0.0
    neg = token.startswith("(") and token.endswith(")")
    cleaned = token.strip("()").replace(",", "")
    if not re.fullmatch(r"-?\d+(\.\d+)?", cleaned):
        return None
    val = float(cleaned)
    return -val if neg else val


def _parse_period_headers(text_lines: list[str]) -> list[str]:
    """Find the row of quarter-end dates and return them as ISO strings."""
    for line in text_lines:
        dates = _DATE_RE.findall(line)
        if len(dates) >= 4:  # the quarterly header row has several dates
            return [_iso_date(d) for d in dates]
    return []


def _iso_date(token: str) -> str:
    token = token.replace("\u2010", "-")
    try:
        return pd.to_datetime(token, format="%d-%b-%y").strftime("%Y-%m-%d")
    except Exception:
        return token


def parse_income_statement(pdf_bytes: bytes, quarter: str) -> pd.DataFrame:
    """Return a long DataFrame: period_end, metric, value_m, quarter_tag."""
    if pdfplumber is None:
        raise ImportError("pdfplumber is required to parse Data Pack PDFs")

    pdf = pdfplumber.open(io.BytesIO(pdf_bytes))
    # The group income statement is near the front; scan the first ~8 pages for
    # the page whose text contains the consolidated income statement header.
    target_text = None
    for page in pdf.pages[:8]:
        txt = page.extract_text() or ""
        if "consolidated income statement" in txt.lower():
            target_text = txt
            break
    if target_text is None:
        raise ValueError(f"{quarter}: income statement page not found")

    lines = target_text.splitlines()
    periods = _parse_period_headers(lines)
    if not periods:
        raise ValueError(f"{quarter}: could not read quarterly date headers")
    # Only the first len(periods) numbers on each row are the 'quarter ended'
    # columns (the pack repeats some as year-to-date); we keep the quarterly set.
    n_quarter_cols = min(len(periods), 5)

    records: list[dict] = []
    for line in lines:
        low = line.lower()
        matched = next((tidy for key, tidy in METRIC_ROWS.items()
                        if low.startswith(key)), None)
        if not matched:
            continue
        tokens = _NUM_RE.findall(line)
        values = [_to_float(t) for t in tokens]
        values = [v for v in values if v is not None]
        for period, val in zip(periods[:n_quarter_cols], values[:n_quarter_cols]):
            records.append({"period_end": period, "metric": matched,
                            "value_m": val, "source_quarter": quarter})

    df = pd.DataFrame(records).drop_duplicates(subset=["period_end", "metric"])
    return df.sort_values(["metric", "period_end"]).reset_index(drop=True)


def parse_from_registry() -> pd.DataFrame:
    """Parse every downloaded pack listed in the scraper registry."""
    import json
    reg_file = _ROOT / "data" / "datapack_registry.json"
    if not reg_file.exists():
        raise FileNotFoundError(
            "No registry found. Run scrapers.hsbc_financials_scraper first.")
    registry = json.loads(reg_file.read_text())

    frames = []
    for key, rec in registry.items():
        path = Path(rec["local_path"])
        pdf_bytes = path.read_bytes() if path.exists() else \
            requests.get(rec["url"], headers=HEADERS, timeout=90).content
        try:
            frames.append(parse_income_statement(pdf_bytes, key))
            print(f"[parser] {key}: parsed OK")
        except Exception as exc:
            print(f"[parser] {key}: FAILED ({exc})")

    if not frames:
        return pd.DataFrame(columns=["period_end", "metric", "value_m"])
    combined = (pd.concat(frames, ignore_index=True)
                .drop_duplicates(subset=["period_end", "metric"])
                .sort_values(["metric", "period_end"])
                .reset_index(drop=True))
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUTPUT_DIR / "group_income_statement_long.csv"
    combined.to_csv(out, index=False)
    print(f"[parser] wrote {len(combined)} rows -> {out}")
    return combined


if __name__ == "__main__":
    df = parse_from_registry()
    if not df.empty:
        print("\nTidy quarterly series (sample):")
        wide = df.pivot_table(index="period_end", columns="metric",
                              values="value_m", aggfunc="first")
        print(wide.to_string())
