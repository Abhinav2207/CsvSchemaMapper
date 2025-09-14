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
    st.header("Step 2: Map to Canonical Schema")

    if "uploaded_df" not in st.session_state or st.session_state.uploaded_df is None:
        st.error("❌ No data found. Please go back to Step 1 and upload a file.")
        return

    # --- 1. Run Mapping Analysis ---
    if "mapping_results" not in st.session_state:
        st.session_state.mapping_results = []

    if st.button("🚀 Run Mapping Analysis", type="primary"):
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
            st.write(result["mapping_method"])

    st.markdown("---")

    # --- 3. Navigation Buttons ---
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("⬅️ Back to Upload"):
            st.session_state.step = 1
            # Clear state for this step before going back
            st.session_state.mapping_results = []
            st.session_state.pop("mapping_summary", None)
            st.rerun()

    with col2:
        if st.button("➡️ Apply Mappings & Proceed to Cleaning", type="primary"):
            rename_map = {
                original: new_name
                for original, new_name in user_overrides.items()
                if new_name != "-- DO NOT MAP --"
            }

            df = st.session_state.uploaded_df.copy()
            transformed_df = df.rename(columns=rename_map)

            cols_to_drop = [
                header
                for header, choice in user_overrides.items()
                if choice == "-- DO NOT MAP --"
            ]
            transformed_df.drop(columns=cols_to_drop, inplace=True, errors="ignore")

            st.session_state.transformed_df = transformed_df
            st.session_state.applied_mappings = rename_map
            st.session_state.step = 3
            st.rerun()
