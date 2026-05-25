# ================================================================
# src/transformer.py
# ================================================================
# CONTEXT: DataValidator told us WHAT is wrong.
# This file FIXES it.
#
# THE ANALOGY:
# The validator was the doctor running blood tests.
# The transformer is the pharmacist filling the prescription.
# The validator said: "23 missing account balance values, 13 duplicate rows."
# The transformer says: "Fill those 23 with the median. Remove those 13."
#
# WHAT WE ARE BUILDING:
# A class called DataTransformer with 5 transformation steps:
#   1. fill_nulls()          → replace missing values with appropriate defaults
#   2. drop_duplicates()     → remove exact copy rows
#   3. fix_types()           → ensure numeric columns actually ARE numeric
#   4. add_derived_columns() → create new useful columns from existing ones
#   5. add_metadata()        → stamp each row with pipeline tracking information
#
# IMMUTABILITY PRINCIPLE:
# Just like the validator, the transformer ALWAYS works on a copy of the data.
# We never modify the original. This means:
#   - If something goes wrong, we can always start fresh from the original
#   - Calling transformer.fill_nulls() twice gives the same result (idempotent)
#   - The caller's data is never accidentally corrupted

import sys
import pathlib

_root = pathlib.Path(__file__).resolve().parent
while not (_root / "config.py").exists() and _root != _root.parent:
    _root = _root.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import pandas as pd
import numpy as np
import datetime

from config import INDUSTRY, logger


class DataTransformer:
    """
    Cleans and enriches a validated DataFrame.
    """

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self.original_len = len(df)
        self.changes = []

    # ================================================================
    # STEP 1: FILL NULL VALUES
    # ================================================================

    def fill_nulls(self) -> "DataTransformer":
        """
        Replace null values with appropriate defaults.
        """

        # Convert object date-looking columns first
        for col in self.df.columns:
            if "date" in col.lower() or "dob" in col.lower():
                self.df[col] = pd.to_datetime(self.df[col], errors="coerce")

        # Numeric columns → median
        for col in self.df.select_dtypes(include=["number"]).columns:
            n_nulls = int(self.df[col].isna().sum())

            if n_nulls == 0:
                continue

            median_value = self.df[col].median()

            if pd.isna(median_value):
                median_value = 0

            self.df[col] = self.df[col].fillna(median_value)

            self._record_change(
                f"Filled {n_nulls} nulls in '{col}' with median ({median_value:.2f})"
            )

        # Text columns → Unknown
        for col in self.df.select_dtypes(include=["object"]).columns:
            n_nulls = int(self.df[col].isna().sum())

            if n_nulls == 0:
                continue

            self.df[col] = self.df[col].fillna("Unknown")

            self._record_change(
                f"Filled {n_nulls} nulls in '{col}' with 'Unknown'"
            )

        # Boolean columns → False
        for col in self.df.select_dtypes(include=["bool"]).columns:
            n_nulls = int(self.df[col].isna().sum())

            if n_nulls == 0:
                continue

            self.df[col] = self.df[col].fillna(False)

            self._record_change(
                f"Filled {n_nulls} nulls in '{col}' with False"
            )

        # Datetime columns → median/most common date where possible
        for col in self.df.select_dtypes(include=["datetime"]).columns:
            n_nulls = int(self.df[col].isna().sum())

            if n_nulls == 0:
                continue

            valid_dates = self.df[col].dropna()

            if len(valid_dates) > 0:
                fill_value = valid_dates.median()
            else:
                fill_value = pd.Timestamp.today().normalize()

            self.df[col] = self.df[col].fillna(fill_value)

            self._record_change(
                f"Filled {n_nulls} nulls in '{col}' with valid date"
            )

        remaining = int(self.df.isna().sum().sum())

        logger.info(
            f"[TRANSFORM] fill_nulls complete. Remaining nulls: {remaining}"
        )

        return self

    # ================================================================
    # STEP 2: DROP DUPLICATE ROWS
    # ================================================================

    def drop_duplicates(self) -> "DataTransformer":
        """
        Remove rows that are exact copies of a previous row.
        """

        before = len(self.df)

        self.df = self.df.drop_duplicates(keep="first")
        self.df = self.df.reset_index(drop=True)

        removed = before - len(self.df)

        if removed > 0:
            self._record_change(
                f"Removed {removed} duplicate rows ({before:,} → {len(self.df):,})"
            )
        else:
            logger.info("[TRANSFORM] drop_duplicates: no duplicates found")

        return self

    # ================================================================
    # STEP 3: FIX DATA TYPES
    # ================================================================

    def fix_types(self) -> "DataTransformer":
        """
        Ensure numeric and date columns are stored in correct formats.
        """

        # Convert numeric-looking text columns
        for col in self.df.columns:
            if self.df[col].dtype != object:
                continue

            converted = pd.to_numeric(self.df[col], errors="coerce")

            original_non_null = int(self.df[col].notna().sum())
            converted_non_null = int(converted.notna().sum())

            if original_non_null == 0:
                continue

            if converted_non_null >= original_non_null * 0.8:
                self.df[col] = converted

                self._record_change(
                    f"Converted '{col}' from text to numeric "
                    f"({converted_non_null}/{original_non_null} values converted)"
                )

        # Convert banking date columns
        for col in self.df.columns:
            if "date" in col.lower() or "dob" in col.lower():
                before_type = str(self.df[col].dtype)
                self.df[col] = pd.to_datetime(self.df[col], errors="coerce")
                after_type = str(self.df[col].dtype)

                if before_type != after_type:
                    self._record_change(
                        f"Converted '{col}' to datetime"
                    )

        logger.info("[TRANSFORM] fix_types complete")

        return self

    # ================================================================
    # # STEP 4: ADD DERIVED COLUMNS
    # ================================================================

    def add_derived_columns(self) -> "DataTransformer":
        """
        Create new banking-specific columns computed from existing columns.
        """

        # ------------------------------------------------------------
        # Banking derived column: net_transaction_amount
        # ------------------------------------------------------------
        if "transaction_amount" in self.df.columns:
            transaction_amount = pd.to_numeric(
                self.df["transaction_amount"], errors="coerce"
            ).fillna(0)

            if "fee_amount" in self.df.columns:
                fee_amount = pd.to_numeric(
                    self.df["fee_amount"], errors="coerce"
                ).fillna(0)
            else:
                fee_amount = 0

            self.df["net_transaction_amount"] = (
                transaction_amount - fee_amount
            ).round(2)

            self._record_change(
                "Added derived column 'net_transaction_amount' from transaction_amount - fee_amount"
            )

        # ------------------------------------------------------------
        # Banking derived column: balance_after_transaction
        # ------------------------------------------------------------
        if "account_balance" in self.df.columns and "transaction_amount" in self.df.columns:
            account_balance = pd.to_numeric(
                self.df["account_balance"], errors="coerce"
            ).fillna(0)

            transaction_amount = pd.to_numeric(
                self.df["transaction_amount"], errors="coerce"
            ).fillna(0)

            self.df["balance_after_transaction"] = (
                account_balance - transaction_amount
            ).round(2)

            self._record_change(
                "Added derived column 'balance_after_transaction' from account_balance - transaction_amount"
            )

        # ------------------------------------------------------------
        # Banking derived column: estimated_interest_amount
        # ------------------------------------------------------------
        if "account_balance" in self.df.columns and "interest_rate" in self.df.columns:
            account_balance = pd.to_numeric(
                self.df["account_balance"], errors="coerce"
            ).fillna(0)

            interest_rate = pd.to_numeric(
                self.df["interest_rate"], errors="coerce"
            ).fillna(0)

            self.df["estimated_interest_amount"] = (
                account_balance * interest_rate / 100
            ).round(2)

            self._record_change(
                "Added derived column 'estimated_interest_amount' from account_balance × interest_rate"
            )

        # ------------------------------------------------------------
        # Banking derived column: credit_risk_band
        # ------------------------------------------------------------
        if "credit_score" in self.df.columns:
            credit_score = pd.to_numeric(
                self.df["credit_score"], errors="coerce"
            )

            self.df["credit_risk_band"] = pd.cut(
                credit_score,
                bins=[0, 579, 669, 739, 799, 900],
                labels=["Poor", "Fair", "Good", "Very Good", "Excellent"],
                include_lowest=True
            ).astype("object").fillna("Unknown")

            self._record_change(
                "Added derived column 'credit_risk_band' from credit_score"
            )

        # ------------------------------------------------------------
        # Banking derived column: transaction_month
        # ------------------------------------------------------------
        if "transaction_date" in self.df.columns:
            transaction_date = pd.to_datetime(
                self.df["transaction_date"], errors="coerce"
            )

            self.df["transaction_month"] = transaction_date.dt.to_period("M").astype(str)

            self._record_change(
                "Added derived column 'transaction_month' from transaction_date"
            )

        # ------------------------------------------------------------
        # IQR outlier detection
        # ------------------------------------------------------------
        numeric_cols = self.df.select_dtypes(include=["number"]).columns.tolist()

        preferred_cols = [
            "transaction_amount",
            "net_transaction_amount",
            "account_balance",
            "balance_after_transaction",
            "estimated_interest_amount",
            "interest_rate",
            "fee_amount",
            "credit_score",
            "credit_utilization_pct"
        ]

        selected_cols = [col for col in preferred_cols if col in numeric_cols]

        if not selected_cols:
            selected_cols = numeric_cols[:3]

        outlier_flag_columns = []

        for col in selected_cols[:3]:
            Q1 = self.df[col].quantile(0.25)
            Q3 = self.df[col].quantile(0.75)
            IQR = Q3 - Q1

            lower_fence = Q1 - 1.5 * IQR
            upper_fence = Q3 + 1.5 * IQR

            flag_col = f"{col}_is_outlier"

            self.df[flag_col] = (
                (self.df[col] < lower_fence) |
                (self.df[col] > upper_fence)
            )

            outlier_flag_columns.append(flag_col)

            self._record_change(
                f"Added outlier flag '{flag_col}' "
                f"(bounds: {lower_fence:.2f} to {upper_fence:.2f})"
            )

        if outlier_flag_columns:
            self.df["is_any_outlier"] = self.df[outlier_flag_columns].any(axis=1)
            n_outliers = int(self.df["is_any_outlier"].sum())

            self._record_change(
                f"Added 'is_any_outlier': {n_outliers} rows flagged "
                f"({round(n_outliers / len(self.df) * 100, 1)}% of dataset)"
            )

        logger.info(
            f"[TRANSFORM] add_derived_columns complete: "
            f"{len(outlier_flag_columns)} outlier flags added"
        )

        return self

    # ================================================================
    # STEP 5: ADD PIPELINE METADATA
    # ================================================================

    def add_metadata(self) -> "DataTransformer":
        """
        Stamp every row with information about when and how it was processed.
        """

        self.df["_industry"] = INDUSTRY
        self.df["_processed_at"] = datetime.datetime.now().isoformat()
        self.df["_pipeline_version"] = "1.0.0"

        self._record_change(
            "Added metadata columns: _industry, _processed_at, _pipeline_version"
        )

        logger.info("[TRANSFORM] add_metadata complete")

        return self

    # ================================================================
    # HELPER METHODS
    # ================================================================

    def _record_change(self, message: str) -> None:
        """
        Record a transformation action in the audit trail and log it.
        """
        self.changes.append(message)
        logger.info(f"[TRANSFORM] {message}")

    def summary(self) -> dict:
        """
        Return a summary of all transformations applied.
        """
        return {
            "original_rows": self.original_len,
            "final_rows": len(self.df),
            "rows_removed": self.original_len - len(self.df),
            "final_columns": len(self.df.columns),
            "changes_count": len(self.changes),
            "change_log": self.changes,
        }

    # ================================================================
    # DUNDER METHODS
    # ================================================================

    def __str__(self) -> str:
        """Human-readable summary — shown by print(transformer)."""
        return (
            f"DataTransformer("
            f"{self.original_len:,} → {len(self.df):,} rows | "
            f"{len(self.changes)} changes applied)"
        )

    def __repr__(self) -> str:
        """Developer representation — shown in debugger."""
        return (
            f"DataTransformer("
            f"original={self.original_len}, "
            f"final={len(self.df)}, "
            f"changes={len(self.changes)})"
        )


# ================================================================
# QUICK SELF-TEST
# ================================================================
if __name__ == "__main__":
    print("Running DataTransformer banking self-test...")
    print("=" * 50)

    test_df = pd.DataFrame({
        "customer_id": [1, 2, 3, 3],
        "transaction_date": ["2026-01-05", "2026-01-08", None, None],
        "branch_name": ["Calgary Central", "Edmonton West", "Red Deer Branch", "Red Deer Branch"],
        "account_type": ["Savings", "Checking", "Business", "Business"],
        "transaction_type": ["Deposit", "Withdrawal", "Transfer", "Transfer"],
        "transaction_amount": [1200.00, 250.00, None, None],
        "fee_amount": [5.00, 2.50, None, None],
        "account_balance": [15000.00, 8200.00, 42000.00, 42000.00],
        "interest_rate": [2.5, None, 3.1, 3.1],
        "credit_score": [720, 680, 750, 750],
        "credit_utilization_pct": [25, 40, None, None],
    })

    print(
        f"Before transformation: "
        f"{len(test_df)} rows, {test_df.isna().sum().sum()} nulls"
    )

    t = DataTransformer(test_df)

    (
        t
        .fill_nulls()
        .drop_duplicates()
        .fix_types()
        .add_derived_columns()
        .add_metadata()
    )

    print(
        f"After transformation: "
        f"{len(t.df)} rows, {t.df.isna().sum().sum()} nulls"
    )

    print(f"Final columns: {t.df.columns.tolist()}")
    print(t.df.head())
    print(f"{t}")
    print("\nSelf-test complete.")