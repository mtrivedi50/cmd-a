import logging
from contextlib import contextmanager
from typing import Any, TypeVar

from fastapi import HTTPException
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import orm
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select
from sqlmodel import create_engine, select
from starlette.status import HTTP_404_NOT_FOUND

from app.db.models.base import CmdAModel

logger = logging.getLogger(__name__)


T = TypeVar("T", bound=CmdAModel)
R = TypeVar("R", bound=CmdAModel)


class Database:
    def __init__(self, db_url: str, pool_size: int = 10):
        self.db_url = db_url
        self.pool_size = pool_size

        self._engine: Engine = create_engine(
            self.db_url,
            pool_size=self.pool_size,
            max_overflow=2,
            echo=False,
            pool_pre_ping=True,
        )

        self._session_factory = orm.scoped_session(
            orm.sessionmaker(autocommit=False, autoflush=False, bind=self._engine)
        )

    @contextmanager
    def session(self):
        session: orm.Session = self._session_factory()
        try:
            yield session
        except Exception as e:
            logger.exception(f"Session rollback because of exception: {e}")
            session.rollback()
            raise
        finally:
            session.close()

    def get_object(
        self,
        db_type: type[T],
        where_conditions: dict[str, Any],
        session: Session | None = None,
        headers: dict[str, str] | None = None,
    ) -> T:
        """
        Get specific database object that match the criteria defined in the statement.
        """
        db_objects = self.all_objects(db_type, where_conditions, session)
        if not db_objects:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail=f"{db_type.__class__.__name__} with {where_conditions} does not exist!",
                headers=headers if headers else None,
            )
        return db_objects[0]

    def paginated_objects(
        self,
        db_type: type[T],
        order_by: list[str],
        where_conditions: dict[str, Any] | None = None,
        session: Session | None = None,
    ) -> Page[T]:
        where_bool_clause_list = []
        for col, value in (where_conditions or {}).items():
            where_bool_clause_list.append(getattr(db_type, col) == value)
        stmt = (
            select(db_type)
            .where(*where_bool_clause_list)
            .order_by(*[getattr(db_type, col) for col in order_by])
        )
        if session:
            return paginate(session, stmt)

        # Otherwise, create a session and execute
        with self.session() as new_session:
            return paginate(new_session, stmt)

    def all_objects(
        self,
        db_type: type[T],
        where_conditions: dict[str, Any] | None = None,
        session: Session | None = None,
    ) -> list[T]:
        """
        Get all database objects that match the criteria defined in the statement.
        """
        where_bool_clause_list = []
        for col, value in (where_conditions or {}).items():
            where_bool_clause_list.append(getattr(db_type, col) == value)
        stmt = select(db_type).where(*where_bool_clause_list)
        if session:
            res = session.execute(stmt)
            return [row._asdict()[db_type.__name__] for row in res.all()]

        # Otherwise, create a session and execute
        with self.session() as new_session:
            res = new_session.execute(stmt)
            return [row._asdict()[db_type.__name__] for row in res.all()]

    def execute_stmt(
        self,
        stmt: Select,
        session: Session | None = None,
    ) -> list[dict[str, Any]]:
        """
        Execute arbitrary SQL statement and return the result as a list of dictionaries
        """
        if session:
            res = session.execute(stmt)
            return [row._asdict() for row in res.all()]

        # Otherwise, create a session and execute
        with self.session() as new_session:
            res = new_session.execute(stmt)
            return [row._asdict() for row in res.all()]

    def update_object(
        self,
        db_type: type[T],
        where_conditions: dict[str, Any],
        headers: dict[str, str] | None = None,
        **kwargs,
    ) -> T:
        with self.session() as session:
            obj = self.get_object(db_type, where_conditions, session, headers)
            for attr, val in kwargs.items():
                setattr(obj, attr, val)
            session.commit()
            session.refresh(obj)

        # Return the updated object
        updated_obj = self.get_object(
            db_type, where_conditions, session=None, headers=headers
        )
        return updated_obj

    def get_object_fk_attribute(
        self,
        db_type: type[T],
        where_conditions: dict[str, Any],
        fk: str,
        fk_type: type[R],
        headers: dict[str, str] | None = None,
    ) -> R:
        fk_obj: R | None = None
        with self.session() as session:
            obj = self.get_object(db_type, where_conditions, session, headers)
            if hasattr(obj, fk):
                fk_obj = getattr(obj, fk)
        if fk_obj is None:
            raise Exception(f"`{fk}` ForeignKey does not exist!")
        if not isinstance(fk_obj, fk_type):
            raise Exception(f"`{fk}` ForeignKey is not a {fk_type.__class__.__name__}!")
        return fk_obj

    def add(self, db_object: T, session: Session | None = None) -> T:
        if not session:
            with self.session() as new_session:
                new_session.add(db_object)
                new_session.commit()
                new_session.refresh(db_object)
        else:
            session.add(db_object)
            session.commit()
            session.refresh(db_object)
        return db_object

    def delete(self, db_object: T) -> None:
        with self.session() as session:
            session.delete(db_object)
            session.commit()
