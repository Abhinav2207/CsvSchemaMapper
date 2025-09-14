import os
from typing import List


class MatchMethod:
    EXACT = "Exact Match"
    ABBREVIATION = "Abbreviation Match"
    FUZZY = "Fuzzy Match"
    BEDROCK = "AI (Bedrock)"
    NO_MATCH = "No Match"

    def get_all_match_methods(self) -> List[str]:
        return [v.value for v in self]


class SummaryKey:
    EXACT_MATCHES = "exact_matches"
    ABBREVIATION_MATCHES = "abbreviation_matches"
    FUZZY_MATCHES = "fuzzy_matches"
    BEDROCK_MATCHES = "bedrock_matches"
    NO_MATCHES = "no_matches"


class CONSTANTS:
    COLUMN_DELTA_THRESHOLD = int(os.getenv("COLUMN_DELTA_THRESHOLD", "3"))
    USE_BEDROCK = os.getenv("USE_BEDROCK", "False").lower() == "true"
    BEDROCK_REGION = os.getenv("BEDROCK_REGION", "us-east-1")
    BEDROCK_MODEL = os.getenv("BEDROCK_MODEL", "anthropic.claude-3-haiku-20240307-v1:0")
    MISSING_DATA_THRESHOLD = float(os.getenv("MISSING_DATA_THRESHOLD", "10.0"))
