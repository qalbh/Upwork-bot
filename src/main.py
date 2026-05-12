import asyncio
from src.config_loader import get_settings
from src.deduplicator import Deduplicator
from src.fetcher.playwright_fetcher import PlaywrightFetcher
from src.proposal_generator import ProposalGenerator
from src.sheet_writer import SheetWriter
from src.scheduler import build_scheduler
from src.utils.logger import setup_logger, get_logger

log = get_logger()


async def run_pipeline():
    settings = get_settings()
    dedup = Deduplicator()
    fetcher = PlaywrightFetcher()
    generator = ProposalGenerator()
    writer = SheetWriter()

    await dedup.init()
    total_written = 0

    for query in settings.app.search.queries:
        log.info("pipeline_start", query=query)
        jobs = await fetcher.fetch_jobs(query)

        for job in jobs:
            try:
                if await dedup.is_seen(job.job_id):
                    log.info("job_skipped_duplicate", job_id=job.job_id)
                    continue

                proposal = await generator.generate(job)
                row = writer.append_row(job, proposal)
                await dedup.mark_seen(job.job_id, row)
                total_written += 1

                log.info("job_processed", job_id=job.job_id, title=job.title, row=row)
                await asyncio.sleep(1)

            except Exception as e:
                log.error("job_failed", job_id=job.job_id, error=str(e))
                continue

    seen_count = await dedup.count()
    log.info("pipeline_done", jobs_written=total_written, total_seen=seen_count)


def main():
    setup_logger()
    settings = get_settings()
    log.info("upwork_bot_starting", queries=settings.app.search.queries)

    loop = asyncio.get_event_loop()

    if settings.app.scheduler.sessions_per_day > 0:
        scheduler = build_scheduler(run_pipeline)
        scheduler.start()
        log.info("scheduler_started", sessions_per_day=settings.app.scheduler.sessions_per_day)

        # Run once immediately on start
        loop.run_until_complete(run_pipeline())
        loop.run_forever()
    else:
        loop.run_until_complete(run_pipeline())


if __name__ == "__main__":
    main()
