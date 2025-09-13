import streamlit as st
import pandas as pd


def upload_csv(uploaded_file: pd.DataFrame):
    """Step 1: Upload and preview CSV file."""

    try:
        # Read the CSV file
        df = pd.read_csv(uploaded_file)
        st.session_state.uploaded_df = df
        st.session_state.original_filename = uploaded_file.name
        st.session_state.transformed_df = df

        # Display basic info
        st.success(f"✅ Successfully loaded **{uploaded_file.name}**")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📊 Rows", len(df))
        with col2:
            st.metric("📋 Columns", len(df.columns))
        with col3:
            st.metric("💾 Size", f"{uploaded_file.size:,} bytes")

        # Data preview
        st.subheader("👀 Data Preview")
        st.dataframe(df.head(5), width="stretch")

    except Exception as e:
        st.error(f"❌ Error reading file: {str(e)}")
