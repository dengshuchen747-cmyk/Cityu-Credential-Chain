import argparse
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import joinedload
from web3 import Web3

from app.core.config import settings
from app.core.database import SessionLocal
from app.models import AuditLog, Claim, Credential
from app.services.blockchain import blockchain
from app.services.credential_hash import build_credential_hash


EVENT_SIGNATURE = "CredentialIssued(uint256,address,address,bytes32,string)"


@dataclass
class ReconciliationResult:
    inserted: int = 0
    already_indexed: int = 0
    unmatched_events: int = 0


def _issued_events(from_block: int, to_block: int, chunk_size: int):
    topic = Web3.to_hex(Web3.keccak(text=EVENT_SIGNATURE))
    contract_address = blockchain.contract.address
    for start in range(from_block, to_block + 1, chunk_size):
        end = min(start + chunk_size - 1, to_block)
        logs = blockchain.web3.eth.get_logs(
            {
                "address": contract_address,
                "fromBlock": start,
                "toBlock": end,
                "topics": [topic],
            }
        )
        for log in logs:
            yield blockchain.contract.events.CredentialIssued().process_log(log)


def reconcile(from_block: int, chunk_size: int = 20_000) -> ReconciliationResult:
    blockchain._require_configured()
    latest_block = blockchain.web3.eth.block_number
    result = ReconciliationResult()

    with SessionLocal() as db:
        claims = list(
            db.scalars(
                select(Claim)
                .options(joinedload(Claim.campaign), joinedload(Claim.credential))
                .where(Claim.status.in_(("approved", "issued")))
            )
        )
        claims_by_hash = {
            build_credential_hash(claim.campaign, claim).lower(): claim
            for claim in claims
        }

        for event in _issued_events(from_block, latest_block, chunk_size):
            args = event["args"]
            data_hash = Web3.to_hex(args["dataHash"]).lower()
            claim = claims_by_hash.get(data_hash)
            if claim is None:
                result.unmatched_events += 1
                continue
            if claim.credential is not None:
                result.already_indexed += 1
                continue
            if args["student"].lower() != claim.student_wallet.lower():
                continue
            if args["issuer"].lower() != claim.campaign.issuer_wallet.lower():
                continue

            token_id = int(args["tokenId"])
            verification = blockchain.contract.functions.verifyCredential(
                token_id, bytes.fromhex(data_hash[2:])
            ).call()
            valid, hash_matches, revoked, student, issuer, issued_at, metadata_uri = (
                verification
            )
            if (
                not valid
                or not hash_matches
                or revoked
                or student.lower() != claim.student_wallet.lower()
                or issuer.lower() != claim.campaign.issuer_wallet.lower()
            ):
                continue

            transaction_hash = Web3.to_hex(event["transactionHash"]).lower()
            if db.scalar(
                select(Credential).where(
                    (Credential.token_id == token_id)
                    | (Credential.transaction_hash == transaction_hash)
                    | (Credential.data_hash == data_hash)
                )
            ):
                result.already_indexed += 1
                continue

            credential = Credential(
                claim_id=claim.id,
                token_id=token_id,
                contract_address=blockchain.contract.address.lower(),
                network="sepolia",
                transaction_hash=transaction_hash,
                data_hash=data_hash,
                metadata_uri=metadata_uri,
                issuer_wallet=issuer.lower(),
                issued_at=datetime.fromtimestamp(issued_at, tz=timezone.utc),
            )
            claim.status = "issued"
            db.add(credential)
            db.flush()
            db.add(
                AuditLog(
                    actor_wallet=issuer.lower(),
                    action="credential.reconciled",
                    entity_type="credential",
                    entity_id=str(credential.id),
                    details=transaction_hash,
                )
            )
            result.inserted += 1

        db.commit()
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Index successful CredentialIssued events missing from MySQL."
    )
    parser.add_argument(
        "--from-block",
        type=int,
        default=None,
        help="First Sepolia block to inspect (defaults to latest - 100000).",
    )
    parser.add_argument("--chunk-size", type=int, default=20_000)
    args = parser.parse_args()

    blockchain._require_configured()
    latest = blockchain.web3.eth.block_number
    from_block = args.from_block if args.from_block is not None else max(0, latest - 100_000)
    result = reconcile(from_block=from_block, chunk_size=args.chunk_size)
    print(
        "Credential reconciliation complete: "
        f"inserted={result.inserted}, "
        f"already_indexed={result.already_indexed}, "
        f"unmatched_events={result.unmatched_events}."
    )


if __name__ == "__main__":
    main()
