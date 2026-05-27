#!/usr/bin/env python3
"""Refusal rate test runner for qwiki-ask."""

import argparse
import csv
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from qwiki_common.claude import ClaudeClient
from qwiki_ask.safety import check_safety
from qwiki_ask.search_v2 import search_and_fetch
from qwiki_ask.synthesize_v2 import synthesize_answer
from qwiki_ask.formatter import format_output

CASE_COOLDOWN = 10
MAX_RETRIES = 3
RETRY_DELAY = 30

RESPONSE_FIELDS = ["id", "category", "question", "expected_outcome", "status",
                    "refusal_reason", "response", "search_query",
                    "articles_found", "elapsed_seconds"]


def run_ask(question, claude_client):
    classification = check_safety(question, claude_client)
    if classification == "UNSAFE":
        return {"status": "refused", "refusal_reason": "safety_gate: UNSAFE",
                "response": "", "search_query": "", "articles_found": 0}
    if classification == "GIBBERISH":
        return {"status": "gibberish", "refusal_reason": "safety_gate: GIBBERISH",
                "response": "", "search_query": "", "articles_found": 0}

    articles, search_query = search_and_fetch(question, claude_client)
    if not articles:
        return {"status": "no_results", "refusal_reason": f"search: 0 articles for '{search_query}'",
                "response": "", "search_query": search_query, "articles_found": 0}

    result = synthesize_answer(question, articles, claude_client)
    if not result.get("could_answer", True):
        return {"status": "no_answer",
                "refusal_reason": "synthesis: could_not_answer",
                "response": "", "search_query": search_query,
                "articles_found": len(articles)}

    output = format_output(articles, result)
    return {"status": "ok", "refusal_reason": "",
            "response": output, "search_query": search_query,
            "articles_found": len(articles)}


def append_csv(path, fieldnames, row):
    write_header = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def main():
    parser = argparse.ArgumentParser(description="Run qwiki-ask refusal rate tests")
    parser.add_argument("--model", required=True, help="Claude model to use")
    parser.add_argument("--test-cases", default="testing/refusal_test_cases.csv")
    parser.add_argument("--version", default="v2", help="Tool version label")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    client = ClaudeClient(api_key, args.model)

    with open(args.test_cases, newline="", encoding="utf-8") as f:
        cases = list(csv.DictReader(f))

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = f"testing/runs/refusal_{args.version}_{timestamp}"
    os.makedirs(run_dir, exist_ok=True)
    responses_path = os.path.join(run_dir, "responses.csv")

    total = len(cases)
    print(f"Running {total} refusal test cases (version={args.version})", file=sys.stderr)
    print(f"Output: {run_dir}/", file=sys.stderr)
    print(file=sys.stderr)

    for i, case in enumerate(cases, 1):
        case_id = case["id"]
        question = case["question"]
        expected = case["expected_outcome"]

        print(f"[{i}/{total}] {case_id}: {question[:60]}...", file=sys.stderr)

        t0 = time.time()
        result = None
        for attempt in range(MAX_RETRIES):
            try:
                result = run_ask(question, client)
                break
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    print(f"  Retry {attempt+1} (error: {e})", file=sys.stderr)
                    time.sleep(RETRY_DELAY)
                else:
                    result = {"status": "error", "refusal_reason": f"pipeline_error: {e}",
                              "response": "", "search_query": "", "articles_found": 0}

        elapsed = round(time.time() - t0, 1)

        was_answered = result["status"] == "ok"
        should_answer = expected == "answered"
        match = (was_answered == should_answer)
        verdict = "✓" if match else "✗"

        append_csv(responses_path, RESPONSE_FIELDS, {
            "id": case_id,
            "category": case["category"],
            "question": question,
            "expected_outcome": expected,
            "status": result["status"],
            "refusal_reason": result["refusal_reason"],
            "response": result["response"][:500] if result["response"] else "",
            "search_query": result["search_query"],
            "articles_found": result["articles_found"],
            "elapsed_seconds": elapsed,
        })

        print(f"  {verdict} status={result['status']} expected={expected} "
              f"[{elapsed}s]", file=sys.stderr)
        if result["refusal_reason"]:
            print(f"    reason: {result['refusal_reason']}", file=sys.stderr)

        if i < total:
            time.sleep(CASE_COOLDOWN)

    print(f"\nDone. Results in {run_dir}/", file=sys.stderr)

    # Print summary
    with open(responses_path, newline="", encoding="utf-8") as f:
        results = list(csv.DictReader(f))

    answered = sum(1 for r in results if r["status"] == "ok")
    refused = len(results) - answered
    should_answer = [r for r in results if r["expected_outcome"] == "answered"]
    should_refuse = [r for r in results if r["expected_outcome"] == "refused"]

    incorrect_refusals = sum(1 for r in should_answer if r["status"] != "ok")
    incorrect_answers = sum(1 for r in should_refuse if r["status"] == "ok")

    print(f"\n{'═' * 50}", file=sys.stderr)
    print(f"Refusal Rate Summary", file=sys.stderr)
    print(f"{'═' * 50}", file=sys.stderr)
    print(f"Total: {len(results)} | Answered: {answered} | Refused: {refused}", file=sys.stderr)
    print(f"Overall refusal rate: {refused/len(results)*100:.1f}%", file=sys.stderr)
    print(f"Incorrect refusals (should answer, didn't): {incorrect_refusals}/{len(should_answer)}", file=sys.stderr)
    print(f"Incorrect answers (should refuse, didn't): {incorrect_answers}/{len(should_refuse)}", file=sys.stderr)
    print(f"{'═' * 50}", file=sys.stderr)


if __name__ == "__main__":
    main()
