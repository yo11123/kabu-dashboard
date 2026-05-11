from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Kabu Dashboard v2 Backend"
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "tauri://localhost",
    ]
    cache_ttl_seconds: int = 60

    class Config:
        env_prefix = "KABU_V2_"


settings = Settings()
