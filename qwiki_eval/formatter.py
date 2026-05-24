import json
import shutil


def format_table(results, composite):
    term_width = shutil.get_terminal_size((80, 24)).columns
    max_reason_width = max(term_width - 38, 20)

    judge_col = 19
    result_col = 6

    def truncate(text, width):
        if len(text) <= width:
            return text
        return text[: width - 3] + "..."

    header = (
        f"┌─{'Judge':─<{judge_col}}─┬─"
        f"{'Result':─<{result_col}}─┬─"
        f"{'':─<{max_reason_width}}─┐"
    )
    sep = (
        f"├─{'':─<{judge_col}}─┼─"
        f"{'':─<{result_col}}─┼─"
        f"{'':─<{max_reason_width}}─┤"
    )
    footer_sep = (
        f"├─{'':─<{judge_col}}─┼─"
        f"{'':─<{result_col}}─┼─"
        f"{'':─<{max_reason_width}}─┤"
    )
    bottom = (
        f"└─{'':─<{judge_col}}─┴─"
        f"{'':─<{result_col}}─┴─"
        f"{'':─<{max_reason_width}}─┘"
    )

    lines = [header]
    lines.append(
        f"│ {'Judge':<{judge_col}} │ {'Result':<{result_col}} "
        f"│ {'Reasoning':<{max_reason_width}} │"
    )
    lines.append(sep)

    for r in results:
        result_str = "PASS" if r.passed else "FAIL"
        reasoning = truncate(r.reasoning, max_reason_width)
        lines.append(
            f"│ {r.judge_name:<{judge_col}} │ {result_str:<{result_col}} "
            f"│ {reasoning:<{max_reason_width}} │"
        )

    passed = sum(1 for r in results if r.passed)
    total = len(results)
    score_str = f"{composite:.1f}%"
    summary = f"{passed}/{total} judges passed"

    lines.append(footer_sep)
    lines.append(
        f"│ {'COMPOSITE SCORE':<{judge_col}} │ {score_str:<{result_col}} "
        f"│ {summary:<{max_reason_width}} │"
    )
    lines.append(bottom)

    return "\n".join(lines)


def format_json(results, composite, question, response, model):
    data = {
        "question": question,
        "response": response,
        "model": model,
        "composite_score": round(composite, 1),
        "results": [
            {
                "judge": r.judge_name,
                "passed": r.passed,
                "reasoning": r.reasoning,
                "evidence": r.evidence,
            }
            for r in results
        ],
    }
    return json.dumps(data, indent=2, ensure_ascii=False)
