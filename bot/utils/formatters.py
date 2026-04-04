from datetime import datetime


def format_amount(amount: float) -> str:
    """Форматировать сумму: 1500.0 → '1 500', 1500.5 → '1 500.50'."""
    if amount == int(amount):
        return f"{int(amount):,}".replace(",", " ")
    return f"{amount:,.2f}".replace(",", " ")


def format_date(date_str: str) -> str:
    """Форматировать дату: '2024-11-15' → '15 ноября'."""
    months = [
        "января", "февраля", "марта", "апреля", "мая", "июня",
        "июля", "августа", "сентября", "октября", "ноября", "декабря"
    ]
    try:
        dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
        return f"{dt.day} {months[dt.month - 1]}"
    except (ValueError, IndexError):
        return date_str


def get_user_display_name(user_name: str) -> str:
    """Получить отображаемое имя пользователя."""
    return user_name or "Неизвестный"
