from functools import lru_cache
from typing import Literal
from pydantic import SecretStr

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name : str = "OTEL Obs Inv"
    environment: Literal["local","test","staging","production"] = "local"
    database_url: SecretStr
    service_name: str = "order-api"
    otel_traces_endpoint: str = "http://127.0.0.1:4318/v1/traces"
    model_config = SettingsConfigDict(
        env_file =".env",
        env_file_encoding = "utf-8",
        extra="ignore"
    )



@lru_cache()
def get_settings() -> Settings:
    return Settings()
