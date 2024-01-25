from pydantic import BaseModel, Field


class OwnerModel(BaseModel):
    id: int
    name: str
    username: str
    scopes: str | None = None
    is_admin: bool | None = Field(default=False)
    enabled: bool | None = None


class NewOwnerModel(BaseModel):
    name: str
    username: str
    password: str
    scopes: str | None = None
    is_admin: bool | None = Field(default=False)
    enabled: bool | None = None


class UpdateOwnerModel(BaseModel):
    name: str | None = Field(default="None")
    username: str | None = Field(default="None")
    password: str | None = Field(default="None")
    scopes: str | None = Field(default="None")
    is_admin: bool | None = Field(default=False)
    enabled: bool | None = Field(default=True)


class OwnerDbModel(OwnerModel):
    id: int | None = Field(default=None)
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None
    scopes: list[str] = []