import logging
from typing import Any, Optional
from neo4j import GraphDatabase, AsyncGraphDatabase, Driver, AsyncDriver, Session, AsyncSession
from backend.app.config import settings

logger = logging.getLogger("firecrow.services.neo4j_client")

_driver: Optional[Driver] = None
_async_driver: Optional[AsyncDriver] = None


def _get_auth() -> tuple[str, str] | None:
    if settings.NEO4J_USER and settings.NEO4J_PASSWORD:
        return (settings.NEO4J_USER, settings.NEO4J_PASSWORD)
    return None


def get_driver() -> Driver:
    global _driver
    if _driver is None:
        auth = _get_auth()
        _driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=auth,
            max_connection_lifetime=3600,
            connection_timeout=10,
        )
        logger.info("Connected to Neo4j at %s", settings.NEO4J_URI)
    return _driver


def get_async_driver() -> AsyncDriver:
    global _async_driver
    if _async_driver is None:
        auth = _get_auth()
        _async_driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=auth,
            max_connection_lifetime=3600,
            connection_timeout=10,
        )
    return _async_driver


def get_session() -> Session:
    driver = get_driver()
    return driver.session(database=settings.NEO4J_DATABASE)


async def get_async_session() -> AsyncSession:
    driver = get_async_driver()
    return driver.session(database=settings.NEO4J_DATABASE)


def close():
    global _driver, _async_driver
    if _driver:
        _driver.close()
        _driver = None
    if _async_driver:
        import asyncio
        coro = _async_driver.close()
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(coro)
            else:
                loop.run_until_complete(coro)
        except Exception:
            pass
        _async_driver = None


def verify_connectivity() -> bool:
    try:
        driver = get_driver()
        driver.verify_connectivity()
        logger.info("Neo4j connectivity verified successfully.")
        return True
    except Exception as e:
        if not settings.DEBUG:
            logger.critical("FATAL: Cannot connect to Neo4j in production: %s", e)
            return False
        logger.warning("Neo4j connectivity check failed (DEBUG mode): %s", e)
        return False


def execute_query(query: Any, parameters: dict | None = None) -> list[dict]:
    with get_session() as session:
        result = session.run(query, parameters or {})
        return [record.data() for record in result]


async def execute_query_async(query: Any, parameters: dict | None = None) -> list[dict]:
    session = await get_async_session()
    try:
        result = await session.run(query, parameters or {})
        records = await result.data()
        return records
    finally:
        await session.close()
