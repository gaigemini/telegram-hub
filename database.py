# database.py
import os
from dotenv import load_dotenv

# --- CORRECTED IMPORTS ---
from sqlalchemy import create_engine, Column, Integer, String, LargeBinary, UniqueConstraint
from sqlalchemy.orm import sessionmaker, declarative_base

from telethon.sessions.abstract import Session
from telethon.crypto import AuthKey
# --- ADDED THIS IMPORT ---
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

class Entity(Base):
    __tablename__ = "entities"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    entity_id = Column(Integer)
    hash = Column(Integer)
    username = Column(String)
    phone = Column(String)
    name = Column(String)
    
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
        
        self._dc_id = 0
        self._server_address = None
        self._port = 443
        self._auth_key = None
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
        
        self._db_session.commit()

    def close(self): self._db_session.close()

    def delete(self):
        session = self._get_session_from_db()
        if session:
            self._db_session.delete(session)
            self._db_session.query(Entity).filter(Entity.session_id == self._session_id).delete()
            self._db_session.commit()

    def get_input_entity(self, key):
        try:
            entity_id = int(key)
            entity = self._db_session.query(Entity).filter(
                Entity.session_id == self._session_id,
                Entity.entity_id == entity_id
            ).first()
            if entity:
                if entity.hash == 0:
                    return InputPeerUser(entity.entity_id, entity.hash)
                elif entity.hash > 0:
                    return InputPeerChat(entity.entity_id)
                else:
                    return InputPeerChannel(entity.entity_id, entity.hash)
        except (TypeError, ValueError):
            pass
        return None

    def process_entities(self, tlo):
        rows = []
        for entity in tlo:
            if not isinstance(entity, (User, Chat, Channel)):
                continue
            
            # A more robust solution would use session.merge() to upsert
            # But for simplicity, we query first.
            existing = self._db_session.query(Entity).filter(
                Entity.session_id == self._session_id,
                Entity.entity_id == entity.id
            ).first()
            if existing:
                continue

            row = Entity(
                session_id=self._session_id,
                entity_id=entity.id,
                hash=getattr(entity, 'access_hash', 0),
                username=getattr(entity, 'username', None),
                phone=getattr(entity, 'phone', None),
                name=getattr(entity, 'title', None) or f"{getattr(entity, 'first_name', '')} {getattr(entity, 'last_name', '')}".strip()
            )
            rows.append(row)
        
        if rows:
            self._db_session.add_all(rows)
            self._db_session.commit()
    
    def get_update_state(self, entity_id): return None
    def set_update_state(self, entity_id, state): pass
    def get_update_states(self): return []
    @property
    def takeout_id(self): return None
    def get_file(self, md5_digest, file_size, cls): return None
    def cache_file(self, md5_digest, file_size, instance): pass

def get_db_session(session_id: str):
    return SQLAlchemySession(session_id)