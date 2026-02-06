from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Scenario Service"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

    # Database Settings
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DB_PORT: int = 5432
    DB_NAME: str = "postgres"
    DB_HOST: str = "localhost"

    # External Service URLs
    BE_ROUTER_HOST: str = "be_router"
    BE_ROUTER_PORT: int = 8010

    GM_HOST: str = "gm"
    GM_PORT: int = 8020

    SCENARIO_SERVICE_HOST: str = "scenario_service"
    SCENARIO_SERVICE_PORT: int = 8030

    STATE_MANAGER_HOST: str = "state_manager"
    STATE_MANAGER_PORT: int = 8040

    RULE_ENGINE_HOST: str = "rule_engine"
    RULE_ENGINE_PORT: int = 8050

    LLM_GATEWAY_HOST: str = "llm_gateway"
    LLM_GATEWAY_PORT: int = 8060

    # LLM Settings
    LLM_MODEL_NAME: str = "gemini-2.0-flash-lite"

    # Logic Settings
    SCENARIO_GRAPH_NAME: str = "scenario_graph"

    model_config = SettingsConfigDict(
        env_file=".env", env_ignore_empty=True, extra="ignore"
    )

    @computed_field
    @property
    def STATE_MANAGER_URL(self) -> str:
        return f"http://{self.STATE_MANAGER_HOST}:{self.STATE_MANAGER_PORT}"

    @computed_field
    @property
    def SCENARIO_SERVICE_URL(self) -> str:
        return f"http://{self.SCENARIO_SERVICE_HOST}:{self.SCENARIO_SERVICE_PORT}"

    @computed_field
    @property
    def RULE_ENGINE_URL(self) -> str:
        return f"http://{self.RULE_ENGINE_HOST}:{self.RULE_ENGINE_PORT}"

    @computed_field
    @property
    def LLM_GATEWAY_URL(self) -> str:
        return f"http://{self.LLM_GATEWAY_HOST}:{self.LLM_GATEWAY_PORT}"

    @property
    def database_dsn(self) -> str:
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


settings = Settings()
