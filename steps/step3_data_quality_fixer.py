import pandas as pd
import streamlit as st

from common_utils.constants import CONSTANTS
from common_utils.data_validator import DataValidator


def data_quality_fixer():
    """
    Step 3: Run validation, display a summary dashboard, and report detailed errors.
    """
    st.header("Step 3: Clean & Validate Data")

    if (
        "transformed_df" not in st.session_state
        or st.session_state.transformed_df is None
    ):
        st.warning(
            "No mapped data found. Please complete Step 2 and apply mappings first."
        )
        return

    # --- 1. User-Triggered Analysis ---
    # The analysis runs only when the user clicks the button.
    df = st.session_state.transformed_df
    validator = DataValidator()

    # The results are stored in the session state to prevent re-calculation.
    st.session_state.missing_summary = validator.get_missing_data_summary(df)
    st.session_state.validation_errors = validator.validate_dataframe(df)

    # --- 2. Display Results (if they exist in the session state) ---
    if "missing_summary" not in st.session_state:
        st.info("Click the button above to analyze the data's quality and validity.")
        return

    # --- Missing Data Dashboard ---
    missing_summary = st.session_state.missing_summary
    missing_percentage = missing_summary.get("missing_percentage", 0.0)

    st.subheader("Missing Data Analysis (for required fields)")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Rows", missing_summary.get("total_rows", "N/A"))
    col2.metric(
        "Rows with Missing Data", missing_summary.get("rows_with_missing_data", "N/A")
    )
    col3.metric("Missing Data Ratio", f"{missing_percentage:.1f}%")

    if missing_percentage > CONSTANTS.MISSING_DATA_THRESHOLD:
        st.error(
            f"**Process Halted:** Missing data ratio ({missing_percentage:.1f}%) "
            f"exceeds the threshold of {CONSTANTS.MISSING_DATA_THRESHOLD:.1f}%. "
            "AI-powered fixing is not recommended for this volume of missing data. "
            "Please fix the source data before proceeding."
        )
        # We use return to stop executing the rest of the step.
        return
    else:
        st.success("Missing data ratio is within the acceptable threshold.")

    st.markdown("---")

    # --- Detailed Validation Error Report ---
    errors = st.session_state.validation_errors

    if not errors:
        st.success("✅ **Congratulations! No validation errors were found.**")
        st.balloons()
        st.info(
            "Your data appears to be clean and valid according to the canonical schema. "
            "You can now proceed to the final review step."
        )
        # Here you would typically enable navigation to the next step.
        return

    st.subheader("Data Validation Errors Found")
    st.warning(f"Found **{len(errors)}** specific issues that need your attention.")

    # Displaying errors in a DataFrame is clean and efficient.
    errors_df = pd.DataFrame(errors)
    st.dataframe(errors_df, width="stretch")

    if st.button("➡️ Proceed to Review", type="primary", key="proceed_btn"):
        st.session_state.step = 4
        st.rerun()
