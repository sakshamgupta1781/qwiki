import os
import sys

from .banner import print_banner
from .config import setup_interactive, save_config


COMMANDS = {}


def register(name):
    def decorator(func):
        COMMANDS[name] = func
        return func
    return decorator


def dispatch(line, config):
    parts = line.lstrip("/").split(None, 1)
    cmd_name = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""

    handler = COMMANDS.get(cmd_name)
    if not handler:
        print(f"\033[31m  Unknown command: /{cmd_name}\033[0m")
        print(f"  Type /help for available commands.")
        return

    handler(args, config)


@register("help")
def cmd_help(args, config):
    print()
    print("\033[36m  Available commands:\033[0m")
    print()
    print("  \033[1m/ask <question>\033[0m        Ask a question (runs eval judges by default)")
    print("  \033[1m/ask --no-eval <q>\033[0m     Ask without running eval judges")
    print("  \033[1m/setup\033[0m                 Configure API key and model preferences")
    print("  \033[1m/calibrate-judges\033[0m      Run 100-case judge calibration suite")
    print("  \033[1m/run-evals\033[0m             Run 50-case eval + refusal test suites")
    print("  \033[1m/clear\033[0m                 Clear screen and show banner")
    print("  \033[1m/help\033[0m                  Show this help message")
    print("  \033[1m/exit\033[0m                  Exit qwiki")
    print()


@register("exit")
def cmd_exit(args, config):
    print("\n  Goodbye! 👋")
    sys.exit(0)


@register("quit")
def cmd_quit(args, config):
    cmd_exit(args, config)


@register("clear")
def cmd_clear(args, config):
    os.system("clear" if os.name != "nt" else "cls")
    print_banner()


@register("setup")
def cmd_setup(args, config):
    new_config = setup_interactive(config)
    if new_config:
        config.update(new_config)


@register("ask")
def cmd_ask(args, config):
    if not args:
        print("  \033[31mPlease provide a question: /ask <question>\033[0m")
        return

    run_eval = True
    question = args
    if args.startswith("--no-eval "):
        run_eval = False
        question = args[len("--no-eval "):]
    elif args.strip() == "--no-eval":
        print("  \033[31mPlease provide a question: /ask --no-eval <question>\033[0m")
        return

    from qwiki_common.claude import ClaudeClient
    from qwiki_ask.pipeline import run

    client = ClaudeClient(config["api_key"], config["ask_model"])
    print()
    run(question, client, run_eval=run_eval)
    print()


@register("calibrate-judges")
def cmd_calibrate_judges(args, config):
    from qwiki_common.claude import ClaudeClient
    from qwiki_eval.cli import cmd_calibrate
    import argparse

    golden_path = "golden/eval_set.csv"
    if not os.path.exists(golden_path):
        print(f"  \033[31mGolden eval set not found: {golden_path}\033[0m")
        return

    print(f"\n  Running judge calibration on 100 cases...")
    print(f"  Model: {config['eval_model']}")
    print(f"  This will take several hours with 60s cooldowns.\n")

    cal_args = argparse.Namespace(
        golden=golden_path,
        model=config["eval_model"],
        judges=None,
    )
    cmd_calibrate(cal_args)
    print()


@register("run-evals")
def cmd_run_evals(args, config):
    test_cases_path = "testing/test_cases.csv"
    refusal_cases_path = "testing/refusal_test_cases.csv"

    if not os.path.exists(test_cases_path):
        print(f"  \033[31mTest cases not found: {test_cases_path}\033[0m")
        return
    if not os.path.exists(refusal_cases_path):
        print(f"  \033[31mRefusal test cases not found: {refusal_cases_path}\033[0m")
        return

    print(f"\n  Running eval + refusal test suites (100 cases total)...")
    print(f"  Ask model: {config['ask_model']}")
    print(f"  Eval model: {config['eval_model']}")
    print()

    print("\033[36m  ━━━ Part 1: Eval Test Suite (50 cases) ━━━\033[0m\n")
    os.system(
        f"python3 testing/run_tests.py "
        f"--model {config['eval_model']} --version v3"
    )

    print("\n\033[36m  ━━━ Part 2: Refusal Test Suite (50 cases) ━━━\033[0m\n")
    os.system(
        f"python3 testing/run_refusal_tests.py "
        f"--model {config['ask_model']} --version v3"
    )
    print()
