"""
Utility module to manage learned mappings from user interactions.

This module handles storing and retrieving mappings that users have made
through Manual overrides or AI (Gemini) suggestions to improve future
mapping accuracy.
"""

import json
import os
import re
from typing import Dict, List, Optional


class LearnedMappingsManager:
    """Manages learned mappings storage and retrieval."""

    def __init__(self, mappings_file: str = "schemas/learned_mappings.json"):
        """
        Initialize the learned mappings manager.

        Args:
            mappings_file: Path to the learned mappings JSON file
        """
        self.mappings_file = mappings_file
        self._ensure_mappings_file_exists()

    def _ensure_mappings_file_exists(self):
        """Create the learned mappings file if it doesn't exist."""
        if not os.path.exists(self.mappings_file):
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.mappings_file), exist_ok=True)

            # Create initial structure
            initial_structure = {
                "version": "1.0",
                "description": "Learned mappings from user interactions (Manual and AI matches)",
                "mappings": {},
            }

            with open(self.mappings_file, "w", encoding="utf-8") as f:
                json.dump(initial_structure, f, indent=2, ensure_ascii=False)

    def _normalize_header(self, header: str) -> str:
        """
        Normalize header name for consistent storage.

        Args:
            header: Original header name

        Returns:
            Normalized header name (lowercase, underscores, no special chars)
        """
        # Convert to lowercase
        normalized = header.lower().strip()

        # Replace common separators with underscores
        normalized = re.sub(r"[/\-\s]+", "_", normalized)

        # Remove special characters except underscores
        normalized = re.sub(r"[^a-z0-9_]", "", normalized)

        # Remove multiple underscores
        normalized = re.sub(r"_+", "_", normalized)

        # Remove leading/trailing underscores
        normalized = normalized.strip("_")

        return normalized

    def load_learned_mappings(self) -> Dict:
        """
        Load learned mappings from JSON file.

        Returns:
            Dictionary containing learned mappings
        """
        try:
            with open(self.mappings_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("mappings", {})
        except (FileNotFoundError, json.JSONDecodeError):
            # Return empty mappings if file doesn't exist or is corrupted
            return {}

    def save_learned_mapping(
        self,
        original_header: str,
        canonical_field: str,
        mapping_method: str,
        confidence: float,
    ):
        """
        Save a new learned mapping.

        Args:
            original_header: The original CSV header
            canonical_field: The canonical field it was mapped to
            mapping_method: How it was mapped (Manual Match, AI (Gemini), etc.)
            confidence: Confidence score of the mapping
        """
        # Only save Manual and AI mappings
        if mapping_method not in ["Manual Match", "AI (Gemini)"]:
            return

        # Load current mappings
        current_data = self._load_full_data()
        mappings = current_data.get("mappings", {})

        # Normalize the original header
        normalized_header = self._normalize_header(original_header)

        # Initialize canonical field if not exists
        if canonical_field not in mappings:
            mappings[canonical_field] = []

        # Check if this normalized header is already stored
        if normalized_header not in mappings[canonical_field]:
            mappings[canonical_field].append(normalized_header)

            # Update the data structure
            current_data["mappings"] = mappings

            # Save back to file
            with open(self.mappings_file, "w", encoding="utf-8") as f:
                json.dump(current_data, f, indent=2, ensure_ascii=False)

    def save_batch_learned_mappings(self, learned_mappings: List[Dict]):
        """
        Save multiple learned mappings at once.

        Args:
            learned_mappings: List of dictionaries with keys:
                - original_header: str
                - canonical_field: str
                - mapping_method: str
                - confidence: float
        """
        for mapping in learned_mappings:
            self.save_learned_mapping(
                mapping["original_header"],
                mapping["canonical_field"],
                mapping["mapping_method"],
                mapping["confidence"],
            )

    def _load_full_data(self) -> Dict:
        """Load the complete learned mappings data structure."""
        try:
            with open(self.mappings_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {
                "version": "1.0",
                "description": "Learned mappings from user interactions (Manual and AI matches)",
                "mappings": {},
            }

    def get_learned_abbreviations_for_field(self, canonical_field: str) -> List[str]:
        """
        Get learned abbreviations for a specific canonical field.

        Args:
            canonical_field: The canonical field name

        Returns:
            List of learned abbreviations/variations
        """
        mappings = self.load_learned_mappings()
        return mappings.get(canonical_field, [])

    def find_canonical_by_learned_mapping(self, header: str) -> Optional[str]:
        """
        Find canonical field by checking learned mappings.

        Args:
            header: Original header to check

        Returns:
            Canonical field name if found, None otherwise
        """
        normalized_header = self._normalize_header(header)
        mappings = self.load_learned_mappings()

        for canonical_field, learned_headers in mappings.items():
            if normalized_header in learned_headers:
                return canonical_field

        return None

    def get_stats(self) -> Dict:
        """
        Get statistics about learned mappings.

        Returns:
            Dictionary with statistics
        """
        mappings = self.load_learned_mappings()

        total_fields = len(mappings)
        total_learned_headers = sum(len(headers) for headers in mappings.values())

        return {
            "total_canonical_fields_with_learned_mappings": total_fields,
            "total_learned_header_variations": total_learned_headers,
            "fields_with_learned_mappings": list(mappings.keys()),
        }
