SELECT
    t.transaction_id,
    t.transaction_date,
    t.transaction_time,
    t.amount,
    t.transaction_type,
    t.merchant_name,
    t.merchant_category,
    t.channel,
    t.status AS transaction_status,
    t.is_fraud,
    t.balance_after,

    a.account_id,
    a.account_type,
    a.account_number,
    a.balance,
    a.currency,
    a.opened_date,
    a.status AS account_status,
    a.branch,
    a.interest_rate,

    c.customer_id,
    c.first_name,
    c.last_name,
    c.email,
    c.phone,
    c.date_of_birth,
    c.city,
    c.credit_score,
    c.customer_since,
    c.segment,
    c.is_active,

    l.loan_id,
    l.loan_type,
    l.principal,
    l.interest_rate AS loan_interest_rate,
    l.term_months,
    l.monthly_payment,
    l.disbursed_date,
    l.outstanding_balance,
    l.status AS loan_status,
    l.risk_grade,

    f.alert_id,
    f.alert_date,
    f.alert_type,
    f.severity,
    f.status AS fraud_alert_status,
    f.amount_at_risk

FROM banking.transactions t

JOIN banking.accounts a
    ON t.account_id = a.account_id

JOIN banking.customers c
    ON a.customer_id = c.customer_id

LEFT JOIN banking.loans l
    ON c.customer_id = l.customer_id

LEFT JOIN banking.fraud_alerts f
    ON t.transaction_id = f.transaction_id

LIMIT 50;