"""
run_triage.py
─────────────
Command-line entry point for Task 1.

Usage examples:

  # Triage a ticket from the dataset by ID:
  python run_triage.py --ticket-id TKT-10000

  # Triage a free-text ticket:
  python run_triage.py --subject "Pipeline stopped" --body "Our DataBridge pipeline ERR_CONNECTION_TIMEOUT"

  # Triage with streaming output:
  python run_triage.py --ticket-id TKT-10000 --stream

  # Pretty-print the full JSON result:
  python run_triage.py --ticket-id TKT-10000 --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure project root is in path when run directly
sys.path.insert(0, str(Path(__file__).parent))

from config import TICKETS_PATH
from models import TicketInput
from triage import triage_ticket, triage_ticket_stream


BANNER = """
╔══════════════════════════════════════════════════════════╗
║          🎫  Ticket Triage Agent  — Task 1               ║
╚══════════════════════════════════════════════════════════╝
"""


def load_ticket_from_dataset(ticket_id: str) -> TicketInput:
    tickets = json.loads(TICKETS_PATH.read_text(encoding="utf-8"))
    for t in tickets:
        if t.get("ticket_id") == ticket_id:
            return TicketInput(
                ticket_id=t["ticket_id"],
                subject=t.get("subject", "(no subject)"),
                body=t["body"],
                account_id=t.get("account_id"),
                plan_tier=t.get("plan_tier"),
            )
    raise ValueError(f"Ticket '{ticket_id}' not found in dataset.")


def print_result(result) -> None:
    """Pretty-print the structured triage output to stdout."""
    urgency_colours = {"P1": "\033[91m", "P2": "\033[93m", "P3": "\033[94m", "P4": "\033[92m"}
    reset = "\033[0m"
    colour = urgency_colours.get(result.urgency, "")

    print(f"\n{'─'*60}")
    print(f"  Ticket ID    : {result.ticket_id or '—'}")
    print(f"  Product Area : {result.product_area}")
    print(f"  Category     : {result.issue_category}")
    print(f"  Urgency      : {colour}{result.urgency}{reset}  ({result.urgency_reasoning})")
    print(f"  Responder    : {result.responder_team}")
    print(f"  Reason       : {result.responder_reasoning}")
    print(f"\n  KB Match     : {'✅' if result.kb_match.found else '❌'}  "
          f"{result.kb_match.doc_title or 'No match'} "
          f"[{result.kb_match.confidence}]")
    if result.kb_match.relevant_section:
        print(f"  Section      : {result.kb_match.relevant_section}")
    print(f"\n  Draft Response:\n")
    for line in result.draft_response.splitlines():
        print(f"    {line}")
    print(f"\n  Prompt version: {result.prompt_version}")
    print(f"{'─'*60}\n")


def main():
    parser = argparse.ArgumentParser(description="Ticket Triage Agent CLI")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--ticket-id", help="Ticket ID from the dataset (e.g. TKT-10000)")
    group.add_argument("--body", help="Raw ticket body text")
    parser.add_argument("--subject", default="(no subject)", help="Ticket subject (with --body)")
    parser.add_argument("--stream", action="store_true", help="Stream LLM output token by token")
    parser.add_argument("--json", dest="json_out", action="store_true",
                        help="Output raw JSON result")
    args = parser.parse_args()

    print(BANNER)

    # Load ticket
    if args.ticket_id:
        ticket = load_ticket_from_dataset(args.ticket_id)
        print(f"  Loaded ticket: {ticket.ticket_id}")
        print(f"  Subject: {ticket.subject}\n")
    else:
        ticket = TicketInput(subject=args.subject, body=args.body)
        print(f"  Subject: {ticket.subject}\n")

    if args.stream:
        print("  ── Streaming LLM output ──────────────────────────────\n")
        result_json = None
        for chunk in triage_ticket_stream(ticket):
            if chunk.startswith("data: [RESULT]"):
                result_json = chunk.replace("data: [RESULT] ", "").strip()
            elif chunk == "data: [DONE]\n":
                print("\n")
            else:
                token = chunk.replace("data: ", "")
                print(token, end="", flush=True)

        if result_json and args.json_out:
            print(result_json)
        elif result_json:
            import json as _json
            from models import TriageOutput
            result = TriageOutput.model_validate(_json.loads(result_json))
            print_result(result)
    else:
        result = triage_ticket(ticket)
        if args.json_out:
            print(json.dumps(result.model_dump(), indent=2))
        else:
            print_result(result)


if __name__ == "__main__":
    main()
