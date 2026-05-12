from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class Proposal(BaseModel):
    job_id: str
    text: str
    generated_at: Optional[datetime] = None
    model: str = "deepseek-chat"
    input_tokens: int = 0
    output_tokens: int = 0

    def model_post_init(self, __context):
        if self.generated_at is None:
            object.__setattr__(self, "generated_at", datetime.now())
