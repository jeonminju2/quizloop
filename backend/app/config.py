import secrets
import warnings

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """환경변수 기반 설정. .env.example 참고."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://user:password@localhost:5432/quizloop"

    anthropic_api_key: str = ""
    llm_model: str = "claude-sonnet-4-5"

    upload_dir: str = "./uploads"

    # 임베딩: Voyage AI 사용 (Anthropic 권장 파트너, 다국어/한국어 지원, 계정당 2억 토큰 무료).
    # voyage-4 계열은 output_dimension을 256/512/1024/2048 중에서 고를 수 있음 — 1024가 기본값.
    voyage_api_key: str = ""
    embedding_model: str = "voyage-4"
    embedding_dim: int = 1024

    # 인증 (JWT). JWT_SECRET을 .env에 반드시 설정할 것 — 비워두면 매 프로세스 재시작마다
    # 랜덤 시크릿이 새로 생성돼서 기존 로그인 토큰이 전부 무효화된다 (개발 편의상 fallback만 제공).
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7일

    # 백그라운드 큐 (RQ)
    redis_url: str = "redis://localhost:6379/0"


settings = Settings()

if not settings.jwt_secret:
    warnings.warn(
        "JWT_SECRET이 설정되지 않아서 프로세스 시작 시마다 임의의 시크릿을 생성합니다 — "
        "서버 재시작 시 기존 로그인 토큰이 전부 무효화됩니다. .env에 JWT_SECRET을 설정하세요.",
        stacklevel=1,
    )
    settings.jwt_secret = secrets.token_urlsafe(32)
