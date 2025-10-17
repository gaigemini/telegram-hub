import os
import httpx # To send webhooks
import json
import time
import hmac
import hashlib
import base64

from telethon import TelegramClient, events
from telethon.tl.types import User
from telethon.errors import PhoneCodeInvalidError, PhoneNumberInvalidError
from database import get_db_session, get_all_sessions

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")

# --- Webhook Configuration ---
# Get webhook settings from environment variables
WEBHOOK_ENABLED = os.getenv("WEBHOOK_ENABLED", "false").lower() == "true"

# Global dictionary to store active clients
clients = {}

def generate_signature(api_secret, message):
    # Create a new HMAC object using the API secret and SHA256
    # message = f"{ctx.method}:{ctx.url.path}:{timestamp}:{api_key}:{minified_json}"
    hmac_signature = hmac.new(api_secret.encode(), message.encode(), hashlib.sha256)

    # Return the base64 encoded signature
    return base64.urlsafe_b64encode(hmac_signature.digest()).decode()

async def send_webhook(payload: dict):
    """
    Sends a POST request to the configured webhook URL if enabled.
    """
    if not WEBHOOK_ENABLED:
        return # Do nothing if webhooks are not enabled

    try:
        method = "POST"
        base_url = f"https://gai.co.id/gai-ai-service"
        path = f"/v1/chat"
        api_key = "rrJtlI045p8QL26myUTwJmUXv_a_w_dyzbULiGP9S_g="
        api_secret = "gAAAAABouSCeLPCT3XnfMKZHW45zRr8K03IMCay5O050X7AaMZZjmAkpkU8kwjtzNvEhSgaAti6yQgUzKLK06a2hJeHKS8N1zpUWnc0b4LvDP8ZOhwEsq_ChnUmslhpn4l1afzShQ4pMBD7w2lXdmy8uEiGwwwtzBzoR3whGCm_8IAlieElYuweAYrMwlzq_8A2eKpxNdyOYQb2UpJN4evBAh7CFe05Eg_1oMOWGzpFQhIcpAR3lR3YZqkwXukaR71OhCsGs2Qz5"

        timestamp = str(int(time.time()))
        minified_json = json.dumps(payload, separators=(",", ":"))
        message = f"{method}:{path}:{timestamp}:{api_key}:{minified_json}"
        signature = generate_signature(api_secret, message)
        # Using an async client to not block the event loop
        options = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "x-api-secret": api_secret,
            "x-timestamp": timestamp,
            "x-signature": signature,
        }
        async with httpx.AsyncClient() as client:
            print(f"🚀 Sending webhook to {base_url}... payload: {payload}")
            response = await client.post(f"{base_url}{path}", json=payload, headers=options)
            response.raise_for_status() # Raise an exception for 4xx or 5xx status codes
            print(f"✅ Webhook sent successfully! Status: {response.status_code}")
    except httpx.RequestError as e:
        print(f"❌ Error sending webhook: {e}")
    except Exception as e:
        print(f"❌ An unexpected error occurred during webhook dispatch: {e}")


def get_client(session_id: str) -> TelegramClient:
    """
    Gets or creates a Telethon client instance for a given session ID.
    """
    if session_id in clients:
        return clients[session_id]

    try:
        print(f"Creating new client for session: {session_id}")
        
        db_session = get_db_session(session_id)
        client = TelegramClient(db_session, API_ID, API_HASH)
        
        @client.on(events.NewMessage)
        async def handle_new_message(event):
            try:
                sender = await event.get_sender()
                sender_info_summary = f"ID: {event.sender_id}"

                if sender and isinstance(sender, User):
                    if sender.username:
                        sender_info_summary = f"@{sender.username}"
                    elif sender.first_name:
                        sender_info_summary = sender.first_name
                    
                    print(f"\n--- Sender info: {sender} ---\n")
                else:
                    print(f"\n--- Sender is not a standard user (e.g., a channel) or couldn't be fetched. ID: {event.sender_id} ---\n")

                message_text = event.message.text or "[Media/Sticker]"
                print(f"[{session_id}] New message from {sender_info_summary}: '{message_text[:100]}{'...' if len(message_text) > 100 else ''}'")
                print(f"Event details:{event}")
                
                # --- ADDED SECTION: Webhook Logic ---
                # This is where your custom business logic starts.

                # 1. Construct the payload
                if not WEBHOOK_ENABLED:
                    return

                # 1. Get sender details
                sender_details = None
                if sender and isinstance(sender, User):
                    sender_details = {
                        "id": sender.id,
                        "first_name": sender.first_name,
                        "last_name": sender.last_name,
                        "username": sender.username,
                        "phone": sender.phone,
                        "is_bot": sender.bot,
                        "is_verified": sender.verified,
                    }
                else:
                    # Fallback for channels or other non-user entities
                    sender_details = {"id": event.sender_id}

                # 2. Get the session's own user ID
                me = await event.client.get_me()
                session_user_id = me.id if me else None
                
                # 3. Build the question_context object
                question_context = {
                    "chat_id": event.chat_id,
                    "msg_id": event.message.id,
                    "sender_info": sender_details,
                    "user_id": session_user_id # This is the ID of the logged-in account
                }

                webhook_payload = {
                    "channel_id": session_id,
                    "channelref": sender.phone if sender and isinstance(sender, User) and sender.phone else str(event.chat_id),
                    "channel": "TELEGRAM",
                    "sub_channel": "chat",
                    "question": message_text,
                    "question_context": question_context,
                }

                # 2. Send the webhook
                await send_webhook(webhook_payload)

                # You can add other business logic here as well.
                # --- END OF ADDED SECTION ---
                
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
                
                client = get_client(session_id)
                await client.connect()
                
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
        if client.is_connected():
            await client.disconnect()
        
        if hasattr(client.session, 'close'):
            client.session.close()
        
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

