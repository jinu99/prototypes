"""데이터 모델 정의."""


class User:
    def __init__(self, name: str, email: str):
        self.name = name
        self.email = email

    def validate_email(self) -> bool:
        """이메일 형식을 검증한다. @ 포함 및 도메인 확인."""
        if "@" not in self.email:
            return False
        local, domain = self.email.rsplit("@", 1)
        return len(local) > 0 and "." in domain

    def display_name(self) -> str:
        return self.name.title()


class Order:
    def __init__(self, user: User, items: list[str]):
        self.user = user
        self.items = items
        self.total = 0.0

    def calculate_total(self, prices: dict[str, float]) -> float:
        self.total = sum(prices.get(item, 0.0) for item in self.items)
        return self.total

    def summary(self) -> str:
        return f"Order for {self.user.display_name()}: {len(self.items)} items, ${self.total:.2f}"
