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
    BE_ROUTER_URL: str = f"http://{BE_ROUTER_HOST}:{BE_ROUTER_PORT}"

    GM_HOST: str = "gm"
    GM_PORT: int = 8020
    GM_SERVICE_URL: str = f"http://{GM_HOST}:{GM_PORT}"

    SCENARIO_SERVICE_HOST: str = "scenario_service"
    SCENARIO_SERVICE_PORT: int = 8030
    SCENARIO_SERVICE_URL: str = (
        f"http://{SCENARIO_SERVICE_HOST}:{SCENARIO_SERVICE_PORT}"
    )

    STATE_MANAGER_HOST: str = "state_manager"
    STATE_MANAGER_PORT: int = 8040
    STATE_MANAGER_URL: str = f"http://{STATE_MANAGER_HOST}:{STATE_MANAGER_PORT}"

    RULE_ENGINE_HOST: str = "rule_engine"
    RULE_ENGINE_PORT: int = 8050
    RULE_ENGINE_URL: str = f"http://{RULE_ENGINE_HOST}:{RULE_ENGINE_PORT}"

    LLM_GATEWAY_HOST: str = "llm_gateway"
    LLM_GATEWAY_PORT: int = 8060
    LLM_GATEWAY_URL: str = f"http://{LLM_GATEWAY_HOST}:{LLM_GATEWAY_PORT}"

    # LLM Settings
    LLM_MODEL_NAME: str = "gemini-2.0-flash-lite"

    # Logic Settings
    SCENARIO_GRAPH_NAME: str = "scenario_graph"

    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

    @property
    def database_dsn(self) -> str:
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


settings = Settings()
