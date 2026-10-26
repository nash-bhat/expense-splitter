from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app import splitting
from app.db import Base, get_session
from app.main import app


@pytest.fixture
def client() -> Iterator[TestClient]:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override() -> Iterator[Session]:
        with TestSession() as session:
            yield session

    app.dependency_overrides[get_session] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


def make_group(client: TestClient, *names: str) -> tuple[int, dict[str, int]]:
    resp = client.post("/groups", json={"name": "Trip", "members": list(names)})
    assert resp.status_code == 201
    body = resp.json()
    return body["id"], {m["name"]: m["id"] for m in body["members"]}


def add_expense(client: TestClient, gid: int, payer: int, paise: int, among: list[int]) -> dict:
    resp = client.post(
        f"/groups/{gid}/expenses",
        json={"payer_id": payer, "amount_paise": paise, "description": "x", "split_among": among},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_create_group_and_add_member(client: TestClient) -> None:
    gid, ids = make_group(client, "Asha", "Bala")
    resp = client.post(f"/groups/{gid}/members", json={"name": "Chetan"})
    assert resp.status_code == 201

    group = client.get(f"/groups/{gid}").json()
    assert group["name"] == "Trip"
    assert [m["name"] for m in group["members"]] == ["Asha", "Bala", "Chetan"]


def test_add_and_list_expenses(client: TestClient) -> None:
    gid, ids = make_group(client, "Asha", "Bala", "Chetan")
    expense = add_expense(client, gid, ids["Asha"], 1000, list(ids.values()))

    # 1000 paise / 3 -> one member absorbs the extra paisa; shares sum exactly.
    assert sorted(s["share_paise"] for s in expense["shares"]) == [333, 333, 334]
    assert sum(s["share_paise"] for s in expense["shares"]) == 1000

    listed = client.get(f"/groups/{gid}/expenses").json()
    assert [e["id"] for e in listed] == [expense["id"]]


def test_balances(client: TestClient) -> None:
    gid, ids = make_group(client, "Asha", "Bala", "Chetan")
    a, b, c = ids["Asha"], ids["Bala"], ids["Chetan"]
    add_expense(client, gid, a, 90000, [a, b, c])  # each owes 300.00
    add_expense(client, gid, b, 20000, [b, c])  # each owes 100.00

    balances = {r["name"]: r["balance_paise"] for r in client.get(f"/groups/{gid}/balances").json()}
    assert balances == {"Asha": 60000, "Bala": -20000, "Chetan": -40000}
    assert sum(balances.values()) == 0


def test_settle(client: TestClient) -> None:
    gid, ids = make_group(client, "Asha", "Bala", "Chetan")
    a, b, c = ids["Asha"], ids["Bala"], ids["Chetan"]
    add_expense(client, gid, a, 90000, [a, b, c])
    add_expense(client, gid, b, 20000, [b, c])

    transfers = client.get(f"/groups/{gid}/settle").json()
    assert [t["summary"] for t in transfers] == ["Chetan pays Asha ₹400", "Bala pays Asha ₹200"]
    assert transfers[0]["amount_paise"] == 40000


def test_settle_when_already_even(client: TestClient) -> None:
    gid, ids = make_group(client, "Asha", "Bala")
    add_expense(client, gid, ids["Asha"], 5000, [ids["Asha"]])
    assert client.get(f"/groups/{gid}/settle").json() == []


def test_settle_zeroes_every_balance() -> None:
    balances = {1: 700, 2: -250, 3: -250, 4: 50, 5: -250}
    after = dict(balances)
    for debtor, creditor, paise in splitting.settle(balances):
        after[debtor] += paise
        after[creditor] -= paise
    assert all(v == 0 for v in after.values())


def test_format_rupees() -> None:
    assert splitting.format_rupees(40000) == "₹400"
    assert splitting.format_rupees(12345) == "₹123.45"
    assert splitting.format_rupees(5) == "₹0.05"
