"""비즈니스 로직 서비스."""

from .models import Order, User


def create_user(name: str, email: str) -> User:
    user = User(name, email)
    if not user.validate_email():
        raise ValueError(f"Invalid email: {email}")
    return user


def process_order(user: User, items: list[str], prices: dict[str, float]) -> Order:
    order = Order(user, items)
    order.calculate_total(prices)
    return order


def send_notification(user: User, message: str) -> str:
    """사용자에게 알림을 전송한다. 이메일 검증 후 전송."""
    if not user.validate_email():
        return f"[FAILED] Invalid email for {user.name}"
    return f"[NOTIFY] {user.display_name()}: {message}"
