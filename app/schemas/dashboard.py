from pydantic import BaseModel


class NormalizedTransaction(BaseModel):
    transaction_id: str
    account_id: str | None = None
    name: str
    merchant_name: str | None = None
    amount: float
    date: str
    bucket: str
    pending: bool
    plaid_primary_category: str | None = None
    plaid_detailed_category: str | None = None
    plaid_category_confidence: str | None = None


class RecurringStream(BaseModel):
    stream_id: str
    account_id: str | None = None
    description: str
    merchant_name: str | None = None
    bucket: str
    frequency: str | None = None
    status: str | None = None
    is_active: bool
    average_amount: float | None = None
    last_amount: float | None = None
    first_date: str | None = None
    last_date: str | None = None
    predicted_next_date: str | None = None
    transaction_ids: list[str]
    plaid_primary_category: str | None = None
    plaid_detailed_category: str | None = None
    plaid_category_confidence: str | None = None


class CreditCardObligation(BaseModel):
    account_id: str
    account_name: str
    institution_name: str | None = None
    current_balance: float | None = None
    last_statement_balance: float | None = None
    minimum_payment_amount: float | None = None
    next_payment_due_date: str | None = None
    last_statement_issue_date: str | None = None
    last_payment_amount: float | None = None
    last_payment_date: str | None = None
    projected_payment_amount: float
    payment_strategy: str = "statement_balance"
    is_already_paid_this_cycle: bool = False


class CashFlowEvent(BaseModel):
    date: str
    amount: float
    bucket: str
    label: str
    account_id: str | None = None
    source: str


class DashboardSummaryResponse(BaseModel):
    checking_balance: float
    income_total: float
    housing_total: float
    expenses_total: float
    subscriptions_total: float
    transfer_total: float
    income_posted_total: float
    housing_posted_total: float
    expenses_posted_total: float
    subscriptions_posted_total: float
    credit_card_payments_posted_total: float
    income_upcoming_total: float
    housing_upcoming_total: float
    subscriptions_upcoming_total: float
    credit_card_payments_upcoming_total: float
    protected_balance: float
    projected_month_end_balance: float
    safe_to_move_amount: float
    safe_to_move_today: float
    lowest_projected_balance: float
    lowest_projected_balance_date: str | None = None
    transactions: list[NormalizedTransaction]
    recurring_streams: list[RecurringStream] = []
    credit_card_obligations: list[CreditCardObligation] = []
    cash_flow_events: list[CashFlowEvent] = []
