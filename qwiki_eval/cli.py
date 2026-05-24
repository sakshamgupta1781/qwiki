import argparse
import csv
import os
import sys

from .api.claude import ClaudeClient
from .runner import run_eval, ALL_JUDGES
from .formatter import format_table, format_json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from calibration.metrics import compute_metrics


def get_api_key():
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        print("Error: ANTHROPIC_API_KEY environment variable not set.", file=sys.stderr)
        print("  export ANTHROPIC_API_KEY=\"your-key-here\"", file=sys.stderr)
        sys.exit(1)
    return key


def pick_model_interactive(api_key):
    client = ClaudeClient(api_key, "")
    try:
        models = client.list_models()
    except Exception as e:
        print(f"Error listing models: {e}", file=sys.stderr)
        sys.exit(1)

    if not models:
        print("No Claude models found for this API key.", file=sys.stderr)
        sys.exit(1)

    print("\nAvailable Claude models:", file=sys.stderr)
    for i, m in enumerate(models, 1):
        print(f"  {i}. {m}", file=sys.stderr)

    while True:
        try:
            choice = input(f"\nSelect a model (1-{len(models)}): ")
            idx = int(choice) - 1
            if 0 <= idx < len(models):
                return models[idx]
            print(f"Please enter a number between 1 and {len(models)}.", file=sys.stderr)
        except (ValueError, EOFError):
            print("Invalid input.", file=sys.stderr)
            sys.exit(1)


def get_response(args):
    if args.response:
        return args.response
    if args.response_file:
        with open(args.response_file) as f:
            return f.read()
    if not sys.stdin.isatty():
        return sys.stdin.read()
    print("Error: provide --response, --response-file, or pipe via stdin.", file=sys.stderr)
    sys.exit(1)


def cmd_eval(args):
    api_key = get_api_key()
    model = args.model or pick_model_interactive(api_key)
    response = get_response(args)

    client = ClaudeClient(api_key, model)
    results, composite = run_eval(args.question, response, client)

    if args.format == "json":
        print(format_json(results, composite, args.question, response, model))
    else:
        print(format_table(results, composite))


def cmd_calibrate(args):
    api_key = get_api_key()
    model = args.model or pick_model_interactive(api_key)
    client = ClaudeClient(api_key, model)

    judge_filter = None
    if args.judges:
        judge_filter = set(args.judges.split(","))

    with open(args.golden, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        cases = list(reader)

    if not cases:
        print("Error: golden eval set is empty.", file=sys.stderr)
        sys.exit(1)

    judge_names = [j.name for j in ALL_JUDGES]
    if judge_filter:
        judge_names = [n for n in judge_names if n in judge_filter]

    per_judge_auto = {name: [] for name in judge_names}
    per_judge_human = {name: [] for name in judge_names}

    total = len(cases)
    for i, case in enumerate(cases, 1):
        question = case.get("question", "")
        response = case.get("response", "")
        case_id = case.get("id", f"case-{i}")

        print(f"[{i}/{total}] Evaluating {case_id}...", file=sys.stderr)
        results, _ = run_eval(question, response, client, judge_names=set(judge_names))

        result_by_name = {r.judge_name: r for r in results}

        for name in judge_names:
            label_key = f"label_{name}"
            human_label = case.get(label_key, "").strip().upper()
            if human_label not in ("PASS", "FAIL"):
                continue

            human_pass = human_label == "PASS"

            if name in result_by_name:
                per_judge_auto[name].append(result_by_name[name].passed)
                per_judge_human[name].append(human_pass)

    print(f"\nqwiki-eval calibrate — Judge Calibration Report")
    print(f"Model: {model}")
    print(f"Golden set: {args.golden} ({total} cases)")
    print("═" * 57)
    print(f"{'Judge':<19} {'Precision':>9} {'Recall':>9} {'F1':>9} {'N':>5}")
    print("─" * 57)

    all_metrics = []
    for name in judge_names:
        if not per_judge_auto[name]:
            print(f"{name:<19} {'N/A':>9} {'N/A':>9} {'N/A':>9} {'0':>5}")
            continue

        m = compute_metrics(per_judge_auto[name], per_judge_human[name])
        all_metrics.append(m)
        print(
            f"{name:<19} {m['precision']:>9.2f} {m['recall']:>9.2f} "
            f"{m['f1']:>9.2f} {m['n']:>5}"
        )

    if all_metrics:
        print("─" * 57)
        macro_p = sum(m["precision"] for m in all_metrics) / len(all_metrics)
        macro_r = sum(m["recall"] for m in all_metrics) / len(all_metrics)
        macro_f1 = sum(m["f1"] for m in all_metrics) / len(all_metrics)
        total_n = sum(m["n"] for m in all_metrics)
        print(
            f"{'OVERALL (macro)':<19} {macro_p:>9.2f} {macro_r:>9.2f} "
            f"{macro_f1:>9.2f} {total_n:>5}"
        )


def main():
    parser = argparse.ArgumentParser(
        prog="qwiki-eval",
        description="Evaluation tool for qwiki Wikipedia Q&A system",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    eval_parser = subparsers.add_parser("eval", help="Evaluate a single question-response pair")
    eval_parser.add_argument("--question", required=True, help="The question that was asked")
    eval_parser.add_argument("--response", help="The plain text response (answer + sources)")
    eval_parser.add_argument("--response-file", help="Path to a file containing the response")
    eval_parser.add_argument("--model", help="Claude model to use (interactive picker if omitted)")
    eval_parser.add_argument(
        "--format", choices=["table", "json"], default="table",
        help="Output format (default: table)",
    )

    cal_parser = subparsers.add_parser("calibrate", help="Run judges against a golden eval set")
    cal_parser.add_argument("--golden", required=True, help="Path to golden eval set CSV")
    cal_parser.add_argument("--model", help="Claude model to use (interactive picker if omitted)")
    cal_parser.add_argument(
        "--judges", help="Comma-separated list of judges to run (default: all)",
    )

    args = parser.parse_args()

    if args.command == "eval":
        cmd_eval(args)
    elif args.command == "calibrate":
        cmd_calibrate(args)
