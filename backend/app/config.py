from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """환경변수 기반 설정. .env.example 참고."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://user:password@localhost:5432/quizloop"

    anthropic_api_key: str = ""
    llm_model: str = "claude-sonnet-4-5"

    upload_dir: str = "./uploads"

    embedding_model: str = "voyage-3"
    embedding_dim: int = 1536


settings = Settings()
