"""
Data Validator and Cleaner Module

Handles the validation of data against the canonical schema rules
and provides suggestions for fixing common issues.
"""
import pandas as pd
import re
from typing import List, Dict, Any

from modules.schema_loader import SchemaLoader, get_schema_loader


class DataValidator:
    """
    Validates a DataFrame against a canonical schema.
    """

    def __init__(self, schema_loader: SchemaLoader = get_schema_loader()):
        self.schema_loader = schema_loader

    def validate_dataframe(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Orchestrates the validation of the entire DataFrame.

        Args:
            df: The DataFrame to validate.

        Returns:
            A list of dictionaries, where each dict represents a validation error.
        """
        errors = []
        canonical_columns = self.schema_loader.get_canonical_columns()

        for col_name, col_def in canonical_columns.items():
            if col_name not in df.columns:
                continue  # Skip validation if column is not in the dataframe

            validators = col_def.get("validators", [])
            column_series = df[col_name]

            # 1. Non-empty validation
            if "non_empty" in validators:
                errors.extend(self._validate_non_empty(column_series, col_name))

            # 2. Regex validation
            regex_validator = next((v for v in validators if v.startswith("regex:")), None)
            if regex_validator:
                pattern = regex_validator.split("regex:", 1)[1]
                errors.extend(self._validate_regex(column_series, col_name, pattern))

            # 3. Data Type validation
            col_type = col_def.get("type")
            if col_type == "numeric":
                errors.extend(self._validate_type_numeric(column_series, col_name))
            elif col_type == "date":
                date_formats = col_def.get("formats", [])
                errors.extend(self._validate_type_date(column_series, col_name, date_formats))

        return errors

    def _validate_non_empty(self, column: pd.Series, col_name: str) -> List[Dict]:
        """Check for null or empty string values."""
        error_list = []
        # Check for NaN, None, or empty strings
        empty_mask = column.isnull() | (column.astype(str).str.strip() == "")
        for index in column[empty_mask].index:
            error_list.append({
                "row": index,
                "column": col_name,
                "value": column.at[index],
                "error_type": "Missing Value",
                "message": f"Column '{col_name}' cannot be empty."
            })
        return error_list

    def _validate_regex(self, column: pd.Series, col_name: str, pattern: str) -> List[Dict]:
        """Check values against a regex pattern."""
        error_list = []
        # Drop nulls before regex matching
        valid_series = column.dropna()
        if valid_series.empty:
            return []

        try:
            # Ensure series is string type for regex
            mask = ~valid_series.astype(str).str.match(pattern, na=False)
            for index in valid_series[mask].index:
                error_list.append({
                    "row": index,
                    "column": col_name,
                    "value": column.at[index],
                    "error_type": "Invalid Format",
                    "message": f"Value in '{col_name}' does not match the required pattern."
                })
        except re.error as e:
            # Handle cases where the regex pattern itself is invalid
            print(f"Warning: Invalid regex for column '{col_name}': {e}")
        return error_list

    def _validate_type_numeric(self, column: pd.Series, col_name: str) -> List[Dict]:
        """Check if values can be converted to a numeric type."""
        error_list = []
        # Drop nulls before numeric conversion check
        valid_series = column.dropna()
        if valid_series.empty:
            return []

        # Attempt to convert to numeric, coercing errors to NaN
        numeric_series = pd.to_numeric(valid_series, errors='coerce')
        # Find indices where conversion resulted in NaN (i.e., failed)
        mask = numeric_series.isnull()
        for index in valid_series[mask].index:
            error_list.append({
                "row": index,
                "column": col_name,
                "value": column.at[index],
                "error_type": "Incorrect Type",
                "message": f"Value in '{col_name}' must be a number."
            })
        return error_list

    def _validate_type_date(self, column: pd.Series, col_name: str, formats: List[str]) -> List[Dict]:
        """Check if values can be parsed as a date with given formats."""
        error_list = []
        # Drop nulls before date parsing
        valid_series = column.dropna()
        if valid_series.empty:
            return []

        # If formats are provided, try them. Otherwise, let pandas infer.
        for index, value in valid_series.items():
            try:
                # Attempt to parse the date. If formats are specified, pandas requires trying one by one.
                # If no formats, pd.to_datetime is very flexible.
                pd.to_datetime(value, format=None if not formats else 'mixed')
            except (ValueError, TypeError):
                error_list.append({
                    "row": index,
                    "column": col_name,
                    "value": value,
                    "error_type": "Incorrect Type",
                    "message": f"Value in '{col_name}' is not a valid date."
                })
        return error_list

    def get_missing_data_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculates statistics on missing data for required columns.

        Args:
            df: The DataFrame to analyze.

        Returns:
            A dictionary with summary statistics.
        """
        required_cols = [
            col for col,
            props in self.schema_loader.get_canonical_columns().items()
            if "non_empty" in props.get("validators", []) and col in df.columns
        ]

        if not required_cols:
            return {"total_rows": len(df), "rows_with_missing_data": 0, "missing_percentage": 0.0}

        missing_mask = df[required_cols].isnull().any(axis=1)
        rows_with_missing = missing_mask.sum()
        total_rows = len(df)
        missing_percentage = (rows_with_missing / total_rows * 100) if total_rows > 0 else 0

        return {
            "total_rows": total_rows,
            "rows_with_missing_data": rows_with_missing,
            "missing_percentage": missing_percentage
        }
