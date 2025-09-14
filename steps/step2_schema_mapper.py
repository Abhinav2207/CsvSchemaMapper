import streamlit as st

from common_utils.constants import SummaryKey
from common_utils.schema_mapper import SchemaMapper
from modules.schema_loader import get_schema_loader


def display_mapping_summary(summary):
    """Displays the summary metrics of the mapping results."""
    st.subheader("Schema Mapping Summary")

    metrics = [
        ("🎯 Exact Matches", SummaryKey.EXACT_MATCHES),
        ("📚 Abbreviation Matches", SummaryKey.ABBREVIATION_MATCHES),
        ("🔍 Fuzzy Matches", SummaryKey.FUZZY_MATCHES),
        ("🤖 AI Matches", SummaryKey.BEDROCK_MATCHES),
        ("❌ No Matches", SummaryKey.NO_MATCHES),
    ]

    cols = st.columns(len(metrics))
    for col, (label, key) in zip(cols, metrics):
        col.metric(label, summary.get(key, 0))

    success_rate = summary.get("mapping_percentage", 0)
    st.progress(int(success_rate), text=f"Success Rate: {success_rate:.1f}%")


def schema_mapper():
    """
    Step 2: Display mapping suggestions and allow user to review and override.
    """

    if "uploaded_df" not in st.session_state or st.session_state.uploaded_df is None:
        st.error("❌ No data found. Please go back to Step 1 and upload a file.")
        return

    # --- 1. Run Mapping Analysis ---
    if "mapping_results" not in st.session_state:
        st.session_state.mapping_results = []

    with st.spinner("Analyzing headers and generating suggestions..."):
        mapper = SchemaMapper()
        results = mapper.map_headers(st.session_state.uploaded_df)
        summary = mapper.get_mapping_summary(results)
        st.session_state.mapping_results = results
        st.session_state.mapping_summary = summary

    if not st.session_state.mapping_results:
        st.info("Click the button above to start the schema mapping analysis.")
        return

    # --- 2. Display Results and Interactive Override ---
    display_mapping_summary(st.session_state.mapping_summary)
    st.markdown("---")
    st.subheader("Review and Confirm Mappings")
    st.markdown(
        "Review the suggestions below. You can override any mapping using the dropdowns."
    )

    schema_loader = get_schema_loader()
    canonical_columns = list(schema_loader.get_canonical_columns().keys())
    mapping_options = ["-- DO NOT MAP --"] + canonical_columns

    user_overrides = {}

    # --- Interactive Table Header ---
    col1, col2, col3, col4 = st.columns([2, 3, 1, 2])
    col1.markdown("**Your CSV Header**")
    col2.markdown("**Your Choice (Override if needed)**")
    col3.markdown("**Confidence**")
    col4.markdown("**Method**")

    # --- Interactive Table Rows ---
    for i, result in enumerate(st.session_state.mapping_results):
        original_header = result["original_header"]
        suggested = result["suggested_canonical"]

        try:
            default_index = mapping_options.index(suggested) if suggested else 0
        except ValueError:
            default_index = 0

        c1, c2, c3, c4 = st.columns([2, 3, 1, 2])
        with c1:
            st.write(original_header)
            with st.expander("Show samples"):
                st.json(result["sample_values"])
        with c2:
            user_choice = st.selectbox(
                f"map_{original_header}",
                options=mapping_options,
                index=default_index,
                label_visibility="collapsed",
                key=f"select_{i}",
            )
            user_overrides[original_header] = user_choice
        with c3:
            st.write(f"{result['confidence']:.2f}")
        with c4:
            mapping_method = result["mapping_method"]
            if mapping_method == "No Match":
                st.markdown(
                    f"<span style='background-color: #ffebee; color: #d32f2f; padding: 4px 8px; border-radius: 4px; font-weight: bold;'>⚠️ {mapping_method}</span>",
                    unsafe_allow_html=True,
                )
            else:
                st.write(mapping_method)

    st.markdown("---")

    # --- 3. Navigation Buttons ---
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("⬅️ Back to Upload"):
            st.session_state.step = 1
            # Clear state for this step before going back
            st.session_state.mapping_results = []
            st.session_state.pop("mapping_summary", None)
            st.session_state.pop("mappings_applied", None)
            st.session_state.pop("transformed_df", None)
            st.rerun()

    with col2:
        # Check if mappings have been applied
        mappings_applied = st.session_state.get("mappings_applied", False)

        if not mappings_applied:
            if st.button("✅ Apply Mappings", type="primary"):
                # Only rename columns that have actual mappings (not "-- DO NOT MAP --")
                rename_map = {
                    original: new_name
                    for original, new_name in user_overrides.items()
                    if new_name != "-- DO NOT MAP --"
                }

                df = st.session_state.uploaded_df.copy()
                transformed_df = df.rename(columns=rename_map)

                # Keep all columns - no dropping
                # Columns marked as "-- DO NOT MAP --" will keep their original names

                st.session_state.transformed_df = transformed_df
                st.session_state.applied_mappings = rename_map
                st.session_state.mappings_applied = True
                st.rerun()
        else:
            # Show disabled Apply Mappings button
            st.button("✅ Apply Mappings", type="primary", disabled=True)

    # --- 4. Show Transformed DataFrame (if mappings applied) ---
    if st.session_state.get("mappings_applied", False):
        st.markdown("---")
        st.success("✅ Mappings applied successfully!")
        st.subheader("Preview of Transformed Data")
        st.info(
            "Review the transformed data below. Mapped columns have been renamed to canonical names, while unmapped columns kept their original names."
        )

        if "transformed_df" in st.session_state:
            st.dataframe(st.session_state.transformed_df.head(10), width="stretch")

            # Show mapping summary
            with st.expander("📋 Applied Mappings Summary", expanded=False):
                if st.session_state.get("applied_mappings"):
                    st.write("**Column Renames:**")
                    for old_name, new_name in st.session_state.applied_mappings.items():
                        st.write(f"• `{old_name}` → `{new_name}`")
                else:
                    st.write("No column renames were applied.")

                # Show unmapped columns info (get from current user selections)
                current_overrides = {}
                for i, result in enumerate(st.session_state.mapping_results):
                    original_header = result["original_header"]
                    current_overrides[original_header] = st.session_state.get(
                        f"select_{i}", "-- DO NOT MAP --"
                    )

                unmapped_cols = [
                    header
                    for header, choice in current_overrides.items()
                    if choice == "-- DO NOT MAP --"
                ]
                if unmapped_cols:
                    st.write("**Unmapped Columns (kept with original names):**")
                    for col in unmapped_cols:
                        st.write(f"• `{col}`")
                else:
                    st.write("All columns were mapped to canonical schema.")

        # --- 5. Proceed Button (appears below transformed data) ---
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button(
                "➡️ Proceed to Clean & Validate", type="primary", key="proceed_btn"
            ):
                st.session_state.step = 3
                st.rerun()
