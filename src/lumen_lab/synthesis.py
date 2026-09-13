from .ledger import Outcome, analyze_calibration
from .models import Experiment
from .planner import ranked


def journal_section_count(journal_text: str) -> int:
    return sum(line.startswith("## ") for line in journal_text.splitlines())


def repeated_lesson_signals(outcomes: list[Outcome]) -> list[tuple[str, list[str]]]:
    rules = (
        (
            "deterministic-controls",
            ("deterministic", "dry-run", "validation", "explicit", "fallback"),
        ),
        (
            "safety-boundaries",
            ("safety", "allowlist", "containment", "unmanaged", "risk"),
        ),
        (
            "tests-and-documentation",
            ("tests", "documentation", "document"),
        ),
    )
    signals: list[tuple[str, list[str]]] = []
    for name, keywords in rules:
        supporting = sorted(
            outcome.experiment_id
            for outcome in outcomes
            if any(keyword in outcome.result.lower() for keyword in keywords)
        )
        if len(supporting) >= 2:
            signals.append((name, supporting))
    return signals


def render_synthesis(
    experiments: list[Experiment],
    outcomes: list[Outcome],
    journal_text: str,
) -> str:
    completed = sorted(item.id for item in experiments if item.status == "done")
    pending = ranked(experiments)
    report = analyze_calibration(outcomes)
    signals = repeated_lesson_signals(outcomes)
    mae = "n/a" if report.mae is None else f"{report.mae:.2f}"
    signed = (
        "n/a"
        if report.mean_signed_error is None
        else f"{report.mean_signed_error:+.2f}"
    )

    lines = [
        "# Lumen Synthesis",
        "",
        "This snapshot is generated deterministically from repository state and journal text.",
        "It does not use a model, network service, or secret, and it does not modify the journal.",
        "",
        "## Evidence",
        "",
        f"- Completed experiments: {len(completed)}",
        f"- Completed IDs: {', '.join(f'`{item}`' for item in completed) or 'none'}",
        f"- Recorded outcomes: {len(outcomes)}",
        f"- Journal sections: {journal_section_count(journal_text)}",
        f"- Calibration MAE: {mae}",
        f"- Mean signed residual: {signed}",
        f"- Calibration direction: {report.direction}",
        "",
        "## Repeated lesson signals",
        "",
    ]
    if signals:
        lines.extend(
            f"- `{name}` — supported by {', '.join(f'`{item}`' for item in ids)}"
            for name, ids in signals
        )
    else:
        lines.append("No lesson signal has support from at least two recorded outcomes.")

    lines.extend(["", "## Missing capabilities", ""])
    if pending:
        lines.extend(
            f"- `{item.id}` — {item.title} — priority `{item.score():.2f}`"
            for item in pending
        )
    else:
        lines.append("No backlog capability is currently pending.")

    lines.extend(
        [
            "",
            "## Interpretation limits",
            "",
            (
                "- Lesson signals are keyword rules over recorded outcome summaries, "
                "not semantic claims."
            ),
            "- A signal is shown only when at least two distinct outcomes support it.",
            "- Missing capabilities are the current ranked backlog, not generated recommendations.",
            (
                "- The journal remains the append-only narrative source; this file is "
                "a disposable view."
            ),
            "",
        ]
    )
    return "\n".join(lines)
