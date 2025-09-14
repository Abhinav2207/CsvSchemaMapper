from typing import Any, Dict, List

import pandas as pd
import streamlit as st

from common_utils.constants import CONSTANTS
from common_utils.data_validator import DataValidator
from common_utils.gemini_agent import GeminiAgent


def data_quality_fixer():
    """
    Step 3: Run validation, display a summary dashboard, suggest fixes, and allow application.
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

    df = st.session_state.transformed_df
    validator = DataValidator()

    # Initialize validation results if not exists
    if "validation_results" not in st.session_state:
        st.session_state.validation_results = None
        st.session_state.applied_fixes = []
        st.session_state.initial_errors = []
        st.session_state.quality_summary = None

    # --- 1. Initial Analysis Button ---
    if st.button("🔍 Analyze Data Quality", type="primary"):
        with st.spinner("Analyzing data quality and suggesting fixes..."):
            # Get missing data summary
            missing_summary = validator.get_missing_data_summary(df)

            # Get validation results with fix suggestions
            validation_results = validator.validate_and_suggest_fixes(df)

            # Store initial errors for quality summary
            all_initial_errors = []
            all_initial_errors.extend(validation_results["remaining_errors"])
            for fix_group in validation_results["grouped_fixes"]:
                all_initial_errors.extend(fix_group["errors"])

            st.session_state.missing_summary = missing_summary
            st.session_state.validation_results = validation_results
            st.session_state.applied_fixes = []
            st.session_state.initial_errors = all_initial_errors
        st.rerun()

    # --- 2. Display Results (if they exist) ---
    if st.session_state.validation_results is None:
        st.info("Click the button above to analyze the data's quality and validity.")
        return

    # --- Missing Data Dashboard ---
    missing_summary = st.session_state.missing_summary
    missing_percentage = missing_summary.get("missing_percentage", 0.0)

    st.subheader("📊 Missing Data Analysis")
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
        return
    else:
        st.success("Missing data ratio is within the acceptable threshold.")

    st.markdown("---")

    # --- Validation Results Summary ---
    validation_results = st.session_state.validation_results
    total_errors = validation_results["total_errors"]
    fixable_errors = validation_results["fixable_errors"]
    grouped_fixes = validation_results["grouped_fixes"]
    remaining_errors = validation_results["remaining_errors"]

    if total_errors == 0:
        st.success("✅ **Congratulations! No validation errors were found.**")
        st.balloons()
        st.info(
            "Your data appears to be clean and valid according to the canonical schema. "
            "You can now proceed to the final review step."
        )
        if st.button("➡️ Proceed to Review", type="primary", key="proceed_btn"):
            # Generate quality summary even for clean data
            quality_summary = validator.generate_quality_summary(
                st.session_state.initial_errors,
                [],  # No final errors
                st.session_state.applied_fixes,
            )
            st.session_state.quality_summary = quality_summary

            st.session_state.step = 4
            st.rerun()
        return

    st.subheader("🔧 Data Quality Issues & Suggested Fixes")

    # Check if there are unmapped columns in the dataframe
    df = st.session_state.transformed_df
    canonical_columns = set(validator.schema_loader.get_canonical_columns().keys())
    unmapped_columns = [col for col in df.columns if col not in canonical_columns]

    if unmapped_columns:
        st.info(
            f"📝 **Note**: {len(unmapped_columns)} unmapped column(s) are excluded from validation. "
            f"Only columns mapped to the canonical schema are quality-checked. "
            f"Unmapped columns: {', '.join(f'`{col}`' for col in unmapped_columns[:5])}"
            + (
                f" and {len(unmapped_columns) - 5} more..."
                if len(unmapped_columns) > 5
                else ""
            )
        )

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Issues", total_errors)
    col2.metric("Auto-Fixable", fixable_errors)
    col3.metric("Remaining", len(remaining_errors))
    col4.metric("Applied Fixes", len(st.session_state.applied_fixes))

    if fixable_errors > 0:
        st.info(
            f"Found **{fixable_errors}** issues that can be automatically fixed using deterministic rules."
        )

        # --- Global Apply All Button ---
        st.subheader("🚀 Quick Fix All Issues")

        total_fixable_count = sum(
            len(group["errors"]) for group in grouped_fixes if group["errors"]
        )

        col1, col2 = st.columns([2, 3])

        with col1:
            if st.button(
                f"⚡ Apply All Fixes ({total_fixable_count})",
                type="primary",
                key="apply_all_global",
                help="Apply all suggested fixes from all categories at once",
            ):
                apply_all_fixes_global(grouped_fixes)
                st.rerun()

        with col2:
            st.info(
                "💡 This will apply all deterministic fixes automatically. You can review individual categories below if you prefer selective application."
            )

        st.markdown("---")

        # --- Display Grouped Fixes ---
        display_grouped_fixes(grouped_fixes)

    # --- Display Remaining Errors ---
    if remaining_errors:
        st.subheader("❌ Issues Requiring Manual Review")
        st.warning(
            f"Found **{len(remaining_errors)}** issues that cannot be automatically fixed."
        )

        remaining_df = pd.DataFrame(remaining_errors)
        st.dataframe(remaining_df, width="stretch")

        # --- AI Fix Option ---
        st.markdown("---")
        st.subheader("🤖 Try AI-Powered Fixes")
        st.info(
            "Can't find deterministic fixes? Let AI analyze these errors and suggest solutions."
        )

        col1, col2 = st.columns([2, 3])

        with col1:
            if st.button(
                f"🚀 Get AI Suggestions ({len(remaining_errors)} errors)",
                type="secondary",
                key="ai_fix_button",
                help="Use AI to analyze remaining errors and suggest fixes",
            ):
                get_ai_fix_suggestions(remaining_errors)

        with col2:
            if CONSTANTS.USE_GEMINI:
                st.info(
                    "💡 AI will analyze each error and propose potential fixes for your review."
                )
            else:
                st.warning("⚠️ AI features are disabled. Set USE_GEMINI=true to enable.")

        # Display AI suggestions if available
        display_ai_fix_suggestions()

    # Final proceed button
    if st.button("➡️ Proceed to Review", type="primary", key="final_proceed_btn"):
        # Generate quality summary for review page
        final_errors = []
        final_errors.extend(remaining_errors)
        for fix_group in grouped_fixes:
            final_errors.extend(fix_group["errors"])

        quality_summary = validator.generate_quality_summary(
            st.session_state.initial_errors,
            final_errors,
            st.session_state.applied_fixes,
        )
        st.session_state.quality_summary = quality_summary

        st.session_state.step = 4
        st.rerun()


def display_grouped_fixes(grouped_fixes: List[Dict[str, Any]]):
    """
    Display grouped fixes with apply buttons.
    """
    if not grouped_fixes:
        return

    st.subheader("🛠️ Suggested Fixes")

    for idx, fix_group in enumerate(grouped_fixes):
        with st.expander(
            f"**{fix_group['column']}** - {fix_group['description']} ({len(fix_group['errors'])} issues)",
            expanded=False,
        ):
            st.write(f"**Error Type:** {fix_group['error_type']}")
            st.write(f"**Fix Description:** {fix_group['description']}")

            # Show sample of errors
            errors_df = pd.DataFrame(fix_group["errors"])
            sample_size = min(5, len(errors_df))

            if len(errors_df) > sample_size:
                st.write(
                    f"**Sample of {sample_size} errors (out of {len(errors_df)}):**"
                )
                display_df = errors_df.head(sample_size)[
                    ["row", "value", "suggested_fix"]
                ]
            else:
                st.write(f"**All {len(errors_df)} errors:**")
                display_df = errors_df[["row", "value", "suggested_fix"]]

            st.dataframe(display_df, width="stretch")

            # Apply buttons
            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button(
                    f"Apply All ({len(fix_group['errors'])})",
                    key=f"apply_all_{idx}",
                    type="secondary",
                ):
                    apply_fixes_to_dataframe(fix_group["errors"], apply_all=True)
                    st.rerun()

            with col2:
                if st.button(
                    "Apply Individual", key=f"apply_individual_{idx}", type="secondary"
                ):
                    st.session_state[f"show_individual_{idx}"] = True
                    st.rerun()

            with col3:
                if st.button("Preview Changes", key=f"preview_{idx}", type="secondary"):
                    preview_fixes(fix_group["errors"])

            # Individual fix selection
            if st.session_state.get(f"show_individual_{idx}", False):
                st.write("**Select individual fixes to apply:**")

                selected_fixes = []
                for error_idx, error in enumerate(fix_group["errors"]):
                    if st.checkbox(
                        f"Row {error['row']}: '{error['value']}' → '{error['suggested_fix']}'",
                        key=f"individual_{idx}_{error_idx}",
                    ):
                        selected_fixes.append(error)

                if selected_fixes and st.button(
                    f"Apply Selected ({len(selected_fixes)})",
                    key=f"apply_selected_{idx}",
                    type="primary",
                ):
                    apply_fixes_to_dataframe(selected_fixes, apply_all=False)
                    st.session_state[f"show_individual_{idx}"] = False
                    st.rerun()


def apply_fixes_to_dataframe(errors: List[Dict], apply_all: bool = True):
    """
    Apply fixes to the transformed dataframe.
    """
    validator = DataValidator()

    # Prepare fixes for application
    fixes_to_apply = []
    for error in errors:
        if error.get("suggested_fix") is not None:
            fixes_to_apply.append(
                {
                    "row": error["row"],
                    "column": error["column"],
                    "new_value": error["suggested_fix"],
                }
            )

    if fixes_to_apply:
        # Apply fixes to the dataframe
        updated_df = validator.apply_fixes(
            st.session_state.transformed_df, fixes_to_apply
        )
        st.session_state.transformed_df = updated_df

        # Track applied fixes
        st.session_state.applied_fixes.extend(fixes_to_apply)

        # Re-run validation to update results
        new_validation_results = validator.validate_and_suggest_fixes(updated_df)
        st.session_state.validation_results = new_validation_results

        # Update quality summary for individual fixes
        current_errors = []
        current_errors.extend(new_validation_results["remaining_errors"])
        for fix_group in new_validation_results["grouped_fixes"]:
            current_errors.extend(fix_group["errors"])

        quality_summary = validator.generate_quality_summary(
            st.session_state.initial_errors,
            current_errors,
            st.session_state.applied_fixes,
        )
        st.session_state.quality_summary = quality_summary

        # Show success message
        fix_count = len(fixes_to_apply)
        st.success(
            f"✅ Applied {fix_count} fix{'es' if fix_count > 1 else ''} successfully!"
        )

        # Show summary of what was fixed
        with st.expander("View Applied Fixes", expanded=False):
            applied_df = pd.DataFrame(fixes_to_apply)
            st.dataframe(applied_df, width="stretch")


def preview_fixes(errors: List[Dict]):
    """
    Preview what the fixes would look like.
    """
    st.write("**Preview of suggested changes:**")

    preview_data = []
    for error in errors:
        if error.get("suggested_fix") is not None:
            preview_data.append(
                {
                    "Row": error["row"],
                    "Column": error["column"],
                    "Current Value": error["value"],
                    "Suggested Fix": error["suggested_fix"],
                    "Change": f"'{error['value']}' → '{error['suggested_fix']}'",
                }
            )

    if preview_data:
        preview_df = pd.DataFrame(preview_data)
        st.dataframe(preview_df, width="stretch")
    else:
        st.info("No fixable issues in this group.")


def display_quality_summary():
    """
    Display the data quality summary on the review page.
    """
    if "quality_summary" not in st.session_state:
        st.info(
            "No quality summary available. Please complete the data validation step first."
        )
        return

    summary = st.session_state.quality_summary

    # Debug info
    st.write(f"🔍 Debug: Quality summary data:")
    st.write(f"- Initial errors: {summary.get('total_initial_errors', 'N/A')}")
    st.write(f"- Final errors: {summary.get('total_final_errors', 'N/A')}")
    st.write(f"- Total fixes applied: {summary.get('total_fixes_applied', 'N/A')}")
    st.write(f"- AI fixes: {summary.get('ai_fixes_applied', 'N/A')}")
    st.write(
        f"- Deterministic fixes: {summary.get('deterministic_fixes_applied', 'N/A')}"
    )
    st.markdown("---")

    st.subheader("📋 Data Quality Summary")
    st.write("Overview of data quality issues found and resolved during validation.")

    # Overall metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Initial Issues", summary["total_initial_errors"])
    col2.metric("Issues Fixed", summary["total_fixes_applied"])
    col3.metric("Remaining Issues", summary["total_final_errors"])
    col4.metric("Improvement", f"{summary['improvement_percentage']:.1f}%")

    # Show breakdown of fix types if both types were used
    if (
        summary.get("ai_fixes_applied", 0) > 0
        or summary.get("deterministic_fixes_applied", 0) > 0
    ):
        st.markdown("---")
        st.subheader("🔧 Fix Type Breakdown")

        col1, col2, col3 = st.columns(3)
        col1.metric("🤖 AI Fixes", summary.get("ai_fixes_applied", 0))
        col2.metric(
            "⚙️ Deterministic Fixes", summary.get("deterministic_fixes_applied", 0)
        )
        col3.metric("📈 Total Applied", summary["total_fixes_applied"])

    if summary["total_initial_errors"] == 0:
        st.success("🎉 Your data was already clean! No validation issues were found.")
        return

    # Error breakdown by type
    if summary["error_breakdown"]:
        st.subheader("🔍 Issues by Error Type")

        error_data = []
        for error_type, data in summary["error_breakdown"].items():
            error_data.append(
                {
                    "Error Type": error_type,
                    "Total Found": data["total_found"],
                    "Fixed": data["fixed"],
                    "Remaining": data["remaining"],
                    "Columns Affected": ", ".join(data["columns_affected"]),
                }
            )

        error_df = pd.DataFrame(error_data)
        st.dataframe(error_df, width="stretch")

    # Column-wise breakdown
    if summary["column_summary"]:
        st.subheader("📋 Issues by Column")

        column_data = []
        for column, data in summary["column_summary"].items():
            if data["total_errors"] > 0:  # Only show columns that had errors
                column_data.append(
                    {
                        "Column": column,
                        "Total Issues": data["total_errors"],
                        "Fixed": data["errors_fixed"],
                        "Remaining": data["errors_remaining"],
                        "Error Types": ", ".join(data["error_types"]),
                    }
                )

        if column_data:
            column_df = pd.DataFrame(column_data)
            st.dataframe(column_df, width="stretch")
        else:
            st.info("All columns are now clean!")

    # Quality improvement message
    st.markdown("---")

    if summary["total_final_errors"] == 0:
        st.success(
            "🎉 **Perfect!** All data quality issues have been resolved. Your data is now fully compliant with the canonical schema."
        )
    elif summary["improvement_percentage"] > 0:
        st.info(
            f"📈 **Good progress!** Data quality improved by {summary['improvement_percentage']:.1f}%. {summary['total_final_errors']} issues remain that require manual attention."
        )
    else:
        st.warning(
            "⚠️ No automatic fixes were applied. All issues require manual review."
        )

    # Recommendations
    if summary["total_final_errors"] > 0:
        st.subheader("💡 Recommendations")
        st.write("For remaining issues:")
        st.write("• Review the data source to prevent similar issues in future imports")
        st.write("• Consider manual corrections for critical data points")
        st.write("• Document any acceptable exceptions for business rules")
        st.write("• Set up data validation at the source to catch issues early")


def apply_all_fixes_global(grouped_fixes: List[Dict[str, Any]]):
    """
    Apply all suggested fixes from all groups at once.
    """
    validator = DataValidator()

    # Collect all errors with suggested fixes
    all_errors_to_fix = []
    fix_summary = {}

    for group in grouped_fixes:
        group_errors = group["errors"]
        fixable_errors = [
            error for error in group_errors if error.get("suggested_fix") is not None
        ]

        if fixable_errors:
            all_errors_to_fix.extend(fixable_errors)

            # Track what's being fixed by category
            fix_type = group["description"]
            fix_summary[fix_type] = len(fixable_errors)

    if not all_errors_to_fix:
        st.warning("⚠️ No fixable errors found in the current groups.")
        return

    # Prepare fixes for application
    fixes_to_apply = []
    for error in all_errors_to_fix:
        fixes_to_apply.append(
            {
                "row": error["row"],
                "column": error["column"],
                "new_value": error["suggested_fix"],
            }
        )

    # Apply all fixes to the dataframe
    updated_df = validator.apply_fixes(st.session_state.transformed_df, fixes_to_apply)
    st.session_state.transformed_df = updated_df

    # Track applied fixes
    st.session_state.applied_fixes.extend(fixes_to_apply)

    # Re-run validation to update results
    new_validation_results = validator.validate_and_suggest_fixes(updated_df)
    st.session_state.validation_results = new_validation_results

    # Update quality summary for global fixes
    current_errors = []
    current_errors.extend(new_validation_results["remaining_errors"])
    for fix_group in new_validation_results["grouped_fixes"]:
        current_errors.extend(fix_group["errors"])

    quality_summary = validator.generate_quality_summary(
        st.session_state.initial_errors, current_errors, st.session_state.applied_fixes
    )
    st.session_state.quality_summary = quality_summary

    # Show comprehensive success message
    total_fixes = len(fixes_to_apply)
    st.success(f"✅ Applied **{total_fixes}** fixes across all categories!")

    # Show detailed breakdown
    with st.expander(f"📋 View Summary of {total_fixes} Applied Fixes", expanded=False):
        st.write("**Fixes applied by category:**")

        for fix_type, count in fix_summary.items():
            st.write(f"• **{fix_type}**: {count} fixes")

        st.markdown("---")
        st.write("**Detailed list of applied fixes:**")

        applied_df = pd.DataFrame(fixes_to_apply)
        if not applied_df.empty:
            # Group by column for better readability
            for column in applied_df["column"].unique():
                column_fixes = applied_df[applied_df["column"] == column]
                st.write(f"**{column}** ({len(column_fixes)} fixes):")
                st.dataframe(column_fixes[["row", "new_value"]], width="stretch")

    # Show improvement metrics
    remaining_fixable = sum(
        len(group["errors"]) for group in new_validation_results["grouped_fixes"]
    )
    remaining_total = new_validation_results["total_errors"]

    if remaining_total == 0:
        st.balloons()
        st.success("🎉 **Perfect!** All validation issues have been resolved!")
    elif remaining_fixable == 0:
        st.info(
            f"✨ **Great progress!** All auto-fixable issues resolved. {remaining_total} manual issues remain."
        )
    else:
        st.info(
            f"📈 **Progress made!** {remaining_fixable} more auto-fixable issues available, {remaining_total} total issues remain."
        )


def get_ai_fix_suggestions(remaining_errors: List[Dict]):
    """
    Get AI suggestions for remaining errors.
    """
    if not CONSTANTS.USE_GEMINI:
        st.error("❌ AI features are disabled. Please enable Gemini to use AI fixes.")
        return

    gemini_agent = GeminiAgent()
    df = st.session_state.transformed_df

    ai_suggestions = []

    with st.spinner(f"🤖 Analyzing {len(remaining_errors)} errors with AI..."):
        progress_bar = st.progress(0)

        for i, error in enumerate(remaining_errors):
            try:
                # Get AI suggestion for this error
                suggestion = gemini_agent.suggest_data_fix(error, df)

                if suggestion:
                    ai_suggestions.append(
                        {
                            "error": error,
                            "ai_suggestion": suggestion,
                            "status": "pending",  # pending, approved, rejected
                        }
                    )
                else:
                    ai_suggestions.append(
                        {
                            "error": error,
                            "ai_suggestion": None,
                            "status": "no_suggestion",
                        }
                    )

                # Update progress
                progress_bar.progress((i + 1) / len(remaining_errors))

            except Exception as e:
                st.error(
                    f"AI suggestion failed for error at row {error.get('row', 'unknown')}: {str(e)}"
                )
                ai_suggestions.append(
                    {"error": error, "ai_suggestion": None, "status": "failed"}
                )

        progress_bar.empty()

    # Store AI suggestions in session state
    st.session_state.ai_suggestions = ai_suggestions

    successful_suggestions = len(
        [s for s in ai_suggestions if s["ai_suggestion"] is not None]
    )

    if successful_suggestions > 0:
        st.success(
            f"✅ AI generated {successful_suggestions} suggestions out of {len(remaining_errors)} errors!"
        )
    else:
        st.warning(
            "⚠️ AI couldn't generate suggestions for any of the remaining errors."
        )


def display_ai_fix_suggestions():
    """
    Display AI fix suggestions with approve/reject options.
    """
    if "ai_suggestions" not in st.session_state or not st.session_state.ai_suggestions:
        return

    ai_suggestions = st.session_state.ai_suggestions

    # Count suggestions by status
    suggestions_with_fixes = [
        s for s in ai_suggestions if s["ai_suggestion"] is not None
    ]

    if not suggestions_with_fixes:
        return

    st.subheader("🎯 AI Suggestions")
    st.write(
        f"Review and approve AI suggestions for {len(suggestions_with_fixes)} errors:"
    )

    # Bulk actions
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("✅ Approve All AI Suggestions", key="approve_all_ai"):
            apply_bulk_ai_suggestions(suggestions_with_fixes, approve=True)
            st.rerun()

    with col2:
        if st.button("❌ Reject All AI Suggestions", key="reject_all_ai"):
            apply_bulk_ai_suggestions(suggestions_with_fixes, approve=False)
            st.rerun()

    with col3:
        approved_count = len(
            [s for s in suggestions_with_fixes if s["status"] == "approved"]
        )
        if approved_count > 0:
            if st.button(
                f"🚀 Apply {approved_count} Approved Fixes",
                key="apply_approved_ai",
                type="primary",
            ):
                apply_approved_ai_fixes()
                st.rerun()

    # Individual suggestions
    for i, suggestion_data in enumerate(suggestions_with_fixes):
        error = suggestion_data["error"]
        ai_suggestion = suggestion_data["ai_suggestion"]
        status = suggestion_data["status"]

        with st.expander(
            f"Row {error['row']} - {error['column']}: '{error['value']}' → '{ai_suggestion}'",
            expanded=(status == "pending"),
        ):
            col1, col2 = st.columns([3, 1])

            with col1:
                st.write(f"**Error:** {error['message']}")
                st.write(f"**Current Value:** `{error['value']}`")
                st.write(f"**AI Suggestion:** `{ai_suggestion}`")
                st.write(f"**Status:** {status.replace('_', ' ').title()}")

            with col2:
                if status == "pending":
                    if st.button("✅ Approve", key=f"approve_ai_{i}"):
                        st.session_state.ai_suggestions[
                            suggestions_with_fixes.index(suggestion_data)
                        ]["status"] = "approved"
                        st.rerun()

                    if st.button("❌ Reject", key=f"reject_ai_{i}"):
                        st.session_state.ai_suggestions[
                            suggestions_with_fixes.index(suggestion_data)
                        ]["status"] = "rejected"
                        st.rerun()
                elif status == "approved":
                    st.success("✅ Approved")
                elif status == "rejected":
                    st.error("❌ Rejected")


def apply_bulk_ai_suggestions(suggestions_with_fixes: List[Dict], approve: bool):
    """
    Apply bulk approve/reject to all AI suggestions.
    """
    new_status = "approved" if approve else "rejected"

    for suggestion_data in suggestions_with_fixes:
        # Find the index in the main ai_suggestions list
        for i, ai_sug in enumerate(st.session_state.ai_suggestions):
            if (
                ai_sug["error"] == suggestion_data["error"]
                and ai_sug["ai_suggestion"] == suggestion_data["ai_suggestion"]
            ):
                st.session_state.ai_suggestions[i]["status"] = new_status
                break

    action = "approved" if approve else "rejected"
    st.success(f"✅ {action.title()} {len(suggestions_with_fixes)} AI suggestions!")


def apply_approved_ai_fixes():
    """
    Apply all approved AI fixes to the dataframe.
    """
    if "ai_suggestions" not in st.session_state:
        return

    validator = DataValidator()
    approved_suggestions = [
        s
        for s in st.session_state.ai_suggestions
        if s["status"] == "approved" and s["ai_suggestion"] is not None
    ]

    if not approved_suggestions:
        st.warning("⚠️ No approved AI suggestions to apply.")
        return

    # Prepare fixes for application
    ai_fixes_to_apply = []
    for suggestion_data in approved_suggestions:
        error = suggestion_data["error"]
        ai_suggestion = suggestion_data["ai_suggestion"]

        ai_fixes_to_apply.append(
            {"row": error["row"], "column": error["column"], "new_value": ai_suggestion}
        )

    # Debug: Show before applying fixes
    st.info(f"🔍 Debug: Applying AI fixes to {len(ai_fixes_to_apply)} rows...")

    # Debug: Check if row indices are valid
    df = st.session_state.transformed_df
    for i, fix in enumerate(ai_fixes_to_apply):
        row_idx = fix["row"]
        column = fix["column"]
        if row_idx not in df.index:
            st.error(
                f"❌ Debug: Row index {row_idx} not found in dataframe (max index: {df.index.max()})"
            )
        elif column not in df.columns:
            st.error(f"❌ Debug: Column {column} not found in dataframe")
        else:
            old_value = df.at[row_idx, column]
            st.write(
                f"🔍 Debug Fix {i+1}: Row {row_idx}, {column}: '{old_value}' → '{fix['new_value']}'"
            )

    # Apply AI fixes to the dataframe
    original_df = st.session_state.transformed_df.copy()
    updated_df = validator.apply_fixes(
        st.session_state.transformed_df, ai_fixes_to_apply
    )

    # Debug: Check if dataframe actually changed
    if not original_df.equals(updated_df):
        st.success(f"✅ Debug: DataFrame successfully updated with AI fixes")

        # Show a sample of what changed
        for fix in ai_fixes_to_apply[:3]:  # Show first 3 fixes
            row_idx = fix["row"]
            column = fix["column"]
            new_value = fix["new_value"]
            old_value = original_df.at[row_idx, column]
            actual_new_value = updated_df.at[row_idx, column]
            st.write(
                f"Row {row_idx}, {column}: '{old_value}' → '{actual_new_value}' (expected: '{new_value}')"
            )
            if str(actual_new_value) != str(new_value):
                st.warning(
                    f"⚠️ Warning: Expected '{new_value}' but got '{actual_new_value}'"
                )

        # Show the actual dataframe rows that changed
        st.write("🔍 Debug: Updated rows in dataframe:")
        changed_rows = []
        for fix in ai_fixes_to_apply[:3]:
            changed_rows.append(fix["row"])
        if changed_rows:
            st.dataframe(updated_df.loc[changed_rows], width="stretch")
    else:
        st.error("❌ Debug: DataFrame was not updated - fixes may have failed")

    st.session_state.transformed_df = updated_df

    # Track applied fixes (mark them as AI fixes)
    for fix in ai_fixes_to_apply:
        fix["fix_type"] = "ai_fix"  # Mark as AI fix for summary

    st.session_state.applied_fixes.extend(ai_fixes_to_apply)

    # Re-run validation to update results
    new_validation_results = validator.validate_and_suggest_fixes(updated_df)
    st.session_state.validation_results = new_validation_results

    # Update quality summary with AI fixes applied
    current_errors = []
    current_errors.extend(new_validation_results["remaining_errors"])
    for fix_group in new_validation_results["grouped_fixes"]:
        current_errors.extend(fix_group["errors"])

    quality_summary = validator.generate_quality_summary(
        st.session_state.initial_errors, current_errors, st.session_state.applied_fixes
    )
    st.session_state.quality_summary = quality_summary

    # Clear AI suggestions since they've been applied
    st.session_state.ai_suggestions = []

    # Show success message
    fix_count = len(ai_fixes_to_apply)
    st.success(
        f"✅ Applied {fix_count} AI-suggested fix{'es' if fix_count > 1 else ''} successfully!"
    )

    # Show summary of what was fixed
    with st.expander("View Applied AI Fixes", expanded=False):
        applied_df = pd.DataFrame(ai_fixes_to_apply)
        st.dataframe(applied_df, width="stretch")

    # Show improvement metrics
    remaining_total = new_validation_results["total_errors"]

    # Debug: Show validation results
    st.write(f"🔍 Debug: After AI fixes - Total errors: {remaining_total}")
    st.write(
        f"🔍 Debug: Total fixes applied so far: {len(st.session_state.applied_fixes)}"
    )

    if remaining_total == 0:
        st.balloons()
        st.success(
            "🎉 **Perfect!** All validation issues have been resolved with AI assistance!"
        )
    else:
        st.info(
            f"📈 **Progress made!** {remaining_total} issues still remain after AI fixes."
        )
