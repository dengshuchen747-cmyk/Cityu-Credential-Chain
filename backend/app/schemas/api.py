from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class NonceRequest(BaseModel):
    wallet_address: str


class NonceResponse(BaseModel):
    wallet_address: str
    message: str
    expires_at: datetime


class VerifySignatureRequest(BaseModel):
    wallet_address: str
    signature: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    wallet_address: str
    is_issuer: bool
    is_admin: bool


class CampaignCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10, max_length=5000)
    credential_type: str = Field(min_length=2, max_length=120)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    max_claims: int | None = Field(default=None, gt=0)
    metadata_uri: str = Field(default="", max_length=500)


class CampaignRead(ORMModel):
    id: int
    slug: str
    title: str
    description: str
    credential_type: str
    issuer_wallet: str
    status: str
    starts_at: datetime | None
    ends_at: datetime | None
    max_claims: int | None
    metadata_uri: str
    created_at: datetime


class ClaimRead(ORMModel):
    id: int
    campaign_id: int
    student_wallet: str
    student_name: str
    student_email: str
    evidence_hash: str
    status: str
    review_note: str
    submitted_at: datetime
    reviewed_at: datetime | None


class ClaimReview(BaseModel):
    status: str = Field(pattern="^(approved|rejected)$")
    note: str = Field(default="", max_length=3000)


class CredentialRead(ORMModel):
    id: int
    claim_id: int
    token_id: int
    contract_address: str
    network: str
    transaction_hash: str
    data_hash: str
    metadata_uri: str
    issuer_wallet: str
    issued_at: datetime
    revoked_at: datetime | None


class ChainTransaction(BaseModel):
    to: str
    data: str
    chain_id: int


class TransactionConfirmation(BaseModel):
    transaction_hash: str = Field(min_length=64, max_length=66)


class CredentialIssuePreparation(BaseModel):
    claim_id: int
    student_wallet: str
    data_hash: str
    metadata_uri: str
    transaction: ChainTransaction


class CredentialRevokePreparation(BaseModel):
    token_id: int
    reason: str
    reason_hash: str
    transaction: ChainTransaction


class CredentialRevokeConfirmation(TransactionConfirmation):
    reason: str = Field(min_length=3, max_length=1000)


class PublicCredential(BaseModel):
    token_id: int
    campaign_title: str
    campaign_description: str
    credential_type: str
    student_wallet: str
    issuer_wallet: str
    issued_at: datetime | None
    valid: bool
    revoked: bool
    chain_available: bool
    metadata_uri: str
    transaction_hash: str
    contract_address: str
    network: str


class StudentCredentialPortfolio(BaseModel):
    student_wallet: str
    credentials: list[PublicCredential]


class CredentialVerification(BaseModel):
    token_id: int
    chain_available: bool
    valid: bool
    hash_matches: bool
    revoked: bool
    student_wallet: str
    issuer_wallet: str
    issued_at: datetime | None
    metadata_uri: str
    transaction_hash: str = ""


class RevokeCredentialRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)


class IssuerRoleChangeRequest(BaseModel):
    wallet_address: str
    action: Literal["grant", "revoke"]
    label: str = Field(default="", max_length=120)


class IssuerRoleChangeConfirmation(IssuerRoleChangeRequest):
    transaction_hash: str = Field(min_length=64, max_length=66)


class IssuerRolePreparation(BaseModel):
    wallet_address: str
    action: Literal["grant", "revoke"]
    transaction: ChainTransaction


class IssuerRoleRecord(BaseModel):
    wallet_address: str
    label: str
    active: bool
    transaction_hash: str = ""
    updated_at: datetime | None = None


class ShareCreate(BaseModel):
    expires_in_hours: int = Field(default=24, ge=1, le=168)
    verifier_wallet: str | None = None


class ShareCreated(BaseModel):
    share_token: str
    expires_at: datetime


class ShareView(BaseModel):
    token_id: int
    credential_type: str
    student_name: str
    student_email: str
    issuer_wallet: str
    issued_at: datetime
    revoked: bool
