# ================================================================
# src/validator.py
# ================================================================
# We are building this file together as a class.
#
# CONTEXT: We just ran Module 03 and extracted banking data from
# the banking database into raw-data.csv.
# Before we clean anything, we need to know WHAT is wrong.
# That is exactly what this file does.
#
# THE ANALOGY:
# Imagine you work in a hospital laboratory.
# Before a doctor can treat a patient, the lab runs tests first.
# The tests do not treat the patient — they just report what is wrong.
# A DataValidator is the lab test for your data.
# It NEVER changes the data. It only reads and reports.
#
# WHAT WE ARE BUILDING:
# A class called DataValidator with 5 methods:
#   1. check_not_empty()      → is there any data at all?
#   2. check_nulls()          → which columns have missing values?
#   3. check_duplicates()     → are any rows exact copies?
#   4. check_numeric_ranges() → are there impossible values in banking data?
#   5. compute_stats()        → summarise everything we found
#
# HOW WE USE IT (preview — we build this in etl_pipeline.py):
#   validator = DataValidator(raw_dataframe)
#   validator.check_not_empty().check_nulls().check_duplicates().compute_stats()
#   if validator._passed:
#       print("Data is good — proceed to transformation")
# ================================================================

# ── What are imports? ─────────────────────────────────────────────────
# When Python runs a file, it only knows about built-in functions (print, len, etc.)
# To use pandas, logging, or our config — we have to explicitly import them.
# Think of it like opening a toolbox before you can use the tools inside.

import sys       # sys lets us modify Python's module search path
import pathlib   # pathlib gives us cross-platform file path tools

# sys.path is a list of folders Python looks in when you write "import something".
# By default it does not include our project root folder.
# This block walks UP the folder tree until it finds config.py,
# then adds that folder to sys.path so Python can find our config module.
_root = pathlib.Path(__file__).resolve().parent   # start at src/ folder
while not (_root / "config.py").exists() and _root != _root.parent:
    _root = _root.parent   # move up one level: src/ → teaching-project/ → module-05/ → ...
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))   # add project root to Python's search path

# Now we can import from our project's config.py
import pandas as pd            # pandas: the core Python data library
                               # pd is the conventional short alias — everyone uses pd
from config import logger, MAX_NULL_PERCENT, MAX_DUPLICATE_PERCENT
# logger              → our shared logging object (prints timestamped messages)
# MAX_NULL_PERCENT    → threshold for flagging a column CRITICAL
# MAX_DUPLICATE_PERCENT → threshold for flagging duplicates CRITICAL


# ================================================================
# THE DataValidator CLASS
# ================================================================
# In Python, a class is a blueprint for creating objects.
# An object bundles together:
#   - DATA (called attributes or instance variables): self.df, self.issues
#   - BEHAVIOUR (called methods): check_nulls(), check_duplicates()
#
# Why use a class here instead of separate functions?
# ──────────────────────────────────────────────────
# If we used separate functions, each function would run and throw away its results.
# The class REMEMBERS everything. After running 5 checks, we can still read:
#   validator.issues     → all problems found
#   validator.stats      → summary statistics
#   validator._passed    → overall pass/fail result
#
# The ETLPipeline (etl_pipeline.py) will read these to make decisions.
# ================================================================

class DataValidator:
    """
    Inspects a raw DataFrame and reports all data quality issues.

    DESIGN PRINCIPLE: Read-Only
    This class never modifies the data. Its only job is to look and report.
    Fixing data is DataTransformer's responsibility.

    This separation (inspect vs fix) comes from the
    Single Responsibility Principle — each class does ONE thing well.
    """

    # ── CLASS ATTRIBUTES ─────────────────────────────────────────────────
    # Class attributes are defined at the class level (not inside any method).
    # They are SHARED by all instances of this class.
    # Think of them as settings that apply to every DataValidator we ever create.
    #
    # We use the values from config.py (imported above) so they are consistent
    # across the whole project.
    MAX_NULL_PCT = MAX_NULL_PERCENT
    MAX_DUP_PCT  = MAX_DUPLICATE_PERCENT

    def __init__(self, df: pd.DataFrame):
        """
        __init__ is the constructor — it runs automatically when you create an object.
        When you write:
            validator = DataValidator(my_dataframe)
        Python calls __init__(self, my_dataframe) for you.

        'self' refers to this specific instance being created.
        It is how a method accesses the object's own data.

        The colon in (df: pd.DataFrame) is a TYPE HINT.
        It tells you and your teammates: "df should be a pandas DataFrame."
        Python does not enforce this — it is documentation for humans.

        Args:
            df    the raw DataFrame to inspect
        """

        # df.copy() creates an INDEPENDENT copy of the DataFrame in memory.
        # If we stored df directly (self.df = df), then any changes to self.df
        # would also change the original df in the caller's code.
        # That would be a very hard-to-find bug.
        # Copying is defensive programming — we protect the caller's data.
        self.df = df.copy()

        # self.issues is a list that starts empty and grows as we find problems.
        # Each problem is stored as a dictionary with keys: severity, column, message.
        # Example: {"severity": "WARNING", "column": "account_balance", "message": "23 nulls (1.9%)"}
        self.issues = []

        # self.stats is a dictionary that will hold summary statistics.
        # It is filled by compute_stats() and used by the pipeline's report.
        self.stats = {}

        # self._passed starts True (we assume the data is good).
        # If any CRITICAL issue is found, it flips to False.
        # The underscore prefix (_passed) is a Python convention meaning:
        #   "This is for internal use — please do not access it directly from outside."
        self._passed = True

    # ================================================================
    # THE 5 CHECK METHODS
    # ================================================================
    # Notice: every check method returns 'self' at the end.
    # This enables METHOD CHAINING — calling multiple methods in sequence:
    #   validator.check_not_empty().check_nulls().check_duplicates()
    # Without returning self, you would have to write:
    #   validator.check_not_empty()
    #   validator.check_nulls()
    #   validator.check_duplicates()
    # Both work. Method chaining reads more naturally for pipelines.
    # ================================================================

    def check_not_empty(self) -> "DataValidator":
        """
        Check 1: Does the DataFrame have any rows at all?

        Why this check exists:
        ─────────────────────────
        If the SQL query in Module 03 had a bug in the WHERE clause,
        it might return zero rows. Every downstream check on zero rows
        would either crash or produce meaningless results.
        We catch this immediately and stop early.

        "Fail fast" is an engineering principle:
        detect problems as early as possible, as close to the source as possible.

        Return type hint -> "DataValidator":
        The quotes around DataValidator are needed because we are inside
        the class definition — DataValidator is not fully defined yet
        when Python reads this line. The quotes tell Python:
        "this refers to the class we are currently defining."
        """

        # len() returns the number of rows in a DataFrame
        if len(self.df) == 0:

            # _add_issue() is our internal helper (defined below).
            # CRITICAL severity means the pipeline should stop.
            # This row-count problem affects the whole dataset, not just one column,
            # so we use "row_count" as the column name.
            self._add_issue(
                severity="CRITICAL",
                column="row_count",
                message=(
                    "DataFrame has 0 rows. "
                    "Check that Module 03 ran successfully and "
                    "that INDUSTRY in config.py is correct."
                )
            )

            # Flip the pass flag — this is a showstopper
            self._passed = False

        else:
            # f-string with :, formatting:
            # {len(self.df):,} formats the number with comma separators
            # e.g. 1200 → "1,200"   1000000 → "1,000,000"
            logger.info(f"[VALIDATE] Row count: {len(self.df):,} rows ✓")

        # Return self enables chaining: .check_not_empty().check_nulls()
        return self

    def check_nulls(self) -> "DataValidator":
        """
        Check 2: Which columns have missing (null/NaN) values?

        WHAT IS A NULL VALUE?
        ─────────────────────
        NULL in SQL, NaN in pandas — both mean "no value here."
        Not zero. Not empty string. The ABSENCE of a value.

        NULL values are dangerous because:
          - account_balance.mean() on a column with NaN gives misleading results
          - You cannot compare NaN to anything: NaN != NaN (in math!)
          - ML models cannot handle NaN — training will crash or produce garbage

        WHERE DO NULLS COME FROM?
        ──────────────────────────
        - LEFT JOINs in SQL: when the right table has no match, the joined
          columns become NULL for that row.
        - Optional customer records where account details were not filled.
        - System migrations: data that was never collected in the old banking system.

        OUR THRESHOLDS:
        ────────────────
        0%  to 50% null → WARNING (we note it but the pipeline continues)
        >50% null        → CRITICAL (more than half missing — column is unreliable)
        """

        # self.df.isna() returns a DataFrame of True/False values.
        # True wherever there is a null, False everywhere else.
        # .sum() on a boolean DataFrame counts the True values per column.
        # The result is a Series: column_name → count_of_nulls
        null_counts = self.df.isna().sum()

        # Loop through each column name and its null count
        for col, count in null_counts.items():

            # If this column has no nulls, nothing to report — skip it
            if count == 0:
                continue   # 'continue' immediately jumps to the next loop iteration

            # Calculate what percentage of this column's values are null
            # count: number of nulls in this column
            # len(self.df): total number of rows
            # Multiply by 100 to get percentage, round to 1 decimal place
            pct = round(count / len(self.df) * 100, 1)

            # Classify severity based on our threshold
            if pct > self.MAX_NULL_PCT:
                severity = "CRITICAL"     # more than half the column is missing
                self._passed = False      # flip the overall pass flag
            else:
                severity = "WARNING"      # some nulls, but manageable

            self._add_issue(
                severity=severity,
                column=col,
                message=f"{count:,} null values ({pct}% of rows)"
            )

        # Log how many columns had ANY nulls
        n_cols_with_nulls = int((null_counts > 0).sum())
        logger.info(
            f"[VALIDATE] Null check complete — "
            f"{n_cols_with_nulls} columns have null values"
        )

        return self

    def check_duplicates(self) -> "DataValidator":
        """
        Check 3: Are any rows exact copies of another row?

        WHAT IS A DUPLICATE ROW?
        ─────────────────────────
        A duplicate is a row where EVERY column value is identical to
        another row in the same DataFrame.

        HOW DO DUPLICATES ENTER PRODUCTION DATA?
        ──────────────────────────────────────────
        1. SQL JOIN ERRORS
           A JOIN between customers, accounts, transactions, and branches where
           the join key is not unique creates multiple copies of each banking row.

        2. PIPELINE RAN TWICE
           An ETL pipeline was triggered twice by a scheduling bug.
           The same records were inserted into the database twice.

        3. MANUAL DATA ENTRY
           Someone imported a spreadsheet twice.

        WHY DUPLICATES HURT YOUR ANALYSIS:
        ────────────────────────────────────
        If one customer transaction appears 3 times:
          - Your total transaction amount is overstated
          - Your account activity analysis becomes biased
          - Your customer risk or profitability report becomes inaccurate
        """

        # df.duplicated() returns a boolean Series.
        # True for every row that is an EXACT copy of a previous row.
        # keep="first" means the FIRST occurrence is NOT flagged — only copies are.
        # .sum() counts the True values (number of duplicate rows)
        dup_count = int(self.df.duplicated(keep="first").sum())

        # Only record if there are any duplicates
        if dup_count > 0:

            # Calculate the percentage of rows that are duplicates
            dup_pct = round(dup_count / len(self.df) * 100, 1)

            # Classify severity
            if dup_pct > self.MAX_DUP_PCT:
                severity = "CRITICAL"
                self._passed = False
            else:
                severity = "WARNING"

            self._add_issue(
                severity=severity,
                column="duplicates",   # not a column — "duplicates" describes the issue type
                message=(
                    f"{dup_count:,} exact duplicate rows "
                    f"({dup_pct}% of dataset)"
                )
            )
        else:
            logger.info("[VALIDATE] Duplicate check: 0 duplicate rows found ✓")

        return self

    def check_numeric_ranges(self) -> "DataValidator":
        """
        Check 4: Do numeric columns have values that are logically impossible?

        EXAMPLES OF IMPOSSIBLE VALUES:
        ────────────────────────────────
        account_balance      = -5000   → A balance may be negative only for overdraft accounts
        transaction_amount   = -300    → Transaction amount should not be negative unless represented as a withdrawal
        credit_score         = 1000    → Credit scores should normally be between 300 and 900
        interest_rate        = 150     → Interest rate should normally be between 0 and 100
        credit_utilization_pct = 140   → Credit utilization should be between 0 and 100

        WHERE DO IMPOSSIBLE VALUES COME FROM?
        ──────────────────────────────────────
        - Sign errors in calculations
        - Unit mismatches
        - Data entry errors
        - Bad SQL: old values and new values joined or calculated incorrectly

        IMPORTANT — SOME NEGATIVES ARE VALID:
        ───────────────────────────────────────
        "Difference" columns legitimately go negative:
          balance_difference = -500 means this customer's balance is below the benchmark
          payment_difference = -200 means the customer paid less than expected
          transaction_delta = -100 means transaction value decreased

        We skip these columns because negative values are expected there.
        """

        # These column names represent differences/deltas — negatives are expected
        DELTA_COLUMNS = {
            "balance_difference",
            "transaction_delta",
            "interest_delta",
            "loan_balance_gap",
            "branch_transaction_gap",
            "customer_balance_gap",
            "credit_score_difference",
            "payment_difference",
            "deposit_withdrawal_gap",
            "account_variance",
        }

        # select_dtypes(include=["number"]) returns ONLY numeric columns.
        # This automatically skips text columns like "department" or "email"
        # where you cannot meaningfully check for negatives.
        for col in self.df.select_dtypes(include=["number"]).columns:

            if col in DELTA_COLUMNS:
                continue   # skip — negatives are expected in this column

            # Count how many values in this column are less than zero
            # (self.df[col] < 0) creates a boolean Series: True where value < 0
            # .sum() counts the True values
            neg_count = int((self.df[col] < 0).sum())

            if neg_count > 0:
                self._add_issue(
                    severity="WARNING",
                    column=col,
                    message=(
                        f"{neg_count} unexpected negative values. "
                        f"Check if '{col}' should always be positive."
                    )
                )

            if col == "interest_rate":
                invalid_interest_rate = int(((self.df[col] < 0) | (self.df[col] > 100)).sum())

                if invalid_interest_rate > 0:
                    self._add_issue(
                        severity="WARNING",
                        column=col,
                        message=(
                            f"{invalid_interest_rate} invalid interest rate values. "
                            "Interest rate should be between 0 and 100."
                        )
                    )

            if col == "credit_utilization_pct":
                invalid_credit_utilization = int(((self.df[col] < 0) | (self.df[col] > 100)).sum())

                if invalid_credit_utilization > 0:
                    self._add_issue(
                        severity="WARNING",
                        column=col,
                        message=(
                            f"{invalid_credit_utilization} invalid credit utilization values. "
                            "Credit utilization percentage should be between 0 and 100."
                        )
                    )

            if col == "credit_score":
                invalid_credit_score = int(((self.df[col] < 300) | (self.df[col] > 900)).sum())

                if invalid_credit_score > 0:
                    self._add_issue(
                        severity="WARNING",
                        column=col,
                        message=(
                            f"{invalid_credit_score} invalid credit score values. "
                            "Credit score should normally be between 300 and 900."
                        )
                    )

        return self

    def compute_stats(self) -> "DataValidator":
        """
        Check 5 (not really a check — a summary): Compute dataset statistics.

        This gathers key facts about the dataset in one dictionary.
        These stats are used by:
          - ETLPipeline.report() to show what we received
          - Module 06 EDA engine as a starting profile
          - Module 14 MLOps monitor as the baseline for drift detection

        WHAT IS A DICTIONARY?
        ──────────────────────
        A dictionary (dict) maps keys to values:
            my_dict = {"name": "Kwame", "account_balance": 92000}
            my_dict["account_balance"]  → 92000

        self.stats is a dict where each key is a metric name
        and each value is the measured value for that metric.
        """

        # Count numeric columns by using select_dtypes to filter
        # .columns gives us the column names as an Index object
        # len() counts how many there are
        num_col_count = len(self.df.select_dtypes(include=["number"]).columns)
        txt_col_count = len(self.df.select_dtypes(include=["object"]).columns)
        boo_col_count = len(self.df.select_dtypes(include=["bool"]).columns)

        self.stats = {
            "rows":            len(self.df),
            "columns":         len(self.df.columns),
            "numeric_cols":    num_col_count,
            "text_cols":       txt_col_count,
            "bool_cols":       boo_col_count,
            "total_nulls":     int(self.df.isna().sum().sum()),
            "null_pct":        round(self.df.isna().sum().sum() / self.df.size * 100, 2),
            "duplicates":      int(self.df.duplicated().sum()),
            "memory_mb":       round(self.df.memory_usage(deep=True).sum() / 1024**2, 2),
            "total_issues":    len(self.issues),
            "critical_count":  sum(1 for i in self.issues if i["severity"] == "CRITICAL"),
            "warning_count":   sum(1 for i in self.issues if i["severity"] == "WARNING"),
            "passed":          self._passed,
        }

        logger.info(
            f"[VALIDATE] Stats computed: "
            f"{self.stats['rows']:,} rows | "
            f"{self.stats['total_nulls']:,} nulls | "
            f"{self.stats['total_issues']} issues found | "
            f"result: {'PASSED ✓' if self._passed else 'FAILED ✗'}"
        )

        return self

    # ================================================================
    # PRIVATE HELPER METHOD
    # ================================================================

    def _add_issue(self, severity: str, column: str, message: str) -> None:
        """
        Record one data quality issue in self.issues.
        """

        issue = {
            "severity": severity,
            "column": column,
            "message": message,
        }

        self.issues.append(issue)

        if severity == "CRITICAL":
            logger.error(f"[VALIDATE] CRITICAL | {column} | {message}")
        else:
            logger.warning(f"[VALIDATE] WARNING  | {column} | {message}")

    # ================================================================
    # DUNDER (MAGIC) METHODS
    # ================================================================

    def __str__(self) -> str:
        """
        Called automatically when you write print(validator).
        Should return a SHORT, human-readable summary.
        """
        status = "PASSED ✓" if self._passed else "FAILED ✗"
        return (
            f"DataValidator("
            f"result={status} | "
            f"{len(self.issues)} issues found | "
            f"{len(self.df):,} rows inspected)"
        )

    def __repr__(self) -> str:
        """
        Called in the Python REPL and debugger.
        Should return a string that shows the object's key state.
        """
        return (
            f"DataValidator("
            f"rows={len(self.df):,}, "
            f"issues={len(self.issues)}, "
            f"passed={self._passed})"
        )


# ================================================================
# QUICK SELF-TEST
# ================================================================

if __name__ == "__main__":
    # Create some test data — a small fake DataFrame
    import pandas as pd

    print("Running DataValidator self-test...")
    print("=" * 50)

    # Test 1: Clean data — should pass
    clean_df = pd.DataFrame({
        "customer_id": [1, 2, 3, 4, 5],
        "branch_name": ["Calgary", "Edmonton", "Red Deer", "Airdrie", "Lethbridge"],
        "account_type": ["Savings", "Checking", "Business", "Student", "Credit"],
        "transaction_count": [12, 8, 15, 6, 20],
        "account_balance": [12000, 8500, 42000, 3500, 15000],
        "interest_rate": [2.5, 1.8, 3.1, 1.2, 2.9],
        "transaction_amount": [450, 1200, 7800, 320, 950],
        "credit_score": [720, 680, 750, 640, 700],
        "credit_utilization_pct": [25, 40, 10, 55, 30],
    })

    v1 = DataValidator(clean_df)
    v1.check_not_empty().check_nulls().check_duplicates().check_numeric_ranges().compute_stats()
    print(f"Test 1 (clean data): {v1}")

    # Test 2: Data with nulls — should warn
    dirty_df = clean_df.copy()
    dirty_df.loc[0, "transaction_amount"] = None   # introduce one null
    dirty_df.loc[1, "interest_rate"] = 150
    dirty_df.loc[2, "credit_score"] = 1000
    dirty_df.loc[3, "credit_utilization_pct"] = 140

    v2 = DataValidator(dirty_df)
    v2.check_not_empty().check_nulls().check_duplicates().check_numeric_ranges().compute_stats()
    print(f"Test 2 (with null): {v2}")

    # Test 3: Empty data — should FAIL
    empty_df = pd.DataFrame()
    v3 = DataValidator(empty_df)
    v3.check_not_empty()
    print(f"Test 3 (empty):     {v3}")

    print("\nSelf-test complete.")