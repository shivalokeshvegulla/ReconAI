from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Query,
    Depends,
    HTTPException,
)
from sqlalchemy.orm import Session
from sqlalchemy import select
from decimal import Decimal, InvalidOperation
from datetime import datetime
import csv
import uuid
import os
from io import StringIO
from src.config import get_settings
from src.database import get_db
from src.models.schema import SchemaManifest, SchemaManifestDB


router = APIRouter(tags=["Ingest"])


@router.post("/ingest/ledger")
async def ingest_ledger(
    file: UploadFile = File(...),
    batch_id: str | None = Query(None),
    db: Session = Depends(get_db),
):
    # Step 5: Read configuration
    settings = get_settings()
    upload_dir = settings.UPLOAD_DIR

    # Step 6: Generate batch ID if not supplied
    if not batch_id:
        batch_id = str(uuid.uuid4())

    # Step 7: Save uploaded file
    os.makedirs(upload_dir, exist_ok=True)

    file_path = os.path.join(
        upload_dir,
        f"{batch_id}_ledger.csv",
    )

    content = await file.read()

    with open(file_path, "wb") as f:
        f.write(content)

    # Step 8: Parse CSV
    text = content.decode("utf-8")
    reader = csv.DictReader(StringIO(text))
    rows = list(reader)

    # Step 9: Load the latest schema manifest
    statement = (
        select(SchemaManifestDB)
        .order_by(SchemaManifestDB.id.desc())
        .limit(1)
    )

    record = db.scalar(statement)

    if record is None:
        raise HTTPException(
            status_code=404,
            detail="Schema manifest not found",
        )

    manifest = SchemaManifest.model_validate(
        record,
        from_attributes=True,
    )

    # Step 10: Initialise containers
    valid_rows = []
    exceptions = []

    # Step 11: Validate every row
    for idx, row in enumerate(rows, start=1):

        # Check required fields
        missing_fields = [
            field
            for field in manifest.required_fields_ledger
            if not row.get(field)
        ]

        if missing_fields:
            exceptions.append({
                "row": idx,
                "rule": "missing_required_fields",
                "message": f"Missing fields: {missing_fields}",
            })
            continue

        # Convert amount to Decimal
        try:
            amount = Decimal(row["amount"])

            if not amount.is_finite():
                raise InvalidOperation

        except (InvalidOperation, ValueError):
            exceptions.append({
                "row": idx,
                "rule": "amount_not_numeric",
                "message": (
                    f"Cannot convert {row['amount']!r} to Decimal"
                ),
            })
            continue

        # Check currency length
        if len(row["currency"]) != 3:
            exceptions.append({
                "row": idx,
                "rule": "invalid_currency",
                "message": "Currency must contain 3 characters",
            })
            continue

        # Parse date
        try:
            datetime.strptime(
                row["value_date"],
                manifest.date_format,
            )
        except ValueError:
            exceptions.append({
                "row": idx,
                "rule": "invalid_date",
                "message": (
                    f"Invalid date: {row['value_date']}"
                ),
            })
            continue

        # Store cleaned values
        row["amount"] = format(amount, "f")
        row["currency"] = row["currency"].upper()

        valid_rows.append(row)

    # Step 12: Detect duplicates
    ledger_index = {}
    seen_keys = set()
    duplicates = []

    for row in valid_rows:
        key = (row["txn_ref"], row["currency"])

        if key in seen_keys:
            duplicates.append(row["txn_ref"])
        else:
            seen_keys.add(key)
            ledger_index[key] = row

    # Step 13: Calculate control totals
    control_totals = {}

    for row in valid_rows:
        currency = row["currency"]
        amount = Decimal(row["amount"])

        control_totals[currency] = (
            control_totals.get(currency, Decimal("0"))
            + amount
        )

    control_totals = {
        currency: format(total, ".2f")
        for currency, total in control_totals.items()
    }

    # Step 14: Persist results using the database session.
    # The guide does not specify the SQLAlchemy model
    # for storing ingestion rows and control totals.
    # We must identify the existing model before adding
    # db.add(...) and db.commit() here.

    # Step 15: Return the response
    return {
        "batch_id": batch_id,
        "source": "ledger",
        "row_count": len(rows),
        "valid_count": len(valid_rows),
        "invalid_count": len(exceptions),
        "control_totals": control_totals,
        "duplicates": duplicates,
        "exceptions": exceptions,
    }



@router.post("/ingest/settlement")
async def ingest_settlement(
    file: UploadFile = File(...),
    batch_id: str | None = Query(None),
    db: Session = Depends(get_db),
):
    # Step 5: Read configuration
    settings = get_settings()
    upload_dir = settings.UPLOAD_DIR

    # Step 6: Generate batch ID if not supplied
    if not batch_id:
        batch_id = str(uuid.uuid4())

    # Step 7: Save uploaded settlement file
    os.makedirs(upload_dir, exist_ok=True)

    file_path = os.path.join(
        upload_dir,
        f"{batch_id}_settlement.csv",
    )

    content = await file.read()

    with open(file_path, "wb") as f:
        f.write(content)

    # Step 8: Parse CSV
    text = content.decode("utf-8")
    reader = csv.DictReader(StringIO(text))
    rows = list(reader)

    # Step 9: Load the current schema manifest
    statement = (
        select(SchemaManifestDB)
        .order_by(SchemaManifestDB.id.desc())
        .limit(1)
    )

    record = db.scalar(statement)

    if record is None:
        raise HTTPException(
            status_code=404,
            detail="Schema manifest not found",
        )

    manifest = SchemaManifest.model_validate(
        record,
        from_attributes=True,
    )

    # Step 10: Initialise containers
    valid_rows = []
    exceptions = []

    # Step 11: Validate every settlement row
    for idx, row in enumerate(rows, start=1):

        # Check required fields from settlement schema
        missing_fields = [
            field
            for field in manifest.required_fields_settlement
            if not row.get(field)
        ]

        if missing_fields:
            exceptions.append({
                "row": idx,
                "rule": "missing_required_fields",
                "message": f"Missing fields: {missing_fields}",
            })
            continue

        # Convert amount to Decimal
        try:
            amount = Decimal(row["amount"])

            if not amount.is_finite():
                raise InvalidOperation

        except (InvalidOperation, ValueError):
            exceptions.append({
                "row": idx,
                "rule": "amount_not_numeric",
                "message": (
                    f"Cannot convert {row['amount']!r} to Decimal"
                ),
            })
            continue

        # Check currency length
        if len(row["currency"]) != 3:
            exceptions.append({
                "row": idx,
                "rule": "invalid_currency",
                "message": "Currency must contain 3 characters",
            })
            continue

        # Parse date
        try:
            datetime.strptime(
                row["value_date"],
                manifest.date_format,
            )

        except ValueError:
            exceptions.append({
                "row": idx,
                "rule": "invalid_date",
                "message": f"Invalid date: {row['value_date']}",
            })
            continue

        # Store cleaned values
        row["amount"] = format(amount, "f")
        row["currency"] = row["currency"].upper()

        valid_rows.append(row)

    # Step 12: Build settlement index and detect duplicates
    settlement_index = {}
    seen_keys = set()
    duplicates = []

    for row in valid_rows:
        key = (row["txn_ref"], row["currency"])

        if key in seen_keys:
            duplicates.append(row["txn_ref"])
        else:
            seen_keys.add(key)
            settlement_index[key] = row

    # Step 13: Calculate control totals
    control_totals = {}

    for row in valid_rows:
        currency = row["currency"]
        amount = Decimal(row["amount"])

        control_totals[currency] = (
            control_totals.get(currency, Decimal("0"))
            + amount
        )

    control_totals = {
        currency: format(total, ".2f")
        for currency, total in control_totals.items()
    }

    # Step 14: Persist settlement results
    # Use the existing settlement database model and table here.
    # Section 6.4's persistence is also pending identification
    # of the corresponding SQLAlchemy model.

    # Step 15: Return the settlement report
    return {
        "batch_id": batch_id,
        "source": "settlement",
        "row_count": len(rows),
        "valid_count": len(valid_rows),
        "invalid_count": len(exceptions),
        "control_totals": control_totals,
        "duplicates": duplicates,
        "exceptions": exceptions,
    }