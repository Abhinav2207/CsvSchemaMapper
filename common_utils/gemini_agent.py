import json
from typing import Dict, List, Optional

import google.generativeai as genai
import pandas as pd
import streamlit as st
from rapidfuzz import fuzz

from common_utils.constants import CONSTANTS
from modules.schema_loader import get_schema_loader


class GeminiAgent:
    def __init__(self, use_gemini: bool = CONSTANTS.USE_GEMINI):
        self.use_gemini = use_gemini
        self.gemini_model = None

        if self.use_gemini:
            try:
                # Configure Gemini API
                genai.configure(api_key=CONSTANTS.GEMINI_API_KEY)
                self.gemini_model = genai.GenerativeModel(CONSTANTS.GEMINI_MODEL)
            except Exception as e:
                print(f"Failed to initialize Gemini client: {e}")
                self.use_gemini = False

    def map_headers_batch(
        self,
        headers: List[str],
        canonical_columns: List[str],
        df: pd.DataFrame,
        header_map: Dict[str, str],
    ) -> Dict[str, Optional[str]]:
        """
        Query Gemini to map multiple headers at once.

        Args:
            headers: List of normalized headers to map
            canonical_columns: List of available canonical column names
            df: DataFrame for getting sample values
            header_map: Mapping from normalized headers to original headers

        Returns:
            Dictionary mapping headers to canonical columns (or None)
        """
        if not self.use_gemini or not self.gemini_model:
            return {}

        try:
            # Prepare header info with sample values
            header_info = []
            for norm_header in headers:
                orig_header = header_map.get(norm_header, norm_header)
                sample_values = self._get_sample_values(df, orig_header, 3)
                header_info.append(f"'{norm_header}' (samples: {sample_values})")

            # Create the prompt
            prompt = f"""You are a data mapping expert. Map these CSV headers to the most appropriate canonical fields.

Headers to map:
{chr(10).join([f"{i+1}. {info}" for i, info in enumerate(header_info)])}

Available canonical fields:
{', '.join(canonical_columns)}

Rules:
- Each header should map to exactly ONE canonical field
- Each canonical field can only be used ONCE
- If no good match exists, respond with "NONE"
- Consider semantic meaning, data types, and common business terminology

Respond in JSON format like:
{{"header1": "canonical_field1", "header2": "canonical_field2", "header3": "NONE"}}

Only return the JSON, no other text."""

            # Generate response using Gemini
            response = self.gemini_model.generate_content(prompt)
            response_text = response.text.strip()

            # Increment Gemini calls counter
            if "gemini_calls_count" in st.session_state:
                st.session_state.gemini_calls_count += 1

            # Parse JSON response
            try:
                mappings = json.loads(response_text)
                # Validate mappings
                validated_mappings = {}
                for header, canonical in mappings.items():
                    if canonical == "NONE":
                        validated_mappings[header] = None
                    elif canonical in canonical_columns:
                        validated_mappings[header] = canonical
                    else:
                        # Try fuzzy match for AI suggestions
                        best_match = None
                        best_score = 0
                        for col in canonical_columns:
                            score = fuzz.ratio(canonical.lower(), col.lower()) / 100.0
                            if score > best_score and score > 0.7:
                                best_score = score
                                best_match = col
                        validated_mappings[header] = best_match

                return validated_mappings

            except json.JSONDecodeError:
                # Fallback: try to extract mappings from text
                return self._parse_text_response(
                    response_text, headers, canonical_columns
                )

        except Exception as e:
            print(f"Gemini batch query failed: {e}")
            return {}

    def _parse_text_response(
        self, text: str, headers: List[str], canonical_columns: List[str]
    ) -> Dict[str, Optional[str]]:
        """Fallback parser for non-JSON responses."""
        mappings = {}
        for header in headers:
            mappings[header] = None
            for line in text.split("\n"):
                if header.lower() in line.lower():
                    for col in canonical_columns:
                        if col.lower() in line.lower():
                            mappings[header] = col
                            break
        return mappings

    def suggest_data_fix(self, error: Dict, df: pd.DataFrame) -> Optional[str]:
        """
        Query Gemini to suggest a fix for a single data validation error.

        Args:
            error: The error dictionary from the DataValidator.
            df: The full DataFrame for context.

        Returns:
            A string suggestion for the fix, or None if it fails.
        """
        if not self.use_gemini or not self.gemini_model:
            return None

        col_name = error["column"]
        invalid_value = error["value"]
        error_type = error["error_type"]

        # Get column definition for context
        schema_loader = get_schema_loader()
        col_def = schema_loader.get_column_definition(col_name)
        if not col_def:
            return None

        # Get some valid samples from the same column
        valid_samples = df[col_name].dropna().head(5).tolist()

        prompt = f"""You are an expert data cleaner. A data validation process found an error. Your task is to suggest a single, most likely correction for the invalid value.

Error Details:
- Column: "{col_name}" (Expected Type: {col_def.get('type', 'N/A')})
- Invalid Value: "{invalid_value}"
- Error Type: "{error_type}"
- Validation Rule: "{error.get('message', 'N/A')}"

Context from the dataset:
- Here are some other valid values from the "{col_name}" column: {valid_samples}

Instructions:
- Analyze the invalid value and the error.
- Consider the column type and other valid values for context.
- Provide the most probable corrected value.
- Respond in JSON format like this: {{"suggestion": "your_suggested_fix"}}
- Only return the JSON, no other text or explanation. If you cannot determine a fix, respond with {{"suggestion": null}}.
"""

        try:
            response = self.gemini_model.generate_content(prompt)
            response_text = response.text.strip()

            # Increment Gemini calls counter
            if "gemini_calls_count" in st.session_state:
                st.session_state.gemini_calls_count += 1

            # Parse the JSON response
            suggestion_json = json.loads(response_text)
            return suggestion_json.get("suggestion")

        except Exception as e:
            print(f"Gemini data fix suggestion failed for value '{invalid_value}': {e}")
            return None

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
