def review_results():
    pass


# def step4_review_results():
#     """Step 3: Review final results and download transformed CSV."""
#     st.header("✅ Step 3: Review Final Results")

#     if not st.session_state.mapping_results or st.session_state.transformed_df is None:
#         st.error("❌ No results found. Please go back to Step 2 and apply mappings.")
#         return

#     st.markdown(
#         """
#     Review the final results including the transformed CSV with updated column headers.
#     You can download the transformed data or start over with a new file.
#     """
#     )

#     results = st.session_state.mapping_results

#     # Summary
#     st.subheader("📋 Final Mapping Summary")

#     successful_mappings = [r for r in results if r["suggested_canonical"]]
#     failed_mappings = [r for r in results if not r["suggested_canonical"]]
#     ai_mappings = [r for r in results if r.get("gemini_suggested")]

#     col1, col2, col3 = st.columns(3)
#     with col1:
#         st.metric("✅ Successfully Mapped", len(successful_mappings))
#     with col2:
#         st.metric("❌ No Match Found", len(failed_mappings))
#     with col3:
#         st.metric("🤖 AI-Suggested", len(ai_mappings))

#     # Successful mappings
#     if successful_mappings:
#         st.subheader("✅ Successfully Mapped Fields")

#         mapping_data = []
#         for result in successful_mappings:
#             mapping_data.append(
#                 {
#                     "Your Header": result["original_header"],
#                     "Canonical Field": result["suggested_canonical"],
#                     "Confidence": f"{result['confidence']:.2f}",
#                     "Method": result.get("mapping_method", "Unknown"),
#                     "Sample Data": ", ".join(result["sample_values"][:2]),
#                 }
#             )

#         mapping_df = pd.DataFrame(mapping_data)
#         st.dataframe(mapping_df, width="stretch")

#     # Failed mappings
#     if failed_mappings:
#         st.subheader("❌ Fields That Need Attention")
#         st.warning(
#             f"Found {len(failed_mappings)} headers that couldn't be automatically mapped."
#         )

#         failed_data = []
#         for result in failed_mappings:
#             failed_data.append(
#                 {
#                     "Header": result["original_header"],
#                     "Lemmatized": ", ".join(result.get("normalized_lemmas", [])),
#                     "Sample Values": ", ".join(result["sample_values"][:2]),
#                 }
#             )

#         failed_df = pd.DataFrame(failed_data)
#         st.dataframe(failed_df, width="stretch")

#     # Show applied transformations
#     st.subheader("🔄 Applied Transformations")

#     if st.session_state.applied_mappings:
#         st.success(
#             f"✅ Successfully applied {len(st.session_state.applied_mappings)} column mappings:"
#         )

#         transformation_data = []
#         for original, canonical in st.session_state.applied_mappings.items():
#             transformation_data.append(
#                 {"Original Header": original, "New Header (Canonical)": canonical}
#             )

#         transformation_df = pd.DataFrame(transformation_data)
#         st.dataframe(transformation_df, width="stretch")

#         # Show before/after comparison
#         st.subheader("📊 Data Comparison")

#         col1, col2 = st.columns(2)

#         with col1:
#             st.markdown("**🔸 Original Data**")
#             st.dataframe(st.session_state.uploaded_df.head(5), width="stretch")

#         with col2:
#             st.markdown("**🔹 Transformed Data**")
#             st.dataframe(st.session_state.transformed_df.head(5), width="stretch")

#     else:
#         st.info("ℹ️ No transformations were applied.")

#     # Download results
#     st.subheader("💾 Download Options")

#     # Prepare download data
#     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#     original_name = st.session_state.original_filename.replace(".csv", "")

#     # Create mapping report
#     report_data = {
#         "original_filename": st.session_state.original_filename,
#         "analysis_timestamp": timestamp,
#         "total_headers": len(results),
#         "successful_mappings": len(successful_mappings),
#         "failed_mappings": len(failed_mappings),
#         "ai_calls_made": st.session_state.gemini_calls_count,
#         "mapping_details": results,
#     }

#     import json

#     report_json = json.dumps(report_data, indent=2, default=str)

#     col1, col2, col3 = st.columns(3)

#     with col1:
#         # Download transformed CSV (main output)
#         if st.session_state.transformed_df is not None:
#             transformed_csv = st.session_state.transformed_df.to_csv(index=False)

#             st.download_button(
#                 label="📥 **Download Transformed CSV**",
#                 data=transformed_csv,
#                 file_name=f"{original_name}_transformed_{timestamp}.csv",
#                 mime="text/csv",
#                 type="primary",
#                 help="Download CSV with updated column headers",
#             )

#     with col2:
#         # Download mapping report
#         st.download_button(
#             label="📥 Download Mapping Report (JSON)",
#             data=report_json,
#             file_name=f"{original_name}_mapping_report_{timestamp}.json",
#             mime="application/json",
#             help="Detailed analysis report",
#         )

#     with col3:
#         # Simple CSV mapping
#         if successful_mappings:
#             csv_mapping = "Original Header,Canonical Field,Confidence,Method\n"
#             for result in successful_mappings:
#                 csv_mapping += f"{result['original_header']},{result['suggested_canonical']},{result['confidence']:.2f},{result.get('mapping_method', 'Unknown')}\n"

#             st.download_button(
#                 label="📥 Download Mappings (CSV)",
#                 data=csv_mapping,
#                 file_name=f"{original_name}_mappings_{timestamp}.csv",
#                 mime="text/csv",
#                 help="Summary of column mappings",
#             )

#     # Action buttons
#     st.subheader("🚀 Next Steps")
#     col1, col2 = st.columns(2)

#     with col1:
#         if st.button("🔄 Start Over", key="restart"):
#             # Reset session state
#             st.session_state.step = 1
#             st.session_state.uploaded_df = None
#             st.session_state.mapping_results = []
#             st.session_state.gemini_calls_count = 0
#             st.session_state.transformed_df = None
#             st.session_state.applied_mappings = {}
#             st.session_state.original_filename = ""
#             st.rerun()

#     with col2:
#         if st.button("⬅️ Back to Analysis", key="back_to_step2"):
#             # Reset transformations when going back to mapping
#             st.session_state.transformed_df = None
#             st.session_state.applied_mappings = {}
#             st.session_state.step = 2
#             st.rerun()
