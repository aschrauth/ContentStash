"""
Deterministic checks for summary fallback generation.
"""
from app.services import background


SAMPLE_TEXT = """
# Highway 29 bottleneck study

Napa transportation planners are evaluating several redesign options for the Highway 29 and Airport Boulevard intersection.
The proposed changes are meant to reduce congestion, improve left-turn movement, and keep traffic flowing during peak travel times.
Officials are comparing costs, right-of-way impacts, and the long-term feasibility of each alternative before selecting a preferred plan.
"""


def test_extractive_summary_fallback() -> None:
    summary = background._extractive_summary_fallback(SAMPLE_TEXT)
    assert summary
    lines = [line for line in summary.splitlines() if line.strip()]
    assert len(lines) >= 2
    assert all(line.startswith("- ") for line in lines)


def test_generate_auto_categorization_salvages_non_json() -> None:
    original_is_available = background.gemini_service.is_available
    original_generate_content = background.gemini_service.generate_content

    try:
        background.gemini_service.is_available = lambda: True
        background.gemini_service.generate_content = lambda prompt, model="gemini-2.5-flash-lite": """
Here are the key points:
- Napa is studying redesign options for the Highway 29 chokepoint.
- Officials want to improve traffic flow and reduce delays at Airport Boulevard.
- Cost and feasibility will determine which concept moves forward.
"""

        result = background.generate_auto_categorization(SAMPLE_TEXT)
        assert result is not None
        assert result["summary"].startswith("- ")
    finally:
        background.gemini_service.is_available = original_is_available
        background.gemini_service.generate_content = original_generate_content


def test_generate_auto_categorization_falls_back_without_gemini() -> None:
    original_is_available = background.gemini_service.is_available

    try:
        background.gemini_service.is_available = lambda: False
        result = background.generate_auto_categorization(SAMPLE_TEXT)
        assert result is not None
        assert result["summary"].startswith("- ")
    finally:
        background.gemini_service.is_available = original_is_available


if __name__ == "__main__":
    test_extractive_summary_fallback()
    test_generate_auto_categorization_salvages_non_json()
    test_generate_auto_categorization_falls_back_without_gemini()
    print("All summary fallback tests passed")
