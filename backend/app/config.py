from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str
    twelvedata_api_key: str = ""
    coingecko_demo_key: str = ""
    fx_ttl_seconds: int = 60
    crypto_ttl_seconds: int = 30
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def async_database_url(self) -> str:
        from urllib.parse import urlparse, urlencode, parse_qs, urlunparse
        url = self.database_url
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        parsed = urlparse(url)
        params = parse_qs(parsed.query, keep_blank_values=True)
        # asyncpg uses 'ssl' not 'sslmode'; drop channel_binding
        if "sslmode" in params:
            params["ssl"] = params.pop("sslmode")
        params.pop("channel_binding", None)
        new_query = urlencode({k: v[0] for k, v in params.items()})
        return urlunparse(parsed._replace(query=new_query))


settings = Settings()
