from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    credential_type: Mapped[str] = mapped_column(String(120))
    issuer_wallet: Mapped[str] = mapped_column(String(42), index=True)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    max_claims: Mapped[int | None]
    metadata_uri: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    claims: Mapped[list[Claim]] = relationship(back_populates="campaign")


class Claim(Base):
    __tablename__ = "claims"
    __table_args__ = (
        Index("uq_claim_campaign_wallet", "campaign_id", "student_wallet", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"), index=True)
    student_wallet: Mapped[str] = mapped_column(String(42), index=True)
    student_name: Mapped[str] = mapped_column(String(120))
    student_email: Mapped[str] = mapped_column(String(200))
    evidence_path: Mapped[str] = mapped_column(String(500), default="")
    evidence_hash: Mapped[str] = mapped_column(String(66), default="")
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    review_note: Mapped[str] = mapped_column(Text, default="")
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    campaign: Mapped[Campaign] = relationship(back_populates="claims")
    credential: Mapped[Credential | None] = relationship(
        back_populates="claim", uselist=False
    )


class Credential(Base):
    __tablename__ = "credentials"

    id: Mapped[int] = mapped_column(primary_key=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("claims.id"), unique=True)
    token_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    contract_address: Mapped[str] = mapped_column(String(42))
    network: Mapped[str] = mapped_column(String(40), default="sepolia")
    transaction_hash: Mapped[str] = mapped_column(String(66), unique=True)
    data_hash: Mapped[str] = mapped_column(String(66), unique=True)
    metadata_uri: Mapped[str] = mapped_column(String(500), default="")
    issuer_wallet: Mapped[str] = mapped_column(String(42), index=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revocation_reason: Mapped[str] = mapped_column(Text, default="")

    claim: Mapped[Claim] = relationship(back_populates="credential")
    shares: Mapped[list[ShareGrant]] = relationship(back_populates="credential")


class ShareGrant(Base):
    __tablename__ = "share_grants"

    id: Mapped[int] = mapped_column(primary_key=True)
    credential_id: Mapped[int] = mapped_column(ForeignKey("credentials.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    verifier_wallet: Mapped[str | None] = mapped_column(String(42))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    credential: Mapped[Credential] = relationship(back_populates="shares")


class WalletNonce(Base):
    __tablename__ = "wallet_nonces"

    wallet_address: Mapped[str] = mapped_column(String(42), primary_key=True)
    nonce: Mapped[str] = mapped_column(String(100), unique=True)
    message: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_wallet: Mapped[str] = mapped_column(String(42), index=True)
    action: Mapped[str] = mapped_column(String(100), index=True)
    entity_type: Mapped[str] = mapped_column(String(50))
    entity_id: Mapped[str] = mapped_column(String(100))
    details: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
