from pydantic import BaseModel, EmailStr


class BusinessOut(BaseModel):
    id: str
    name: str
    email: str
    phone: str
    business_type: str
    is_active: bool

    class Config:
        from_attributes = True
