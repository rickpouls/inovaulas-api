from pydantic import BaseModel, Field
from typing import Optional

class UserBase(BaseModel):
    username: str = Field(..., max_length=50)
    full_name: Optional[str] = Field(default=None, max_length=120)
    role: str = Field(..., max_length=30)

class UserCreate(UserBase):
    pass

class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, max_length=120)
    role: Optional[str] = Field(default=None, max_length=30)

class UserOut(UserBase):
    id: int

    class Config:
        from_attributes = True