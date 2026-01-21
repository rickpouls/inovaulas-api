from pydantic import BaseModel, Field

class LoginIn(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)

class LoginOut(BaseModel):
    access_token: str
    token_type: str = "bearer"