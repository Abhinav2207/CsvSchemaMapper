from typing import Any, Dict, List

import pandas as pd
import streamlit as st

from common_utils.constants import CONSTANTS
from common_utils.data_validator import DataValidator


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

    st.subheader("📋 Data Quality Summary")
    st.write("Overview of data quality issues found and resolved during validation.")

    # Overall metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Initial Issues", summary["total_initial_errors"])
    col2.metric("Issues Fixed", summary["total_fixes_applied"])
    col3.metric("Remaining Issues", summary["total_final_errors"])
    col4.metric("Improvement", f"{summary['improvement_percentage']:.1f}%")

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
