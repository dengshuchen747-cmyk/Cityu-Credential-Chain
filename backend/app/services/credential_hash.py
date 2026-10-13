import json

from web3 import Web3

from app.models import Campaign, Claim


def build_credential_hash(campaign: Campaign, claim: Claim) -> str:
    public_proof = {
        "campaign_id": campaign.id,
        "credential_type": campaign.credential_type,
        "evidence_hash": claim.evidence_hash,
        "issuer_wallet": campaign.issuer_wallet.lower(),
        "student_wallet": claim.student_wallet.lower(),
    }
    canonical = json.dumps(public_proof, sort_keys=True, separators=(",", ":"))
    # HexBytes.hex() no longer guarantees a 0x prefix across Web3.py
    # versions. Keep the API and contract-event representation canonical.
    return Web3.to_hex(Web3.keccak(text=canonical))
