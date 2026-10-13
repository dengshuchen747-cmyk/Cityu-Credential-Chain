import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ["WEB3_RPC_URL"] = ""
os.environ["CREDENTIAL_CONTRACT_ADDRESS"] = ""

from app.core.database import Base  # noqa: E402
from app import models  # noqa: E402, F401


@pytest.fixture()
def db_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, expire_on_commit=False)
    with TestingSession() as session:
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()
