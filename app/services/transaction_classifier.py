from typing import Final

INCOME: Final = "INCOME"
HOUSING: Final = "HOUSING"
EXPENSES: Final = "EXPENSES"
SUBSCRIPTIONS: Final = "SUBSCRIPTIONS"
TRANSFER: Final = "TRANSFER"
IGNORE: Final = "IGNORE"

BUCKETS: Final = {
    INCOME,
    HOUSING,
    EXPENSES,
    SUBSCRIPTIONS,
    TRANSFER,
    IGNORE,
}

HOUSING_KEYWORDS: Final = {
    "rent",
    "mortgage",
    "apartment",
    "utility",
    "electric",
    "internet",
    "xfinity",
    "comcast",
    "water",
    "gas bill",
}

SUBSCRIPTION_KEYWORDS: Final = {
    "netflix",
    "spotify",
    "hulu",
    "disney+",
    "disney plus",
    "youtube premium",
    "openai",
    "chatgpt",
    "icloud storage",
    "apple music",
    "amazon prime",
    "adobe",
    "dropbox",
    "gym membership",
}

TRANSFER_CATEGORY_KEYWORDS: Final = {
    "transfer",
    "loan payment",
    "credit card payment",
    "bank transfer",
    "payment thank you",
    "autopay",
}

PLAID_INCOME_PRIMARY: Final = {
    "INCOME",
}

PLAID_TRANSFER_PRIMARY: Final = {
    "TRANSFER_IN",
    "TRANSFER_OUT",
    "LOAN_DISBURSEMENTS",
    "LOAN_REPAYMENTS",
}

PLAID_HOUSING_PRIMARY: Final = {
    "RENT_AND_UTILITIES",
}

PLAID_HOUSING_DETAILED: Final = {
    "LOAN_PAYMENTS_MORTGAGE_PAYMENT",
    "RENT_AND_UTILITIES_GAS_AND_ELECTRICITY",
    "RENT_AND_UTILITIES_INTERNET_AND_CABLE",
    "RENT_AND_UTILITIES_RENT",
    "RENT_AND_UTILITIES_SEWAGE_AND_WASTE_MANAGEMENT",
    "RENT_AND_UTILITIES_TELEPHONE",
    "RENT_AND_UTILITIES_WATER",
    "RENT_AND_UTILITIES_OTHER_UTILITIES",
}

PLAID_TRANSFER_DETAILED: Final = {
    "LOAN_PAYMENTS_CREDIT_CARD_PAYMENT",
    "TRANSFER_IN_CASH_ADVANCES_AND_LOANS",
    "TRANSFER_IN_DEPOSIT",
    "TRANSFER_IN_INVESTMENT_AND_RETIREMENT_FUNDS",
    "TRANSFER_IN_SAVINGS",
    "TRANSFER_IN_ACCOUNT_TRANSFER",
    "TRANSFER_IN_OTHER_TRANSFER_IN",
    "TRANSFER_OUT_INVESTMENT_AND_RETIREMENT_FUNDS",
    "TRANSFER_OUT_SAVINGS",
    "TRANSFER_OUT_WITHDRAWAL",
    "TRANSFER_OUT_ACCOUNT_TRANSFER",
    "TRANSFER_OUT_OTHER_TRANSFER_OUT",
}

PLAID_EXPENSE_DETAILED: Final = {
    "BANK_FEES_ATM_FEES",
    "BANK_FEES_FOREIGN_TRANSACTION_FEES",
    "BANK_FEES_INSUFFICIENT_FUNDS",
    "BANK_FEES_INTEREST_CHARGE",
    "BANK_FEES_OVERDRAFT_FEES",
    "BANK_FEES_OTHER_BANK_FEES",
    "ENTERTAINMENT_CASINOS_AND_GAMBLING",
    "ENTERTAINMENT_SPORTING_EVENTS_AMUSEMENT_PARKS_AND_MUSEUMS",
    "ENTERTAINMENT_VIDEO_GAMES",
    "ENTERTAINMENT_OTHER_ENTERTAINMENT",
    "FOOD_AND_DRINK_BEER_WINE_AND_LIQUOR",
    "FOOD_AND_DRINK_COFFEE",
    "FOOD_AND_DRINK_FAST_FOOD",
    "FOOD_AND_DRINK_GROCERIES",
    "FOOD_AND_DRINK_RESTAURANT",
    "FOOD_AND_DRINK_VENDING_MACHINES",
    "FOOD_AND_DRINK_OTHER_FOOD_AND_DRINK",
    "GENERAL_MERCHANDISE_BOOKSTORES_AND_NEWSSTANDS",
    "GENERAL_MERCHANDISE_CLOTHING_AND_ACCESSORIES",
    "GENERAL_MERCHANDISE_CONVENIENCE_STORES",
    "GENERAL_MERCHANDISE_DEPARTMENT_STORES",
    "GENERAL_MERCHANDISE_DISCOUNT_STORES",
    "GENERAL_MERCHANDISE_ELECTRONICS",
    "GENERAL_MERCHANDISE_GIFTS_AND_NOVELTIES",
    "GENERAL_MERCHANDISE_OFFICE_SUPPLIES",
    "GENERAL_MERCHANDISE_ONLINE_MARKETPLACES",
    "GENERAL_MERCHANDISE_PET_SUPPLIES",
    "GENERAL_MERCHANDISE_SPORTING_GOODS",
    "GENERAL_MERCHANDISE_SUPERSTORES",
    "GENERAL_MERCHANDISE_TOBACCO_AND_VAPE",
    "GENERAL_MERCHANDISE_OTHER_GENERAL_MERCHANDISE",
    "HOME_IMPROVEMENT_FURNITURE",
    "HOME_IMPROVEMENT_HARDWARE",
    "HOME_IMPROVEMENT_REPAIR_AND_MAINTENANCE",
    "HOME_IMPROVEMENT_SECURITY",
    "HOME_IMPROVEMENT_OTHER_HOME_IMPROVEMENT",
    "MEDICAL_DENTAL_CARE",
    "MEDICAL_EYE_CARE",
    "MEDICAL_NURSING_CARE",
    "MEDICAL_PHARMACIES_AND_SUPPLEMENTS",
    "MEDICAL_PRIMARY_CARE",
    "MEDICAL_VETERINARY_SERVICES",
    "MEDICAL_OTHER_MEDICAL",
    "PERSONAL_CARE_HAIR_AND_BEAUTY",
    "PERSONAL_CARE_LAUNDRY_AND_DRY_CLEANING",
    "PERSONAL_CARE_OTHER_PERSONAL_CARE",
    "GENERAL_SERVICES_ACCOUNTING_AND_FINANCIAL_PLANNING",
    "GENERAL_SERVICES_AUTOMOTIVE",
    "GENERAL_SERVICES_CHILDCARE",
    "GENERAL_SERVICES_CONSULTING_AND_LEGAL",
    "GENERAL_SERVICES_EDUCATION",
    "GENERAL_SERVICES_INSURANCE",
    "GENERAL_SERVICES_POSTAGE_AND_SHIPPING",
    "GENERAL_SERVICES_STORAGE",
    "GENERAL_SERVICES_OTHER_GENERAL_SERVICES",
    "GOVERNMENT_AND_NON_PROFIT_DONATIONS",
    "GOVERNMENT_AND_NON_PROFIT_GOVERNMENT_DEPARTMENTS_AND_AGENCIES",
    "GOVERNMENT_AND_NON_PROFIT_TAX_PAYMENT",
    "GOVERNMENT_AND_NON_PROFIT_OTHER_GOVERNMENT_AND_NON_PROFIT",
    "TRANSPORTATION_BIKES_AND_SCOOTERS",
    "TRANSPORTATION_GAS",
    "TRANSPORTATION_PARKING",
    "TRANSPORTATION_PUBLIC_TRANSIT",
    "TRANSPORTATION_TAXIS_AND_RIDE_SHARES",
    "TRANSPORTATION_TOLLS",
    "TRANSPORTATION_OTHER_TRANSPORTATION",
    "TRAVEL_FLIGHTS",
    "TRAVEL_LODGING",
    "TRAVEL_RENTAL_CARS",
    "TRAVEL_OTHER_TRAVEL",
    "LOAN_PAYMENTS_CAR_PAYMENT",
    "LOAN_PAYMENTS_PERSONAL_LOAN_PAYMENT",
    "LOAN_PAYMENTS_STUDENT_LOAN_PAYMENT",
    "LOAN_PAYMENTS_OTHER_PAYMENT",
}

PLAID_SUBSCRIPTION_LIKE_DETAILED: Final = {
    "ENTERTAINMENT_MUSIC_AND_AUDIO",
    "ENTERTAINMENT_TV_AND_MOVIES",
    "PERSONAL_CARE_GYMS_AND_FITNESS_CENTERS",
}

PLAID_EXPENSE_PRIMARY: Final = {
    "BANK_FEES",
    "ENTERTAINMENT",
    "FOOD_AND_DRINK",
    "GENERAL_MERCHANDISE",
    "GENERAL_SERVICES",
    "GOVERNMENT_AND_NON_PROFIT",
    "HOME_IMPROVEMENT",
    "MEDICAL",
    "PERSONAL_CARE",
    "TRANSPORTATION",
    "TRAVEL",
}


def classify_transaction(transaction: dict) -> str:
    plaid_bucket = _bucket_from_plaid_categories(transaction)
    if plaid_bucket:
        return plaid_bucket

    text = _searchable_text(transaction)

    if _looks_like_transfer(transaction, text):
        return TRANSFER

    if transaction.get("amount", 0) < 0:
        return INCOME

    if _contains_keyword(text, HOUSING_KEYWORDS):
        return HOUSING

    if _contains_keyword(text, SUBSCRIPTION_KEYWORDS):
        return SUBSCRIPTIONS

    return EXPENSES


def is_subscription_like(transaction: dict) -> bool:
    detailed = _category_code(transaction.get("plaid_detailed_category"))
    if detailed in PLAID_SUBSCRIPTION_LIKE_DETAILED:
        return True

    return classify_transaction(transaction) == SUBSCRIPTIONS


def _bucket_from_plaid_categories(transaction: dict) -> str | None:
    primary = _category_code(transaction.get("plaid_primary_category"))
    detailed = _category_code(transaction.get("plaid_detailed_category"))

    if detailed in PLAID_TRANSFER_DETAILED or primary in PLAID_TRANSFER_PRIMARY:
        return TRANSFER

    if primary in PLAID_INCOME_PRIMARY:
        return INCOME

    if detailed in PLAID_HOUSING_DETAILED or primary in PLAID_HOUSING_PRIMARY:
        return HOUSING

    if detailed in PLAID_SUBSCRIPTION_LIKE_DETAILED:
        return SUBSCRIPTIONS

    if detailed in PLAID_EXPENSE_DETAILED or primary in PLAID_EXPENSE_PRIMARY:
        return EXPENSES

    return None


def _looks_like_transfer(transaction: dict, text: str) -> bool:
    primary = _normalize(transaction.get("plaid_primary_category"))
    detailed = _normalize(transaction.get("plaid_detailed_category"))
    category_text = f"{primary} {detailed} {text}"

    return _contains_keyword(category_text, TRANSFER_CATEGORY_KEYWORDS)


def _searchable_text(transaction: dict) -> str:
    category = transaction.get("category")
    if isinstance(category, list):
        category_text = " ".join(str(value) for value in category)
    else:
        category_text = str(category or "")

    values = [
        transaction.get("name"),
        transaction.get("merchant_name"),
        transaction.get("plaid_primary_category"),
        transaction.get("plaid_detailed_category"),
        category_text,
    ]
    return _normalize(" ".join(str(value) for value in values if value))


def _contains_keyword(text: str, keywords: set[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _normalize(value: object | None) -> str:
    return str(value or "").replace("_", " ").lower()


def _category_code(value: object | None) -> str:
    return str(value or "").upper()
