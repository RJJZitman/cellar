from pydantic import BaseModel, Field


class StorageInModel(BaseModel):
    location: str = Field(max_length=200)
    description: str = Field(max_length=2000)


class StorageOutModel(StorageInModel):
    id: int
