import sys

from .safety import check_safety
from .search_v3 import search_and_fetch, deep_search
from .synthesize_v4 import synthesize_answer
from .formatter import (
    format_output, format_refusal, format_gibberish,
    format_no_results, format_no_answer,
)
from .status import StatusLine


def run(question, claude_client, debug=False, run_eval=True, enable_deep_search=True):
    status = StatusLine()

    status.update("Checking safety — classifying question...")
    classification = check_safety(question, claude_client)

    if classification == "UNSAFE":
        status.complete("Blocked — question classified as unsafe")
        print(format_refusal())
        return

    if classification == "GIBBERISH":
        status.complete("Blocked — input classified as gibberish")
        print(format_gibberish())
        return

    status.complete("Safe — question is appropriate to answer")

    status.update("Optimizing search query — converting question to Wikipedia search terms...")
    try:
        articles, search_query = search_and_fetch(question, claude_client)
    except Exception as e:
        status.complete(f"Wikipedia search failed: {e}")
        return

    status.update(f"Searching Wikipedia for \"{search_query}\"...")

    if not articles:
        status.complete("No Wikipedia articles found for this query")
        print(format_no_results(question))
        return

    titles = ", ".join(a["title"] for a in articles[:3])
    suffix = f" + {len(articles) - 3} more" if len(articles) > 3 else ""
    status.complete(f"Found {len(articles)} Wikipedia article{'s' if len(articles) != 1 else ''} — {titles}{suffix}")

    if debug:
        for i, a in enumerate(articles):
            print(f"  \033[90m[{i+1}] {a['title']} ({len(a['extract'])} chars)\033[0m",
                  file=sys.stderr)

    status.update("Synthesizing answer — generating response using only fetched article text...")
    result = synthesize_answer(question, articles, claude_client)

    if not result.get("could_answer", True) and enable_deep_search:
        status.complete("First attempt insufficient — articles didn't fully cover the question")
        status.update("Deep search — generating refined query to find better articles...")

        try:
            expanded_articles, refined_query = deep_search(
                question, search_query, articles, claude_client)
        except Exception as e:
            status.complete(f"Deep search failed: {e}")
            expanded_articles = articles

        if len(expanded_articles) > len(articles):
            status.complete(f"Deep search found {len(expanded_articles) - len(articles)} new article(s)")
            if debug:
                new_titles = [a['title'] for a in expanded_articles if a not in articles]
                for t in new_titles:
                    print(f"  \033[90m[new] {t}\033[0m", file=sys.stderr)

            status.update("Re-synthesizing — generating response with expanded article set...")
            result = synthesize_answer(question, expanded_articles, claude_client)
            articles = expanded_articles
        else:
            status.complete("Deep search found no new articles")

    if not result.get("could_answer", True):
        status.complete("Could not determine answer")
        print(format_no_answer())
        return

    status.complete("Answer ready — synthesis complete")
    output = format_output(articles, result)
    print(output)

    if not run_eval:
        return

    _run_eval_judges(question, output, claude_client, status)


def _run_eval_judges(question, response_text, claude_client, status):
    try:
        from qwiki_eval.runner import run_eval as eval_run, ALL_JUDGES
        from qwiki_eval.formatter import format_table
    except ImportError:
        status.complete("Eval skipped — qwiki_eval not available")
        return

    total = len(ALL_JUDGES)
    status.update(f"Evaluating response — running {total} quality judges...")

    results = []
    from qwiki_eval.judges.base import JudgeResult
    for i, judge in enumerate(ALL_JUDGES):
        status.update(f"Evaluating response ({i+1}/{total}: {judge.name})...")
        try:
            result = judge.evaluate(question, response_text, claude_client)
        except Exception as e:
            result = JudgeResult(
                judge_name=judge.name,
                passed=False,
                reasoning=f"ERROR: {e}",
            )
        results.append(result)

    passed = sum(1 for r in results if r.passed)
    composite = (passed / len(results) * 100) if results else 0.0

    status.complete(f"Evaluation complete — {passed}/{total} judges passed ({composite:.0f}%)")
    print(format_table(results, composite))
