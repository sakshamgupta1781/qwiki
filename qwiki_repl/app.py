import os
import sys
import tty
import termios

from .banner import print_banner
from .commands import dispatch
from .config import load_config, setup_interactive
from .deps import check_dependencies
from .picker import pick_command

HISTORY_FILE = os.path.expanduser("~/.qwiki/history")
PROMPT = "\033[32mqwiki> \033[0m"


def read_input():
    sys.stdout.write(PROMPT)
    sys.stdout.flush()

    if not sys.stdin.isatty():
        return input()

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    buf = []

    try:
        tty.setcbreak(fd)

        while True:
            ch = os.read(fd, 1).decode("utf-8", errors="replace")

            if ch == "\x03":
                sys.stdout.write("\n")
                sys.stdout.flush()
                raise KeyboardInterrupt

            if ch == "\x04":
                sys.stdout.write("\n")
                sys.stdout.flush()
                raise EOFError

            if ch == "\r" or ch == "\n":
                sys.stdout.write("\n")
                sys.stdout.flush()
                return "".join(buf)

            if ch == "\x7f" or ch == "\x08":
                if buf:
                    buf.pop()
                    sys.stdout.write("\b \b")
                    sys.stdout.flush()
                continue

            if ch == "/" and not buf:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                sys.stdout.write("/")
                sys.stdout.flush()
                try:
                    selected = pick_command()
                except Exception:
                    selected = None

                if selected:
                    if selected in ("ask",):
                        sys.stdout.write(f"\r\033[2K{PROMPT}/{selected} ")
                        sys.stdout.flush()
                        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                        extra = input()
                        return f"/{selected} {extra}"
                    else:
                        return f"/{selected}"
                else:
                    sys.stdout.write(f"\r\033[2K{PROMPT}")
                    sys.stdout.flush()
                    tty.setcbreak(fd)
                    continue

            if ch.isprintable():
                buf.append(ch)
                sys.stdout.write(ch)
                sys.stdout.flush()

    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


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

    print(f"  \033[32m✓ Ready\033[0m — model: {config.get('ask_model', 'unknown')}")
    print()

    while True:
        try:
            line = read_input().strip()

            if not line:
                continue

            if not line.startswith("/"):
                print("  Commands start with /. Type /help for available commands.")
                continue

            dispatch(line, config)

        except (EOFError, KeyboardInterrupt):
            print("\n  Goodbye! 👋")
            break
        except Exception as e:
            print(f"\n  \033[31mError: {e}\033[0m\n")
