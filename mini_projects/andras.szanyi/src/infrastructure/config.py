from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """

    GROQ_API_KEY: str
    OPENWEATHER_API_KEY: str

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @classmethod
    def load(cls):
        try:
            return cls()
        except ValidationError as e:
            missing_vars = [err["loc"][0] for err in e.errors() if err["type"] == "missing"]
            if missing_vars:
                raise SystemExit(
                    f"Error: Missing required environment variables: {', '.join(missing_vars)}\n"
                    "Please create a '.env' file based on '.env.example' and set these variables."
                )
            raise


