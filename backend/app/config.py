import os
from pydantic import BaseModel, Field

# Enforce pure-Python SQLAlchemy to avoid Windows AppLocker / WDAC C-extension blocks
os.environ.setdefault("DISABLE_SQLALCHEMY_CEXT", "1")


class Settings(BaseModel):
    app_name: str = "CampusOps API"
    environment: str = Field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    debug: bool = Field(default_factory=lambda: os.getenv("DEBUG", "false").lower() in ("true", "1", "yes"))

    # Default to local SQLite for development/testing; production target is PostgreSQL
    database_url: str = Field(
        default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///./campusops_dev.db")
    )

    # Invitation token configuration (FA-009: 7 calendar days)
    invitation_expiry_days: int = 7


settings = Settings()
