from pydantic import BaseModel, Field


class DbConnModel(BaseModel):
    user: str
    password: str
    database: str = Field(default='')
