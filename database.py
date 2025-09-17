# database.py
import os
from dotenv import load_dotenv

from sqlalchemy import create_engine, Column, Integer, String, LargeBinary, UniqueConstraint, BigInteger
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool

from telethon.sessions.abstract import Session
from telethon.crypto import AuthKey
from telethon.tl.types import User, Chat, Channel, InputPeerUser, InputPeerChat, InputPeerChannel

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Configure engine with better connection handling
if DATABASE_URL.startswith('sqlite'):
    engine = create_engine(
        DATABASE_URL,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=300,
        pool_size=10,
        max_overflow=20
    )

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
    user_id = Column(BigInteger)

class Entity(Base):
    __tablename__ = "entities"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    entity_id = Column(BigInteger)
    hash = Column(BigInteger)
    username = Column(String)
    phone = Column(String)
    name = Column(String)
    type = Column(String) 
    
    __table_args__ = (UniqueConstraint('session_id', 'entity_id', name='_session_entity_uc'),)


def init_db():
    """Creates the database tables if they don't exist."""
    Base.metadata.create_all(bind=engine)

# --- Custom Telethon Session Class (Fixed Version) ---
class SQLAlchemySession(Session):
    """
    A Telethon session handler that stores session data in a PostgreSQL database.
    """
    def __init__(self, session_id: str):
        super().__init__()
        self._session_id = session_id
        self._db_session = None
        
        # Initialize with proper defaults
        self._dc_id = None
        self._server_address = None
        self._port = None
        self._auth_key = None
        self._user_id = None
        
        # Load existing session data
        self.load()

    def _get_db_session(self):
        """Get a fresh database session"""
        if not self._db_session:
            self._db_session = SessionLocal()
        return self._db_session

    def _get_session_from_db(self):
        db_session = self._get_db_session()
        try:
            return db_session.query(TelegramSession).filter(
                TelegramSession.session_id == self._session_id
            ).first()
        except Exception as e:
            print(f"Database query error: {e}")
            db_session.rollback()
            # Create new session and retry
            self._db_session = SessionLocal()
            return self._db_session.query(TelegramSession).filter(
                TelegramSession.session_id == self._session_id
            ).first()

    def load(self):
        """Load session data from database"""
        try:
            session = self._get_session_from_db()
            if session:
                self._dc_id = session.dc_id
                self._server_address = session.server_address
                self._port = session.port
                if session.auth_key:
                    self._auth_key = AuthKey(data=session.auth_key)
                self._user_id = session.user_id
                print(f"Loaded session data for {self._session_id}: DC={self._dc_id}, User={self._user_id}")
        except Exception as e:
            print(f"Error loading session {self._session_id}: {e}")

    @property
    def dc_id(self):
        return self._dc_id
    
    @property
    def server_address(self):
        return self._server_address
    
    @property
    def port(self):
        return self._port
    
    @property
    def auth_key(self):
        return self._auth_key

    def set_dc(self, dc_id, server_address, port):
        """Set data center information"""
        self._dc_id = dc_id
        self._server_address = server_address
        self._port = port
        self.save()

    @auth_key.setter
    def auth_key(self, value):
        """Set authentication key"""
        self._auth_key = value
        self.save()
    
    def save(self):
        """Save session data to database"""
        db_session = self._get_db_session()
        try:
            session = self._get_session_from_db()
            if not session:
                session = TelegramSession(session_id=self._session_id)
                db_session.add(session)
            
            session.dc_id = self._dc_id
            session.server_address = self._server_address
            session.port = self._port
            session.auth_key = self._auth_key.key if self._auth_key else None
            session.user_id = self._user_id
            
            db_session.commit()
        except Exception as e:
            print(f"Error saving session {self._session_id}: {e}")
            db_session.rollback()
            # Try to recreate session
            try:
                self._db_session = SessionLocal()
                self.save()  # Recursive call with fresh session
            except Exception as e2:
                print(f"Failed to save session after retry: {e2}")

    def close(self):
        """Close database connection"""
        if self._db_session:
            try:
                self._db_session.close()
            except Exception as e:
                print(f"Error closing session: {e}")
            finally:
                self._db_session = None

    def delete(self):
        """Delete session and associated entities from database"""
        db_session = self._get_db_session()
        try:
            session = self._get_session_from_db()
            if session:
                db_session.delete(session)
            
            # Delete associated entities
            db_session.query(Entity).filter(
                Entity.session_id == self._session_id
            ).delete()
            
            db_session.commit()
        except Exception as e:
            print(f"Error deleting session {self._session_id}: {e}")
            db_session.rollback()

    def get_input_entity(self, key):
        """Get input entity for a given key"""
        if key == 'self':
            if not self._user_id:
                raise ValueError("No user_id available for 'self'")
            return InputPeerUser(self._user_id, 0)

        db_session = self._get_db_session()
        
        # Try to parse as integer ID
        try:
            entity_id = int(key)
        except (ValueError, TypeError):
            # Try to find by username
            try:
                entity = db_session.query(Entity).filter(
                    Entity.session_id == self._session_id,
                    Entity.username == key.lstrip('@')
                ).first()
                
                if entity:
                    if entity.type == 'user':
                        return InputPeerUser(entity.entity_id, entity.hash)
                    elif entity.type == 'chat':
                        return InputPeerChat(entity.entity_id)
                    elif entity.type == 'channel':
                        return InputPeerChannel(entity.entity_id, entity.hash)
            except Exception as e:
                print(f"Error querying entity by username: {e}")
            
            raise ValueError(f"Could not find input entity for key '{key}'")
        
        # Find by entity ID
        try:
            entity = db_session.query(Entity).filter(
                Entity.session_id == self._session_id,
                Entity.entity_id == entity_id
            ).first()

            if entity:
                if entity.type == 'user':
                    return InputPeerUser(entity.entity_id, entity.hash)
                elif entity.type == 'chat':
                    return InputPeerChat(entity.entity_id)
                elif entity.type == 'channel':
                    return InputPeerChannel(entity.entity_id, entity.hash)
        except Exception as e:
            print(f"Error querying entity by ID: {e}")

        raise ValueError(f"Could not find input entity for ID {entity_id}")

    def process_entities(self, tlo):
        """Process and store entities from Telegram objects"""
        if not tlo:
            return
        
        # Handle different types of TLO responses
        entities_to_process = []
        
        # Extract entities based on the type of TLO
        if hasattr(tlo, 'users') and tlo.users:
            entities_to_process.extend(tlo.users)
        
        if hasattr(tlo, 'chats') and tlo.chats:
            entities_to_process.extend(tlo.chats)
            
        # For responses that don't contain processable entities, return early
        if hasattr(tlo, '__class__'):
            class_name = tlo.__class__.__name__
            if class_name in ['Config', 'SentCode', 'Authorization', 'State', 'DifferenceEmpty', 'ResolvedPeer']:
                return
            
        # If tlo is directly iterable and contains User/Chat/Channel objects
        try:
            if hasattr(tlo, '__iter__') and not isinstance(tlo, (str, bytes)):
                for item in tlo:
                    if isinstance(item, (User, Chat, Channel)):
                        entities_to_process.append(item)
        except (TypeError, AttributeError):
            # TLO is not iterable or doesn't contain the expected types
            pass
        
        if not entities_to_process:
            return
            
        db_session = self._get_db_session()
        try:
            rows_to_add = []
            for entity in entities_to_process:
                entity_type = None
                if isinstance(entity, User):
                    entity_type = 'user'
                elif isinstance(entity, Chat):
                    entity_type = 'chat' 
                elif isinstance(entity, Channel):
                    entity_type = 'channel'
                
                if not entity_type:
                    continue
                
                # Check if entity already exists
                existing = db_session.query(Entity).filter(
                    Entity.session_id == self._session_id,
                    Entity.entity_id == entity.id
                ).first()
                
                if existing:
                    # Update existing entity
                    existing.hash = getattr(entity, 'access_hash', 0) or 0
                    existing.username = getattr(entity, 'username', None)
                    existing.phone = getattr(entity, 'phone', None)
                    existing.name = self._get_entity_name(entity)
                    existing.type = entity_type
                else:
                    # Add new entity
                    rows_to_add.append(Entity(
                        session_id=self._session_id,
                        entity_id=entity.id,
                        hash=getattr(entity, 'access_hash', 0) or 0,
                        username=getattr(entity, 'username', None),
                        phone=getattr(entity, 'phone', None),
                        name=self._get_entity_name(entity),
                        type=entity_type
                    ))
            
            if rows_to_add:
                db_session.add_all(rows_to_add)
            
            db_session.commit()
        except Exception as e:
            db_session.rollback()
            # Silently handle entity processing errors to avoid spam

    def _get_entity_name(self, entity):
        """Extract name from entity"""
        if hasattr(entity, 'title') and entity.title:
            return entity.title
        
        name_parts = []
        if hasattr(entity, 'first_name') and entity.first_name:
            name_parts.append(entity.first_name)
        if hasattr(entity, 'last_name') and entity.last_name:
            name_parts.append(entity.last_name)
        
        return ' '.join(name_parts) if name_parts else None

    def set_user_id(self, user_id):
        """Set the user ID for this session"""
        self._user_id = user_id
        self.save()

    # Placeholder methods for update states (not needed for basic functionality)
    def get_update_state(self, entity_id):
        return None
    
    def set_update_state(self, entity_id, state):
        pass
    
    def get_update_states(self):
        return []
    
    @property
    def takeout_id(self):
        return None
    
    def get_file(self, md5_digest, file_size, cls):
        return None
    
    def cache_file(self, md5_digest, file_size, instance):
        pass

def get_all_sessions():
    """Get all session IDs from the database"""
    db_session = SessionLocal()
    try:
        sessions = db_session.query(TelegramSession).filter(
            TelegramSession.user_id.isnot(None)  # Only get authenticated sessions
        ).all()
        return [session.session_id for session in sessions]
    except Exception as e:
        print(f"Error getting all sessions: {e}")
        return []
    finally:
        db_session.close()

def get_db_session(session_id: str):
    return SQLAlchemySession(session_id)