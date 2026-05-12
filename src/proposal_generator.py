from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from src.config_loader import get_settings
from src.models.job import Job
from src.models.proposal import Proposal
from src.utils.logger import get_logger

log = get_logger()


class ProposalGenerator:
    def __init__(self):
        self.settings = get_settings()
        self.client = OpenAI(
            api_key=self.settings.deepseek_api_key,
            base_url="https://api.deepseek.com",
        )

    def _build_system_prompt(self) -> str:
        f = self.settings.app.freelancer
        highlights = "\n".join(f"- {h}" for h in f.portfolio_highlights)
        skills = ", ".join(f.skills)
        return f"""You write Upwork proposals on behalf of a freelancer.

Freelancer Profile:
Name: {f.name}
Bio: {f.bio}
Skills: {skills}
Portfolio Highlights:
{highlights}

Proposal Rules:
- Open by referencing the specific problem in the job post directly
- Mention 1-2 relevant skills or portfolio items that match the job
- End with a short, thoughtful question that shows you read the post
- Tone: {f.tone}
- Length: under {f.max_proposal_words} words
- Never use openers like "I am writing to apply..." or "I am interested in..."
- Never use bullet points unless the job is highly technical
- Never mention you are an AI"""

    @retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=10, max=60),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def generate(self, job: Job) -> Proposal:
        log.info("generating_proposal", job_id=job.job_id, title=job.title)

        skills_str = ", ".join(job.skills) if job.skills else "Not specified"
        user_message = f"""Write a proposal for this Upwork job:

Title: {job.title}
Budget: {job.budget_amount} ({job.budget_type})
Duration: {job.duration}
Experience Level: {job.experience_level}
Skills Required: {skills_str}
Client Location: {job.client_location}

Job Description:
{job.description[:2000]}"""

        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": self._build_system_prompt()},
                {"role": "user", "content": user_message},
            ],
            max_tokens=600,
            temperature=0.8,
        )

        text = response.choices[0].message.content.strip()
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens

        log.info("proposal_generated", job_id=job.job_id, tokens_used=input_tokens + output_tokens)

        return Proposal(
            job_id=job.job_id,
            text=text,
            model=response.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
