import pandas as pd
import streamlit as st

from common_utils.constants import CONSTANTS, MatchMethod, SummaryKey
from common_utils.schema_mapper import SchemaMapper
from modules.schema_loader import get_schema_loader


def validate_column_count(
    uploaded_df: pd.DataFrame, threshold: int = CONSTANTS.COLUMN_DELTA_THRESHOLD
) -> bool:
    """
    Validate column count between uploaded CSV and canonical schema.

    Args:
        uploaded_df: The uploaded DataFrame
        threshold: Maximum allowed difference in column count (default: 2)

    Returns:
        dict: Validation results with status, message, and metrics
    """
    # Get uploaded CSV column count
    uploaded_columns = len(uploaded_df.columns)

    # Get canonical schema column count
    schema_loader = get_schema_loader()
    canonical_columns = schema_loader.get_canonical_columns()
    canonical_column_count = len(canonical_columns)

    # Get column names for comparison
    uploaded_column_names = list(uploaded_df.columns)
    canonical_column_names = list(canonical_columns.keys())

    # Calculate delta
    delta = abs(uploaded_columns - canonical_column_count)

    if delta > threshold:
        root_message = f"⚠️ Column count mismatch detected! Your CSV has {uploaded_columns} columns, but canonical schema expects {canonical_column_count}."
        if uploaded_columns > canonical_column_count:
            st.warning(f"{root_message} You have {delta} extra columns.")
        else:
            st.warning(f"{root_message} You're missing {delta} columns.")

        with st.expander("🔍 View Detailed Column Comparison"):
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**📁 Your CSV Columns:**")
                for i, col in enumerate(uploaded_column_names, 1):
                    st.write(f"{i}. {col}")

            with col2:
                st.markdown("**🎯 Expected Canonical Columns:**")
                for i, col in enumerate(canonical_column_names, 1):
                    st.write(f"{i}. {col}")

        return False
    return True


def display_mapping_results(summary, results=None):
    # Prefer passed results, fallback to session state
    results = results or st.session_state.get("mapping_results", [])

    if not results:
        return

    st.subheader("Schema Mapping Summary")

    # Define summary metrics config
    metrics = [
        ("🎯 Exact Matches", SummaryKey.EXACT_MATCHES, False),
        ("📚 Abbreviation Matches", SummaryKey.ABBREVIATION_MATCHES, False),
        ("🔍 Fuzzy Matches", SummaryKey.FUZZY_MATCHES, False),
        ("🤖 AI Matches", SummaryKey.BEDROCK_MATCHES, False),
        ("❌ No Matches", SummaryKey.NO_MATCHES, False),
        ("📈 Success Rate", "mapping_percentage", True),
    ]

    cols = st.columns(len(metrics))
    for col, (label, key, is_percent) in zip(cols, metrics):
        value = f"{summary[key]:.1f}%" if is_percent else summary[key]
        col.metric(label, value)

    # Detailed results
    # st.subheader("🔍 Detailed Mapping Results")

    # Status mapping dictionary
    status_map = {
        MatchMethod.EXACT: "🎯",
        MatchMethod.ABBREVIATION: "📚",
        MatchMethod.FUZZY: "🔍",
        MatchMethod.BEDROCK: "🤖",
        MatchMethod.NO_MATCH: "❌",
    }

    schema_loader = get_schema_loader()

    with st.expander("🔍 Detailed Mapping Results"):
        for result in results:
            method = result.get("mapping_method", "No Match")
            confidence = result.get("confidence", 0.0)
            icon = status_map.get(method, "❌")
            suggested = result.get("suggested_canonical")

            with st.expander(
                f"{icon} **{result['original_header']}** → **{suggested or 'No Match'}** "
                f"(Confidence: {confidence:.1f})"
            ):
                col1, col2 = st.columns(2)

                # Left: Header details + samples
                with col1:
                    st.markdown("**📝 Header Analysis**")
                    st.write(f"• **Original:** {result['original_header']}")
                    st.write(
                        f"• **Normalized:** {result.get('normalized_header', 'N/A')}"
                    )
                    st.write(f"• **Method:** {method}")

                    st.markdown("**📋 Sample Values**")
                    for val in result.get("sample_values", [])[:3]:
                        st.write(f"• {val}")

                # Right: Canonical schema info (if available)
                with col2:
                    if suggested:
                        col_def = schema_loader.get_column_definition(suggested)
                        if col_def:
                            st.markdown("**🎯 Canonical Field Info**")
                            st.write(f"• **Type:** {col_def.get('type', 'N/A')}")
                            st.write(
                                f"• **Description:** {col_def.get('description', 'N/A')}"
                            )
                            st.write(f"• **Example:** {col_def.get('example', 'N/A')}")

                            if col_def.get("validators"):
                                st.write(
                                    f"• **Validators:** {', '.join(col_def['validators'])}"
                                )
                    else:
                        st.warning("⚠️ No canonical field match found")
                        st.markdown("**Possible reasons:**")
                        st.write(
                            "• Header doesn't match any known field or abbreviation"
                        )
                        st.write("• May need manual review or additional mapping rules")
                        st.write("• Could be handled by future advanced matching")


def schema_mapper():
    """Step 2: Intelligent header mapping with exact match priority, then lemmatization and AI fallback."""
    if st.session_state.uploaded_df is None:
        st.error("❌ No data found. Please go back to Step 1.")
        return

    # Column Count Validation (at the very beginning)
    validation_success = validate_column_count(st.session_state.uploaded_df)
    if not validation_success:
        return

    # Run Mapping Analysis automatically
    try:
        # Initialize basic header mapper
        mapper = SchemaMapper()

        # Run mapping analysis
        mapping_results = mapper.map_headers(st.session_state.uploaded_df)
        mapping_summary = mapper.get_mapping_summary(mapping_results)

        # Store results
        st.session_state.mapping_results = mapping_results
        st.session_state.bedrock_calls_count = 0

    except Exception as e:
        st.error(f"❌ Mapping analysis failed: {str(e)}")
        return

    # Display mapping results
    display_mapping_results(mapping_summary, mapping_results)

    for mapping_result in mapping_results:
        if mapping_result["suggested_canonical"]:
            st.session_state.transformed_df = st.session_state.transformed_df.rename(
                columns={
                    mapping_result["original_header"]: mapping_result[
                        "suggested_canonical"
                    ]
                }
            )

    st.dataframe(st.session_state.transformed_df.head(5), width="stretch")
