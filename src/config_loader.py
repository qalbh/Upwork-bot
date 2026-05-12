import yaml
from pathlib import Path
from functools import lru_cache
from typing import Optional, List
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class BudgetConfig(BaseModel):
    min_fixed: float = 0
    min_hourly: float = 0


class SearchConfig(BaseModel):
    queries: List[str]
    budget: BudgetConfig = BudgetConfig()
    experience_level: List[str] = []
    jobs_per_session: int = 5


class FreelancerConfig(BaseModel):
    name: str
    bio: str
    skills: List[str]
    portfolio_highlights: List[str] = []
    tone: str = "professional"
    max_proposal_words: int = 300


class GoogleSheetsConfig(BaseModel):
    spreadsheet_id: str
    sheet_name: str
    credentials_path: str


class SchedulerConfig(BaseModel):
    sessions_per_day: int = 3
    run_times: List[str]
    random_offset_minutes: int = 20


class UpworkConfig(BaseModel):
    homepage: str = "https://www.upwork.com"
    min_delay_seconds: float = 5
    max_delay_seconds: float = 15


class AppConfig(BaseModel):
    search: SearchConfig
    freelancer: FreelancerConfig
    google_sheets: GoogleSheetsConfig
    scheduler: SchedulerConfig
    upwork: UpworkConfig


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    deepseek_api_key: str
    upwork_email: str
    upwork_password: str

    app: Optional[AppConfig] = None

    def model_post_init(self, __context):
        config_path = Path(__file__).parent.parent / "config" / "config.yaml"
        with open(config_path, "r") as f:
            raw = yaml.safe_load(f)
        object.__setattr__(self, "app", AppConfig(**raw))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
