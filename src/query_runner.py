# ================================================================
# src/query_runner.py
# P02 Banking SQL — Query Runner
# ================================================================

import sys
import pathlib
import time
import pandas as pd

_root = pathlib.Path(__file__).resolve().parent
while not (_root / "config.py").exists() and _root != _root.parent:
    _root = _root.parent

if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from config import engine, DB_AVAILABLE, SQL_DIR, INDUSTRY, logger


class SQLQueryRunner:
    """
    Executes SQL queries against the banking PostgreSQL database.
    Returns SQL results as pandas DataFrames.
    """

    def __init__(self):
        self.industry = INDUSTRY
        self.history = []
        logger.info(f"SQLQueryRunner ready — schema: {self.industry}, db_available: {DB_AVAILABLE}")

    def run(self, sql: str, params: dict = None) -> pd.DataFrame:
        """
        Execute a SQL query and return the result as a DataFrame.
        """
        if not DB_AVAILABLE or engine is None:
            logger.error("[SQL] Database not available. Check DB_URL in .env.")
            return pd.DataFrame()

        sql = sql.replace("{industry}", self.industry)
        start_time = time.time()

        try:
            df = pd.read_sql(sql, engine, params=params)

            duration_ms = round((time.time() - start_time) * 1000, 1)

            self.history.append({
                "sql_preview": sql[:100].strip(),
                "rows": len(df),
                "cols": len(df.columns),
                "duration_ms": duration_ms,
                "status": "success",
            })

            logger.info(
                f"[SQL] Query complete — {len(df):,} rows × {len(df.columns)} columns | {duration_ms} ms"
            )

            return df

        except Exception as e:
            duration_ms = round((time.time() - start_time) * 1000, 1)

            self.history.append({
                "sql_preview": sql[:100].strip(),
                "rows": 0,
                "cols": 0,
                "duration_ms": duration_ms,
                "status": f"error: {str(e)[:100]}",
            })

            logger.error(f"[SQL] Query failed: {e}")
            return pd.DataFrame()

    def run_file(self, filename: str) -> pd.DataFrame:
        """
        Load a SQL file from the sql/ folder and execute it.
        """
        sql_path = SQL_DIR / filename

        if not sql_path.exists():
            logger.error(f"[SQL] File not found: {sql_path}")
            return pd.DataFrame()

        logger.info(f"[SQL] Loading SQL file: {filename}")

        sql_text = sql_path.read_text(encoding="utf-8")
        return self.run(sql_text)

    def demo_basics(self) -> None:
        """
        Run basic banking table checks.
        """
        demos = [
            (
                "Sample customers",
                f"""
                SELECT
                    customer_id,
                    first_name,
                    last_name,
                    gender,
                    city,
                    customer_segment,
                    credit_score
                FROM {self.industry}.customers
                LIMIT 10;
                """
            ),
            (
                "Sample accounts",
                f"""
                SELECT
                    account_id,
                    customer_id,
                    account_type,
                    account_balance,
                    interest_rate,
                    opened_date,
                    account_status
                FROM {self.industry}.accounts
                LIMIT 10;
                """
            ),
            (
                "Sample transactions",
                f"""
                SELECT
                    transaction_id,
                    account_id,
                    transaction_date,
                    transaction_type,
                    transaction_amount,
                    fee_amount,
                    channel,
                    transaction_status
                FROM {self.industry}.transactions
                LIMIT 10;
                """
            ),
        ]

        for title, sql in demos:
            print(f"\n── {title}:")
            df = self.run(sql)
            if not df.empty:
                print(df.to_string(index=False))

    def demo_aggregation(self) -> None:
        """
        Run banking transaction aggregation.
        """
        sql = f"""
        SELECT
            a.account_type,
            c.customer_segment,
            COUNT(t.transaction_id) AS total_transactions,
            SUM(t.transaction_amount) AS total_transaction_amount,
            AVG(t.transaction_amount) AS average_transaction_amount,
            SUM(t.fee_amount) AS total_fees,
            AVG(a.account_balance) AS average_account_balance
        FROM {self.industry}.transactions t
        JOIN {self.industry}.accounts a
            ON t.account_id = a.account_id
        JOIN {self.industry}.customers c
            ON a.customer_id = c.customer_id
        GROUP BY
            a.account_type,
            c.customer_segment
        ORDER BY total_transaction_amount DESC;
        """

        print("\n── Banking Transaction Aggregation by Account Type and Customer Segment:")
        df = self.run(sql)
        if not df.empty:
            print(df.to_string(index=False))

    def demo_joins(self) -> None:
        """
        Run joined banking extract preview.
        """
        sql = f"""
        SELECT
            c.customer_id,
            c.first_name,
            c.last_name,
            c.gender,
            c.city,
            c.customer_segment,
            c.credit_score,

            a.account_id,
            a.account_type,
            a.account_balance,
            a.interest_rate,
            a.opened_date,
            a.account_status,

            t.transaction_id,
            t.transaction_date,
            t.transaction_type,
            t.transaction_amount,
            t.fee_amount,
            t.channel,
            t.transaction_status,

            b.branch_id,
            b.branch_name,
            b.region,
            b.manager

        FROM {self.industry}.customers c
        JOIN {self.industry}.accounts a
            ON c.customer_id = a.customer_id
        JOIN {self.industry}.transactions t
            ON a.account_id = t.account_id
        LEFT JOIN {self.industry}.branches b
            ON a.branch_id = b.branch_id
        LIMIT 10;
        """

        print("\n── Banking Joined Extract Preview:")
        df = self.run(sql)
        if not df.empty:
            print(df.to_string(index=False))

    def __str__(self) -> str:
        return f"SQLQueryRunner(industry={self.industry!r}, queries_run={len(self.history)})"

    def __repr__(self) -> str:
        return f"SQLQueryRunner(industry={self.industry!r})"