import pandas as pd
import streamlit as st


def upload_csv():
    """Step 1: Upload and preview CSV file."""
    st.header("Step 1: Upload CSV File")

    # The file uploader is now part of this step, making it self-contained.
    uploaded_file = st.file_uploader(
        "Choose a CSV file to begin the process",
        type=["csv"],
        help="Upload a CSV file to analyze",
    )

    if uploaded_file is not None:
        try:
            # Clear any data from previous runs to ensure a fresh start
            for key in [
                "uploaded_df",
                "original_filename",
                "mapping_results",
                "transformed_df",
                "validation_errors",
            ]:
                if key in st.session_state:
                    del st.session_state[key]

            df = pd.read_csv(uploaded_file)
            # Save the uploaded data to the session state for other steps to use
            st.session_state.uploaded_df = df
            st.session_state.original_filename = uploaded_file.name

            st.success(f"✅ Successfully loaded **{uploaded_file.name}**")
            st.dataframe(df.head(5), width="stretch")

            # Navigation Button to proceed to the next step
            if st.button("➡️ Proceed to Schema Mapping", type="primary"):
                st.session_state.step = 2
                st.rerun()

        except Exception as e:
            st.error(f"❌ Error reading file: {str(e)}")
