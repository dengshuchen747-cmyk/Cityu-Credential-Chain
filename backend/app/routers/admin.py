import json

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models import AuditLog
from app.schemas.api import (
    IssuerRoleChangeConfirmation,
    IssuerRoleChangeRequest,
    IssuerRolePreparation,
    IssuerRoleRecord,
)
from app.services.auth import normalize_wallet, require_admin
from app.services.blockchain import blockchain


router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/issuers", response_model=list[IssuerRoleRecord])
def list_issuers(
    _: str = Depends(require_admin), db: Session = Depends(get_db)
) -> list[IssuerRoleRecord]:
    rows = list(
        db.scalars(
            select(AuditLog)
            .where(AuditLog.action.in_(["issuer.granted", "issuer.revoked"]))
            .order_by(AuditLog.created_at.desc())
        ).all()
    )
    latest: dict[str, AuditLog | None] = {}
    for row in rows:
        latest.setdefault(row.entity_id.lower(), row)

    for wallet in settings.issuer_wallet_set:
        latest.setdefault(wallet, None)

    records: list[IssuerRoleRecord] = []
    for wallet, row in latest.items():
        label = "Configured issuer"
        transaction_hash = ""
        updated_at = None
        if row is not None:
            updated_at = row.created_at
            try:
                details = json.loads(row.details)
                label = details.get("label") or "Activity creator"
                transaction_hash = details.get("transaction_hash", "")
            except (TypeError, ValueError):
                label = "Activity creator"
        records.append(
            IssuerRoleRecord(
                wallet_address=wallet,
                label=label,
                active=blockchain.is_issuer(wallet),
                transaction_hash=transaction_hash,
                updated_at=updated_at,
            )
        )
    return sorted(records, key=lambda record: (not record.active, record.label.lower()))


@router.post("/issuers/prepare", response_model=IssuerRolePreparation)
def prepare_issuer_role_change(
    payload: IssuerRoleChangeRequest,
    _: str = Depends(require_admin),
) -> IssuerRolePreparation:
    target = normalize_wallet(payload.wallet_address)
    transaction = blockchain.prepare_issuer_role_change(target, payload.action)
    return IssuerRolePreparation(
        wallet_address=target,
        action=payload.action,
        transaction=transaction,
    )


@router.post("/issuers/confirm", response_model=IssuerRoleRecord)
def confirm_issuer_role_change(
    payload: IssuerRoleChangeConfirmation,
    admin_wallet: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> IssuerRoleRecord:
    target = normalize_wallet(payload.wallet_address)
    transaction_hash = blockchain.confirm_issuer_role_change(
        payload.transaction_hash,
        admin_wallet,
        target,
        payload.action,
    )
    action = "issuer.granted" if payload.action == "grant" else "issuer.revoked"
    audit = AuditLog(
        actor_wallet=admin_wallet,
        action=action,
        entity_type="issuer",
        entity_id=target,
        details=json.dumps(
            {
                "label": payload.label.strip(),
                "transaction_hash": transaction_hash,
            }
        ),
    )
    db.add(audit)
    db.commit()
    db.refresh(audit)
    return IssuerRoleRecord(
        wallet_address=target,
        label=payload.label.strip() or "Activity creator",
        active=payload.action == "grant",
        transaction_hash=transaction_hash,
        updated_at=audit.created_at,
    )
