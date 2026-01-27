from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global application settings using Pydantic V2 Settings."""

    PROJECT_NAME: str = "Scenario Service"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

    REMOTE_HOST: str = "localhost"

    # Database Settings
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DB_PORT: int = 5432
    DB_NAME: str = "postgres"
    DB_HOST: str = "localhost"

    STATE_SERVICE_URL: str = "http://localhost:8030"
    SCENARIO_SERVICE_URL: str = "http://localhost:8040"
    RULE_SERVICE_URL: str = "http://localhost:8050"
    LLM_GATEWAY_URL: str = "http://localhost:8060"
    LLM_MODEL_NAME: str = "gemini-2.0-flash-lite"

    # Logic Settings
    SCENARIO_GRAPH_NAME: str = "scenario_graph"

    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

    @model_validator(mode="after")
    def configure_remote_host(self) -> "Settings":
        if self.REMOTE_HOST != "localhost":
            # Update DB Server if it's still default
            if self.DB_HOST == "localhost":
                self.DB_HOST = self.REMOTE_HOST

            # Update Service URLs by replacing localhost
            # This preserves the port and protocol
            if "localhost" in self.STATE_SERVICE_URL:
                self.STATE_SERVICE_URL = self.STATE_SERVICE_URL.replace(
                    "localhost", self.REMOTE_HOST
                )

            if "localhost" in self.SCENARIO_SERVICE_URL:
                self.SCENARIO_SERVICE_URL = self.SCENARIO_SERVICE_URL.replace(
                    "localhost", self.REMOTE_HOST
                )

            if "localhost" in self.RULE_SERVICE_URL:
                self.RULE_SERVICE_URL = self.RULE_SERVICE_URL.replace(
                    "localhost", self.REMOTE_HOST
                )

            if "localhost" in self.LLM_GATEWAY_URL:
                self.LLM_GATEWAY_URL = self.LLM_GATEWAY_URL.replace(
                    "localhost", self.REMOTE_HOST
                )

        return self

    @property
    def database_dsn(self) -> str:
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


settings = Settings()
