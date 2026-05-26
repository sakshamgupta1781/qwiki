import argparse
import os
import sys

from qwiki_common.claude import ClaudeClient
from .pipeline import run


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


def main():
    parser = argparse.ArgumentParser(
        prog="qwiki-ask",
        description="Answer questions using Wikipedia and Claude",
    )
    parser.add_argument("question", nargs="+", help="The question to answer")
    parser.add_argument("--model", help="Claude model to use (interactive picker if omitted)")
    parser.add_argument("--debug", action="store_true", help="Show debug output for each pipeline phase")
    parser.add_argument("--no-eval", action="store_true", help="Skip eval judges (faster)")

    args = parser.parse_args()
    question = " ".join(args.question)

    api_key = get_api_key()
    model = args.model or pick_model_interactive(api_key)

    client = ClaudeClient(api_key, model)
    run(question, client, debug=args.debug, run_eval=not args.no_eval)
