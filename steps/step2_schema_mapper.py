import streamlit as st

from common_utils.constants import MatchMethod, SummaryKey
from common_utils.learned_mappings import LearnedMappingsManager
from common_utils.schema_mapper import SchemaMapper
from modules.schema_loader import get_schema_loader


def display_mapping_summary(summary):
    """Displays the summary metrics of the mapping results."""
    st.subheader("Schema Mapping Summary")

    metrics = [
        ("🎯 Exact Matches", SummaryKey.EXACT_MATCHES),
        ("📚 Abbreviation Matches", SummaryKey.ABBREVIATION_MATCHES),
        ("🔍 Fuzzy Matches", SummaryKey.FUZZY_MATCHES),
        ("🤖 AI Matches", SummaryKey.GEMINI_MATCHES),
        ("✋ Manual Matches", SummaryKey.MANUAL_MATCHES),
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

    # --- 1. Run Mapping Analysis (only once) ---
    if (
        "mapping_results" not in st.session_state
        or not st.session_state.mapping_results
    ):
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

    # Helper function to update mapping results with manual overrides
    def update_mapping_results_with_overrides():
        updated_results = []
        for i, result in enumerate(st.session_state.mapping_results):
            updated_result = result.copy()
            original_suggestion = result.get("suggested_canonical")
            current_selection = st.session_state.get(f"select_{i}")

            # If user changed the selection, mark as manual match
            if (
                current_selection
                and current_selection != original_suggestion
                and current_selection != "No Mapping Found"
            ):
                updated_result["mapping_method"] = MatchMethod.MANUAL
                updated_result["suggested_canonical"] = current_selection
                updated_result["confidence"] = (
                    1.0  # Manual selections have 100% confidence
                )
            elif current_selection == "No Mapping Found":
                updated_result["mapping_method"] = MatchMethod.NO_MATCH
                updated_result["suggested_canonical"] = None
                updated_result["confidence"] = 0.0

            updated_results.append(updated_result)
        return updated_results

    # Update results with current overrides and recalculate summary
    current_mapping_results = update_mapping_results_with_overrides()
    mapper = SchemaMapper()
    current_summary = mapper.get_mapping_summary(current_mapping_results)

    # --- 2. Display Results and Interactive Override ---
    display_mapping_summary(current_summary)

    # Show Gemini calls count
    gemini_calls = st.session_state.get("gemini_calls_count", 0)
    if gemini_calls > 0:
        st.info(f"🤖 Gemini API calls made: {gemini_calls}")

    st.markdown("---")
    st.subheader("Review and Confirm Mappings")
    st.markdown(
        "Review the suggestions below. You can override any mapping using the dropdowns."
    )

    schema_loader = get_schema_loader()
    canonical_columns = list(schema_loader.get_canonical_columns().keys())
    mapping_options = ["No Mapping Found"] + canonical_columns

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
            # Get the current confidence (could be updated for manual overrides)
            current_confidence = current_mapping_results[i]["confidence"]
            st.write(f"{current_confidence:.2f}")
        with c4:
            # Get the current method (could be overridden)
            current_result = current_mapping_results[i]
            mapping_method = current_result["mapping_method"]

            if mapping_method == MatchMethod.NO_MATCH:
                st.markdown(
                    f"<span style='background-color: #ffebee; color: #d32f2f; padding: 4px 8px; border-radius: 4px; font-weight: bold;'>⚠️ {mapping_method}</span>",
                    unsafe_allow_html=True,
                )
            elif mapping_method == MatchMethod.MANUAL:
                st.markdown(
                    f"<span style='background-color: #e8f5e8; color: #2e7d32; padding: 4px 8px; border-radius: 4px; font-weight: bold;'>✋ {mapping_method}</span>",
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
                # Update mapping results with final overrides
                st.session_state.mapping_results = current_mapping_results
                st.session_state.mapping_summary = current_summary

                # Save learned mappings from Manual and Gemini matches
                learned_mappings_manager = LearnedMappingsManager()
                learned_mappings_to_save = []

                for result in current_mapping_results:
                    original_header = result["original_header"]
                    canonical_field = result.get("suggested_canonical")
                    mapping_method = result.get("mapping_method", "")
                    confidence = result.get("confidence", 0.0)

                    # Only save Manual Match and AI (Gemini) mappings
                    if canonical_field and mapping_method in [
                        MatchMethod.MANUAL,
                        MatchMethod.GEMINI,
                    ]:
                        learned_mappings_to_save.append(
                            {
                                "original_header": original_header,
                                "canonical_field": canonical_field,
                                "mapping_method": mapping_method,
                                "confidence": confidence,
                            }
                        )

                # Save all learned mappings in batch
                if learned_mappings_to_save:
                    learned_mappings_manager.save_batch_learned_mappings(
                        learned_mappings_to_save
                    )
                    st.success(
                        f"💡 Saved {len(learned_mappings_to_save)} learned mappings for future use!"
                    )

                # Only rename columns that have actual mappings (not "No Mapping Found")
                rename_map = {
                    original: new_name
                    for original, new_name in user_overrides.items()
                    if new_name != "No Mapping Found"
                }

                df = st.session_state.uploaded_df.copy()
                transformed_df = df.rename(columns=rename_map)

                # Keep all columns - no dropping
                # Columns marked as "No Mapping Found" will keep their original names

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
                        f"select_{i}", "No Mapping Found"
                    )

                unmapped_cols = [
                    header
                    for header, choice in current_overrides.items()
                    if choice == "No Mapping Found"
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
