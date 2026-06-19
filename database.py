import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship, declarative_base

SQLALCHEMY_DATABASE_URL = "sqlite:///./local_app.db"

# connect_args={"check_same_thread": False} chỉ cần thiết cho SQLite
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class GlossaryCollection(Base):
    __tablename__ = "glossary_collections"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # cascade="all, delete-orphan" tự động xóa các terms thuộc collection khi collection bị xóa
    terms = relationship("GlossaryTerm", back_populates="collection", cascade="all, delete-orphan")

class GlossaryTerm(Base):
    __tablename__ = "glossary_terms"

    id = Column(Integer, primary_key=True, index=True)
    collection_id = Column(Integer, ForeignKey("glossary_collections.id", ondelete="CASCADE"), nullable=False)
    source_term = Column(String, index=True, nullable=False)
    target_term = Column(String, nullable=False)

    collection = relationship("GlossaryCollection", back_populates="terms")

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
