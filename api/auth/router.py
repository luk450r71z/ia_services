from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

# Modelos Pydantic para la validación de datos
class UserBase(BaseModel):
    username: str
    email: Optional[str] = None

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    is_active: bool = True

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register_user(user: UserCreate):
    # Aquí implementarías la lógica de registro
    return {
        "id": 1,
        "username": user.username,
        "email": user.email,
        "is_active": True
    }

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    # Aquí implementarías la lógica de autenticación
    if form_data.username == "test" and form_data.password == "test":
        return {
            "access_token": "example_token",
            "token_type": "bearer"
        }
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"},
    )

@router.get("/me", response_model=User)
async def read_users_me(token: str = Depends(oauth2_scheme)):
    # Aquí implementarías la lógica para obtener el usuario actual
    return {
        "id": 1,
        "username": "test_user",
        "email": "test@example.com",
        "is_active": True
    } 