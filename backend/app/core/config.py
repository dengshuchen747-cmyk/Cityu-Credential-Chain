from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "CityU Credential Chain API"
    app_env: str = "development"
    secret_key: str = "development-only-change-me"
    database_url: str = (
        "mysql+pymysql://unicredential:change-me@127.0.0.1:3306/"
        "unicredential?charset=utf8mb4"
    )
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    upload_dir: str = "uploads"
    max_upload_bytes: int = 10 * 1024 * 1024
    issuer_wallets: str = ""
    web3_rpc_url: str = ""
    chain_id: int = 11155111
    credential_contract_address: str = ""
    disclosure_contract_address: str = ""
    auth_token_max_age_seconds: int = 8 * 60 * 60
    nonce_ttl_minutes: int = 10

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def issuer_wallet_set(self) -> set[str]:
        return {
            item.strip().lower()
            for item in self.issuer_wallets.split(",")
            if item.strip()
        }

    @property
    def upload_path(self) -> Path:
        path = Path(self.upload_dir)
        return path if path.is_absolute() else BACKEND_DIR / path


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
