# main.py
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from telethon.tl.types import InputPeerUser, PeerUser
from telethon.errors import (
    SessionPasswordNeededError, 
    PhoneCodeInvalidError, 
    PhoneNumberInvalidError,
    FloodWaitError,
    AuthKeyUnregisteredError,
    UsernameNotOccupiedError,
    PeerIdInvalidError
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

@app.post("/entity/resolve")
async def resolve_entity(request: dict):
    """
    Force resolve and cache an entity for future use
    """
    session_id = request.get("session_id")
    entity_identifier = request.get("entity_identifier")  # user_id, username, or phone
    
    try:
        if not await is_client_authenticated(session_id):
            raise HTTPException(status_code=401, detail="User is not authenticated")
        
        client = get_client(session_id)
        await ensure_client_connected(session_id)
        
        print(f"Resolving entity: {entity_identifier} for session: {session_id}")
        
        # Try multiple resolution methods
        entity = None
        
        # Method 1: Direct resolution
        try:
            entity = await client.get_entity(entity_identifier)
            print(f"Direct resolution successful: {entity}")
        except Exception as e1:
            print(f"Direct resolution failed: {e1}")
            
            # Method 2: Try as integer if it's digits
            if str(entity_identifier).strip().isdigit():
                try:
                    entity = await client.get_entity(int(entity_identifier))
                    print(f"Integer resolution successful: {entity}")
                except Exception as e2:
                    print(f"Integer resolution failed: {e2}")
            
            # Method 3: Search in contacts
            if not entity:
                try:
                    contacts = await client.get_contacts()
                    for contact in contacts:
                        if (str(contact.id) == str(entity_identifier) or 
                            (hasattr(contact, 'username') and contact.username == str(entity_identifier).lstrip('@')) or
                            (hasattr(contact, 'phone') and contact.phone == str(entity_identifier))):
                            entity = contact
                            print(f"Found in contacts: {entity}")
                            break
                except Exception as e3:
                    print(f"Contact search failed: {e3}")
        
        if not entity:
            # Method 4: Search in recent dialogs
            try:
                print("Searching in dialogs...")
                async for dialog in client.iter_dialogs(limit=200):
                    dialog_entity = dialog.entity
                    if (str(dialog_entity.id) == str(entity_identifier) or
                        (hasattr(dialog_entity, 'username') and dialog_entity.username == str(entity_identifier).lstrip('@'))):
                        entity = dialog_entity
                        print(f"Found in dialogs: {entity}")
                        break
            except Exception as e4:
                print(f"Dialog search failed: {e4}")
        
        if entity:
            # Force store the entity in session
            try:
                # Create a fake update to store the entity
                from telethon.tl.types import UpdateShortMessage
                fake_update = type('FakeUpdate', (), {
                    'users': [entity] if hasattr(entity, 'first_name') else [],
                    'chats': [entity] if not hasattr(entity, 'first_name') else []
                })()
                
                client.session.process_entities(fake_update)
                print(f"Entity stored in session cache")
            except Exception as store_error:
                print(f"Warning - could not store entity: {store_error}")
            
            return {
                "status": "success",
                "message": "Entity resolved and cached",
                "entity": {
                    "id": entity.id,
                    "type": type(entity).__name__,
                    "username": getattr(entity, 'username', None),
                    "first_name": getattr(entity, 'first_name', None),
                    "last_name": getattr(entity, 'last_name', None),
                    "phone": getattr(entity, 'phone', None),
                    "title": getattr(entity, 'title', None)
                }
            }
        else:
            raise HTTPException(
                status_code=404, 
                detail=f"Could not resolve entity: {entity_identifier}"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error resolving entity: {e}")
        raise HTTPException(status_code=500, detail=f"Entity resolution failed: {str(e)}")


# Enhanced send_message endpoint
@app.post("/message/send")
async def send_message(request: SendMessageRequest):
    """
    Sends a message to a specified chat with automatic entity resolution.
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
        
        chat_id = request.chat_id.strip()
        print(f"Sending message from session {request.session_id} to {chat_id}")
        
        # Try to send directly first
        entity = None
        try:
            entity = await client.get_entity(chat_id)
            sent_message = await client.send_message(entity, request.message)
            
            return {
                "status": "success",
                "message": "Message sent successfully",
                "message_id": sent_message.id
            }
            
        except Exception as direct_error:
            print(f"Direct send failed: {direct_error}")
            
            # Auto-resolve entity and retry
            try:
                print(f"Attempting auto-resolution for {chat_id}")
                
                # Call our own resolve endpoint internally
                resolve_payload = {
                    "session_id": request.session_id,
                    "entity_identifier": chat_id
                }
                
                # Resolve entity using our resolution logic
                entity = await resolve_entity_internal(request.session_id, chat_id, client)
                
                if entity:
                    sent_message = await client.send_message(entity, request.message)
                    print(f"Message sent after resolution. Message ID: {sent_message.id}")
                    
                    return {
                        "status": "success",
                        "message": "Message sent successfully after entity resolution",
                        "message_id": sent_message.id,
                        "resolved_entity": {
                            "id": entity.id,
                            "type": type(entity).__name__
                        }
                    }
                else:
                    raise ValueError(f"Could not resolve entity for chat_id: {chat_id}")
                    
            except Exception as resolve_error:
                print(f"Auto-resolution failed: {resolve_error}")
                raise HTTPException(
                    status_code=404,
                    detail=f"Chat not found and could not be resolved: {chat_id}. Try using /entity/resolve first."
                )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error sending message for session {request.session_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send message: {str(e)}"
        )


# Internal helper function
async def resolve_entity_internal(session_id: str, entity_identifier: str, client):
    """Internal entity resolution without HTTP overhead"""
    try:
        print(f"Internal entity resolution for: {entity_identifier}")
        
        # Try direct resolution first
        try:
            entity = await client.get_entity(entity_identifier)
            return entity
        except:
            pass
        
        # Try as integer
        if str(entity_identifier).strip().isdigit():
            try:
                entity = await client.get_entity(int(entity_identifier))
                return entity
            except:
                pass
        
        # Search in dialogs (most comprehensive)
        try:
            async for dialog in client.iter_dialogs(limit=200):
                dialog_entity = dialog.entity
                if (str(dialog_entity.id) == str(entity_identifier) or
                    (hasattr(dialog_entity, 'username') and 
                     dialog_entity.username == str(entity_identifier).lstrip('@'))):
                    
                    # Store entity in session
                    try:
                        fake_update = type('FakeUpdate', (), {
                            'users': [dialog_entity] if hasattr(dialog_entity, 'first_name') else [],
                            'chats': [dialog_entity] if not hasattr(dialog_entity, 'first_name') else []
                        })()
                        client.session.process_entities(fake_update)
                    except:
                        pass
                    
                    return dialog_entity
        except Exception as dialog_error:
            print(f"Dialog search error: {dialog_error}")
        
        return None
        
    except Exception as e:
        print(f"Internal entity resolution error: {e}")
        return None


# Add endpoint to check what entities are cached
@app.get("/session/{session_id}/entities")
async def list_cached_entities(session_id: str):
    """List all cached entities for a session"""
    try:
        from database import SessionLocal, Entity
        
        db_session = SessionLocal()
        try:
            entities = db_session.query(Entity).filter(
                Entity.session_id == session_id
            ).all()
            
            return {
                "status": "success",
                "session_id": session_id,
                "cached_entities": [
                    {
                        "entity_id": entity.entity_id,
                        "type": entity.type,
                        "name": entity.name,
                        "username": entity.username,
                        "phone": entity.phone
                    }
                    for entity in entities
                ]
            }
        finally:
            db_session.close()
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list entities: {str(e)}")


# Add endpoint to manually cache an entity from a recent message
@app.post("/session/{session_id}/cache-from-messages")
async def cache_entities_from_messages(session_id: str):
    """Cache entities from recent messages"""
    try:
        if not await is_client_authenticated(session_id):
            raise HTTPException(status_code=401, detail="User is not authenticated")
        
        client = get_client(session_id)
        await ensure_client_connected(session_id)
        
        cached_count = 0
        
        # Iterate through recent messages to cache senders
        async for message in client.iter_messages('me', limit=100):
            if message.sender:
                try:
                    # Process this message to cache the sender
                    fake_update = type('FakeUpdate', (), {
                        'users': [message.sender] if hasattr(message.sender, 'first_name') else [],
                        'chats': [message.sender] if not hasattr(message.sender, 'first_name') else []
                    })()
                    client.session.process_entities(fake_update)
                    cached_count += 1
                except:
                    pass
        
        return {
            "status": "success",
            "message": f"Cached {cached_count} entities from recent messages"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cache entities: {str(e)}")
        

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