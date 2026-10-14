pydantic import BaseModel, Field

class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    completed: bool = False

class UserCreate(BaseModel):
    username: str
    email: str 
    password: str 