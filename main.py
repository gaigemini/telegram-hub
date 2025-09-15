# main.py
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from telethon.errors import SessionPasswordNeededError

from models import *
from telegram_manager import get_client, disconnect_client, clients
from database import init_db

# This cache is for holding login details (like phone_code_hash) temporarily between API calls.
login_details_cache = {}

def format_phone(phone: str) -> str:
    """Ensure phone number is in international format e.g. +62..."""
    # Strip all non-digit characters first.
    digits = ''.join(filter(str.isdigit, phone))
    # Then, add a leading '+' to conform to the international standard.
    return f"+{digits}"

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Hub is starting up...")
    init_db()
    yield
    print("Hub is shutting down...")
    for session_id in list(clients.keys()):
        await disconnect_client(session_id)

app = FastAPI(lifespan=lifespan)

@app.get("/")
def read_root():
    return {"status": "Telegram API Hub is running"}

@app.post("/login/start")
async def login_start(request: LoginStartRequest):
    """Starts the login process by sending a code to the user's phone."""
    client = get_client(request.session_id)
    phone = format_phone(request.phone_number)
    try:
        if hasattr(client.session, '_user_id') and client.session._user_id is not None:
            return {"status": "already_logged_in", "message": "User is already logged in."}

        # Let Telethon handle the connection automatically. This is the most reliable way.
        result = await client.send_code_request(phone)
        
        login_details_cache[request.session_id] = {
            "phone_number": phone,
            "phone_code_hash": result.phone_code_hash
        }
        return {"status": "success", "message": "Code sent", "phone_code_hash": result.phone_code_hash}
    except Exception as e:
        # If anything goes wrong, clean up the client to ensure the next request starts fresh.
        await disconnect_client(request.session_id)
        raise HTTPException(status_code=400, detail=f"An error occurred: {e}")

@app.post("/login/code")
async def login_code(request: LoginCodeRequest):
    """Submits the login code received by the user."""
    client = get_client(request.session_id)
    details = login_details_cache.get(request.session_id)
    if not details:
        raise HTTPException(status_code=404, detail="Session not found or expired. Please use /login/start again.")

    try:
        user = await client.sign_in(
            phone=details["phone_number"],
            code=request.phone_code,
            phone_code_hash=request.phone_code_hash
        )

        if hasattr(client.session, '_user_id'):
            client.session._user_id = user.id
            client.session.save()

        return {"status": "success", "message": "Login successful"}
    
    except SessionPasswordNeededError:
        return {"status": "2fa_required", "message": "Password is required for this account"}
    except Exception as e:
        # If anything goes wrong, clean up the client.
        await disconnect_client(request.session_id)
        raise HTTPException(status_code=400, detail=f"An error occurred: {e}")

@app.post("/login/password")
async def login_password(request: LoginPasswordRequest):
    """Submits the 2FA password."""
    client = get_client(request.session_id)
    try:
        user = await client.sign_in(password=request.password)
        
        if hasattr(client.session, '_user_id'):
            client.session._user_id = user.id
            client.session.save()

        if request.session_id in login_details_cache:
            del login_details_cache[request.session_id]
        return {"status": "success", "message": "Login successful"}
    except Exception as e:
        # If anything goes wrong, clean up the client.
        await disconnect_client(request.session_id)
        raise HTTPException(status_code=400, detail=f"An error occurred: {e}")

@app.post("/message/send")
async def send_message(request: SendMessageRequest):
    """Sends a message to a specified chat."""
    client = get_client(request.session_id)
    try:
        # Let Telethon auto-connect here as well if needed.
        entity = await client.get_entity(request.chat_id)
        await client.send_message(entity, request.message)
        return {"status": "success", "message": "Message sent"}
    except Exception as e:
        # If anything goes wrong, clean up the client.
        await disconnect_client(request.session_id)
        raise HTTPException(status_code=400, detail=f"An error occurred: {e}")

