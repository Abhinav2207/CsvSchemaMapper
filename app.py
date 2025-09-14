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

    # --- Sidebar for Developer Tools ---
    with st.sidebar:
        st.header("Developer Tools")
        debug_mode = st.checkbox("Show Session State", value=False)
        if debug_mode:
            with st.expander("🔬 Current Session State", expanded=False):
                st.write(st.session_state)

    # --- Main Page Container ---
    # Placing all main content inside this container solves the overlap issue.
    main_container = st.container()

    with main_container:
        # --- Main Header ---
        st.title("📊 Schema Mapper & Data Quality Fixer")
        st.markdown(
            "Automatically map, clean, and validate messy partner CSVs into a single canonical format."
        )
        st.markdown("---")

        # --- Visual Progress Bar / Stepper ---
        steps = ["Upload", "Map Schema", "Clean & Validate", "Review & Download"]
        current_step_index = st.session_state.step - 1

        cols = st.columns(len(steps))
        for i, col in enumerate(cols):
            with col:
                if i < current_step_index:
                    st.success(f"✓ {steps[i]}", icon="✅")
                elif i == current_step_index:
                    st.info(f"➡️ {steps[i]}", icon="⚙️")
                else:
                    st.write(f"⚪ {steps[i]}")

        st.markdown("---")

        # --- Page Router ---
        if st.session_state.step == 1:
            step1_upload_csv()
        elif st.session_state.step == 2:
            step2_schema_mapper()
        elif st.session_state.step == 3:
            step3_data_quality_fixer()
        elif st.session_state.step == 4:
            step4_review_results()


if __name__ == "__main__":
    main()
