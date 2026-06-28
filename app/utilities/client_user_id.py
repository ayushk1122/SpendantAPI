import re

CLIENT_USER_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


class InvalidClientUserIDError(ValueError):
    pass


def normalize_client_user_id(value: str) -> str:
    normalized = value.strip()
    if not normalized or not CLIENT_USER_ID_PATTERN.fullmatch(normalized):
        raise InvalidClientUserIDError(
            "client_user_id must be 1-128 characters and use letters, numbers, '.', '_', or '-'."
        )
    return normalized
