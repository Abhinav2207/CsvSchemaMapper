"""
Schema Loader Module

Handles loading and accessing canonical schema definitions and synonym mappings.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class SchemaLoader:
    """Loads and manages canonical schema and synonym definitions."""

    def __init__(self, schemas_dir: str = "schemas"):
        """
        Initialize the schema loader.

        Args:
            schemas_dir: Directory containing schema files
        """
        self.schemas_dir = Path(schemas_dir)
        self.canonical_schema = None
        # self.synonyms = None
        self._load_schemas()

    def _load_schemas(self) -> None:
        """Load canonical schema and synonyms from JSON files."""
        try:
            # Load canonical schema
            canonical_path = self.schemas_dir / "canonical.json"
            with open(canonical_path, "r", encoding="utf-8") as f:
                self.canonical_schema = json.load(f)

        except FileNotFoundError as e:
            raise FileNotFoundError(f"Schema file not found: {e}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in schema file: {e}")

    def get_canonical_columns(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all canonical column definitions.

        Returns:
            Dictionary of column definitions from canonical schema
        """
        if not self.canonical_schema:
            raise ValueError("Canonical schema not loaded")
        return self.canonical_schema.get("columns", {})

    def get_column_definition(self, column_name: str) -> Optional[Dict[str, Any]]:
        """
        Get definition for a specific canonical column.

        Args:
            column_name: Name of the canonical column

        Returns:
            Column definition dictionary or None if not found
        """
        columns = self.get_canonical_columns()
        return columns.get(column_name)

    def get_validators_for_column(self, column_name: str) -> List[str]:
        """
        Get validators for a canonical column.

        Args:
            column_name: Name of the canonical column

        Returns:
            List of validator names
        """
        column_def = self.get_column_definition(column_name)
        if column_def:
            return column_def.get("validators", [])
        return []

    def get_column_type(self, column_name: str) -> Optional[str]:
        """
        Get the data type for a canonical column.

        Args:
            column_name: Name of the canonical column

        Returns:
            Data type string or None if not found
        """
        column_def = self.get_column_definition(column_name)
        if column_def:
            return column_def.get("type")
        return None

    def get_allowed_values(self, column_name: str) -> Optional[List[str]]:
        """
        Get allowed values for a canonical column.

        Args:
            column_name: Name of the canonical column

        Returns:
            List of allowed values or None if not restricted
        """
        column_def = self.get_column_definition(column_name)
        if column_def:
            return column_def.get("allowed_values")
        return None

    def get_date_formats(self, column_name: str) -> List[str]:
        """
        Get date formats for a canonical date column.

        Args:
            column_name: Name of the canonical column

        Returns:
            List of date format strings
        """
        column_def = self.get_column_definition(column_name)
        if column_def and column_def.get("type") == "date":
            return column_def.get("formats", [])
        return []

    def is_required_column(self, column_name: str) -> bool:
        """
        Check if a column is required (has non_empty validator).

        Args:
            column_name: Name of the canonical column

        Returns:
            True if column is required, False otherwise
        """
        validators = self.get_validators_for_column(column_name)
        return "non_empty" in validators

    def reload_schemas(self) -> None:
        """Reload schema files from disk."""
        self._load_schemas()


# Singleton instance for easy access
_schema_loader = None


def get_schema_loader(schemas_dir: str = "schemas") -> SchemaLoader:
    """
    Get singleton instance of SchemaLoader.

    Args:
        schemas_dir: Directory containing schema files

    Returns:
        SchemaLoader instance
    """
    global _schema_loader
    if _schema_loader is None:
        _schema_loader = SchemaLoader(schemas_dir)
    return _schema_loader
