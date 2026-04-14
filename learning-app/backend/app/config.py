from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Python Learning Backend"
    cors_origins: list[str] = ["http://localhost:3000"]
    execution_timeout: int = 30
    max_memory_mb: int = 512

    class Config:
        env_prefix = "LEARNING_"


settings = Settings()
