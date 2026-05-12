from datetime import datetime
from typing import Literal
from pydantic import BaseModel


class Job(BaseModel):
    job_id: str
    title: str
    url: str
    budget_type: Literal["hourly", "fixed", "unknown"] = "unknown"
    budget_amount: str = ""
    duration: str = ""
    experience_level: str = ""
    skills: list[str] = []
    client_location: str = ""
    client_rating: float | None = None
    client_hire_count: int | None = None
    description: str = ""
    found_at: datetime = None

    def model_post_init(self, __context):
        if self.found_at is None:
            object.__setattr__(self, "found_at", datetime.now())
