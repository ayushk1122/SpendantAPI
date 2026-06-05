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


class DashboardSummaryResponse(BaseModel):
    checking_balance: float
    income_total: float
    housing_total: float
    expenses_total: float
    subscriptions_total: float
    transfer_total: float
    protected_balance: float
    projected_month_end_balance: float
    safe_to_move_amount: float
    transactions: list[NormalizedTransaction]
    recurring_streams: list[RecurringStream] = []
