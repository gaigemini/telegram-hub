from pydantic import BaseModel
from typing import Optional

class LoginStartRequest(BaseModel):
    session_id: str
    phone_number: str

class LoginCodeRequest(BaseModel):
    session_id: str
    phone_code: str
    phone_code_hash: str

class LoginPasswordRequest(BaseModel):
    session_id: str
    password: str

class SendMessageRequest(BaseModel):
    session_id: str
    chat_id: str # Can be a username, phone number, or channel/group ID
    message: str

class LogoutRequest(BaseModel):
    session_id: str

class SessionStatusResponse(BaseModel):
    session_id: str
    is_connected: bool
    is_authenticated: bool
    user_info: Optional[dict] = None
    error: Optional[str] = None
    in_login_cache: bool = False