#!/usr/bin/env python3
"""End-to-end test runner for qwiki-ask with integrated eval."""

import argparse
import csv
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from qwiki_common.claude import ClaudeClient
from qwiki_ask.safety import check_safety
from qwiki_ask.search import search_and_fetch
from qwiki_ask.synthesize import synthesize_answer
from qwiki_ask.formatter import format_output
from qwiki_eval.runner import ALL_JUDGES
from qwiki_eval.judges.base import JudgeResult

TRUSTED_JUDGES = {"directness", "accuracy", "objectivity", "safety",
                  "false_premise", "completeness", "relevance"}
CASE_COOLDOWN = 60
ASK_MAX_RETRIES = 3
ASK_RETRY_DELAY = 60

RESPONSE_FIELDS = ["id", "category", "question", "response", "search_query",
                    "articles_found", "elapsed_seconds", "status"]
EVAL_FIELDS = ["id", "category", "question",
               "judge_directness", "judge_accuracy", "judge_source_quality",
               "judge_conciseness", "judge_objectivity", "judge_safety",
               "judge_false_premise", "judge_completeness", "judge_relevance",
               "judge_groundedness",
               "composite_score", "trusted_score"]


def run_ask_pipeline(question, claude_client):
    classification = check_safety(question, claude_client)
    if classification == "UNSAFE":
        return {"response": "[REFUSED — unsafe query]", "search_query": "",
                "articles_found": 0, "status": "refused"}
    if classification == "GIBBERISH":
        return {"response": "[REFUSED — gibberish input]", "search_query": "",
                "articles_found": 0, "status": "gibberish"}

    articles, search_query = search_and_fetch(question, claude_client)
    if not articles:
        return {"response": "[NO RESULTS]", "search_query": search_query,
                "articles_found": 0, "status": "no_results"}

    result = synthesize_answer(question, articles, claude_client)
    if not result.get("could_answer", True):
        return {"response": "[COULD NOT ANSWER]", "search_query": search_query,
                "articles_found": len(articles), "status": "no_answer"}

    output = format_output(articles, result)
    return {"response": output, "search_query": search_query,
            "articles_found": len(articles), "status": "ok"}


def run_eval_judges(question, response, claude_client):
    results = {}
    for judge in ALL_JUDGES:
        try:
            r = judge.evaluate(question, response, claude_client)
            results[judge.name] = "PASS" if r.passed else "FAIL"
        except Exception as e:
            results[judge.name] = f"ERROR"
    return results


def compute_scores(judge_results):
    all_judges = [j.name for j in ALL_JUDGES]
    non_error = {k: v for k, v in judge_results.items() if v != "ERROR"}
    trusted_non_error = {k: v for k, v in non_error.items() if k in TRUSTED_JUDGES}

    total = len(non_error)
    passed = sum(1 for v in non_error.values() if v == "PASS")
    composite = (passed / total * 100) if total > 0 else 0.0

    trusted_total = len(trusted_non_error)
    trusted_passed = sum(1 for v in trusted_non_error.values() if v == "PASS")
    trusted_score = (trusted_passed / trusted_total * 100) if trusted_total > 0 else 0.0

    return round(composite, 1), round(trusted_score, 1)


def append_csv(path, fieldnames, row):
    write_header = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def main():
    parser = argparse.ArgumentParser(description="Run qwiki-ask test suite with evals")
    parser.add_argument("--model", required=True, help="Claude model to use")
    parser.add_argument("--test-cases", default="testing/test_cases.csv",
                        help="Path to test cases CSV")
    parser.add_argument("--version", default="v1", help="Prompt version label")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    client = ClaudeClient(api_key, args.model)

    with open(args.test_cases, newline="", encoding="utf-8") as f:
        cases = list(csv.DictReader(f))

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = f"testing/runs/{args.version}_{timestamp}"
    os.makedirs(run_dir, exist_ok=True)

    responses_path = os.path.join(run_dir, "responses.csv")
    eval_path = os.path.join(run_dir, "eval_results.csv")

    total = len(cases)
    print(f"Running {total} test cases (version={args.version}, model={args.model})",
          file=sys.stderr)
    print(f"Output: {run_dir}/", file=sys.stderr)
    print(file=sys.stderr)

    for i, case in enumerate(cases, 1):
        case_id = case["id"]
        question = case["question"]
        category = case["category"]

        print(f"[{i}/{total}] {case_id}: {question[:60]}...", file=sys.stderr)

        t0 = time.time()
        ask_result = None
        for attempt in range(ASK_MAX_RETRIES):
            try:
                ask_result = run_ask_pipeline(question, client)
                break
            except Exception as e:
                if attempt < ASK_MAX_RETRIES - 1:
                    print(f"  Retry {attempt+1}/{ASK_MAX_RETRIES} (ask failed: {e})",
                          file=sys.stderr)
                    time.sleep(ASK_RETRY_DELAY)
                else:
                    ask_result = {"response": f"[ERROR: {e}]", "search_query": "",
                                  "articles_found": 0, "status": "error"}

        elapsed = round(time.time() - t0, 1)

        append_csv(responses_path, RESPONSE_FIELDS, {
            "id": case_id,
            "category": category,
            "question": question,
            "response": ask_result["response"],
            "search_query": ask_result["search_query"],
            "articles_found": ask_result["articles_found"],
            "elapsed_seconds": elapsed,
            "status": ask_result["status"],
        })

        if ask_result["status"] in ("refused", "gibberish"):
            judge_results = {}
            for j in ALL_JUDGES:
                if j.name == "safety":
                    judge_results[j.name] = "PASS"
                else:
                    judge_results[j.name] = "N/A"
            composite, trusted = 100.0, 100.0
        elif ask_result["status"] in ("error", "no_results", "no_answer"):
            judge_results = {j.name: "SKIP" for j in ALL_JUDGES}
            composite, trusted = 0.0, 0.0
        else:
            print(f"  Running eval judges...", file=sys.stderr)
            judge_results = run_eval_judges(question, ask_result["response"], client)
            composite, trusted = compute_scores(judge_results)

        eval_row = {
            "id": case_id,
            "category": category,
            "question": question,
            "composite_score": composite,
            "trusted_score": trusted,
        }
        for j in ALL_JUDGES:
            eval_row[f"judge_{j.name}"] = judge_results.get(j.name, "N/A")

        append_csv(eval_path, EVAL_FIELDS, eval_row)

        status = ask_result["status"]
        errors = sum(1 for v in judge_results.values() if v == "ERROR")
        print(f"  → {status} | composite={composite}% trusted={trusted}% "
              f"({errors} eval errors) [{elapsed}s]", file=sys.stderr)

        if i < total:
            time.sleep(CASE_COOLDOWN)

    print(f"\nDone. Results in {run_dir}/", file=sys.stderr)


if __name__ == "__main__":
    main()
