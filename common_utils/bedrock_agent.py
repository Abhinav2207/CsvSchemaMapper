import boto3
import json
from typing import Dict, List, Optional
import pandas as pd
from rapidfuzz import fuzz

from common_utils.constants import CONSTANTS


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
