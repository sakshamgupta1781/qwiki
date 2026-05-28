import os
import sys

try:
    import tty
    import termios
    HAS_TERMIOS = True
except ImportError:
    HAS_TERMIOS = False

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


def _read_key(fd):
    ch = os.read(fd, 1).decode("utf-8", errors="replace")
    if ch == "\x1b":
        ch2 = os.read(fd, 1).decode("utf-8", errors="replace")
        if ch2 == "[":
            ch3 = os.read(fd, 1).decode("utf-8", errors="replace")
            if ch3 == "A":
                return "UP"
            elif ch3 == "B":
                return "DOWN"
            return None
        return "ESC"
    return ch


def _draw(typed, matches, selected_idx, num_prev_lines):
    out = sys.stdout

    for _ in range(num_prev_lines):
        out.write("\033[1A\033[2K")

    out.write(f"\r\033[2K\033[32mqwiki> \033[0m/{typed}\n")

    for i, (name, desc) in enumerate(matches):
        if i == selected_idx:
            out.write(f"\033[2K  \033[36m▸ /{name:<22}\033[0m \033[90m{desc}\033[0m\n")
        else:
            out.write(f"\033[2K    \033[90m/{name:<22} {desc}\033[0m\n")

    out.flush()
    return len(matches) + 1


def _cleanup(num_lines):
    out = sys.stdout
    for _ in range(num_lines):
        out.write("\033[1A\033[2K")
    out.write("\r\033[2K")
    out.flush()


def pick_command():
    if not HAS_TERMIOS or not sys.stdin.isatty():
        return _fallback_pick()

    fd = sys.stdin.fileno()

    try:
        old_settings = termios.tcgetattr(fd)
    except Exception:
        return _fallback_pick()

    typed = ""
    selected_idx = 0
    matches = list(COMMAND_INFO)

    drawn_lines = _draw(typed, matches, selected_idx, 0)

    try:
        tty.setcbreak(fd)

        while True:
            key = _read_key(fd)

            if key is None:
                continue

            if key == "ESC" or key == "\x03":
                _cleanup(drawn_lines)
                return None

            if key == "\r" or key == "\n":
                if matches:
                    selected = matches[selected_idx][0]
                    _cleanup(drawn_lines)
                    return selected
                continue

            if key == "UP":
                if selected_idx > 0:
                    selected_idx -= 1
                    drawn_lines = _draw(typed, matches, selected_idx, drawn_lines)
                continue

            if key == "DOWN":
                if selected_idx < len(matches) - 1:
                    selected_idx += 1
                    drawn_lines = _draw(typed, matches, selected_idx, drawn_lines)
                continue

            if key == "\x7f" or key == "\x08":
                if typed:
                    typed = typed[:-1]
                    matches = [(n, d) for n, d in COMMAND_INFO if n.startswith(typed)]
                    selected_idx = 0
                    drawn_lines = _draw(typed, matches, selected_idx, drawn_lines)
                continue

            if key.isprintable():
                typed += key
                matches = [(n, d) for n, d in COMMAND_INFO if n.startswith(typed)]
                selected_idx = 0
                drawn_lines = _draw(typed, matches, selected_idx, drawn_lines)

    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def _fallback_pick():
    print("\n  Available commands:")
    for i, (name, desc) in enumerate(COMMAND_INFO, 1):
        print(f"  {i}. /{name:<22} {desc}")
    try:
        choice = input(f"\n  Select [1-{len(COMMAND_INFO)}]: ").strip()
        idx = int(choice) - 1
        if 0 <= idx < len(COMMAND_INFO):
            return COMMAND_INFO[idx][0]
    except (ValueError, EOFError):
        pass
    return None
