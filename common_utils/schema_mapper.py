from collections import Counter
import re
from typing import Dict, List, Tuple

import pandas as pd
from rapidfuzz import fuzz

from common_utils.bedrock_agent import BedrockAgent
from common_utils.constants import CONSTANTS, MatchMethod, SummaryKey
from modules.schema_loader import get_schema_loader


class SchemaMapper:
    def __init__(self, use_bedrock: bool = CONSTANTS.USE_BEDROCK):
        self.schema_loader = get_schema_loader()
        self.canonical_columns = self.schema_loader.get_canonical_columns()
        self.mapped_canonical_columns = (
            set()
        )  # Track which canonical columns are already mapped

        # Initialize Bedrock agent
        self.bedrock_agent = BedrockAgent(use_bedrock=use_bedrock)
        self.use_bedrock = self.bedrock_agent.use_bedrock

    def normalize_header(self, header: str) -> str:
        """
        Normalize header by:
        1. Handling camelCase by inserting underscores before capital letters
        2. Converting to lowercase
        3. Replacing spaces, hyphens, dots with underscores
        4. Removing special characters except underscores
        5. Removing multiple consecutive underscores
        6. Stripping leading/trailing underscores
        """
        if not header or not isinstance(header, str):
            return ""

        # Strip whitespace first
        normalized = header.strip()

        # Handle camelCase by inserting underscores smartly
        # Use regex to insert underscores before capital letters, but handle abbreviations better
        # This pattern handles:
        # - Regular camelCase: "OrderDate" -> "Order_Date"
        # - Abbreviations at end: "OrderID" -> "Order_ID"
        # - Multiple caps: "ProductSKU" -> "Product_SKU"

        # Insert underscore before a capital letter if:
        # 1. It's preceded by a lowercase letter, OR
        # 2. It's followed by a lowercase letter and preceded by another capital
        normalized = re.sub(
            r"([a-z])([A-Z])", r"\1_\2", normalized
        )  # camelCase boundaries
        normalized = re.sub(
            r"([A-Z])([A-Z][a-z])", r"\1_\2", normalized
        )  # Handle XMLParser -> XML_Parser

        # Convert to lowercase
        normalized = normalized.lower()

        # Replace common separators with underscores
        normalized = re.sub(r"[\s\-\.]+", "_", normalized)

        # Remove special characters except underscores and alphanumeric
        normalized = re.sub(r"[^\w]", "_", normalized)

        # Replace multiple underscores with single underscore
        normalized = re.sub(r"_+", "_", normalized)

        # Strip leading/trailing underscores
        normalized = normalized.strip("_")

        return normalized

    def get_exact_matches(
        self, normalized_headers: List[str]
    ) -> Dict[str, Tuple[str, float]]:
        """
        Find exact matches between normalized uploaded headers and canonical columns.
        Returns dict: {original_header: (canonical_column, confidence)}
        """
        exact_matches = {}

        for header in normalized_headers:
            # Check if normalized header matches any canonical column exactly
            if (
                header in self.canonical_columns
                and header not in self.mapped_canonical_columns
            ):
                exact_matches[header] = (header, 1.0)
                self.mapped_canonical_columns.add(header)

        return exact_matches

    def get_common_abbreviation_matches(
        self, normalized_headers: List[str]
    ) -> Dict[str, Tuple[str, float]]:
        """
        Handle common abbreviations and variations using abbreviations from each column definition.
        Only maps to canonical columns that haven't been mapped yet.
        """
        abbreviation_matches = {}

        for header in normalized_headers:
            # Check each canonical column's abbreviations
            for canonical_name, column_def in self.canonical_columns.items():
                # Skip if this canonical column is already mapped
                if canonical_name in self.mapped_canonical_columns:
                    continue

                # Get abbreviations for this column
                abbreviations = column_def.get("abbreviations", [])

                # Check if normalized header matches any abbreviation for this column
                if header in abbreviations:
                    abbreviation_matches[header] = (canonical_name, 0.9)
                    self.mapped_canonical_columns.add(canonical_name)
                    break  # Found a match, stop checking other columns

        return abbreviation_matches

    def get_fuzzy_matches(
        self, normalized_headers: List[str], min_score: float = 0.6
    ) -> Dict[str, Tuple[str, float]]:
        """
        Handle fuzzy string matching for remaining headers.
        Only maps to canonical columns that haven't been mapped yet.
        """
        fuzzy_matches = {}

        for header in normalized_headers:

            best_match = None
            best_score = 0.0

            # Compare against all available canonical columns
            for canonical_name in self.canonical_columns.keys():
                # Skip if this canonical column is already mapped
                if canonical_name in self.mapped_canonical_columns:
                    continue

                # Calculate fuzzy similarity score
                similarity = fuzz.ratio(header, canonical_name) / 100.0

                if similarity > best_score and similarity >= min_score:
                    best_score = similarity
                    best_match = canonical_name

            # Add the best match if it meets the threshold
            if best_match and best_score >= min_score:
                # Scale confidence: 0.6-0.99 similarity -> 0.5-0.8 confidence
                confidence = 0.3 + (best_score - min_score) * 0.5 / (1.0 - min_score)
                fuzzy_matches[header] = (best_match, confidence)
                self.mapped_canonical_columns.add(best_match)

        return fuzzy_matches

    def get_bedrock_matches(
        self,
        normalized_headers: List[str],
        uploaded_df: pd.DataFrame,
        already_mapped_headers: set,
    ) -> Dict[str, Tuple[str, float]]:
        """
        Use AWS Bedrock LLM to match remaining headers to canonical columns.
        Only processes headers that haven't been mapped yet.
        """
        if not self.use_bedrock:
            return {}

        bedrock_matches = {}

        # Get remaining unmapped canonical columns
        available_canonical = [
            col
            for col in self.canonical_columns.keys()
            if col not in self.mapped_canonical_columns
        ]

        if not available_canonical:
            return {}

        # Get original headers for sample values
        original_headers = list(uploaded_df.columns)
        header_map = dict(zip(normalized_headers, original_headers))

        # Process only unmapped headers
        unmapped_headers = [
            header
            for header in normalized_headers
            if header not in already_mapped_headers
        ]

        if not unmapped_headers:
            return {}

        # Query Bedrock for batch mapping using BedrockAgent
        suggested_mappings = self.bedrock_agent.map_headers_batch(
            unmapped_headers, available_canonical, uploaded_df, header_map
        )

        for header, canonical_col in suggested_mappings.items():
            if canonical_col and canonical_col not in self.mapped_canonical_columns:
                # Confidence range 0.7-0.85 for AI suggestions
                confidence = 0.8
                bedrock_matches[header] = (canonical_col, confidence)
                self.mapped_canonical_columns.add(canonical_col)

        return bedrock_matches

    def map_headers(self, uploaded_df: pd.DataFrame) -> List[Dict]:
        """
        Map uploaded DataFrame headers to canonical columns.
        Returns list of mapping results with confidence scores.
        """
        if uploaded_df is None or uploaded_df.empty:
            return []

        # Reset mapped columns for each mapping operation
        self.mapped_canonical_columns = set()

        uploaded_headers = list(uploaded_df.columns)
        normalized_headers = [
            self.normalize_header(header) for header in uploaded_headers
        ]
        mapping_results = []

        # Step 1: Find exact matches (confidence 1.0)
        exact_matches = self.get_exact_matches(normalized_headers)

        # Step 2: Find abbreviation matches (confidence 0.9)
        abbreviation_matches = self.get_common_abbreviation_matches(normalized_headers)

        # Step 3: Find fuzzy matches for remaining headers (confidence 0.5-0.8)
        fuzzy_matches = self.get_fuzzy_matches(normalized_headers)

        # Step 4: Use Bedrock LLM for remaining headers (confidence 0.8)
        already_mapped_headers = (
            set(exact_matches.keys())
            | set(abbreviation_matches.keys())
            | set(fuzzy_matches.keys())
        )
        bedrock_matches = self.get_bedrock_matches(
            normalized_headers, uploaded_df, already_mapped_headers
        )

        # Define the match sources in priority order
        match_sources = [
            (exact_matches, MatchMethod.EXACT),
            (abbreviation_matches, MatchMethod.ABBREVIATION),
            (fuzzy_matches, MatchMethod.FUZZY),
            (bedrock_matches, MatchMethod.BEDROCK),
        ]

        # Process all headers and create results
        for i, header in enumerate(uploaded_headers):
            normalized_header = normalized_headers[i]
            result = {
                "original_header": header,
                "normalized_header": normalized_header,
                "suggested_canonical": None,
                "confidence": 0.0,
                "mapping_method": MatchMethod.NO_MATCH,
                "sample_values": self._get_sample_values(uploaded_df, header, 3),
            }

            # Check matches in order
            for match_dict, method in match_sources:
                if normalized_header in match_dict:
                    canonical_column, confidence = match_dict[normalized_header]
                    result.update(
                        {
                            "suggested_canonical": canonical_column,
                            "confidence": confidence,
                            "mapping_method": method,
                        }
                    )
                    break  # stop at the first match

            mapping_results.append(result)

        return mapping_results

    def _get_sample_values(
        self, df: pd.DataFrame, column: str, n: int = 3
    ) -> List[str]:
        """Get sample values from a column for display purposes."""
        if column not in df.columns:
            return []

        sample_values = []
        for value in df[column].dropna().head(n):
            sample_values.append(str(value))

        return sample_values

    def get_mapping_summary(self, mapping_results: List[Dict]) -> Dict:
        """Compute summary statistics of mapping results."""
        total_columns = len(mapping_results)

        # Count occurrences of mapping methods
        counts = Counter(
            r.get("mapping_method", MatchMethod.NO_MATCH) for r in mapping_results
        )

        # Map keys to friendly names for consistency
        summary = {
            "total_columns": total_columns,
            SummaryKey.EXACT_MATCHES: counts.get(MatchMethod.EXACT, 0),
            SummaryKey.ABBREVIATION_MATCHES: counts.get(MatchMethod.ABBREVIATION, 0),
            SummaryKey.FUZZY_MATCHES: counts.get(MatchMethod.FUZZY, 0),
            SummaryKey.BEDROCK_MATCHES: counts.get(MatchMethod.BEDROCK, 0),
            SummaryKey.NO_MATCHES: counts.get(MatchMethod.NO_MATCH, 0),
        }

        # Derived metrics
        mapped_columns = (
            summary[SummaryKey.EXACT_MATCHES]
            + summary[SummaryKey.ABBREVIATION_MATCHES]
            + summary[SummaryKey.FUZZY_MATCHES]
            + summary[SummaryKey.BEDROCK_MATCHES]
        )

        summary["mapped_columns"] = mapped_columns
        summary["mapping_percentage"] = (
            (mapped_columns / total_columns * 100) if total_columns > 0 else 0
        )

        return summary
