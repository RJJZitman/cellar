from pydantic import BaseModel


class OwnerModel(BaseModel):
    id: int
    name: str
    username: str
    scopes: str | None = None
    is_admin: bool | None = None
    enabled: bool | None = None


class OwnerDbModel(OwnerModel):
    password: str


class TokenData(BaseModel):
    username: str | None = None
    scopes: list[str] = []