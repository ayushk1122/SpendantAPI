from app.services.transaction_classifier import (
    EXPENSES,
    HOUSING,
    INCOME,
    SUBSCRIPTIONS,
    TRANSFER,
    classify_transaction,
    is_subscription_like,
)


def test_classifies_plaid_income_primary() -> None:
    bucket = classify_transaction(
        {
            "amount": -2500,
            "name": "Payroll",
            "plaid_primary_category": "INCOME",
            "plaid_detailed_category": "INCOME_WAGES",
        }
    )
    assert bucket == INCOME


def test_classifies_plaid_housing_rent() -> None:
    bucket = classify_transaction(
        {
            "amount": 1800,
            "name": "Rent Payment",
            "plaid_primary_category": "RENT_AND_UTILITIES",
            "plaid_detailed_category": "RENT_AND_UTILITIES_RENT",
        }
    )
    assert bucket == HOUSING


def test_classifies_plaid_credit_card_payment_as_transfer() -> None:
    bucket = classify_transaction(
        {
            "amount": 450,
            "name": "Chase Payment",
            "plaid_primary_category": "LOAN_PAYMENTS",
            "plaid_detailed_category": "LOAN_PAYMENTS_CREDIT_CARD_PAYMENT",
        }
    )
    assert bucket == TRANSFER


def test_classifies_merchant_subscription_fallback() -> None:
    bucket = classify_transaction(
        {
            "amount": 15.99,
            "name": "Netflix",
            "merchant_name": "Netflix",
        }
    )
    assert bucket == SUBSCRIPTIONS


def test_classifies_negative_amount_without_categories_as_income() -> None:
    bucket = classify_transaction(
        {
            "amount": -100,
            "name": "Deposit",
        }
    )
    assert bucket == INCOME


def test_classifies_generic_spending_as_expenses() -> None:
    bucket = classify_transaction(
        {
            "amount": 42.50,
            "name": "Coffee Shop",
            "plaid_primary_category": "FOOD_AND_DRINK",
            "plaid_detailed_category": "FOOD_AND_DRINK_COFFEE",
        }
    )
    assert bucket == EXPENSES


def test_is_subscription_like_for_streaming_merchant() -> None:
    assert is_subscription_like({"amount": 9.99, "name": "Spotify", "merchant_name": "Spotify"})


def test_transfer_keyword_fallback() -> None:
    bucket = classify_transaction(
        {
            "amount": 300,
            "name": "Credit Card Payment Thank You",
        }
    )
    assert bucket == TRANSFER
