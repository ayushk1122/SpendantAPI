import argparse
import json
from pathlib import Path

CASE_STUDY_PATH = Path("data/case_study_user.json")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a realistic local dashboard case-study user."
    )
    parser.add_argument("--client-user-id", default="spendant-local-user")
    parser.add_argument("--checking-balance", type=float, default=9632.39)
    args = parser.parse_args()

    CASE_STUDY_PATH.parent.mkdir(parents=True, exist_ok=True)
    CASE_STUDY_PATH.write_text(
        json.dumps(build_case_study(args.client_user_id, args.checking_balance), indent=2)
    )
    print(f"wrote {CASE_STUDY_PATH}")
    print(f"client user id: {args.client_user_id}")
    print("use protected_balance=2000 when calling /api/dashboard/summary")
    return 0


def build_case_study(client_user_id: str, checking_balance: float) -> dict:
    return {
        "client_user_id": client_user_id,
        "checking_balance": checking_balance,
        "transactions": [
            transaction(
                transaction_id="case-checking-rent-2026-06-02",
                account_id="case-checking",
                name="RPS Miami World Tow RD 800-7040154 FL 06/01 (...8642)",
                amount=2848.70,
                date="2026-06-02",
                bucket="HOUSING",
                plaid_primary_category="RENT_AND_UTILITIES",
                plaid_detailed_category="RENT_AND_UTILITIES_RENT",
            ),
            transaction(
                transaction_id="case-checking-fpl-2026-06-03",
                account_id="case-checking",
                name="FPL DIRECT DEBIT ELEC PYMT PPD ID: 3590247775",
                amount=47.47,
                date="2026-06-03",
                bucket="EXPENSES",
                plaid_primary_category="RENT_AND_UTILITIES",
                plaid_detailed_category="RENT_AND_UTILITIES_GAS_AND_ELECTRICITY",
            ),
        ],
        "credit_card_obligations": [
            {
                "account_id": "case-sapphire-reserve",
                "account_name": "Sapphire Reserve (...2611)",
                "institution_name": "Chase",
                "current_balance": 1904.18,
                "last_statement_balance": 946.38,
                "minimum_payment_amount": 40.00,
                "next_payment_due_date": "2026-06-12",
                "last_statement_issue_date": None,
                "last_payment_amount": 606.51,
                "last_payment_date": "2026-05-18",
                "projected_payment_amount": 946.38,
                "payment_strategy": "statement_balance",
                "is_already_paid_this_cycle": False,
            },
            {
                "account_id": "case-freedom-unlimited",
                "account_name": "Freedom Unlimited (...2928)",
                "institution_name": "Chase",
                "current_balance": 2663.62,
                "last_statement_balance": 2615.47,
                "minimum_payment_amount": 40.00,
                "next_payment_due_date": "2026-06-22",
                "last_statement_issue_date": None,
                "last_payment_amount": 1634.51,
                "last_payment_date": "2026-05-26",
                "projected_payment_amount": 2615.47,
                "payment_strategy": "statement_balance",
                "is_already_paid_this_cycle": False,
            },
        ],
        "cash_flow_events": [
            event(
                date="2026-06-12",
                amount=-946.38,
                bucket="TRANSFER",
                label="Sapphire Reserve statement payment",
                account_id="case-sapphire-reserve",
                source="liability",
            ),
            event(
                date="2026-06-15",
                amount=3162.03,
                bucket="INCOME",
                label="MARLINS TEAM5605 Payroll",
                account_id="case-checking",
                source="projection",
            ),
            event(
                date="2026-06-22",
                amount=-2615.47,
                bucket="TRANSFER",
                label="Freedom Unlimited statement payment",
                account_id="case-freedom-unlimited",
                source="liability",
            ),
            event(
                date="2026-06-26",
                amount=-92.08,
                bucket="SUBSCRIPTIONS",
                label="Known subscriptions and card autopay",
                account_id="case-checking",
                source="projection",
            ),
            event(
                date="2026-06-30",
                amount=3162.03,
                bucket="INCOME",
                label="MARLINS TEAM5605 Payroll",
                account_id="case-checking",
                source="projection",
            ),
            event(
                date="2026-06-30",
                amount=-2000.00,
                bucket="EXPENSES",
                label="Projected remaining variable spending",
                account_id="case-checking",
                source="projection",
            ),
        ],
        "recurring_streams": [
            {
                "stream_id": "case-payroll-1",
                "account_id": "case-checking",
                "description": "MARLINS TEAM5605 Payroll",
                "merchant_name": "MARLINS TEAM5605",
                "bucket": "INCOME",
                "frequency": "SEMI_MONTHLY",
                "status": "MATURE",
                "is_active": True,
                "average_amount": -3162.03,
                "last_amount": -3162.03,
                "first_date": "2026-04-15",
                "last_date": "2026-05-29",
                "predicted_next_date": "2026-06-15",
                "transaction_ids": [],
                "plaid_primary_category": "INCOME",
                "plaid_detailed_category": "INCOME_WAGES",
            },
            {
                "stream_id": "case-subscriptions-1",
                "account_id": "case-checking",
                "description": "Known subscriptions and card autopay",
                "merchant_name": None,
                "bucket": "SUBSCRIPTIONS",
                "frequency": "MONTHLY",
                "status": "MATURE",
                "is_active": True,
                "average_amount": 92.08,
                "last_amount": 92.08,
                "first_date": "2026-05-26",
                "last_date": "2026-05-26",
                "predicted_next_date": "2026-06-26",
                "transaction_ids": [],
                "plaid_primary_category": "GENERAL_SERVICES",
                "plaid_detailed_category": "GENERAL_SERVICES_OTHER_GENERAL_SERVICES",
            },
        ],
    }


def transaction(
    *,
    transaction_id: str,
    account_id: str,
    name: str,
    amount: float,
    date: str,
    bucket: str,
    plaid_primary_category: str,
    plaid_detailed_category: str,
) -> dict:
    return {
        "transaction_id": transaction_id,
        "account_id": account_id,
        "name": name,
        "merchant_name": None,
        "amount": amount,
        "date": date,
        "bucket": bucket,
        "pending": False,
        "plaid_primary_category": plaid_primary_category,
        "plaid_detailed_category": plaid_detailed_category,
        "plaid_category_confidence": "VERY_HIGH",
    }


def event(
    *,
    date: str,
    amount: float,
    bucket: str,
    label: str,
    account_id: str,
    source: str,
) -> dict:
    return {
        "date": date,
        "amount": amount,
        "bucket": bucket,
        "label": label,
        "account_id": account_id,
        "source": source,
    }


if __name__ == "__main__":
    raise SystemExit(main())
