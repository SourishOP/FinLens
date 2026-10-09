"""SQL safety validation — the security boundary for the NL->SQL feature.

In a banking context, letting an LLM generate SQL that hits the warehouse is only
acceptable with a strict allow-list gate. This module enforces, before ANY query
runs:

  1. Single statement only (no stacked `;` statements).
  2. SELECT (or WITH ... SELECT) only — read-only.
  3. Hard block on any mutating / DDL / admin keyword
     (DROP, DELETE, UPDATE, INSERT, MERGE, ALTER, CREATE, TRUNCATE, GRANT, ...).
  4. Table references restricted to the approved HSBC datasets.
  5. A mandatory LIMIT is injected if the user/LLM didn't supply one.

The validator returns a ValidationResult; the caller must refuse to run anything
that isn't `ok`. This is intentionally conservative: false negatives (rejecting a
safe-but-weird query) are acceptable; false positives (allowing a mutation) are not.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Mutating / DDL / admin keywords that must never appear.
_FORBIDDEN = [
    "insert", "update", "delete", "drop", "truncate", "alter", "create",
    "merge", "replace", "grant", "revoke", "call", "execute", "exec",
    "attach", "detach", "pragma", "vacuum", "reindex", "copy", "load",
    "export", "begin", "commit", "rollback",
]
# Allowed dataset prefixes (set at construction to match config).
_DEFAULT_ALLOWED = ("hsbc_raw", "hsbc_staging", "hsbc_marts")

_DANGEROUS_TOKEN = re.compile(r"[;]")  # statement separator
_LIMIT_RE = re.compile(r"\blimit\s+\d+", re.IGNORECASE)
# crude table-ref finder: words after FROM / JOIN
_TABLE_RE = re.compile(r"\b(?:from|join)\s+`?([a-zA-Z0-9_.\-]+)`?", re.IGNORECASE)


@dataclass
class ValidationResult:
    ok: bool
    sql: str                 # possibly-rewritten safe SQL (LIMIT injected)
    reason: str = ""


class SqlGuard:
    def __init__(self, allowed_datasets: tuple[str, ...] = _DEFAULT_ALLOWED,
                 default_limit: int = 1000):
        self.allowed = tuple(allowed_datasets)
        self.default_limit = default_limit

    def validate(self, sql: str) -> ValidationResult:
        if not sql or not sql.strip():
            return ValidationResult(False, sql, "empty query")

        cleaned = self._strip_comments(sql).strip().rstrip(";").strip()
        lowered = cleaned.lower()

        # 1) single statement
        if _DANGEROUS_TOKEN.search(cleaned):
            return ValidationResult(False, sql,
                                    "multiple statements are not allowed")

        # 2) must start with select or with
        if not (lowered.startswith("select") or lowered.startswith("with")):
            return ValidationResult(False, sql,
                                    "only SELECT queries are allowed")

        # 3) forbidden keywords (word-boundary matched to avoid false hits like
        #    'created_at' containing 'create')
        for kw in _FORBIDDEN:
            if re.search(rf"\b{kw}\b", lowered):
                return ValidationResult(False, sql,
                                        f"forbidden keyword: {kw.upper()}")

        # 4) table references must be within allowed datasets
        bad = self._disallowed_tables(cleaned)
        if bad:
            return ValidationResult(
                False, sql,
                f"table(s) not in allowed datasets {self.allowed}: {', '.join(bad)}")

        # 5) inject a LIMIT if missing
        safe = cleaned
        if not _LIMIT_RE.search(lowered):
            safe = f"{cleaned}\nLIMIT {self.default_limit}"

        return ValidationResult(True, safe, "ok")

    # ------------------------------------------------------------------
    def _strip_comments(self, sql: str) -> str:
        sql = re.sub(r"--[^\n]*", " ", sql)       # line comments
        sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)  # block comments
        return sql

    def _disallowed_tables(self, sql: str) -> list[str]:
        bad = []
        for ref in _TABLE_RE.findall(sql):
            # ref looks like 'hsbc_marts.financial_kpis' or 'project.ds.table'
            parts = ref.split(".")
            dataset = parts[-2] if len(parts) >= 2 else parts[0]
            # subquery aliases / CTE names have no dot -> allow (resolved internally)
            if "." not in ref:
                continue
            if dataset not in self.allowed:
                bad.append(ref)
        return bad
