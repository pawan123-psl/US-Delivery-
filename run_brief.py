"""
run_brief.py  — Task 2
──────────────────────
CLI entry point for the TAM Account Health Summariser.

Usage:
  python run_brief.py --account-id ACC-3336
  python run_brief.py --account-id ACC-3336 --json

Flags:
  --account-id   (required) The account ID to generate a brief for.
  --json         Print raw JSON output instead of the pretty-printed brief.
"""

from __future__ import annotations

# Task 2 — standard library imports
import argparse
import json
import sys


def _parse_args() -> argparse.Namespace:
    """Task 2 — Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        prog="run_brief",
        description="Task 2: Generate a TAM Account Health Brief for the given account.",
    )
    parser.add_argument(
        "--account-id",
        required=True,
        metavar="ACCOUNT_ID",
        help="Account ID to analyse, e.g. ACC-3336",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="raw_json",
        help="Output raw JSON instead of the formatted brief",
    )
    return parser.parse_args()


def _print_brief(brief) -> None:
    """
    Task 2 — Pretty-print the 3-section AccountBrief to the terminal.
    Sections: Executive Summary, Risks & Flags, Talking Points.
    """
    sep = "─" * 70

    # ── Header ────────────────────────────────────────────────────────────────
    print(f"\n{'═' * 70}")
    print(f"  TAM ACCOUNT HEALTH BRIEF  —  Task 2")
    print(f"{'═' * 70}")
    print(f"  Account   : {brief.account_id}  |  {brief.company}")
    print(f"  TAM       : {brief.tam}")
    print(f"  Plan      : {brief.plan_tier}  |  Health: {brief.health_status}")
    if brief.arr_usd:
        print(f"  ARR       : ${brief.arr_usd:,.0f}")
    print(f"  Tickets   : {brief.tickets_analysed} analysed (last 90 days)")
    print(f"  Generated : {brief.generated_at}")
    print(f"{'═' * 70}\n")

    # ── Section 1: Executive Summary ─────────────────────────────────────────
    print("📋  EXECUTIVE SUMMARY")
    print(sep)
    print(brief.executive_summary)
    print()

    # ── Section 2: Risks & Flagged Issues ────────────────────────────────────
    print("⚠️   OPEN RISKS & FLAGGED ISSUES")
    print(sep)
    if not brief.risks:
        print("  (No churn risks or escalation signals identified.)")
    else:
        for i, risk in enumerate(brief.risks, start=1):
            ticket_ref = f"  [{risk.ticket_id}]" if risk.ticket_id else ""
            print(f"  {i}.{ticket_ref} {risk.description}")
            print(f"     Quote: \"{risk.ticket_quote}\"")
            print()
    print()

    # ── Section 3: Talking Points ─────────────────────────────────────────────
    print("💬  RECOMMENDED TALKING POINTS")
    print(sep)
    if not brief.talking_points:
        print("  (No talking points generated.)")
    else:
        for i, point in enumerate(brief.talking_points, start=1):
            print(f"  {i}. {point}")
    print(f"\n{'═' * 70}\n")


def main() -> None:
    """Task 2 — Main CLI entry point."""
    args = _parse_args()

    # Task 2 — import here to avoid import errors surfacing before argparse runs
    from account_brief import generate_brief

    print(f"Generating TAM brief for account: {args.account_id} …", file=sys.stderr)

    try:
        brief = generate_brief(args.account_id)
    except ValueError as exc:
        print(f"\n❌  Error: {exc}", file=sys.stderr)
        sys.exit(1)
    except EnvironmentError as exc:
        print(f"\n❌  Configuration error: {exc}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError as exc:
        print(f"\n❌  Data file error: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"\n❌  Unexpected error: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.raw_json:
        # Task 2: --json flag — output raw JSON for piping / machine consumption
        print(brief.model_dump_json(indent=2))
    else:
        # Task 2: default — pretty-printed human-readable brief
        _print_brief(brief)


if __name__ == "__main__":
    main()
