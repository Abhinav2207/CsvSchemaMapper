from datetime import datetime

import pandas as pd
import streamlit as st

from common_utils.learned_mappings import LearnedMappingsManager

from .step2_schema_mapper import display_mapping_summary
from .step3_data_quality_fixer import display_quality_summary


def review_results():
    """Step 4: Review final results and download transformed CSV."""
    st.header("✅ Step 4: Review Final Results")

    if not st.session_state.mapping_results or st.session_state.transformed_df is None:
        st.error(
            "❌ No results found. Please go back to Step 3 and complete data cleaning."
        )
        return

    st.markdown(
        """
    Review the final results including the transformed CSV with updated column headers.
    You can download the transformed data or start over with a new file.
    """
    )

    # --- 1. Show Transformed DataFrame Head ---
    st.subheader("📊 Transformed Data Preview")
    st.info("Here's a preview of your transformed data with canonical column names:")

    if "transformed_df" in st.session_state:
        # Show 5 rows by default
        st.dataframe(st.session_state.transformed_df.head(5), width="stretch")

        # Show basic info about the dataframe
        col1, col2 = st.columns(2)
        with col1:
            st.metric("📋 Total Rows", len(st.session_state.transformed_df))
        with col2:
            st.metric("📋 Total Columns", len(st.session_state.transformed_df.columns))

    # --- 2. Show Applied Transformations Summary ---
    st.subheader("🔄 Applied Transformations")

    if st.session_state.get("applied_mappings"):
        st.success(
            f"✅ Successfully applied {len(st.session_state.applied_mappings)} column mappings:"
        )

        # Show mapping summary in expandable section
        with st.expander("📋 View All Column Mappings", expanded=False):
            transformation_data = []
            for original, canonical in st.session_state.applied_mappings.items():
                transformation_data.append(
                    {"Original Header": original, "New Header (Canonical)": canonical}
                )

            if transformation_data:
                transformation_df = pd.DataFrame(transformation_data)
                st.dataframe(transformation_df, width="stretch")
    else:
        st.info("ℹ️ No column transformations were applied.")

    # --- 3. Mapping Summary Statistics ---
    if st.session_state.get("mapping_summary"):
        display_mapping_summary(st.session_state.mapping_summary)

    # --- 4. Data Quality Summary ---
    st.markdown("---")
    display_quality_summary()

    # Legacy data quality info (for backward compatibility)
    if st.session_state.get("validation_errors"):
        legacy_error_count = len(st.session_state.validation_errors)
        if legacy_error_count > 0:
            st.info(
                f"Note: {legacy_error_count} legacy validation errors were also found."
            )

    # --- 5. Download Options ---
    st.subheader("💾 Download Options")

    # Prepare download data
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    original_name = st.session_state.get("original_filename", "data").replace(
        ".csv", ""
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        # Download transformed CSV (main output)
        if st.session_state.transformed_df is not None:
            transformed_csv = st.session_state.transformed_df.to_csv(index=False)

            st.download_button(
                label="📥 **Download Transformed CSV**",
                data=transformed_csv,
                file_name=f"{original_name}_transformed_{timestamp}.csv",
                mime="text/csv",
                type="primary",
                help="Download CSV with updated column headers",
            )

    with col2:
        # Download original data for comparison
        if st.session_state.get("uploaded_df") is not None:
            original_csv = st.session_state.uploaded_df.to_csv(index=False)

            st.download_button(
                label="📥 Download Original CSV",
                data=original_csv,
                file_name=f"{original_name}_original_{timestamp}.csv",
                mime="text/csv",
                help="Download original data for comparison",
            )

    with col3:
        # Download mappings as CSV
        if st.session_state.get("applied_mappings"):
            mappings_data = []
            for original, canonical in st.session_state.applied_mappings.items():
                mappings_data.append(f"{original},{canonical}")

            csv_mapping = "Original Header,Canonical Field\n" + "\n".join(mappings_data)

            st.download_button(
                label="📥 Download Mappings CSV",
                data=csv_mapping,
                file_name=f"{original_name}_mappings_{timestamp}.csv",
                mime="text/csv",
                help="Summary of column mappings",
            )

    # --- 6. API Usage Summary ---
    gemini_calls = st.session_state.get("gemini_calls_count", 0)
    if gemini_calls > 0:
        st.subheader("🤖 AI Usage")
        st.info(f"Total Gemini API calls made during this session: {gemini_calls}")

    # --- 7. Learned Mappings Summary ---
    st.subheader("💡 Learning Progress")
    learned_manager = LearnedMappingsManager()
    learned_stats = learned_manager.get_stats()

    if learned_stats["total_learned_header_variations"] > 0:
        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                "📚 Canonical Fields with Learning",
                learned_stats["total_canonical_fields_with_learned_mappings"],
            )
        with col2:
            st.metric(
                "🎯 Total Learned Variations",
                learned_stats["total_learned_header_variations"],
            )

        with st.expander("📋 View Learned Mappings", expanded=False):
            learned_mappings = learned_manager.load_learned_mappings()
            if learned_mappings:
                for canonical_field, variations in learned_mappings.items():
                    st.write(f"**{canonical_field}:**")
                    for variation in variations:
                        st.write(f"  • `{variation}`")
            else:
                st.write("No learned mappings found.")
    else:
        st.info(
            "🎓 No learned mappings yet. Manual overrides and AI suggestions will be saved for future use!"
        )

    # --- 9. Navigation Buttons ---
    st.subheader("🚀 Next Steps")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔄 Start Over", type="secondary"):
            # Reset session state
            st.session_state.step = 1
            st.session_state.uploaded_df = None
            st.session_state.mapping_results = []
            st.session_state.gemini_calls_count = 0
            st.session_state.transformed_df = None
            st.session_state.applied_mappings = {}
            st.session_state.original_filename = ""
            st.session_state.mappings_applied = False
            if "validation_errors" in st.session_state:
                del st.session_state.validation_errors
            st.rerun()

    with col2:
        if st.button("⬅️ Back to Data Quality", type="secondary"):
            st.session_state.step = 3
            st.rerun()
