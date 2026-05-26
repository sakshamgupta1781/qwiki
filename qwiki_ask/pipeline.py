import sys
import time

from .safety import check_safety
from .search import search_and_fetch
from .synthesize import synthesize_answer
from .formatter import (
    format_output, format_refusal, format_gibberish,
    format_no_results, format_no_answer,
)


def run(question, claude_client, debug=False):
    if debug:
        _debug_header(0, "SAFETY GATE")

    t0 = time.time()
    classification, search_query = check_safety(question, claude_client)

    if debug:
        _debug_result("Classification", classification)
        _debug_result("Search query", search_query)
        _debug_result("Elapsed", f"{time.time() - t0:.1f}s")

    if classification == "UNSAFE":
        print(format_refusal())
        return

    if classification == "GIBBERISH":
        print(format_gibberish())
        return

    if debug:
        _debug_header(1, "WIKIPEDIA SEARCH + FETCH")

    t0 = time.time()
    articles = search_and_fetch(search_query, question)

    if debug:
        _debug_result("Articles found", len(articles))
        for i, a in enumerate(articles):
            _debug_result(f"  [{i+1}] {a['title']}", f"{len(a['extract'])} chars")
        _debug_result("Elapsed", f"{time.time() - t0:.1f}s")

    if not articles:
        print(format_no_results(question))
        return

    if debug:
        _debug_header(2, "SYNTHESIS")

    t0 = time.time()
    result = synthesize_answer(question, articles, claude_client)

    if debug:
        _debug_result("Could answer", result.get("could_answer", True))
        _debug_result("Answer length", f"{len(result.get('answer', ''))} chars")
        _debug_result("Sources", ", ".join(result.get("sources", [])))
        _debug_result("Elapsed", f"{time.time() - t0:.1f}s")

    if not result.get("could_answer", True):
        print(format_no_answer())
        return

    if debug:
        _debug_header(3, "OUTPUT")

    print(format_output(articles, result))


def _debug_header(step_num, step_name):
    print(f"\n\033[36m{'─' * 60}\033[0m", file=sys.stderr)
    print(f"\033[36m  Step {step_num}: {step_name}\033[0m", file=sys.stderr)
    print(f"\033[36m{'─' * 60}\033[0m", file=sys.stderr)


def _debug_result(label, value):
    print(f"\033[35m  ✓ {label}: {value}\033[0m", file=sys.stderr)
