"""Database engine, session handling and ORM models."""

import os
from collections.abc import Iterator

from sqlalchemy import ForeignKey, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./expense_splitter.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    members: Mapped[list["Member"]] = relationship(back_populates="group", order_by="Member.id")
    expenses: Mapped[list["Expense"]] = relationship(back_populates="group", order_by="Expense.id")


class Member(Base):
    __tablename__ = "members"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    group: Mapped[Group] = relationship(back_populates="members")


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), index=True)
    payer_id: Mapped[int] = mapped_column(ForeignKey("members.id"))
    amount_paise: Mapped[int] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(String(200))
    group: Mapped[Group] = relationship(back_populates="expenses")
    shares: Mapped[list["ExpenseShare"]] = relationship(
        back_populates="expense", cascade="all, delete-orphan", order_by="ExpenseShare.member_id"
    )


class ExpenseShare(Base):
    """How much of an expense one member owes, in paise."""

    __tablename__ = "expense_shares"

    expense_id: Mapped[int] = mapped_column(ForeignKey("expenses.id"), primary_key=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"), primary_key=True)
    share_paise: Mapped[int] = mapped_column(Integer)
    expense: Mapped[Expense] = relationship(back_populates="shares")


def init_db() -> None:
    Base.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session
