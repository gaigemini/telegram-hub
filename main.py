# main.py
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from telethon.errors import (
    SessionPasswordNeededError, 
    PhoneCodeInvalidError, 
    PhoneNumberInvalidError,
    FloodWaitError,
    AuthKeyUnregisteredError
)

from models import *
from telegram_manager import (
    get_client, 
    disconnect_client, 
    clients, 
    is_client_authenticated,
    ensure_client_connected,
    restore_sessions_on_startup
)
from database import init_db

# Cache for temporary login data
login_details_cache = {}

def format_phone(phone: str) -> str:
    """Ensure phone number is in international format"""
    # Remove all non-digit characters
    digits = ''.join(filter(str.isdigit, phone))
    
    # Add leading '+' if not present
    if not digits.startswith('+'):
        return f"+{digits}"
    return digits

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Telegram API Hub is starting up...")
    init_db()
    print("📊 Database initialized")
    
    # Restore existing sessions from database
    restored_count = await restore_sessions_on_startup()
    print(f"🔄 {restored_count} sessions restored from database")
    
    yield
    
    print("🛑 Telegram API Hub is shutting down...")
    
    # Gracefully disconnect all clients
    for session_id in list(clients.keys()):
        try:
            await disconnect_client(session_id)
        except Exception as e:
            print(f"Error disconnecting client {session_id}: {e}")
    
    print("✅ All clients disconnected")

app = FastAPI(
    title="Telegram API Hub",
    description="A microservice for managing Telegram client sessions",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/")
def read_root():
    return {
        "status": "running",
        "message": "Telegram API Hub is operational",
        "version": "1.0.0"
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "active_sessions": len(clients)
    }

@app.post("/login/start")
async def login_start(request: LoginStartRequest):
    """
    Starts the login process by sending a verification code to the user's phone.
    """
    try:
        # Check if user is already logged in
        if await is_client_authenticated(request.session_id):
            return {
                "status": "already_logged_in", 
                "message": "User is already authenticated for this session"
            }
        
        # Format phone number
        phone = format_phone(request.phone_number)
        print(f"Starting login for session {request.session_id} with phone {phone}")
        
        # Get or create client
        client = get_client(request.session_id)
        
        # Ensure client is connected
        await ensure_client_connected(request.session_id)
        
        # Send code request
        result = await client.send_code_request(phone)
        
        # Cache login details for subsequent requests
        login_details_cache[request.session_id] = {
            "phone_number": phone,
            "phone_code_hash": result.phone_code_hash
        }
        
        print(f"Code sent successfully to {phone} for session {request.session_id}")
        
        return {
            "status": "success",
            "message": "Verification code sent to your phone",
            "phone_code_hash": result.phone_code_hash
        }
        
    except PhoneNumberInvalidError:
        await disconnect_client(request.session_id)
        raise HTTPException(
            status_code=400, 
            detail="Invalid phone number format"
        )
    
    except FloodWaitError as e:
        await disconnect_client(request.session_id)
        raise HTTPException(
            status_code=429,
            detail=f"Too many requests. Please wait {e.seconds} seconds before trying again"
        )
    
    except Exception as e:
        print(f"Error in login_start for session {request.session_id}: {e}")
        await disconnect_client(request.session_id)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start login process: {str(e)}"
        )

@app.post("/login/code")
async def login_code(request: LoginCodeRequest):
    """
    Submits the verification code received by the user.
    """
    try:
        # Get cached login details
        details = login_details_cache.get(request.session_id)
        if not details:
            raise HTTPException(
                status_code=404, 
                detail="Session not found or expired. Please start the login process again"
            )
        
        # Get client and ensure connection
        client = get_client(request.session_id)
        await ensure_client_connected(request.session_id)
        
        print(f"Attempting to sign in with code for session {request.session_id}")
        
        # Attempt to sign in with the code
        user = await client.sign_in(
            phone=details["phone_number"],
            code=request.phone_code,
            phone_code_hash=request.phone_code_hash
        )
        
        # Save user ID to session
        if hasattr(client.session, 'set_user_id'):
            client.session.set_user_id(user.id)
        
        # Clean up cache
        if request.session_id in login_details_cache:
            del login_details_cache[request.session_id]
        
        print(f"Login successful for session {request.session_id}, user: {user.first_name}")
        
        return {
            "status": "success",
            "message": "Login successful",
            "user": {
                "id": user.id,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "username": user.username,
                "phone": user.phone
            }
        }
        
    except SessionPasswordNeededError:
        return {
            "status": "2fa_required",
            "message": "Two-factor authentication is enabled. Please provide your password"
        }
    
    except PhoneCodeInvalidError:
        raise HTTPException(
            status_code=400,
            detail="Invalid verification code. Please try again"
        )
    
    except Exception as e:
        print(f"Error in login_code for session {request.session_id}: {e}")
        await disconnect_client(request.session_id)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to verify code: {str(e)}"
        )

@app.post("/login/password")
async def login_password(request: LoginPasswordRequest):
    """
    Submits the 2FA password for accounts with two-factor authentication.
    """
    try:
        # Get client and ensure connection
        client = get_client(request.session_id)
        await ensure_client_connected(request.session_id)
        
        print(f"Attempting 2FA login for session {request.session_id}")
        
        # Sign in with password
        user = await client.sign_in(password=request.password)
        
        # Save user ID to session
        if hasattr(client.session, 'set_user_id'):
            client.session.set_user_id(user.id)
        
        # Clean up cache
        if request.session_id in login_details_cache:
            del login_details_cache[request.session_id]
        
        print(f"2FA login successful for session {request.session_id}, user: {user.first_name}")
        
        return {
            "status": "success",
            "message": "Login successful",
            "user": {
                "id": user.id,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "username": user.username,
                "phone": user.phone
            }
        }
        
    except Exception as e:
        print(f"Error in login_password for session {request.session_id}: {e}")
        await disconnect_client(request.session_id)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to authenticate with password: {str(e)}"
        )

@app.post("/message/send")
async def send_message(request: SendMessageRequest):
    """
    Sends a message to a specified chat.
    """
    try:
        # Check if user is authenticated
        if not await is_client_authenticated(request.session_id):
            raise HTTPException(
                status_code=401,
                detail="User is not authenticated. Please login first"
            )
        
        # Get client and ensure connection
        client = get_client(request.session_id)
        await ensure_client_connected(request.session_id)
        
        print(f"Sending message from session {request.session_id} to {request.chat_id}")
        
        # Get the entity and send message
        entity = await client.get_entity(request.chat_id)
        await client.send_message(entity, request.message)
        
        return {
            "status": "success",
            "message": "Message sent successfully"
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=f"Chat not found: {str(e)}"
        )
    
    except Exception as e:
        print(f"Error sending message for session {request.session_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send message: {str(e)}"
        )

@app.post("/logout")
async def logout(request: LogoutRequest):
    """
    Logs out a user and cleans up the session.
    """
    try:
        await disconnect_client(request.session_id)
        
        # Clean up cache
        if request.session_id in login_details_cache:
            del login_details_cache[request.session_id]
        
        return {
            "status": "success",
            "message": "Logged out successfully"
        }
        
    except Exception as e:
        print(f"Error during logout for session {request.session_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to logout: {str(e)}"
        )

@app.delete("/session/{session_id}")
async def destroy_session(session_id: str):
    """
    Completely destroys a session - logs out, disconnects client, and deletes session data.
    """
    try:
        # Disconnect client if active
        if session_id in clients:
            client = clients[session_id]
            if client.is_connected():
                await client.disconnect()
            
            # Delete session data from database
            if hasattr(client.session, 'delete'):
                client.session.delete()
            
            # Close database connection
            if hasattr(client.session, 'close'):
                client.session.close()
            
            # Remove from active clients
            del clients[session_id]
        
        # Clean up login cache
        if session_id in login_details_cache:
            del login_details_cache[session_id]
        
        return {
            "status": "success",
            "message": f"Session {session_id} destroyed completely"
        }
        
    except Exception as e:
        print(f"Error destroying session {session_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to destroy session: {str(e)}"
        )

@app.get("/sessions")
async def list_sessions():
    """
    Lists all active sessions with their status.
    """
    try:
        sessions = []
        
        for session_id in clients.keys():
            try:
                client = clients[session_id]
                is_connected = client.is_connected()
                is_authenticated = await is_client_authenticated(session_id)
                
                # Try to get user info if authenticated
                user_info = None
                if is_authenticated:
                    try:
                        me = await client.get_me()
                        user_info = {
                            "id": me.id,
                            "first_name": me.first_name,
                            "last_name": me.last_name,
                            "username": me.username,
                            "phone": me.phone
                        }
                    except Exception:
                        user_info = {"error": "Could not fetch user info"}
                
                sessions.append({
                    "session_id": session_id,
                    "is_connected": is_connected,
                    "is_authenticated": is_authenticated,
                    "user_info": user_info,
                    "in_login_cache": session_id in login_details_cache
                })
                
            except Exception as e:
                sessions.append({
                    "session_id": session_id,
                    "is_connected": False,
                    "is_authenticated": False,
                    "user_info": None,
                    "error": str(e),
                    "in_login_cache": session_id in login_details_cache
                })
        
        return {
            "status": "success",
            "total_sessions": len(sessions),
            "sessions": sessions
        }
        
    except Exception as e:
        print(f"Error listing sessions: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list sessions: {str(e)}"
        )

@app.get("/session/{session_id}/status")
async def get_session_status(session_id: str):
    """
    Gets the authentication status of a session.
    """
    try:
        is_authenticated = await is_client_authenticated(session_id)
        is_active = session_id in clients
        is_connected = False
        user_info = None
        
        if is_active:
            client = clients[session_id]
            is_connected = client.is_connected()
            
            if is_authenticated:
                try:
                    me = await client.get_me()
                    user_info = {
                        "id": me.id,
                        "first_name": me.first_name,
                        "last_name": me.last_name,
                        "username": me.username,
                        "phone": me.phone
                    }
                except Exception:
                    user_info = {"error": "Could not fetch user info"}
        
        return {
            "session_id": session_id,
            "is_authenticated": is_authenticated,
            "is_active": is_active,
            "is_connected": is_connected,
            "user_info": user_info,
            "in_login_cache": session_id in login_details_cache
        }
        
    except Exception as e:
        return {
            "session_id": session_id,
            "is_authenticated": False,
            "is_active": False,
            "is_connected": False,
            "user_info": None,
            "error": str(e),
            "in_login_cache": session_id in login_details_cache
        }

@app.post("/session/{session_id}/reconnect")
async def reconnect_session(session_id: str):
    """
    Attempts to reconnect a disconnected session.
    """
    try:
        if session_id not in clients:
            # Try to restore this specific session from database
            try:
                client = get_client(session_id)
                await client.connect()
                
                # Verify authentication
                me = await client.get_me()
                if me:
                    return {
                        "status": "success", 
                        "message": f"Session restored and connected for user {me.first_name}"
                    }
                else:
                    await disconnect_client(session_id)
                    raise HTTPException(status_code=401, detail="Session is not authenticated")
            except Exception as restore_error:
                raise HTTPException(status_code=404, detail="Session not found or invalid")
        
        client = clients[session_id]
        
        if client.is_connected():
            return {
                "status": "success",
                "message": "Session is already connected"
            }
        
        await client.connect()
        
        return {
            "status": "success",
            "message": "Session reconnected successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error reconnecting session {session_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reconnect session: {str(e)}"
        )

@app.post("/admin/restore-sessions")
async def restore_sessions():
    """
    Manually restore all authenticated sessions from database.
    Useful for debugging or manual recovery.
    """
    try:
        restored_count = await restore_sessions_on_startup()
        return {
            "status": "success",
            "message": f"Restored {restored_count} sessions from database",
            "restored_count": restored_count
        }
    except Exception as e:
        print(f"Error during manual session restoration: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to restore sessions: {str(e)}"
        )