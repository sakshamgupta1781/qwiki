import sys
import tty
import termios

COMMAND_INFO = [
    ("ask", "Ask a question (runs evals by default)"),
    ("scorecard", "Show benchmarks dashboard"),
    ("setup", "Configure API key and models"),
    ("calibrate-judges", "Run 100-case judge calibration"),
    ("run-evals", "Run eval + refusal test suites"),
    ("clear", "Clear screen and show banner"),
    ("help", "Show all commands"),
    ("exit", "Exit qwiki"),
]


def _read_key():
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == "\x1b":
            ch2 = sys.stdin.read(1)
            if ch2 == "[":
                ch3 = sys.stdin.read(1)
                if ch3 == "A":
                    return "UP"
                elif ch3 == "B":
                    return "DOWN"
                return None
            return "ESC"
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _render(typed, matches, selected_idx):
    # Clear previous dropdown
    lines_to_clear = len(matches) + 1
    for _ in range(lines_to_clear):
        sys.stdout.write("\033[2K\033[1A")
    sys.stdout.write("\033[2K\r")

    # Redraw prompt + typed text
    sys.stdout.write(f"\033[32mqwiki> \033[0m/{typed}")
    sys.stdout.write("\n")

    # Draw matches
    for i, (name, desc) in enumerate(matches):
        if i == selected_idx:
            sys.stdout.write(f"  \033[36m▸ /{name:<22}\033[0m \033[90m{desc}\033[0m\n")
        else:
            sys.stdout.write(f"    \033[90m/{name:<22} {desc}\033[0m\n")

    sys.stdout.flush()


def pick_command():
    typed = ""
    selected_idx = 0

    matches = list(COMMAND_INFO)

    # Initial render
    sys.stdout.write("\n")
    for i, (name, desc) in enumerate(matches):
        if i == selected_idx:
            sys.stdout.write(f"  \033[36m▸ /{name:<22}\033[0m \033[90m{desc}\033[0m\n")
        else:
            sys.stdout.write(f"    \033[90m/{name:<22} {desc}\033[0m\n")
    sys.stdout.flush()

    while True:
        key = _read_key()

        if key is None:
            continue

        if key == "ESC":
            # Clear dropdown
            for _ in range(len(matches) + 1):
                sys.stdout.write("\033[2K\033[1A")
            sys.stdout.write("\033[2K\r")
            sys.stdout.write(f"\033[32mqwiki> \033[0m")
            sys.stdout.flush()
            return None

        if key == "\r" or key == "\n":
            # Select current
            if matches:
                selected = matches[selected_idx][0]
                # Clear dropdown
                for _ in range(len(matches) + 1):
                    sys.stdout.write("\033[2K\033[1A")
                sys.stdout.write("\033[2K\r")
                sys.stdout.flush()
                return selected
            continue

        if key == "UP":
            if selected_idx > 0:
                selected_idx -= 1
                _render(typed, matches, selected_idx)
            continue

        if key == "DOWN":
            if selected_idx < len(matches) - 1:
                selected_idx += 1
                _render(typed, matches, selected_idx)
            continue

        if key == "\x7f" or key == "\x08":  # Backspace
            if typed:
                typed = typed[:-1]
                matches = [(n, d) for n, d in COMMAND_INFO if n.startswith(typed)]
                selected_idx = 0
                _render(typed, matches, selected_idx)
            continue

        if key == "\x03":  # Ctrl+C
            for _ in range(len(matches) + 1):
                sys.stdout.write("\033[2K\033[1A")
            sys.stdout.write("\033[2K\r")
            sys.stdout.flush()
            return None

        if key.isprintable():
            typed += key
            matches = [(n, d) for n, d in COMMAND_INFO if n.startswith(typed)]
            selected_idx = 0
            _render(typed, matches, selected_idx)
