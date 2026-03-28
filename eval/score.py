"""eval/score.py — Standalone LLM evaluator for benchmark_results.xlsx.

Reads agent responses that were collected by eval/script.py and fills in
llm_score (1-5) and llm_rationale for any row that has not been scored yet.

Usage (from project root):
    python eval/score.py                     # score only unscored rows
    python eval/score.py --force             # re-score every row
    python eval/score.py --run-id abc12345   # only score a specific run
    python eval/score.py --sheet SmartSales  # only score one agent sheet
"""

import argparse
import asyncio
import json
import os

import openpyxl
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────

EXCEL_FILE = "benchmark_results.xlsx"

AGENT_SHEETS = ["Graph", "Salesforce", "SmartSales", "Orchestrator"]

# Column positions are read dynamically from the header row — no hardcoding needed.

# ── Evaluator prompt ──────────────────────────────────────────────────────────

_SYSTEM = (
    "You are a benchmark evaluator for an AI agent system. "
    "Your job is to score how well an agent's actual response matches an expected answer."
)

_USER_TMPL = """\
Question asked to the agent:
{question}

Expected answer (description of what a correct response should contain):
{expected_answer}

Actual agent response:
{actual_response}

Rate the actual response on a scale of 1 to 5:
  1 – Completely wrong, irrelevant, or no meaningful response
  2 – Partially correct but with major gaps or errors
  3 – Mostly correct with some notable gaps or inaccuracies
  4 – Correct with only minor gaps or formatting differences
  5 – Fully correct and complete

Respond ONLY with valid JSON in this exact format:
{{"score": <integer 1-5>, "rationale": "<one or two sentence justification of the score>", "comments": "<optional broader observations: what was done well, what was missing, or how the response could be improved>"}}
"""


async def evaluate(
    client: AsyncAzureOpenAI,
    deployment: str,
    question: str,
    expected_answer: str,
    actual_response: str,
    success: bool,
) -> tuple[int | None, str, str]:
    """Return (score 1-5, rationale, comments)."""
    if not success or not (actual_response or "").strip():
        return 1, "Agent call failed or returned an empty response.", ""

    try:
        resp = await client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user",   "content": _USER_TMPL.format(
                    question=question,
                    expected_answer=expected_answer,
                    actual_response=actual_response[:4000],
                )},
            ],
            temperature=0,
            max_tokens=300,
        )
        raw  = resp.choices[0].message.content or ""
        data = json.loads(raw)
        return int(data["score"]), str(data.get("rationale", "")), str(data.get("comments", ""))
    except Exception as exc:
        return None, f"Evaluator error: {exc}", ""


# ── Sheet processing ──────────────────────────────────────────────────────────

def _build_col_map(ws) -> dict[str, int]:
    """Read column positions from the header row (row 1). Returns {name: 0-based index}."""
    return {
        cell.value: cell.column - 1
        for cell in ws[1]
        if cell.value is not None
    }


def _cell(row, col_name: str, col_map: dict) -> object:
    """Read a cell value by column name using the dynamic column map."""
    idx = col_map.get(col_name)
    return row[idx].value if idx is not None and idx < len(row) else None


def _is_scored(row, col_map: dict) -> bool:
    score = _cell(row, "llm_score", col_map)
    return score is not None and str(score).strip() != ""


async def score_sheet(
    ws,
    client: AsyncAzureOpenAI,
    deployment: str,
    force: bool,
    run_id_filter: str | None,
) -> tuple[int, int]:
    """Score all eligible rows in a worksheet. Returns (scored, skipped)."""
    col_map = _build_col_map(ws)
    scored  = 0
    skipped = 0

    # Collect rows to score (skip header row 1)
    rows_to_score = []
    for row in ws.iter_rows(min_row=2):
        run_id = _cell(row, "run_id", col_map)

        if run_id_filter and str(run_id) != run_id_filter:
            skipped += 1
            continue

        if not force and _is_scored(row, col_map):
            skipped += 1
            continue

        rows_to_score.append(row)

    total = len(rows_to_score)
    for i, row in enumerate(rows_to_score, 1):
        question        = str(_cell(row, "prompt",          col_map) or "")
        expected_answer = str(_cell(row, "expected_answer", col_map) or "")
        actual_response = str(_cell(row, "actual_response", col_map) or "")
        success_val     = _cell(row, "success", col_map)
        success         = bool(success_val) if success_val is not None else False
        run_id          = _cell(row, "run_id",    col_map)
        difficulty      = _cell(row, "difficulty", col_map)

        print(f"  [{i:02d}/{total:02d}] run={run_id}  [{difficulty}]  {question[:60]!r}")

        score, rationale, comments = await evaluate(
            client, deployment,
            question, expected_answer, actual_response, success,
        )

        # Write scores back — look up column numbers from the header map.
        # If llm_comments column doesn't exist yet (old file), append it to the header first.
        excel_row = row[0].row
        for col_name, value in [
            ("llm_score",     score),
            ("llm_rationale", rationale),
            ("llm_comments",  comments),
        ]:
            if col_name not in col_map:
                # Column missing from this sheet (old file) — add it after the last column
                new_col = ws.max_column + 1
                ws.cell(row=1, column=new_col).value = col_name
                col_map[col_name] = new_col - 1  # update map (0-based)
            ws.cell(row=excel_row, column=col_map[col_name] + 1).value = value

        label = f"{score}/5" if score is not None else "ERR"
        print(f"           → {label}  {rationale[:80]}")
        scored += 1

    return scored, skipped


# ── Entry point ───────────────────────────────────────────────────────────────

async def main(args: argparse.Namespace) -> None:
    if not os.path.exists(EXCEL_FILE):
        print(f"ERROR: {EXCEL_FILE} not found. Run eval/script.py first.")
        return

    deployment = os.environ["deployment"]
    endpoint   = os.environ["AZURE_OPENAI_ENDPOINT"]
    api_key    = os.environ["AZURE_OPENAI_API_KEY"]

    client = AsyncAzureOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version="2024-12-01-preview",
    )

    wb     = openpyxl.load_workbook(EXCEL_FILE)
    sheets = [args.sheet] if args.sheet else AGENT_SHEETS

    total_scored  = 0
    total_skipped = 0

    for sheet_name in sheets:
        if sheet_name not in wb.sheetnames:
            print(f"Sheet '{sheet_name}' not found — skipping.")
            continue

        ws = wb[sheet_name]
        col_map = _build_col_map(ws)
        unscored = sum(
            1 for row in ws.iter_rows(min_row=2)
            if not _is_scored(row, col_map)
            and (not args.run_id or str(_cell(row, "run_id", col_map)) == args.run_id)
        )

        if not args.force and unscored == 0:
            print(f"\n[{sheet_name}] — all rows already scored, skipping. (use --force to re-score)")
            continue

        mode = "re-scoring all" if args.force else f"{unscored} unscored"
        print(f"\n{'─' * 60}")
        print(f"  Sheet: {sheet_name}  ({mode} rows)")
        print(f"{'─' * 60}")

        scored, skipped = await score_sheet(
            ws, client, deployment,
            force=args.force,
            run_id_filter=args.run_id,
        )
        total_scored  += scored
        total_skipped += skipped

    # Save
    try:
        wb.save(EXCEL_FILE)
    except PermissionError:
        from datetime import datetime
        fallback = EXCEL_FILE.replace(".xlsx", f"_scored_{datetime.now():%Y%m%d_%H%M%S}.xlsx")
        wb.save(fallback)
        print(f"\nWARNING: {EXCEL_FILE} is locked. Saved to {fallback}")
        return

    print(f"\nDone — scored {total_scored} rows, skipped {total_skipped}.")
    print(f"Results saved → {EXCEL_FILE}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Score benchmark_results.xlsx with LLM evaluator.")
    parser.add_argument(
        "--force", action="store_true",
        help="Re-score rows that already have a score.",
    )
    parser.add_argument(
        "--run-id", metavar="ID",
        help="Only score rows matching this run_id (e.g. abc12345).",
    )
    parser.add_argument(
        "--sheet", choices=["Graph", "Salesforce", "SmartSales", "Orchestrator"],
        help="Only score rows in this agent sheet.",
    )
    args = parser.parse_args()
    asyncio.run(main(args))
