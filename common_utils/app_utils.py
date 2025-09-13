import streamlit as st


def initialize_session_state():
    """Initialize session state variables."""
    if "uploaded_df" not in st.session_state:
        st.session_state.uploaded_df = None
    if "original_filename" not in st.session_state:
        st.session_state.original_filename = ""
    if "mapping_results" not in st.session_state:
        st.session_state.mapping_results = []
    if "bedrock_calls_count" not in st.session_state:
        st.session_state.bedrock_calls_count = 0
    if "transformed_df" not in st.session_state:
        st.session_state.transformed_df = None
    if "applied_mappings" not in st.session_state:
        st.session_state.applied_mappings = {}


def reset_button_state(button_key: str):
    if st.button("⬅️ Back to Upload", key="step2_back"):
        st.session_state.mapping_results = []
        st.session_state.transformed_df = None
        st.session_state.applied_mappings = {}
        st.rerun()
