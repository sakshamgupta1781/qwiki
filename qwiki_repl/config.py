import getpass
import json
import os
import sys

CONFIG_DIR = os.path.expanduser("~/.qwiki")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

DEFAULT_MODEL = "claude-haiku-4-5-20251001"


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return None


def save_config(config):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def setup_interactive(existing_config=None):
    print("\033[36m━━━ qwiki setup ━━━\033[0m\n")

    env_key = os.environ.get("ANTHROPIC_API_KEY", "")
    config_key = (existing_config or {}).get("api_key", "")

    if env_key and config_key:
        print(f"  Found API key in environment: {env_key[:12]}...{env_key[-4:]}")
        print(f"  Found API key in config:      {config_key[:12]}...{config_key[-4:]}")
        choice = input("  Use (e)nvironment, (c)onfig, or enter (n)ew? [e/c/n]: ").strip().lower()
        if choice == "c":
            api_key = config_key
        elif choice == "n":
            api_key = getpass.getpass("  Enter Anthropic API key: ")
        else:
            api_key = env_key
    elif env_key:
        print(f"  Found API key in environment: {env_key[:12]}...{env_key[-4:]}")
        choice = input("  Use this key? [Y/n]: ").strip().lower()
        if choice == "n":
            api_key = getpass.getpass("  Enter Anthropic API key: ")
        else:
            api_key = env_key
    elif config_key:
        print(f"  Found API key in config: {config_key[:12]}...{config_key[-4:]}")
        choice = input("  Use this key? [Y/n]: ").strip().lower()
        if choice == "n":
            api_key = getpass.getpass("  Enter Anthropic API key: ")
        else:
            api_key = config_key
    else:
        api_key = getpass.getpass("  Enter Anthropic API key: ")

    if not api_key:
        print("\033[31m  Error: API key is required.\033[0m")
        return None

    print()
    models = _list_models(api_key)
    if not models:
        print("  Could not fetch models. Using default.")
        ask_model = DEFAULT_MODEL
        eval_model = DEFAULT_MODEL
    else:
        print("  Select model for /ask (answering questions):")
        ask_model = _pick_model(models, DEFAULT_MODEL)

        print("  Select model for eval judges:")
        eval_model = _pick_model(models, DEFAULT_MODEL)

    config = {
        "api_key": api_key,
        "ask_model": ask_model,
        "eval_model": eval_model,
    }
    save_config(config)
    print(f"\n\033[32m  ✓ Settings saved to {CONFIG_FILE}\033[0m\n")
    return config


def _list_models(api_key):
    try:
        from qwiki_common.claude import ClaudeClient
        client = ClaudeClient(api_key, "")
        return client.list_models()
    except Exception:
        return []


def _pick_model(models, default):
    default_idx = None
    for i, m in enumerate(models):
        marker = " (default)" if m == default else ""
        if m == default:
            default_idx = i + 1
        print(f"    {i+1}. {m}{marker}")

    prompt = f"  Select [1-{len(models)}]"
    if default_idx:
        prompt += f" (Enter for {default_idx})"
    prompt += ": "

    choice = input(prompt).strip()
    if not choice and default_idx:
        return default
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(models):
            return models[idx]
    except (ValueError, IndexError):
        pass
    return default
