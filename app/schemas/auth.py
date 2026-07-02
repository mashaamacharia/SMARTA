from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    business_name: str
    business_email: EmailStr
    business_phone: str
    business_type: str
    owner_full_name: str
    owner_email: EmailStr
    owner_password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    business_id: str
    is_active: bool

    class Config:
        from_attributes = True
