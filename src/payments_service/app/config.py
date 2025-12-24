from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "payments"

    database_url: str
    rabbitmq_url: str

    outbox_poll_interval: float = 1.0
    outbox_batch_size: int = 50


settings = Settings()
