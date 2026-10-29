"""FastAPI application for the TraceLedger Demo Expense Tracker.

Runs on 127.0.0.1:8002.
Interacts with sidecar/receiver for real-time audit logging.
"""
from contextlib import asynccontextmanager
import csv
import io
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from .auditor import assert_no_floats, default_auditor
from .database import (
    add_expense,
    delete_expense,
    get_budget,
    get_expenses,
    init_db,
    set_budget,
    update_expense_amount,
)

# Hard-coded demonstration credentials
USERS = {
    "alice": "password123",
    "bob": "builder456",
}

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager: initialize database and start background outbox flusher."""
    init_db()
    default_auditor.start_background_worker()
    yield
    default_auditor.stop_background_worker()


app = FastAPI(title="TraceLedger Demo Expense Tracker", lifespan=lifespan)


class LoginRequest(BaseModel):
    username: str
    password: str


class CreateExpenseRequest(BaseModel):
    user: str = "alice"
    category: str
    amount_minor: int = Field(gt=0, description="Amount in paise (integer)")
    description: str


class UpdateExpenseRequest(BaseModel):
    amount_minor: int = Field(gt=0, description="Amount in paise (integer)")
    user: str = "alice"


class BudgetRequest(BaseModel):
    budget_minor: int = Field(ge=0, description="Budget in paise (integer)")
    user: str = "alice"


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    """Serve the single-page UI."""
    index_file = STATIC_DIR / "index.html"
    return index_file.read_text(encoding="utf-8")


@app.post("/api/login")
def login(req: LoginRequest) -> dict[str, Any]:
    """Authenticate a demo user and emit an authentication audit event."""
    username = req.username.strip()
    expected_pass = USERS.get(username)

    if expected_pass and req.password == expected_pass:
        # Success event
        default_auditor.emit(
            "authentication",
            {"user": username, "result": "success"},
        )
        return {"ok": True, "user": username}
    else:
        # Failure event - Never log passwords or secrets in details!
        default_auditor.emit(
            "authentication",
            {"user": username, "result": "failure", "reason": "invalid_credentials"},
        )
        raise HTTPException(status_code=401, detail="Invalid username or password")


@app.get("/api/expenses")
def list_expenses() -> list[dict[str, Any]]:
    """List all recorded expenses."""
    return get_expenses()


@app.post("/api/expenses")
def create_new_expense(req: CreateExpenseRequest) -> dict[str, Any]:
    """Create a new expense and emit expense_created audit event."""
    assert_no_floats(req.amount_minor, "amount_minor")
    expense = add_expense(
        user=req.user,
        category=req.category,
        amount_minor=req.amount_minor,
        description=req.description,
    )
    # Never log free-text notes or sensitive info in audit details
    default_auditor.emit(
        "expense_created",
        {
            "expense_id": expense["id"],
            "amount_minor": expense["amount_minor"],
            "category": expense["category"],
            "user": expense["user"],
        },
    )
    return expense


@app.put("/api/expenses/{expense_id}")
def update_expense(expense_id: str, req: UpdateExpenseRequest) -> dict[str, Any]:
    """Update an expense amount and emit expense_updated audit event."""
    assert_no_floats(req.amount_minor, "amount_minor")
    updated, old_amount = update_expense_amount(expense_id, req.amount_minor)
    if not updated:
        raise HTTPException(status_code=404, detail="Expense not found")

    default_auditor.emit(
        "expense_updated",
        {
            "expense_id": expense_id,
            "old_amount_minor": old_amount,
            "new_amount_minor": updated["amount_minor"],
            "user": req.user,
        },
    )
    return updated


@app.delete("/api/expenses/{expense_id}")
def delete_single_expense(expense_id: str, user: str = "alice") -> dict[str, Any]:
    """Delete an expense and emit expense_deleted audit event."""
    deleted = delete_expense(expense_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Expense not found")

    default_auditor.emit(
        "expense_deleted",
        {
            "expense_id": expense_id,
            "amount_minor": deleted["amount_minor"],
            "user": user,
        },
    )
    return {"ok": True}


@app.get("/api/budget")
def get_current_budget() -> dict[str, int]:
    """Retrieve monthly budget limit."""
    return {"budget_minor": get_budget()}


@app.post("/api/budget")
def update_current_budget(req: BudgetRequest) -> dict[str, int]:
    """Set monthly budget limit and emit budget_changed audit event."""
    assert_no_floats(req.budget_minor, "budget_minor")
    new_budget, old_budget = set_budget(req.budget_minor)
    default_auditor.emit(
        "budget_changed",
        {
            "old_budget_minor": old_budget,
            "new_budget_minor": new_budget,
            "user": req.user,
        },
    )
    return {"budget_minor": new_budget}


@app.get("/api/export")
def export_csv(user: str = "alice") -> Response:
    """Export expenses as CSV and emit data_exported audit event."""
    expenses = get_expenses()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "user", "category", "amount_minor", "description", "created_at"])
    for exp in expenses:
        writer.writerow([
            exp["id"],
            exp["user"],
            exp["category"],
            exp["amount_minor"],
            exp["description"],
            exp["created_at"],
        ])

    csv_content = output.getvalue()
    default_auditor.emit(
        "data_exported",
        {
            "record_count": len(expenses),
            "format": "csv",
            "user": user,
        },
    )
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=expenses.csv"},
    )


@app.get("/api/status")
def status() -> dict[str, int]:
    """Return sent and queued audit event counts."""
    return default_auditor.get_status()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("demo_app.main:app", host="127.0.0.1", port=8002, reload=False)
