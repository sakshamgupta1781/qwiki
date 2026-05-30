import json
import os

BENCHMARKS_DIR = "benchmarks"


def _load(subdir):
    path = os.path.join(BENCHMARKS_DIR, subdir, "latest.json")
    if not os.path.exists(path):
        return None, None
    with open(path) as f:
        data = json.load(f)
    return data.get("current"), data.get("previous")


def _delta_str(current, previous, fmt=".2f", invert=False):
    if previous is None or current is None:
        return "  —"
    d = current - previous
    if invert:
        d = -d
    if abs(d) < 0.005:
        return "  —"
    sign = "+" if d > 0 else ""
    return f"{sign}{d:{fmt}}"


def render_scorecard():
    print("\n\033[36m━━━ qwiki scorecard ━━━\033[0m\n")

    _render_judge_calibration()
    _render_response_quality()
    _render_refusal_rate()


def _render_judge_calibration():
    current, previous = _load("judge_calibration")
    if not current:
        print("  \033[90m📊 Judge Calibration: no data. Run /calibrate-judges first.\033[0m\n")
        return

    ts = current.get("timestamp", "unknown")[:10]
    model = current.get("model", "unknown")
    versions = current.get("versions", {})
    ver_str = ", ".join(f"{k} {v}" for k, v in sorted(versions.items()))

    print(f"\033[1m📊 Judge Calibration\033[0m (100-case golden set)")
    print(f"   Last run: {ts} | Model: {model}")
    print(f"   \033[90mVersions: {ver_str}\033[0m")
    print()
    print(f"   {'Judge':<18} {'P':>5} {'R':>5} {'F1':>5} {'Δ prev':>7}")
    print(f"   {'─' * 42}")

    judges = current.get("judges", {})
    prev_judges = (previous or {}).get("judges", {}) if previous else {}

    for name in sorted(judges.keys(), key=lambda k: -judges[k]["f1"]):
        j = judges[name]
        pj = prev_judges.get(name, {})
        delta = _delta_str(j["f1"], pj.get("f1"))
        print(f"   {name:<18} {j['precision']:>5.2f} {j['recall']:>5.2f} {j['f1']:>5.2f} {delta:>6}")

    macro = current.get("macro_f1", 0)
    prev_macro = (previous or {}).get("macro_f1") if previous else None
    delta = _delta_str(macro, prev_macro)
    print(f"   {'─' * 42}")
    print(f"   {'MACRO F1':<18} {'':>5} {'':>5} {macro:>5.2f} {delta:>6}")
    print()


def _render_response_quality():
    current, previous = _load("response_quality")
    if not current:
        print("  \033[90m📈 Response Quality: no data. Run /run-evals first.\033[0m\n")
        return

    ts = current.get("timestamp", "unknown")[:10]
    version = current.get("version", "unknown")

    print(f"\033[1m📈 Response Quality\033[0m (50-case eval suite, {version})")
    print(f"   Last run: {ts}")
    print()
    print(f"   {'Judge':<18} {'Pass%':>7} {'Δ prev':>7}")
    print(f"   {'─' * 33}")

    judges = current.get("judges", {})
    prev_judges = (previous or {}).get("judges", {}) if previous else {}

    for name in sorted(judges.keys(), key=lambda k: -judges[k]):
        rate = judges[name]
        prev_rate = prev_judges.get(name)
        delta = _delta_str(rate, prev_rate, ".1f")
        print(f"   {name:<18} {rate:>6.1f}% {delta:>6}")

    composite = current.get("composite", 0)
    trusted = current.get("trusted", 0)
    prev_comp = (previous or {}).get("composite") if previous else None
    prev_trust = (previous or {}).get("trusted") if previous else None

    print(f"   {'─' * 33}")
    print(f"   {'Composite':<18} {composite:>6.1f}% {_delta_str(composite, prev_comp, '.1f'):>6}")
    print(f"   {'Trusted (8)':<18} {trusted:>6.1f}% {_delta_str(trusted, prev_trust, '.1f'):>6}")
    print()


def _render_refusal_rate():
    current, previous = _load("refusal_rate")
    if not current:
        print("  \033[90m🚫 Refusal Rate: no data. Run /run-evals first.\033[0m\n")
        return

    ts = current.get("timestamp", "unknown")[:10]
    version = current.get("version", "unknown")

    print(f"\033[1m🚫 Refusal Rate\033[0m (50-case refusal suite, {version})")
    print(f"   Last run: {ts}")
    print()

    rate = current.get("refusal_rate", 0)
    ir = current.get("incorrect_refusals", 0)
    ir_total = current.get("total_should_answer", 0)
    ia = current.get("incorrect_answers", 0)
    ia_total = current.get("total_should_refuse", 0)

    prev_rate = (previous or {}).get("refusal_rate") if previous else None
    prev_ir = (previous or {}).get("incorrect_refusals") if previous else None
    prev_ia = (previous or {}).get("incorrect_answers") if previous else None

    print(f"   {'Refusal rate:':<24} {rate:>5.1f}%  {_delta_str(rate, prev_rate, '.1f', invert=True):>6}")
    print(f"   {'Incorrect refusals:':<24} {ir:>3}/{ir_total:<3}  {_delta_str(ir, prev_ir, '.0f', invert=True):>6}")
    print(f"   {'Incorrect answers:':<24} {ia:>3}/{ia_total:<3}  {_delta_str(ia, prev_ia, '.0f', invert=True):>6}")
    print()
