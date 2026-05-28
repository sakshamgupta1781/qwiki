BANNER = """\033[36m
  ██████╗ ██╗    ██╗██╗██╗  ██╗██╗
 ██╔═══██╗██║    ██║██║██║ ██╔╝██║
 ██║   ██║██║ █╗ ██║██║█████╔╝ ██║
 ██║▄▄ ██║██║███╗██║██║██╔═██╗ ██║
 ╚██████╔╝╚███╔███╔╝██║██║  ██╗██║
  ╚══▀▀═╝  ╚══╝╚══╝ ╚═╝╚═╝  ╚═╝╚═╝
\033[0m"""

TAGLINE = "\033[33m  Your brain called. It wants Wikipedia back.\033[0m"

VERSION = "v3"


def print_banner():
    print(BANNER)
    print(TAGLINE)
    print(f"\033[90m  Type /help for commands. Type /exit to quit.\033[0m")
    print()
