from datetime import datetime
from typing import Literal, Optional, List
from pydantic import BaseModel


class Job(BaseModel):
    job_id: str
    title: str
    url: str
    budget_type: Literal["hourly", "fixed", "unknown"] = "unknown"
    budget_amount: str = ""
    duration: str = ""
    experience_level: str = ""
    skills: List[str] = []
    client_location: str = ""
    client_rating: Optional[float] = None
    client_hire_count: Optional[int] = None
    description: str = ""
    found_at: Optional[datetime] = None

    def model_post_init(self, __context):
        if self.found_at is None:
            object.__setattr__(self, "found_at", datetime.now())
