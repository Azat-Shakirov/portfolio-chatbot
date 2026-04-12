from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import computed_field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    claude_api_key: str
    recaptcha_v3_secret_key: str
    recaptcha_v2_secret_key: str
    daily_token_budget: int = 50000
    default_personality: str = "casual"
    allowed_origins: str = "http://localhost:3000"
    skip_recaptcha: bool = False  # set True in .env for local dev

    @computed_field
    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


settings = Settings()
