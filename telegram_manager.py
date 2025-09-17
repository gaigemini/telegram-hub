# telegram_manager.py
import os
from telethon import TelegramClient, events
from telethon.errors import PhoneCodeInvalidError, PhoneNumberInvalidError
from database import get_db_session, get_all_sessions

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")

# Global dictionary to store active clients
clients = {}

def get_client(session_id: str) -> TelegramClient:
    """
    Gets or creates a Telethon client instance for a given session ID.
    """
    if session_id in clients:
        return clients[session_id]

    try:
        print(f"Creating new client for session: {session_id}")
        
        # Create database session
        db_session = get_db_session(session_id)
        
        # Create Telethon client
        client = TelegramClient(db_session, API_ID, API_HASH)
        
        # Add message handler
        @client.on(events.NewMessage)
        async def handle_new_message(event):
            try:
                sender_info = "Unknown"
                if event.sender:
                    if hasattr(event.sender, 'username') and event.sender.username:
                        sender_info = f"@{event.sender.username}"
                    elif hasattr(event.sender, 'first_name'):
                        sender_info = event.sender.first_name
                    else:
                        sender_info = str(event.sender_id)
                
                message_text = event.message.text or "[Media/Sticker]"
                print(f"[{session_id}] New message from {sender_info}: '{message_text[:100]}{'...' if len(message_text) > 100 else ''}'")
                
                # Add your custom business logic here
                # For example: save to database, send webhooks, process commands, etc.
                
            except Exception as e:
                print(f"Error handling message for session {session_id}: {e}")

        clients[session_id] = client
        print(f"Client created successfully for session: {session_id}")
        return client
        
    except Exception as e:
        print(f"Error creating client for session {session_id}: {e}")
        raise

async def restore_sessions_on_startup():
    """
    Restore all authenticated sessions from database on startup.
    This ensures sessions persist across app restarts.
    """
    print("🔄 Restoring sessions from database...")
    
    try:
        stored_sessions = get_all_sessions()
        restored_count = 0
        
        for session_id in stored_sessions:
            try:
                print(f"Restoring session: {session_id}")
                
                # Create client (this loads the session data)
                client = get_client(session_id)
                
                # Try to connect and verify authentication
                await client.connect()
                
                # Check if session is still valid by trying to get user info
                try:
                    me = await client.get_me()
                    if me:
                        print(f"✅ Session {session_id} restored successfully - User: {me.first_name}")
                        restored_count += 1
                    else:
                        print(f"⚠️  Session {session_id} - No user info available")
                        await disconnect_client(session_id)
                except Exception as auth_error:
                    print(f"⚠️  Session {session_id} authentication invalid: {auth_error}")
                    await disconnect_client(session_id)
                    
            except Exception as e:
                print(f"❌ Failed to restore session {session_id}: {e}")
                # Remove invalid session from clients if it was added
                if session_id in clients:
                    try:
                        await disconnect_client(session_id)
                    except:
                        pass
        
        print(f"✅ Session restoration complete: {restored_count} sessions restored")
        return restored_count
        
    except Exception as e:
        print(f"❌ Error during session restoration: {e}")
        return 0

async def disconnect_client(session_id: str):
    """
    Disconnects and removes a client from the active pool.
    """
    if session_id not in clients:
        return
    
    try:
        client = clients[session_id]
        
        # Disconnect if connected
        if client.is_connected():
            await client.disconnect()
        
        # Close database session
        if hasattr(client.session, 'close'):
            client.session.close()
        
        # Remove from active clients
        del clients[session_id]
        print(f"Client disconnected and removed for session: {session_id}")
        
    except Exception as e:
        print(f"Error disconnecting client for session {session_id}: {e}")

async def is_client_authenticated(session_id: str) -> bool:
    """
    Check if a client is authenticated (logged in).
    """
    if session_id not in clients:
        return False
    
    try:
        client = clients[session_id]
        if not client.is_connected():
            await client.connect()
        
        # Try to get self - this will fail if not authenticated
        me = await client.get_me()
        return me is not None
        
    except Exception as e:
        print(f"Authentication check failed for session {session_id}: {e}")
        return False

async def ensure_client_connected(session_id: str):
    """
    Ensures the client is connected before use.
    """
    if session_id not in clients:
        raise ValueError(f"No client found for session {session_id}")
    
    client = clients[session_id]
    if not client.is_connected():
        await client.connect()
    
    return client