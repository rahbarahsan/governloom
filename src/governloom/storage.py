import os
from contextlib import contextmanager

from sqlalchemy import JSON, Column, Float, Integer, String, UniqueConstraint, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session


class Base(DeclarativeBase):
    pass


class Entity(Base):
    __tablename__ = "entities"
    id = Column(String, primary_key=True)
    kind = Column(String, nullable=False, index=True)
    application_id = Column(String, index=True)
    payload = Column(JSON, nullable=False)


class Job(Base):
    __tablename__ = "jobs"
    id = Column(String, primary_key=True)
    application_id = Column(String, nullable=False)
    status = Column(String, nullable=False, index=True)
    payload = Column(JSON, nullable=False)
    created_at = Column(String, nullable=False)
    updated_at = Column(String, nullable=False)
    lease_until = Column(Float, nullable=False, default=0)
    owner = Column(String)
    completed = Column(Integer, nullable=False, default=0)
    total = Column(Integer, nullable=False)
    cancel_requested = Column(Integer, nullable=False, default=0)
    error = Column(String)


class Result(Base):
    __tablename__ = "results"
    id = Column(String, primary_key=True)
    run_id = Column(String, nullable=False, index=True)
    case_id = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    __table_args__ = (UniqueConstraint("run_id", "case_id"),)


class Store:
    def __init__(self, url: str | None = None):
        self.url = url or os.environ.get("GOVERNLOOM_DB", "sqlite:///data/governloom.db")
        if self.url.startswith("sqlite:///") and ":memory:" not in self.url:
            from pathlib import Path
            Path(self.url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(self.url, connect_args={"check_same_thread": False, "timeout": 30})

        @event.listens_for(self.engine, "connect")
        def pragmas(connection, _):
            cursor = connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.close()

        Base.metadata.create_all(self.engine)

    @contextmanager
    def session(self):
        with Session(self.engine, expire_on_commit=False) as session:
            with session.begin():
                yield session

    def put(self, kind: str, payload: dict, application_id: str | None = None):
        with self.session() as session:
            if session.get(Entity, payload["id"]):
                raise ValueError("Record already exists")
            session.add(Entity(id=payload["id"], kind=kind, application_id=application_id, payload=payload))
        return payload

    def get(self, kind: str, record_id: str):
        with self.session() as session:
            row = session.get(Entity, record_id)
            if not row or row.kind != kind:
                raise ValueError(f"Unknown {kind}: {record_id}")
            return row.payload

    def list(self, kind: str, application_id: str | None = None):
        from sqlalchemy import select
        with self.session() as session:
            query = select(Entity).where(Entity.kind == kind)
            if application_id:
                query = query.where(Entity.application_id == application_id)
            return [row.payload for row in session.scalars(query.order_by(Entity.id))]
