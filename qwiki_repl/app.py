import os
import readline
import sys

from .banner import print_banner
from .commands import dispatch
from .config import load_config, setup_interactive
from .deps import check_dependencies

HISTORY_FILE = os.path.expanduser("~/.qwiki/history")


def setup_readline():
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    try:
        readline.read_history_file(HISTORY_FILE)
    except FileNotFoundError:
        pass
    readline.set_history_length(500)


def main():
    check_dependencies()

    os.system("clear" if os.name != "nt" else "cls")
    print_banner()

    config = load_config()
    if not config:
        print("  \033[33mFirst time? Let's set you up.\033[0m\n")
        config = setup_interactive()
        if not config:
            print("  Setup cancelled.")
            sys.exit(1)

    setup_readline()

    print(f"  \033[32m✓ Ready\033[0m — model: {config.get('ask_model', 'unknown')}")
    print()

    while True:
        try:
            line = input("\033[32mqwiki> \033[0m").strip()

            if not line:
                continue

            if not line.startswith("/"):
                print("  Commands start with /. Type /help for available commands.")
                continue

            dispatch(line, config)

        except (EOFError, KeyboardInterrupt):
            print("\n\n  Goodbye! 👋")
            break
        except Exception as e:
            print(f"\n  \033[31mError: {e}\033[0m\n")

    try:
        readline.write_history_file(HISTORY_FILE)
    except Exception:
        pass
