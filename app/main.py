"""FastAPI app and HTTP routes."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app import splitting
from app.db import Expense, ExpenseShare, Group, Member, get_session, init_db
from app.schemas import BalanceOut, ExpenseIn, ExpenseOut, GroupIn, GroupOut, MemberIn, MemberOut, TransferOut


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


app = FastAPI(title="expense-splitter", lifespan=lifespan)


def get_group(group_id: int, session: Session = Depends(get_session)) -> Group:
    group = session.get(Group, group_id)
    if group is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "group not found")
    return group


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse("/docs")


@app.post("/groups",response_model=GroupOut, status_code=status.HTTP_201_CREATED)
def create_group(body: GroupIn, session: Session = Depends(get_session)) -> Group:
    group = Group(name=body.name, members=[Member(name=n.strip()) for n in body.members])
    session.add(group)
    session.commit()
    return group


@app.get("/groups/{group_id}", response_model=GroupOut)
def read_group(group: Group = Depends(get_group)) -> Group:
    return group


@app.post("/groups/{group_id}/members", response_model=MemberOut, status_code=status.HTTP_201_CREATED)
def add_member(body: MemberIn, group: Group = Depends(get_group), session: Session = Depends(get_session)) -> Member:
    member = Member(name=body.name.strip(), group=group)
    session.add(member)
    session.commit()
    return member


@app.post("/groups/{group_id}/expenses", response_model=ExpenseOut, status_code=status.HTTP_201_CREATED)
def add_expense(body: ExpenseIn, group: Group = Depends(get_group), session: Session = Depends(get_session)) -> Expense:
    member_ids = {m.id for m in group.members}
    if body.payer_id not in member_ids:
        raise HTTPException(422, "payer is not a member of this group")
    unknown = sorted(set(body.split_among) - member_ids)
    if unknown:
        raise HTTPException(422, f"not members of this group: {unknown}")

    shares = splitting.split_equally(body.amount_paise, body.split_among)
    expense = Expense(
        group=group,
        payer_id=body.payer_id,
        amount_paise=body.amount_paise,
        description=body.description,
        shares=[ExpenseShare(member_id=mid, share_paise=p) for mid, p in shares.items()],
    )
    session.add(expense)
    session.commit()
    return expense


@app.get("/groups/{group_id}/expenses", response_model=list[ExpenseOut])
def list_expenses(group: Group = Depends(get_group)) -> list[Expense]:
    return group.expenses


def _balances(group: Group) -> dict[int, int]:
    return splitting.net_balances(
        (m.id for m in group.members),
        ((e.payer_id, e.amount_paise) for e in group.expenses),
        ((s.member_id, s.share_paise) for e in group.expenses for s in e.shares),
    )


@app.get("/groups/{group_id}/balances", response_model=list[BalanceOut])
def balances(group: Group = Depends(get_group)) -> list[BalanceOut]:
    nets = _balances(group)
    return [BalanceOut(member_id=m.id, name=m.name, balance_paise=nets[m.id]) for m in group.members]


@app.get("/groups/{group_id}/settle", response_model=list[TransferOut])
def settle(group: Group = Depends(get_group)) -> list[TransferOut]:
    names = {m.id: m.name for m in group.members}
    return [
        TransferOut(
            from_member_id=debtor,
            from_name=names[debtor],
            to_member_id=creditor,
            to_name=names[creditor],
            amount_paise=paise,
            summary=f"{names[debtor]} pays {names[creditor]} {splitting.format_rupees(paise)}",
        )
        for debtor, creditor, paise in splitting.settle(_balances(group))
    ]
