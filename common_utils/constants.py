import os
from typing import List


class MatchMethod:
    EXACT = "Exact Match"
    ABBREVIATION = "Abbreviation Match"
    FUZZY = "Fuzzy Match"
    GEMINI = "AI (Gemini)"
    MANUAL = "Manual Match"
    NO_MATCH = "No Match"

    def get_all_match_methods(self) -> List[str]:
        return [v.value for v in self]


class SummaryKey:
    EXACT_MATCHES = "exact_matches"
    ABBREVIATION_MATCHES = "abbreviation_matches"
    FUZZY_MATCHES = "fuzzy_matches"
    GEMINI_MATCHES = "gemini_matches"
    MANUAL_MATCHES = "manual_matches"
    NO_MATCHES = "no_matches"


class CONSTANTS:
    USE_GEMINI = os.getenv("USE_GEMINI", "True").lower() == "true"
    GEMINI_API_KEY = os.getenv(
        "GEMINI_API_KEY", "AIzaSyDxP9FY64eiv3NqB7MXqQvpKAZ9BQ_KWAo"
    )
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    MISSING_DATA_THRESHOLD = float(os.getenv("MISSING_DATA_THRESHOLD", "10.0"))
    AI_CONFIDENCE_THRESHOLD = float(os.getenv("AI_CONFIDENCE_THRESHOLD", "0.7"))
    COLUMN_UNMATCH_THRESHOLD = int(os.getenv("COLUMN_UNMATCH_THRESHOLD", "5"))
