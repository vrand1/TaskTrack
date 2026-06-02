from dataclasses import dataclass

TEST_PASSWORD = "password123"


@dataclass(frozen=True, slots=True)
class TestUser:
    id: int
    email: str
    is_admin: bool
    password: str = TEST_PASSWORD


AdminUser = TestUser(id=1, email="admin@example.dev", is_admin=True)
NormalUser = TestUser(id=2, email="user@example.dev", is_admin=False)
