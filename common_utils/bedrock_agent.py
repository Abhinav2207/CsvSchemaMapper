import boto3
import json
from typing import Dict, List, Optional
import pandas as pd
from rapidfuzz import fuzz

from common_utils.constants import CONSTANTS
from modules.schema_loader import get_schema_loader


class BedrockAgent:
    def __init__(self, use_bedrock: bool = CONSTANTS.USE_BEDROCK):
        self.use_bedrock = use_bedrock
        self.bedrock_client = None

        if self.use_bedrock:
            try:
                self.bedrock_client = boto3.client(
                    "bedrock-runtime", region_name=CONSTANTS.BEDROCK_REGION
                )
            except Exception as e:
                print(f"Failed to initialize Bedrock client: {e}")
                self.use_bedrock = False

    def map_headers_batch(
        self,
        headers: List[str],
        canonical_columns: List[str],
        df: pd.DataFrame,
        header_map: Dict[str, str],
    ) -> Dict[str, Optional[str]]:
        """
        Query Bedrock to map multiple headers at once.

        Args:
            headers: List of normalized headers to map
            canonical_columns: List of available canonical column names
            df: DataFrame for getting sample values
            header_map: Mapping from normalized headers to original headers

        Returns:
            Dictionary mapping headers to canonical columns (or None)
        """
        if not self.use_bedrock or not self.bedrock_client:
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

            # Prepare request for Claude on Bedrock
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 500,
                "messages": [{"role": "user", "content": prompt}],
            }

            response = self.bedrock_client.invoke_model(
                modelId=CONSTANTS.BEDROCK_MODEL,
                body=json.dumps(request_body),
            )

            response_body = json.loads(response["body"].read())
            response_text = response_body["content"][0]["text"].strip()

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
            print(f"Bedrock batch query failed: {e}")
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

    def suggest_data_fix(
        self, error: Dict, df: pd.DataFrame
    ) -> Optional[str]:
        """
        Query Bedrock to suggest a fix for a single data validation error.

        Args:
            error: The error dictionary from the DataValidator.
            df: The full DataFrame for context.

        Returns:
            A string suggestion for the fix, or None if it fails.
        """
        if not self.use_bedrock or not self.bedrock_client:
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
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 100,
                "messages": [{"role": "user", "content": prompt}],
            }

            response = self.bedrock_client.invoke_model(
                modelId=CONSTANTS.BEDROCK_MODEL,
                body=json.dumps(request_body),
            )

            response_body = json.loads(response["body"].read())
            response_text = response_body["content"][0]["text"].strip()

            # Parse the JSON response
            suggestion_json = json.loads(response_text)
            return suggestion_json.get("suggestion")

        except Exception as e:
            print(f"Bedrock data fix suggestion failed for value '{invalid_value}': {e}")
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

