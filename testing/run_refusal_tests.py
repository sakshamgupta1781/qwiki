#!/usr/bin/env python3
"""Refusal rate test runner for qwiki-ask with granular diagnostics."""

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from qwiki_common.claude import ClaudeClient
from qwiki_ask.safety import check_safety
from qwiki_ask.search_v2 import search_and_fetch, optimize_query, check_ambiguity
from qwiki_ask.synthesize_v2 import synthesize_answer
from qwiki_ask.formatter import format_output

CASE_COOLDOWN = 10
MAX_RETRIES = 3
RETRY_DELAY = 30

RESPONSE_FIELDS = ["id", "category", "question", "expected_outcome", "status",
                    "refusal_reason", "article_titles", "search_query",
                    "articles_found", "elapsed_seconds"]


def run_ask_with_diagnostics(question, claude_client):
    diag = {
        "question": question,
        "safety_classification": None,
        "search_query_raw": None,
        "articles": [],
        "ambiguity_detected": False,
        "ambiguity_meanings": [],
        "synthesis_raw_response": None,
        "synthesis_could_answer": None,
        "synthesis_answer": None,
        "synthesis_explanation": None,
        "final_status": None,
        "final_response": None,
    }

    classification = check_safety(question, claude_client)
    diag["safety_classification"] = classification

    if classification == "UNSAFE":
        diag["final_status"] = "refused"
        return {
            "status": "refused",
            "refusal_reason": "safety_gate: UNSAFE",
            "articles": [], "search_query": "", "article_titles": "",
        }, diag

    if classification == "GIBBERISH":
        diag["final_status"] = "gibberish"
        return {
            "status": "gibberish",
            "refusal_reason": "safety_gate: GIBBERISH",
            "articles": [], "search_query": "", "article_titles": "",
        }, diag

    search_query = optimize_query(question, claude_client)
    diag["search_query_raw"] = search_query

    from qwiki_common.mediawiki import MediaWikiClient
    wiki = MediaWikiClient()
    search_results = wiki.search(search_query, limit=5)

    if not search_results:
        simplified = question.split()[:3]
        search_results = wiki.search(" ".join(simplified), limit=5)

    fetched_titles = set()
    articles = []
    for result in search_results:
        article = wiki.get_extract(result["title"])
        if article["extract"]:
            articles.append(article)
            fetched_titles.add(result["title"])

    is_ambiguous, meanings = check_ambiguity(question, claude_client)
    diag["ambiguity_detected"] = is_ambiguous
    diag["ambiguity_meanings"] = meanings

    if is_ambiguous and meanings:
        for meaning_query in meanings:
            additional = wiki.search(meaning_query, limit=2)
            for result in additional:
                if result["title"] not in fetched_titles:
                    article = wiki.get_extract(result["title"])
                    if article["extract"]:
                        articles.append(article)
                        fetched_titles.add(result["title"])

    diag["articles"] = [
        {"title": a["title"], "url": a["url"],
         "extract_length": len(a["extract"]), "extract": a["extract"]}
        for a in articles
    ]

    article_titles = "|".join(a["title"] for a in articles)

    if not articles:
        diag["final_status"] = "no_results"
        return {
            "status": "no_results",
            "refusal_reason": f"search: 0 articles for '{search_query}'",
            "articles": [], "search_query": search_query,
            "article_titles": "",
        }, diag

    result = synthesize_answer(question, articles, claude_client)
    diag["synthesis_raw_response"] = json.dumps(result, ensure_ascii=False)
    diag["synthesis_could_answer"] = result.get("could_answer", True)
    diag["synthesis_answer"] = result.get("answer", "")

    if not result.get("could_answer", True):
        diag["synthesis_explanation"] = result.get("answer", "no explanation provided")
        diag["final_status"] = "no_answer"
        return {
            "status": "no_answer",
            "refusal_reason": f"synthesis: {result.get('answer', 'could_not_answer')[:200]}",
            "articles": articles, "search_query": search_query,
            "article_titles": article_titles,
        }, diag

    output = format_output(articles, result)
    diag["final_status"] = "ok"
    diag["final_response"] = output
    return {
        "status": "ok",
        "refusal_reason": "",
        "articles": articles, "search_query": search_query,
        "article_titles": article_titles,
    }, diag


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
    diag_dir = os.path.join(run_dir, "diagnostics")
    os.makedirs(diag_dir, exist_ok=True)
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
        diag = None
        for attempt in range(MAX_RETRIES):
            try:
                result, diag = run_ask_with_diagnostics(question, client)
                break
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    print(f"  Retry {attempt+1} (error: {e})", file=sys.stderr)
                    time.sleep(RETRY_DELAY)
                else:
                    result = {"status": "error",
                              "refusal_reason": f"pipeline_error: {e}",
                              "articles": [], "search_query": "",
                              "article_titles": ""}
                    diag = {"question": question, "final_status": "error",
                            "error": str(e)}

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
            "article_titles": result.get("article_titles", ""),
            "search_query": result["search_query"],
            "articles_found": len(result.get("articles", [])),
            "elapsed_seconds": elapsed,
        })

        with open(os.path.join(diag_dir, f"{case_id}.json"), "w", encoding="utf-8") as f:
            json.dump(diag, f, indent=2, ensure_ascii=False)

        print(f"  {verdict} status={result['status']} expected={expected} "
              f"articles={len(result.get('articles', []))} [{elapsed}s]", file=sys.stderr)
        if result["refusal_reason"]:
            print(f"    reason: {result['refusal_reason'][:120]}", file=sys.stderr)

        if i < total:
            time.sleep(CASE_COOLDOWN)

    print(f"\nDone. Results in {run_dir}/", file=sys.stderr)

    with open(responses_path, newline="", encoding="utf-8") as f:
        results = list(csv.DictReader(f))

    answered = sum(1 for r in results if r["status"] == "ok")
    refused = len(results) - answered
    should_answer = [r for r in results if r["expected_outcome"] == "answered"]
    should_refuse = [r for r in results if r["expected_outcome"] == "refused"]

    incorrect_refusals = [r for r in should_answer if r["status"] != "ok"]
    incorrect_answers = [r for r in should_refuse if r["status"] == "ok"]

    print(f"\n{'═' * 50}", file=sys.stderr)
    print(f"Refusal Rate Summary", file=sys.stderr)
    print(f"{'═' * 50}", file=sys.stderr)
    print(f"Total: {len(results)} | Answered: {answered} | Refused: {refused}", file=sys.stderr)
    print(f"Overall refusal rate: {refused/len(results)*100:.1f}%", file=sys.stderr)
    print(f"Incorrect refusals: {len(incorrect_refusals)}/{len(should_answer)}", file=sys.stderr)
    print(f"Incorrect answers: {len(incorrect_answers)}/{len(should_refuse)}", file=sys.stderr)

    if incorrect_refusals:
        print(f"\nIncorrect refusals (should have answered):", file=sys.stderr)
        for r in incorrect_refusals:
            print(f"  {r['id']}: {r['question'][:50]}... → {r['status']}", file=sys.stderr)
            print(f"    reason: {r['refusal_reason'][:100]}", file=sys.stderr)

    if incorrect_answers:
        print(f"\nIncorrect answers (should have refused):", file=sys.stderr)
        for r in incorrect_answers:
            print(f"  {r['id']}: {r['question'][:50]}...", file=sys.stderr)

    print(f"\nDiagnostics: {diag_dir}/", file=sys.stderr)
    print(f"{'═' * 50}", file=sys.stderr)


if __name__ == "__main__":
    main()
