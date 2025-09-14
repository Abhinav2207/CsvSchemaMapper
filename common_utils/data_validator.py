"""
Data Validator and Cleaner Module

Handles the validation of data against the canonical schema rules
and provides suggestions for fixing common issues.
"""

from datetime import datetime
import re
from typing import Any, Dict, List, Optional, Union

import pandas as pd

from modules.schema_loader import SchemaLoader, get_schema_loader


class DataValidator:
    """
    Validates a DataFrame against a canonical schema and provides fix suggestions.
    """

    def __init__(self, schema_loader: SchemaLoader = get_schema_loader()):
        self.schema_loader = schema_loader
        self.currency_symbol_map = {
            "$": "USD",
            "€": "EUR",
            "£": "GBP",
            "¥": "JPY",
            "₹": "INR",
            "₱": "PHP",
            "₦": "NGN",
            "₩": "KRW",
            "₡": "CRC",
            "₵": "GHS",
            "Rs": "INR",
            "Rs.": "INR",
        }

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
                continue  # Skip validation if column is not in the dataframe (unmapped column)

            validators = col_def.get("validators", [])
            column_series = df[col_name]
            col_type = col_def.get("type")

            # 1. Non-empty validation
            if "non_empty" in validators:
                errors.extend(self._validate_non_empty(column_series, col_name))

            # 2. Regex validation
            regex_validator = next(
                (v for v in validators if v.startswith("regex:")), None
            )
            if regex_validator:
                pattern = regex_validator.split("regex:", 1)[1]
                errors.extend(
                    self._validate_regex(column_series, col_name, pattern, col_type)
                )

            # 3. Range validation (for numeric fields)
            range_validator = next(
                (v for v in validators if v.startswith("range:")), None
            )
            if range_validator:
                range_params = range_validator.split("range:", 1)[1]
                errors.extend(
                    self._validate_range(column_series, col_name, range_params)
                )

            # 4. Data Type validation
            if col_type == "numeric":
                errors.extend(self._validate_type_numeric(column_series, col_name))
            elif col_type == "date":
                date_formats = col_def.get("formats", [])
                errors.extend(
                    self._validate_type_date(column_series, col_name, date_formats)
                )

        return errors

    def _validate_non_empty(self, column: pd.Series, col_name: str) -> List[Dict]:
        """Check for null or empty string values."""
        error_list = []
        # Check for NaN, None, or empty strings
        empty_mask = column.isnull() | (column.astype(str).str.strip() == "")
        for index in column[empty_mask].index:
            original_value = column.at[index]
            suggested_fix = self._suggest_fix_for_missing(original_value)
            error_list.append(
                {
                    "row": index,
                    "column": col_name,
                    "value": original_value,
                    "error_type": "Missing Value",
                    "message": f"Column '{col_name}' cannot be empty.",
                    "suggested_fix": suggested_fix,
                    "fix_type": "missing_value",
                }
            )
        return error_list

    def _validate_regex(
        self, column: pd.Series, col_name: str, pattern: str, col_type: str = None
    ) -> List[Dict]:
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
                original_value = column.at[index]
                suggested_fix = self._suggest_fix_for_regex(
                    original_value, col_name, pattern, col_type
                )
                error_list.append(
                    {
                        "row": index,
                        "column": col_name,
                        "value": original_value,
                        "error_type": "Invalid Format",
                        "message": f"Value in '{col_name}' does not match the required pattern.",
                        "suggested_fix": suggested_fix,
                        "fix_type": f"regex_{col_name}",
                    }
                )
        except re.error as e:
            # Handle cases where the regex pattern itself is invalid
            print(f"Warning: Invalid regex for column '{col_name}': {e}")
        return error_list

    def _validate_range(
        self, column: pd.Series, col_name: str, range_params: str
    ) -> List[Dict]:
        """Check if numeric values fall within the specified range."""
        error_list = []
        # Drop nulls before range validation
        valid_series = column.dropna()
        if valid_series.empty:
            return []

        try:
            # Parse range parameters (format: "min,max")
            min_val, max_val = map(float, range_params.split(","))
        except ValueError:
            print(
                f"Warning: Invalid range format for column '{col_name}': {range_params}"
            )
            return []

        # First clean and convert to numeric (similar to numeric validation)
        cleaned_series = valid_series.astype(str).str.strip()
        cleaned_series = cleaned_series.str.replace(r"[$,£€¥%]", "", regex=True)
        numeric_series = pd.to_numeric(cleaned_series, errors="coerce")

        # Check for values outside the range (only for successfully converted numeric values)
        valid_numeric_mask = ~numeric_series.isnull()
        valid_numeric_series = numeric_series[valid_numeric_mask]

        # Find values outside the specified range
        out_of_range_mask = (valid_numeric_series < min_val) | (
            valid_numeric_series > max_val
        )

        for index in valid_numeric_series[out_of_range_mask].index:
            original_value = column.at[index]
            suggested_fix = self._suggest_fix_for_range(
                original_value, col_name, min_val, max_val
            )
            error_list.append(
                {
                    "row": index,
                    "column": col_name,
                    "value": original_value,
                    "error_type": "Out of Range",
                    "message": f"Value '{original_value}' in '{col_name}' must be between {min_val} and {max_val}.",
                    "suggested_fix": suggested_fix,
                    "fix_type": f"range_{col_name}",
                }
            )

        return error_list

    def _validate_type_numeric(self, column: pd.Series, col_name: str) -> List[Dict]:
        """Check if values can be converted to a numeric type (integer or float)."""
        error_list = []
        numeric_series = pd.to_numeric(column, errors="coerce")
        # Find indices where conversion resulted in NaN (i.e., failed)
        mask = numeric_series.isnull()
        for index in column[mask].index:
            original_value = column.at[index]
            if pd.isnull(
                original_value
            ):  # Skip null values - they're handled by non_empty validator
                continue
            suggested_fix = self._suggest_fix_for_numeric(original_value, col_name)
            error_list.append(
                {
                    "row": index,
                    "column": col_name,
                    "value": original_value,
                    "error_type": "Incorrect Type",
                    "message": f"Value '{original_value}' in '{col_name}' must be a number (integer or float).",
                    "suggested_fix": suggested_fix,
                    "fix_type": f"numeric_{col_name}",
                }
            )
        return error_list

    def _validate_type_date(
        self, column: pd.Series, col_name: str, formats: List[str]
    ) -> List[Dict]:
        """Check if values can be parsed as a date and are in YYYY-MM-DD format."""
        error_list = []
        # Drop nulls before date parsing
        valid_series = column.dropna()
        if valid_series.empty:
            return []

        for index, value in valid_series.items():
            str_value = str(value).strip()

            # First check if it's already in correct YYYY-MM-DD format
            if self._is_correct_date_format(str_value):
                continue  # This date is already in the correct format

            # Try to parse the date to see if it's valid
            try:
                # Try to parse with pandas (very flexible)
                parsed_date = pd.to_datetime(value, format="mixed")
                # If we can parse it, suggest converting to YYYY-MM-DD format
                suggested_fix = parsed_date.strftime("%Y-%m-%d")
                error_list.append(
                    {
                        "row": index,
                        "column": col_name,
                        "value": value,
                        "error_type": "Incorrect Format",
                        "message": f"Date in '{col_name}' should be in YYYY-MM-DD format.",
                        "suggested_fix": suggested_fix,
                        "fix_type": "date_format",
                    }
                )
            except (ValueError, TypeError):
                # If we can't parse it at all, try our custom parser
                suggested_fix = self._suggest_fix_for_date(value, formats)
                error_list.append(
                    {
                        "row": index,
                        "column": col_name,
                        "value": value,
                        "error_type": "Incorrect Type",
                        "message": f"Value in '{col_name}' is not a valid date.",
                        "suggested_fix": suggested_fix,
                        "fix_type": "date",
                    }
                )
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
            col
            for col, props in self.schema_loader.get_canonical_columns().items()
            if "non_empty" in props.get("validators", []) and col in df.columns
        ]

        if not required_cols:
            return {
                "total_rows": len(df),
                "rows_with_missing_data": 0,
                "missing_percentage": 0.0,
            }

        missing_mask = df[required_cols].isnull().any(axis=1)
        rows_with_missing = missing_mask.sum()
        total_rows = len(df)
        missing_percentage = (
            (rows_with_missing / total_rows * 100) if total_rows > 0 else 0
        )

        return {
            "total_rows": total_rows,
            "rows_with_missing_data": rows_with_missing,
            "missing_percentage": missing_percentage,
        }

    # ====== FIX SUGGESTION METHODS ======

    def _suggest_fix_for_missing(self, value: Any) -> Optional[str]:
        """Suggest fix for missing values."""
        return None  # Missing values can't be auto-fixed

    def _suggest_fix_for_regex(
        self, value: Any, col_name: str, pattern: str, col_type: str = None
    ) -> Optional[str]:
        """Suggest fix for regex validation failures."""
        if pd.isnull(value):
            return None

        str_value = str(value).strip()

        # Email specific fixes
        if col_name == "email":
            # Remove all spaces from email
            fixed_value = str_value.replace(" ", "")
            if self._test_fix_regex(fixed_value, pattern):
                return fixed_value

        # Currency specific fixes
        elif col_name == "currency":
            # Convert to uppercase
            fixed_value = str_value.upper()
            if self._test_fix_regex(fixed_value, pattern):
                return fixed_value

            # Try mapping currency symbols to codes
            for symbol, code in self.currency_symbol_map.items():
                if symbol in str_value:
                    fixed_value = str_value.replace(symbol, code).strip().upper()
                    if self._test_fix_regex(fixed_value, pattern):
                        return fixed_value

        # General fix: strip whitespace
        if self._test_fix_regex(str_value, pattern):
            return str_value

        return None

    def _suggest_fix_for_range(
        self, value: Any, col_name: str, min_val: float, max_val: float
    ) -> Optional[str]:
        """Suggest fix for range validation failures."""
        if pd.isnull(value):
            return None

        str_value = str(value).strip()

        # For percentage fields, convert percentage to decimal
        if col_name in ["discount_pct", "tax_pct"] and "%" in str_value:
            try:
                # Remove % and convert to decimal
                numeric_part = str_value.replace("%", "").strip()
                numeric_value = float(numeric_part) / 100
                if min_val <= numeric_value <= max_val:
                    return str(numeric_value)
            except ValueError:
                pass

        return None

    def _suggest_fix_for_numeric(self, value: Any, col_name: str) -> Optional[str]:
        """Suggest fix for numeric type validation failures."""
        if pd.isnull(value):
            return None

        str_value = str(value).strip()

        # Remove common currency symbols and separators
        cleaned = re.sub(r"[$,£€¥₹%]", "", str_value)

        # For percentage fields, handle % symbol
        if col_name in ["discount_pct", "tax_pct"] and "%" in str_value:
            try:
                numeric_part = str_value.replace("%", "").strip()
                numeric_value = float(numeric_part) / 100
                return str(numeric_value)
            except ValueError:
                pass

        # Try converting cleaned value
        try:
            float(cleaned)
            return cleaned
        except ValueError:
            return None

    def _suggest_fix_for_date(self, value: Any, formats: List[str]) -> Optional[str]:
        """Suggest fix for date validation failures."""
        if pd.isnull(value):
            return None

        str_value = str(value).strip()

        # First try pandas flexible parser
        try:
            parsed_date = pd.to_datetime(str_value, format="mixed")
            return parsed_date.strftime("%Y-%m-%d")
        except:
            pass

        # Try parsing with different specific formats and convert to YYYY-MM-DD
        date_formats_to_try = [
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%d-%m-%Y",
            "%Y/%m/%d",
            "%d/%m/%Y",
            "%m-%d-%Y",
            "%Y%m%d",
            "%d.%m.%Y",
            "%m.%d.%Y",
            "%b %d, %Y",  # Sep 17, 2025
            "%B %d, %Y",  # September 17, 2025
            "%d %b %Y",  # 17 Sep 2025
            "%d %B %Y",  # 17 September 2025
            "%Y-%m-%d %H:%M:%S",  # With time
            "%m/%d/%Y %H:%M:%S",  # With time
        ]

        for fmt in date_formats_to_try:
            try:
                parsed_date = datetime.strptime(str_value, fmt)
                return parsed_date.strftime("%Y-%m-%d")
            except ValueError:
                continue

        return None

    def _test_fix_regex(self, fixed_value: str, pattern: str) -> bool:
        """Test if a fixed value passes regex validation."""
        try:
            return bool(re.match(pattern, fixed_value))
        except re.error:
            return False

    def _is_correct_date_format(self, date_str: str) -> bool:
        """Check if date string is already in correct YYYY-MM-DD format."""
        try:
            # Check if it matches the exact YYYY-MM-DD pattern
            if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
                # Also verify it's a valid date
                datetime.strptime(date_str, "%Y-%m-%d")
                return True
            return False
        except (ValueError, TypeError):
            return False

    # ====== FIX APPLICATION METHODS ======

    def validate_and_suggest_fixes(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Run validation and group errors with suggested fixes.

        Returns:
            Dictionary with validation results and grouped fix suggestions
        """
        errors = self.validate_dataframe(df)

        # Group errors by fix type and suggested fix
        grouped_fixes = {}
        remaining_errors = []

        for error in errors:
            fix_type = error.get("fix_type", "unknown")
            suggested_fix = error.get("suggested_fix")

            if suggested_fix is not None:
                # Create a grouping key based on fix type, column, and suggested fix pattern
                group_key = f"{fix_type}_{error['column']}_{self._get_fix_pattern(suggested_fix, error['value'])}"

                if group_key not in grouped_fixes:
                    grouped_fixes[group_key] = {
                        "fix_type": fix_type,
                        "column": error["column"],
                        "error_type": error["error_type"],
                        "description": self._get_fix_description(error, suggested_fix),
                        "errors": [],
                    }

                grouped_fixes[group_key]["errors"].append(error)
            else:
                remaining_errors.append(error)

        return {
            "grouped_fixes": list(grouped_fixes.values()),
            "remaining_errors": remaining_errors,
            "total_errors": len(errors),
            "fixable_errors": len(errors) - len(remaining_errors),
        }

    def apply_fixes(self, df: pd.DataFrame, fixes_to_apply: List[Dict]) -> pd.DataFrame:
        """
        Apply selected fixes to the dataframe.

        Args:
            df: DataFrame to apply fixes to
            fixes_to_apply: List of fix dictionaries with row, column, and new_value

        Returns:
            Updated DataFrame
        """
        df_copy = df.copy()

        for fix in fixes_to_apply:
            row_idx = fix["row"]
            column = fix["column"]
            new_value = fix["new_value"]

            df_copy.at[row_idx, column] = new_value

        return df_copy

    def _get_fix_pattern(self, suggested_fix: str, original_value: Any) -> str:
        """Get a pattern description for grouping similar fixes."""
        if pd.isnull(original_value):
            return "null_to_value"

        original_str = str(original_value)

        # Check if this is a date format conversion
        try:
            # If suggested fix matches YYYY-MM-DD pattern and original doesn't
            if re.match(r"^\d{4}-\d{2}-\d{2}$", suggested_fix) and not re.match(
                r"^\d{4}-\d{2}-\d{2}$", original_str.strip()
            ):
                return "date_to_iso_format"
        except:
            pass

        if suggested_fix == original_str.strip():
            return "trim_whitespace"
        elif "%" in original_str and suggested_fix == str(
            float(original_str.replace("%", "")) / 100
        ):
            return "percentage_to_decimal"
        elif suggested_fix == original_str.replace(" ", ""):
            return "remove_spaces"
        elif suggested_fix == original_str.upper():
            return "to_uppercase"
        else:
            return "custom_transformation"

    def _get_fix_description(self, error: Dict, suggested_fix: str) -> str:
        """Generate a human-readable description of the fix."""
        original_value = (
            str(error["value"]) if not pd.isnull(error["value"]) else "null"
        )
        pattern = self._get_fix_pattern(suggested_fix, error["value"])

        pattern_descriptions = {
            "trim_whitespace": "Remove leading/trailing whitespace",
            "percentage_to_decimal": "Convert percentage to decimal (divide by 100)",
            "remove_spaces": "Remove all spaces",
            "to_uppercase": "Convert to uppercase",
            "date_to_iso_format": "Convert date to YYYY-MM-DD format",
            "custom_transformation": f'Transform "{original_value}" to "{suggested_fix}"',
        }

        return pattern_descriptions.get(
            pattern, f'Apply suggested fix: "{suggested_fix}"'
        )

    def generate_quality_summary(
        self,
        initial_errors: List[Dict],
        final_errors: List[Dict],
        applied_fixes: List[Dict],
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive data quality summary for the review page.

        Args:
            initial_errors: Errors found during initial validation
            final_errors: Errors remaining after fixes
            applied_fixes: List of fixes that were applied

        Returns:
            Dictionary with quality summary statistics
        """
        summary = {
            "total_initial_errors": len(initial_errors),
            "total_final_errors": len(final_errors),
            "total_fixes_applied": len(applied_fixes),
            "improvement_percentage": 0.0,
            "error_breakdown": {},
            "fix_breakdown": {},
            "column_summary": {},
        }

        if len(initial_errors) > 0:
            summary["improvement_percentage"] = (
                (len(initial_errors) - len(final_errors)) / len(initial_errors)
            ) * 100

        # Breakdown by error type and column
        for error in initial_errors:
            error_type = error.get("error_type", "Unknown")
            column = error.get("column", "Unknown")

            # Error type breakdown
            if error_type not in summary["error_breakdown"]:
                summary["error_breakdown"][error_type] = {
                    "total_found": 0,
                    "fixed": 0,
                    "remaining": 0,
                    "columns_affected": set(),
                }

            summary["error_breakdown"][error_type]["total_found"] += 1
            summary["error_breakdown"][error_type]["columns_affected"].add(column)

            # Column summary
            if column not in summary["column_summary"]:
                summary["column_summary"][column] = {
                    "total_errors": 0,
                    "errors_fixed": 0,
                    "errors_remaining": 0,
                    "error_types": set(),
                }

            summary["column_summary"][column]["total_errors"] += 1
            summary["column_summary"][column]["error_types"].add(error_type)

        # Count fixes applied
        applied_fixes_by_column = {}

        for fix in applied_fixes:
            column = fix.get("column", "Unknown")
            applied_fixes_by_column[column] = applied_fixes_by_column.get(column, 0) + 1

        # Count remaining errors
        for error in final_errors:
            error_type = error.get("error_type", "Unknown")
            column = error.get("column", "Unknown")

            if error_type in summary["error_breakdown"]:
                summary["error_breakdown"][error_type]["remaining"] += 1

            if column in summary["column_summary"]:
                summary["column_summary"][column]["errors_remaining"] += 1

        # Calculate fixed counts
        for error_type in summary["error_breakdown"]:
            total = summary["error_breakdown"][error_type]["total_found"]
            remaining = summary["error_breakdown"][error_type]["remaining"]
            summary["error_breakdown"][error_type]["fixed"] = total - remaining

            # Convert set to list for JSON serialization
            summary["error_breakdown"][error_type]["columns_affected"] = list(
                summary["error_breakdown"][error_type]["columns_affected"]
            )

        for column in summary["column_summary"]:
            total = summary["column_summary"][column]["total_errors"]
            remaining = summary["column_summary"][column]["errors_remaining"]
            summary["column_summary"][column]["errors_fixed"] = total - remaining

            # Convert set to list for JSON serialization
            summary["column_summary"][column]["error_types"] = list(
                summary["column_summary"][column]["error_types"]
            )

        # Fix type breakdown (by fix pattern and type)
        fix_patterns = {}
        ai_fixes_count = 0

        for fix in applied_fixes:
            fix_type = fix.get("fix_type", "deterministic")
            column = fix.get("column", "Unknown")

            # Count AI fixes separately
            if fix_type == "ai_fix":
                ai_fixes_count += 1

            # Group by column and type
            fix_key = f"{column} ({fix_type.replace('_', ' ').title()})"
            fix_patterns[fix_key] = fix_patterns.get(fix_key, 0) + 1

        summary["fix_breakdown"] = fix_patterns
        summary["ai_fixes_applied"] = ai_fixes_count
        summary["deterministic_fixes_applied"] = len(applied_fixes) - ai_fixes_count

        return summary
