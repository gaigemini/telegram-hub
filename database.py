# database.py
import os
from dotenv import load_dotenv

from sqlalchemy import create_engine, Column, Integer, String, LargeBinary, UniqueConstraint, BigInteger
from sqlalchemy.orm import sessionmaker, declarative_base

from telethon.sessions.abstract import Session
from telethon.crypto import AuthKey
from telethon.tl.types import User, Chat, Channel, InputPeerUser, InputPeerChat, InputPeerChannel

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- SQLAlchemy Model for our Sessions ---
class TelegramSession(Base):
    __tablename__ = "sessions"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True)
    dc_id = Column(Integer)
    server_address = Column(String)
    port = Column(Integer)
    auth_key = Column(LargeBinary)
    user_id = Column(BigInteger) # The logged-in user's ID for this session

class Entity(Base):
    __tablename__ = "entities"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    entity_id = Column(BigInteger)
    hash = Column(BigInteger)
    username = Column(String)
    phone = Column(String)
    name = Column(String)
    # Proactively adding a type column to prevent future bugs
    type = Column(String) 
    
    __table_args__ = (UniqueConstraint('session_id', 'entity_id', name='_session_entity_uc'),)


def init_db():
    """Creates the database tables if they don't exist."""
    Base.metadata.create_all(bind=engine)

# --- Custom Telethon Session Class (Definitive Version) ---
class SQLAlchemySession(Session):
    """
    A Telethon session handler that stores session data in a PostgreSQL database.
    This version correctly implements all required abstract methods.
    """
    def __init__(self, session_id: str):
        super().__init__()
        self._session_id = session_id
        self._db_session = SessionLocal()
        
        # Default values
        self._dc_id = 0
        self._server_address = None
        self._port = 443
        self._auth_key = None
        self._user_id = None
        self.load()

    def _get_session_from_db(self):
        return self._db_session.query(TelegramSession).filter(TelegramSession.session_id == self._session_id).first()

    def load(self):
        session = self._get_session_from_db()
        if session and session.auth_key:
            self._dc_id = session.dc_id
            self._server_address = session.server_address
            self._port = session.port
            self._auth_key = AuthKey(data=session.auth_key)
            self._user_id = session.user_id

    @property
    def dc_id(self): return self._dc_id
    
    @property
    def server_address(self): return self._server_address
    
    @property
    def port(self): return self._port
    
    @property
    def auth_key(self): return self._auth_key

    def set_dc(self, dc_id, server_address, port):
        self._dc_id = dc_id
        self._server_address = server_address
        self._port = port
        self.save()

    @auth_key.setter
    def auth_key(self, value):
        self._auth_key = value
        self._user_id = None # When auth key changes, we don't know the user yet
        self.save()
    
    def save(self):
        session = self._get_session_from_db()
        if not session:
            session = TelegramSession(session_id=self._session_id)
            self._db_session.add(session)
        
        session.dc_id = self._dc_id
        session.server_address = self._server_address
        session.port = self._port
        session.auth_key = self._auth_key.key if self._auth_key else b''
        
        # Get the user ID from the auth key itself after a successful login
        if self._auth_key:
            me = self.get_input_entity('self')
            if me:
                self._user_id = me.user_id
        session.user_id = self._user_id
        
        self._db_session.commit()

    def close(self): self._db_session.close()

    def delete(self):
        session = self._get_session_from_db()
        if session:
            self._db_session.delete(session)
            self._db_session.query(Entity).filter(Entity.session_id == self._session_id).delete()
            self._db_session.commit()

    def get_input_entity(self, key):
        # This is the crucial fix. If key is 'self' and we don't have a user_id,
        # we must raise ValueError, not return None.
        if key == 'self' or key == 0:
            if not self._user_id:
                raise ValueError("Cannot get 'self' entity until the user is logged in.")
            return InputPeerUser(self._user_id, 0) # Hash is not needed for self

        try:
            entity_id = int(key)
            entity = self._db_session.query(Entity).filter(
                Entity.session_id == self._session_id,
                Entity.entity_id == entity_id
            ).first()

            if entity:
                # Using the new 'type' column for robustness
                if entity.type == 'user':
                    return InputPeerUser(entity.entity_id, entity.hash)
                elif entity.type == 'chat':
                    return InputPeerChat(entity.entity_id)
                elif entity.type == 'channel':
                    return InputPeerChannel(entity.entity_id, entity.hash)
        except (TypeError, ValueError):
            pass # Will fall through to the final ValueError

        raise ValueError(f"Could not find input entity for key {key}")

    def process_entities(self, tlo):
        rows_to_add = []
        for entity in tlo:
            entity_type = None
            if isinstance(entity, User): entity_type = 'user'
            elif isinstance(entity, Chat): entity_type = 'chat'
            elif isinstance(entity, Channel): entity_type = 'channel'
            
            if not entity_type: continue
            
            # Check if this entity already exists to avoid duplicates
            existing = self._db_session.query(Entity.id).filter(
                Entity.session_id == self._session_id,
                Entity.entity_id == entity.id
            ).first()
            if existing: continue

            rows_to_add.append(Entity(
                session_id=self._session_id,
                entity_id=entity.id,
                hash=getattr(entity, 'access_hash', 0),
                username=getattr(entity, 'username', None),
                phone=getattr(entity, 'phone', None),
                name=getattr(entity, 'title', None) or f"{getattr(entity, 'first_name', '')} {getattr(entity, 'last_name', '')}".strip(),
                type=entity_type
            ))
        
        if rows_to_add:
            self._db_session.add_all(rows_to_add)
            self._db_session.commit()
    
    # These methods are not needed for this project's scope
    def get_update_state(self, entity_id): return None
    def set_update_state(self, entity_id, state): pass
    def get_update_states(self): return []
    @property
    def takeout_id(self): return None
    def get_file(self, md5_digest, file_size, cls): return None
    def cache_file(self, md5_digest, file_size, instance): pass

def get_db_session(session_id: str):
    return SQLAlchemySession(session_id)

