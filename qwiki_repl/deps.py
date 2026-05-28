import sys


def check_dependencies():
    errors = []

    if sys.version_info < (3, 10):
        errors.append(
            f"Python 3.10+ required (found {sys.version_info.major}.{sys.version_info.minor}). "
            f"Install from https://www.python.org/downloads/"
        )

    for package, label in [
        ("qwiki_common", "qwiki_common (shared API clients)"),
        ("qwiki_ask", "qwiki_ask (question-answering tool)"),
        ("qwiki_eval", "qwiki_eval (evaluation judges)"),
    ]:
        try:
            __import__(package)
        except ImportError:
            errors.append(
                f"Package '{label}' not found. "
                f"Make sure you're running from the qwiki project directory."
            )

    if errors:
        print("\033[31m✗ Dependency check failed:\033[0m")
        for e in errors:
            print(f"  \033[31m• {e}\033[0m")
        print()
        print("Fix these issues and try again.")
        sys.exit(1)

    return True
