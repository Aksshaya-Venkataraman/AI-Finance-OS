from datetime import date, timedelta

import pytest

TODAY = date.today()


def make_account(client, headers, name="Current", balance="1000.00", kind="current"):
    resp = client.post(
        "/api/v1/accounts",
        json={"name": name, "account_type": kind, "currency": "GBP", "opening_balance": balance},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def add_tx(client, headers, account_id, amount, category="groceries", description="Tesco", day=TODAY):
    return client.post(
        "/api/v1/transactions",
        json={
            "account_id": account_id,
            "booked_on": day.isoformat(),
            "amount": amount,
            "description": description,
            "category": category,
        },
        headers=headers,
    )


def test_account_balance_includes_transactions(client, auth):
    account = make_account(client, auth)
    add_tx(client, auth, account["id"], "-45.50")
    add_tx(client, auth, account["id"], "2500.00", category="income", description="Salary")
    listed = client.get("/api/v1/accounts", headers=auth).json()
    assert listed[0]["balance"] == "3454.50"


def test_duplicate_account_names_conflict(client, auth):
    make_account(client, auth, name="Savings")
    resp = client.post("/api/v1/accounts", json={"name": "savings", "account_type": "savings"}, headers=auth)
    assert resp.status_code == 409


def test_transactions_filter_and_paginate(client, auth):
    account = make_account(client, auth)
    for i in range(5):
        add_tx(client, auth, account["id"], f"-{10 + i}.00", day=TODAY - timedelta(days=i))
    add_tx(client, auth, account["id"], "-99.00", category="dining", description="Pizza")
    page = client.get("/api/v1/transactions?limit=2&category=groceries", headers=auth).json()
    assert page["total"] == 5
    assert len(page["items"]) == 2
    assert page["items"][0]["booked_on"] >= page["items"][1]["booked_on"]


def test_update_and_delete_transaction(client, auth):
    account = make_account(client, auth)
    tx = add_tx(client, auth, account["id"], "-12.00").json()
    patched = client.patch(f"/api/v1/transactions/{tx['id']}", json={"category": "dining"}, headers=auth)
    assert patched.json()["category"] == "dining"
    assert client.delete(f"/api/v1/transactions/{tx['id']}", headers=auth).status_code == 204
    assert client.get("/api/v1/transactions", headers=auth).json()["total"] == 0


def test_users_cannot_touch_each_others_data(client, auth, other_auth):
    account = make_account(client, auth)
    tx = add_tx(client, auth, account["id"], "-30.00").json()

    # The intruder cannot see, use, change or delete the owner's records.
    assert client.get("/api/v1/accounts", headers=other_auth).json() == []
    assert client.get("/api/v1/transactions", headers=other_auth).json()["total"] == 0
    assert add_tx(client, other_auth, account["id"], "-1.00").status_code == 404
    assert client.patch(f"/api/v1/transactions/{tx['id']}", json={"category": "other"}, headers=other_auth).status_code == 404
    assert client.delete(f"/api/v1/transactions/{tx['id']}", headers=other_auth).status_code == 404
    assert client.delete(f"/api/v1/accounts/{account['id']}", headers=other_auth).status_code == 404
    assert client.get("/api/v1/transactions", headers=auth).json()["total"] == 1


def test_unauthenticated_requests_rejected(client):
    for url in ("/api/v1/accounts", "/api/v1/transactions", "/api/v1/budgets", "/api/v1/holdings"):
        assert client.get(url).status_code == 401


@pytest.mark.parametrize(
    "change",
    [
        {"amount": "0"},
        {"amount": "12.345"},
        {"description": "<img src=x onerror=alert(1)>"},
        {"category": "bitcoin-mining"},
        {"booked_on": "1900-01-01"},
        {"account_id": -1},
        {"owner_id": 2},
    ],
    ids=["zero", "three-dp", "xss", "bad-category", "ancient-date", "negative-id", "mass-assignment"],
)
def test_invalid_transactions_rejected(client, auth, change):
    account = make_account(client, auth)
    body = {
        "account_id": account["id"],
        "booked_on": TODAY.isoformat(),
        "amount": "-5.00",
        "description": "Coffee",
        "category": "dining",
        **change,
    }
    assert client.post("/api/v1/transactions", json=body, headers=auth).status_code == 422


def test_csv_import_all_or_nothing(client, auth):
    account = make_account(client, auth)
    good = "date,amount,description,category\n2026-11-01,-12.50,Cafe,dining\n2026-11-02,1800,Salary,income\n"
    resp = client.post(
        f"/api/v1/transactions/import?account_id={account['id']}", files={"file": ("tx.csv", good, "text/csv")}, headers=auth
    )
    assert resp.status_code == 201
    assert resp.json()["imported"] == 2

    bad = "date,amount,description,category\n2026-11-03,-5,Ok,dining\nnot-a-date,-5,Bad,dining\n"
    resp = client.post(
        f"/api/v1/transactions/import?account_id={account['id']}", files={"file": ("tx.csv", bad, "text/csv")}, headers=auth
    )
    assert resp.status_code == 422
    assert "line 3" in resp.json()["detail"]["errors"][0]
    assert client.get("/api/v1/transactions", headers=auth).json()["total"] == 2


def test_csv_import_rejects_wrong_header_and_foreign_account(client, auth, other_auth):
    account = make_account(client, auth)
    resp = client.post(
        f"/api/v1/transactions/import?account_id={account['id']}", files={"file": ("tx.csv", "a,b\n1,2\n", "text/csv")}, headers=auth
    )
    assert resp.status_code == 422
    resp = client.post(
        f"/api/v1/transactions/import?account_id={account['id']}",
        files={"file": ("tx.csv", "date,amount,description,category\n", "text/csv")},
        headers=other_auth,
    )
    assert resp.status_code == 404


def test_budgets_track_current_month(client, auth):
    account = make_account(client, auth)
    add_tx(client, auth, account["id"], "-90.00", category="dining", description="Dinner", day=TODAY.replace(day=1))
    resp = client.put("/api/v1/budgets/dining", json={"monthly_limit": "100.00"}, headers=auth)
    assert resp.status_code == 200
    status = resp.json()
    assert status["spent_this_month"] == "90.00"
    assert status["status"] == "warning"
    assert client.put("/api/v1/budgets/dining", json={"monthly_limit": "-5"}, headers=auth).status_code == 422
    assert client.delete("/api/v1/budgets/dining", headers=auth).status_code == 204
    assert client.delete("/api/v1/budgets/dining", headers=auth).status_code == 404


def test_holdings_lifecycle(client, auth, other_auth):
    body = {
        "symbol": "vwrl",
        "name": "FTSE All-World ETF",
        "asset_class": "fund",
        "quantity": "10",
        "cost_basis": "900.00",
        "current_price": "105.50",
    }
    created = client.post("/api/v1/holdings", json=body, headers=auth)
    assert created.status_code == 201
    holding = created.json()
    assert holding["symbol"] == "VWRL"
    assert holding["market_value"] == "1055.00"
    assert holding["unrealised_gain"] == "155.00"
    assert client.post("/api/v1/holdings", json=body, headers=auth).status_code == 409
    updated = client.patch(f"/api/v1/holdings/{holding['id']}", json={"current_price": "80"}, headers=auth)
    assert updated.json()["unrealised_gain"] == "-100.00"
    assert client.patch(f"/api/v1/holdings/{holding['id']}", json={"current_price": "1"}, headers=other_auth).status_code == 404
    assert client.delete(f"/api/v1/holdings/{holding['id']}", headers=auth).status_code == 204
