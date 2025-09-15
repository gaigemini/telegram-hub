# main.py
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager

from models import *
from telegram_manager import get_client, disconnect_client, clients
from database import init_db

login_details_cache = {}

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

# --- Login Endpoints (Corrected with `async with`) ---

@app.post("/login/start")
async def login_start(request: LoginStartRequest):
    client = get_client(request.session_id)
    try:
        # The `async with` block correctly handles the connection lifecycle.
        # It connects before entering and disconnects on exit.
        async with client:
            if await client.is_user_authorized():
                return {"status": "success", "message": "User is already logged in."}

            result = await client.send_code_request(request.phone_number)
            login_details_cache[request.session_id] = {
                "phone_number": request.phone_number,
                "phone_code_hash": result.phone_code_hash
            }
            return {"status": "success", "message": "Code sent", "phone_code_hash": result.phone_code_hash}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/login/code")
async def login_code(request: LoginCodeRequest):
    client = get_client(request.session_id)
    details = login_details_cache.get(request.session_id)
    if not details:
        raise HTTPException(status_code=404, detail="Session not found or expired. Please use /login/start again.")

    try:
        async with client:
            await client.sign_in(
                phone=details["phone_number"],
                phone_code=request.phone_code,
                phone_code_hash=request.phone_code_hash
            )
        return {"status": "success", "message": "Login successful or 2FA required"}
    except Exception as e:
        if "SessionPasswordNeededError" in str(e):
            return {"status": "2fa_required", "message": "Password is required for this account"}
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/login/password")
async def login_password(request: LoginPasswordRequest):
    client = get_client(request.session_id)
    try:
        async with client:
            await client.sign_in(password=request.password)
        
        if request.session_id in login_details_cache:
            del login_details_cache[request.session_id]
        return {"status": "success", "message": "Login successful"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- Messaging Endpoint ---
@app.post("/message/send")
async def send_message(request: SendMessageRequest):
    client = get_client(request.session_id)
    try:
        async with client:
            # The is_user_authorized check is safe inside the `with` block.
            if not await client.is_user_authorized():
                raise HTTPException(status_code=401, detail="User is not authorized. Please log in.")
            
            entity = await client.get_entity(request.chat_id)
            await client.send_message(entity, request.message)
            return {"status": "success", "message": "Message sent"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))