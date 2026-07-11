from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Generator

from neo4j import Driver, GraphDatabase, Session

from app.config import settings
from app.services.redaction import redact_text

logger = logging.getLogger("firecrow.graph.database")
_driver: Driver | None = None


def _build_driver() -> Driver:
    if settings.DATABASE_BACKEND != "neo4j":
        raise RuntimeError("Neo4j driver requested while DATABASE_BACKEND is not set to neo4j.")
    if not settings.NEO4J_URI or not settings.NEO4J_USER or not settings.NEO4J_PASSWORD:
        raise RuntimeError("Neo4j configuration is incomplete.")
    return GraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        max_connection_pool_size=settings.NEO4J_MAX_CONNECTION_POOL_SIZE,
        connection_timeout=settings.NEO4J_CONNECTION_TIMEOUT_SECONDS,
    )


def get_neo4j_driver() -> Driver:
    global _driver
    if _driver is None:
        _driver = _build_driver()
    return _driver


def verify_neo4j_connectivity() -> None:
    try:
        get_neo4j_driver().verify_connectivity()
        logger.info("Connected to Neo4j database %s", redact_text(settings.NEO4J_URI))
    except Exception as exc:
        logger.error("Neo4j connectivity check failed: %s", redact_text(str(exc)))
        raise


@contextmanager
def neo4j_session() -> Generator[Session, None, None]:
    driver = get_neo4j_driver()
    with driver.session(database=settings.NEO4J_DATABASE) as session:
        yield session


def get_neo4j_session() -> Generator[Session, None, None]:
    with neo4j_session() as session:
        yield session


def close_neo4j_driver() -> None:
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None
