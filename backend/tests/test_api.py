from eth_account import Account
from eth_account.messages import encode_defunct
import pytest
from sqlalchemy.orm import Session

from app.main import app, health
from app.models import Campaign, Claim, Credential
from app.routers.auth import verify_signature
from app.routers.campaigns import create_campaign, list_campaigns
from app.routers.credentials import (
    list_public_student_credentials,
    prepare_claim_issuance,
)
from app.schemas.api import CampaignCreate, VerifySignatureRequest
from app.services.auth import build_nonce
from app.services.blockchain import blockchain
from app.services.credential_hash import build_credential_hash


ISSUER = "0x0000000000000000000000000000000000000a11"


def test_health_and_expected_routes() -> None:
    assert health()["status"] == "ok"
    paths = set(app.openapi()["paths"])
    assert "/api/v1/admin/issuers/prepare" in paths
    assert "/api/v1/public/students/{wallet}/credentials" in paths
    assert "/api/v1/issuer/claims/{claim_id}/issue/prepare" in paths


def test_wallet_signature_login(db_session: Session) -> None:
    account = Account.create()
    nonce = build_nonce(db_session, account.address)
    signed = account.sign_message(encode_defunct(text=nonce.message))
    response = verify_signature(
        VerifySignatureRequest(
            wallet_address=account.address,
            signature=signed.signature.hex(),
        ),
        db_session,
    )
    assert response.access_token
    assert response.wallet_address == account.address.lower()
    assert response.is_admin is False


def test_create_and_list_campaign(db_session: Session) -> None:
    campaign = create_campaign(
        CampaignCreate(
            title="Solidity Workshop 2026",
            description="Complete the practical Solidity workshop and assessment.",
            credential_type="Workshop Completion",
            max_claims=50,
            metadata_uri="ipfs://workshop-2026",
        ),
        ISSUER.lower(),
        db_session,
    )
    assert campaign.issuer_wallet == ISSUER.lower()

    campaigns = list_campaigns(status="active", db=db_session)
    assert len(campaigns) == 1
    assert campaigns[0].title == "Solidity Workshop 2026"


def test_public_wallet_portfolio_excludes_private_claim_data(
    db_session: Session,
) -> None:
    student = "0x0000000000000000000000000000000000000b22"
    campaign = Campaign(
        slug="cityu-hackathon",
        title="CityU Web3 Hackathon",
        description="Completed the university Web3 hackathon.",
        credential_type="Hackathon Participant",
        issuer_wallet=ISSUER.lower(),
        status="active",
        max_claims=100,
        metadata_uri="ipfs://hackathon",
    )
    db_session.add(campaign)
    db_session.flush()
    claim = Claim(
        campaign_id=campaign.id,
        student_wallet=student,
        student_name="Private Student Name",
        student_email="private@example.edu",
        evidence_path="private/evidence.pdf",
        evidence_hash="0x" + "11" * 32,
        status="issued",
    )
    db_session.add(claim)
    db_session.flush()
    db_session.add(
        Credential(
            claim_id=claim.id,
            token_id=12,
            contract_address="0x0000000000000000000000000000000000000c33",
            network="sepolia",
            transaction_hash="0x" + "22" * 32,
            data_hash="0x" + "33" * 32,
            metadata_uri="ipfs://hackathon",
            issuer_wallet=ISSUER.lower(),
        )
    )
    db_session.commit()

    portfolio = list_public_student_credentials(student, db_session)
    serialized = portfolio.model_dump()
    credential = serialized["credentials"][0]
    assert credential["campaign_title"] == "CityU Web3 Hackathon"
    assert credential["credential_type"] == "Hackathon Participant"
    assert "student_name" not in credential
    assert "student_email" not in credential
    assert "evidence_hash" not in credential


def test_prepare_issuance_returns_metamask_transaction(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    campaign = Campaign(
        slug="issuer-flow",
        title="Blockchain Workshop",
        description="Completed the blockchain systems workshop.",
        credential_type="Workshop Completion",
        issuer_wallet=ISSUER.lower(),
        status="active",
        max_claims=50,
        metadata_uri="ipfs://workshop",
    )
    db_session.add(campaign)
    db_session.flush()
    claim = Claim(
        campaign_id=campaign.id,
        student_wallet="0x0000000000000000000000000000000000000b22",
        student_name="Student",
        student_email="student@example.edu",
        evidence_path="private/evidence.pdf",
        evidence_hash="0x" + "44" * 32,
        status="approved",
    )
    db_session.add(claim)
    db_session.commit()

    monkeypatch.setattr(
        blockchain,
        "prepare_issue_credential",
        lambda *_: {
            "to": "0x0000000000000000000000000000000000000c33",
            "data": "0x1234",
            "chain_id": 11155111,
        },
    )
    response = prepare_claim_issuance(
        claim.id, ISSUER.lower(), db_session
    )
    assert response.transaction.chain_id == 11155111
    assert response.transaction.data == "0x1234"


def test_credential_hash_is_canonical_hex(db_session: Session) -> None:
    campaign = Campaign(
        id=21,
        slug="canonical-hash",
        title="Canonical Hash",
        description="Hash regression test.",
        credential_type="Workshop Completion",
        issuer_wallet=ISSUER.lower(),
        status="active",
        max_claims=1,
        metadata_uri="",
    )
    claim = Claim(
        campaign_id=21,
        student_wallet="0x0000000000000000000000000000000000000b22",
        student_name="Student",
        student_email="student@example.edu",
        evidence_path="private/evidence.pdf",
        evidence_hash="0x" + "55" * 32,
        status="approved",
    )

    data_hash = build_credential_hash(campaign, claim)

    assert data_hash.startswith("0x")
    assert len(data_hash) == 66
