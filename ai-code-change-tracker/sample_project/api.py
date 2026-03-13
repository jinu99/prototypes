"""API 엔드포인트 핸들러."""

from .models import User
from .services import create_user, process_order, send_notification


def handle_register(name: str, email: str) -> dict:
    user = create_user(name, email)
    send_notification(user, "Welcome!")
    return {"status": "ok", "user": user.display_name()}


def handle_order(name: str, email: str, items: list[str]) -> dict:
    user = create_user(name, email)
    prices = {"apple": 1.5, "banana": 0.75, "coffee": 3.0}
    order = process_order(user, items, prices)
    send_notification(user, f"Order placed: {order.summary()}")
    return {"status": "ok", "total": order.total}
