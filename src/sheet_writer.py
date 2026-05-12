from pathlib import Path
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from tenacity import retry, stop_after_attempt, wait_exponential
from src.config_loader import get_settings
from src.models.job import Job
from src.models.proposal import Proposal
from src.utils.logger import get_logger

log = get_logger()

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

HEADERS = [
    "Job ID", "Date Found", "Title", "URL", "Budget Type",
    "Budget Amount", "Duration", "Experience Level", "Skills Required",
    "Client Location", "Client Rating", "Client Hire Count",
    "Description Excerpt", "Generated Proposal", "Status",
]


class SheetWriter:
    def __init__(self):
        self.settings = get_settings()
        self.sheet_cfg = self.settings.app.google_sheets
        self._service = None

    def _get_service(self):
        if self._service:
            return self._service
        creds_path = Path(self.sheet_cfg.credentials_path)
        creds = Credentials.from_service_account_file(str(creds_path), scopes=SCOPES)
        self._service = build("sheets", "v4", credentials=creds, cache_discovery=False)
        return self._service

    def _sheet_range(self, cell_range: str) -> str:
        return f"{self.sheet_cfg.sheet_name}!{cell_range}"

    def _ensure_header(self):
        service = self._get_service()
        result = service.spreadsheets().values().get(
            spreadsheetId=self.sheet_cfg.spreadsheet_id,
            range=self._sheet_range("A1:O1"),
        ).execute()

        existing = result.get("values", [])
        if not existing:
            service.spreadsheets().values().update(
                spreadsheetId=self.sheet_cfg.spreadsheet_id,
                range=self._sheet_range("A1"),
                valueInputOption="RAW",
                body={"values": [HEADERS]},
            ).execute()
            log.info("sheet_header_created")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    def append_row(self, job: Job, proposal: Proposal) -> int:
        self._ensure_header()
        service = self._get_service()

        skills_str = ", ".join(job.skills) if job.skills else ""
        found_at = job.found_at.strftime("%Y-%m-%d %H:%M") if job.found_at else ""
        rating = str(job.client_rating) if job.client_rating is not None else ""
        hires = str(job.client_hire_count) if job.client_hire_count is not None else ""
        description_excerpt = job.description[:500] if job.description else ""

        row = [
            job.job_id,
            found_at,
            job.title,
            job.url,
            job.budget_type.capitalize(),
            job.budget_amount,
            job.duration,
            job.experience_level,
            skills_str,
            job.client_location,
            rating,
            hires,
            description_excerpt,
            proposal.text,
            "New",
        ]

        result = service.spreadsheets().values().append(
            spreadsheetId=self.sheet_cfg.spreadsheet_id,
            range=self._sheet_range("A1"),
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": [row]},
        ).execute()

        updated_range = result.get("updates", {}).get("updatedRange", "")
        row_number = self._parse_row_number(updated_range)
        log.info("row_appended", job_id=job.job_id, row=row_number)
        return row_number

    def _parse_row_number(self, updated_range: str) -> int:
        try:
            return int(updated_range.split(":")[-1].lstrip("ABCDEFGHIJKLMNOPQRSTUVWXYZ"))
        except Exception:
            return 0
