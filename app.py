"""
Simple Schema Mapper - Streamlit Application

A streamlined tool for CSV header mapping using lemmatization and minimal AI calls.
"""

import streamlit as st

from common_utils.app_utils import initialize_session_state
from steps import (
    step1_upload_csv,
    step2_schema_mapper,
    step3_data_quality_fixer,
    step4_review_results,
)


def main():
    """Main application function."""
    st.set_page_config(page_title="Finkraft", page_icon="💰", layout="wide")

    initialize_session_state()

    # Header
    st.title("📊 Schema Mapper &amp; Data Quality Fixer")
    st.markdown(
        "Automatically map, clean, and validate messy partner CSVs into a single canonical format—reducing manual effort and surfacing only the issues that need attention."
    )

    st.markdown("---")

    uploaded_file = st.file_uploader(
        "Choose a CSV file", type=["csv"], help="Upload a CSV file to analyze"
    )

    if uploaded_file is not None:
        step1_upload_csv(uploaded_file)
        step2_schema_mapper()

        # TODO: Uncomment these when we have the data quality fixer and review results steps
        # step3_data_quality_fixer()
        # step4_review_results()


if __name__ == "__main__":
    main()
