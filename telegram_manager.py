# telegram_manager.py
import os
from telethon import TelegramClient, events
from database import get_db_session

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")

clients = {}

def get_client(session_id: str) -> TelegramClient:
    """
    Gets a Telethon client instance for a given session ID.
    This function now ONLY creates the client; it does not connect it.
    """
    try:
        if session_id in clients:
            return clients[session_id]

        print(f"Creating new client object for session: {session_id}")
        db_session = get_db_session(session_id)
        print(f"db_session: {db_session}")
        client = TelegramClient(db_session, API_ID, API_HASH)
        print(f"Client: {client}")
        
        @client.on(events.NewMessage)
        async def handle_new_message(event):
            print(f"[{session_id}] New message from {event.sender_id}: '{event.message.text}'")
            # Your business logic here

        clients[session_id] = client
        return client   
    except Exception as e:
        print(f"Error creating client for session {session_id}: {e}")
        raise e 

async def disconnect_client(session_id: str):
    """Disconnects and removes a client from the active pool."""
    if session_id in clients:
        if clients[session_id].is_connected():
            await clients[session_id].disconnect()
        clients[session_id].session.close()
        del clients[session_id]