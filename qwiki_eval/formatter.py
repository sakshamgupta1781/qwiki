import json
import shutil
import textwrap


def format_table(results, composite):
    term_width = shutil.get_terminal_size((80, 24)).columns
    wrap_width = max(term_width - 4, 40)

    passed = sum(1 for r in results if r.passed)
    total = len(results)
    score_str = f"{composite:.1f}%"

    lines = []
    thin = "─" * wrap_width

    for r in results:
        result_str = "\033[32mPASS\033[0m" if r.passed else "\033[31mFAIL\033[0m"
        lines.append(f"  {r.judge_name:<19} {result_str}")
        wrapped = textwrap.fill(r.reasoning, width=wrap_width,
                                initial_indent="    ", subsequent_indent="    ")
        lines.append(f"\033[90m{wrapped}\033[0m")
        lines.append("")

    lines.append(f"  {thin}")
    lines.append(f"  \033[1mCOMPOSITE SCORE: {score_str}\033[0m — {passed}/{total} judges passed")

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
