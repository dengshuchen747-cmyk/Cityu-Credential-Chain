import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from web3 import Web3
from web3.exceptions import TimeExhausted
from web3.logs import DISCARD

from app.core.config import settings


ABI_PATH = Path(__file__).resolve().parents[1] / "contracts" / "UniCredentialSBT.abi.json"
DEFAULT_ADMIN_ROLE = bytes(32)
ISSUER_ROLE = Web3.keccak(text="ISSUER_ROLE")


class BlockchainService:
    def __init__(self) -> None:
        self.web3 = (
            Web3(
                Web3.HTTPProvider(
                    settings.web3_rpc_url, request_kwargs={"timeout": 10}
                )
            )
            if settings.web3_rpc_url
            else None
        )
        self.contract = None
        if self.web3 and settings.credential_contract_address and ABI_PATH.exists():
            abi = json.loads(ABI_PATH.read_text(encoding="utf-8"))
            self.contract = self.web3.eth.contract(
                address=Web3.to_checksum_address(
                    settings.credential_contract_address
                ),
                abi=abi,
            )

    @property
    def configured(self) -> bool:
        return self.web3 is not None and self.contract is not None

    def _require_configured(self) -> None:
        if not self.configured:
            raise HTTPException(
                status_code=503,
                detail="Contract RPC and address must be configured",
            )

    @staticmethod
    def _hex_value(value: Any) -> str:
        if isinstance(value, str):
            return value.lower()
        return Web3.to_hex(value).lower()

    @staticmethod
    def _transaction_hash(value: str) -> str:
        normalized = value if value.startswith("0x") else f"0x{value}"
        try:
            int(normalized[2:], 16)
        except ValueError as exc:
            raise HTTPException(
                status_code=422, detail="Invalid transaction hash"
            ) from exc
        if len(normalized) != 66:
            raise HTTPException(status_code=422, detail="Invalid transaction hash")
        return normalized.lower()

    def _prepared_transaction(self, contract_call: Any) -> dict[str, Any]:
        self._require_configured()
        return {
            "to": self.contract.address,
            "data": contract_call._encode_transaction_data(),
            "chain_id": settings.chain_id,
        }

    def is_issuer(self, wallet: str) -> bool:
        if not self.configured:
            return False
        try:
            return bool(
                self.contract.functions.isIssuer(
                    Web3.to_checksum_address(wallet)
                ).call()
            )
        except Exception:
            return False

    def is_admin(self, wallet: str) -> bool:
        if not self.configured:
            return False
        try:
            return bool(
                self.contract.functions.hasRole(
                    DEFAULT_ADMIN_ROLE, Web3.to_checksum_address(wallet)
                ).call()
            )
        except Exception:
            return False

    def prepare_issuer_role_change(
        self, wallet: str, action: str
    ) -> dict[str, Any]:
        self._require_configured()
        target = Web3.to_checksum_address(wallet)
        if action == "grant":
            contract_call = self.contract.functions.grantRole(ISSUER_ROLE, target)
        elif action == "revoke":
            contract_call = self.contract.functions.revokeRole(ISSUER_ROLE, target)
        else:
            raise HTTPException(status_code=422, detail="Invalid role action")
        return self._prepared_transaction(contract_call)

    def prepare_issue_credential(
        self, student_wallet: str, data_hash: str, metadata_uri: str
    ) -> dict[str, Any]:
        self._require_configured()
        contract_call = self.contract.functions.issueCredential(
            Web3.to_checksum_address(student_wallet),
            bytes.fromhex(data_hash.removeprefix("0x")),
            metadata_uri,
        )
        return self._prepared_transaction(contract_call)

    def token_id_by_data_hash(self, data_hash: str) -> int:
        if not self.configured:
            return 0
        try:
            value = bytes.fromhex(data_hash.removeprefix("0x"))
            return int(self.contract.functions.tokenIdByDataHash(value).call())
        except Exception:
            return 0

    def prepare_revoke_credential(
        self, token_id: int, reason_hash: str
    ) -> dict[str, Any]:
        self._require_configured()
        contract_call = self.contract.functions.revokeCredential(
            token_id, bytes.fromhex(reason_hash.removeprefix("0x"))
        )
        return self._prepared_transaction(contract_call)

    def _confirmed_transaction(
        self,
        transaction_hash: str,
        expected_sender: str,
        expected_data: str,
    ) -> tuple[Any, str]:
        self._require_configured()
        normalized_hash = self._transaction_hash(transaction_hash)
        try:
            receipt = self.web3.eth.wait_for_transaction_receipt(
                normalized_hash, timeout=120
            )
            transaction = self.web3.eth.get_transaction(normalized_hash)
        except TimeExhausted as exc:
            raise HTTPException(
                status_code=504, detail="Transaction confirmation timed out"
            ) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=502, detail="Could not read transaction from Sepolia"
            ) from exc

        if receipt["status"] != 1:
            raise HTTPException(status_code=409, detail="Transaction reverted")
        destination = transaction.get("to")
        if not destination or destination.lower() != self.contract.address.lower():
            raise HTTPException(
                status_code=409, detail="Transaction targets the wrong contract"
            )
        if transaction["from"].lower() != expected_sender.lower():
            raise HTTPException(
                status_code=409,
                detail="Transaction was not signed by the authenticated wallet",
            )
        if self._hex_value(transaction["input"]) != expected_data.lower():
            raise HTTPException(
                status_code=409, detail="Transaction data does not match this request"
            )
        return receipt, normalized_hash

    def confirm_issuer_role_change(
        self,
        transaction_hash: str,
        admin_wallet: str,
        target_wallet: str,
        action: str,
    ) -> str:
        prepared = self.prepare_issuer_role_change(target_wallet, action)
        _, normalized_hash = self._confirmed_transaction(
            transaction_hash, admin_wallet, prepared["data"]
        )
        should_be_active = action == "grant"
        if self.is_issuer(target_wallet) != should_be_active:
            raise HTTPException(
                status_code=409, detail="Issuer role state does not match the request"
            )
        return normalized_hash

    def confirm_issue_credential(
        self,
        transaction_hash: str,
        issuer_wallet: str,
        student_wallet: str,
        data_hash: str,
        metadata_uri: str,
    ) -> dict[str, Any]:
        prepared = self.prepare_issue_credential(
            student_wallet, data_hash, metadata_uri
        )
        receipt, normalized_hash = self._confirmed_transaction(
            transaction_hash, issuer_wallet, prepared["data"]
        )
        events = self.contract.events.CredentialIssued().process_receipt(
            receipt, errors=DISCARD
        )
        if len(events) != 1:
            raise HTTPException(
                status_code=409, detail="CredentialIssued event was not found"
            )
        args = events[0]["args"]
        if (
            args["student"].lower() != student_wallet.lower()
            or args["issuer"].lower() != issuer_wallet.lower()
            or self._hex_value(args["dataHash"]) != data_hash.lower()
            or args["metadataURI"] != metadata_uri
        ):
            raise HTTPException(
                status_code=409, detail="CredentialIssued event does not match the claim"
            )
        return {
            "token_id": int(args["tokenId"]),
            "transaction_hash": normalized_hash,
            "issuer_wallet": args["issuer"].lower(),
        }

    def confirm_revoke_credential(
        self,
        transaction_hash: str,
        issuer_wallet: str,
        token_id: int,
        reason_hash: str,
    ) -> str:
        prepared = self.prepare_revoke_credential(token_id, reason_hash)
        receipt, normalized_hash = self._confirmed_transaction(
            transaction_hash, issuer_wallet, prepared["data"]
        )
        events = self.contract.events.CredentialRevoked().process_receipt(
            receipt, errors=DISCARD
        )
        if len(events) != 1:
            raise HTTPException(
                status_code=409, detail="CredentialRevoked event was not found"
            )
        args = events[0]["args"]
        if (
            int(args["tokenId"]) != token_id
            or args["revokedBy"].lower() != issuer_wallet.lower()
            or self._hex_value(args["reasonHash"]) != reason_hash.lower()
        ):
            raise HTTPException(
                status_code=409, detail="CredentialRevoked event does not match the request"
            )
        return normalized_hash

    def verify_credential(self, token_id: int, data_hash: str) -> dict[str, Any]:
        self._require_configured()
        try:
            result = self.contract.functions.verifyCredential(
                token_id, bytes.fromhex(data_hash.removeprefix("0x"))
            ).call()
        except Exception as exc:
            raise HTTPException(
                status_code=502, detail="Blockchain verification failed"
            ) from exc
        return {
            "valid": bool(result[0]),
            "hash_matches": bool(result[1]),
            "revoked": bool(result[2]),
            "student_wallet": result[3].lower(),
            "issuer_wallet": result[4].lower(),
            "issued_at": (
                datetime.fromtimestamp(result[5], timezone.utc)
                if result[5]
                else None
            ),
            "metadata_uri": result[6],
        }


blockchain = BlockchainService()
