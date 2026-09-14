from __future__ import annotations

from pathlib import Path


def test_desktop_surfaces_backend_recommendation_reasons() -> None:
    app_source = Path("apps/desktop/src/App.tsx").read_text(encoding="utf-8")
    component_source = Path(
        "apps/desktop/src/RecommendationExplanation.tsx"
    ).read_text(encoding="utf-8")

    assert 'import RecommendationExplanation from "./RecommendationExplanation";' in app_source
    assert app_source.count("<RecommendationExplanation") == 2
    assert app_source.count("reasons={today.selection?.reasons}") == 2
    assert app_source.count("exclude={today.why_now}") == 2

    assert 'data-recommendation-explanation="true"' in component_source
    assert "reason !== excluded" in component_source
    assert "items.indexOf(reason) === index" in component_source
    assert "<details" in component_source
