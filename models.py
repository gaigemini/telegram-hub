from pydantic import BaseModel

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