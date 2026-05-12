import random
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from src.config_loader import get_settings
from src.utils.logger import get_logger

log = get_logger()


def build_scheduler(pipeline_fn) -> AsyncIOScheduler:
    settings = get_settings()
    scheduler_cfg = settings.app.scheduler
    scheduler = AsyncIOScheduler(timezone="UTC")

    for run_time in scheduler_cfg.run_times:
        hour, minute = map(int, run_time.split(":"))
        offset = random.randint(
            -scheduler_cfg.random_offset_minutes,
            scheduler_cfg.random_offset_minutes,
        )
        scheduled = datetime.now().replace(hour=hour, minute=minute, second=0) + timedelta(minutes=offset)
        cron_hour = scheduled.hour
        cron_minute = scheduled.minute

        scheduler.add_job(
            pipeline_fn,
            trigger=CronTrigger(hour=cron_hour, minute=cron_minute),
            id=f"upwork_pipeline_{run_time}",
            replace_existing=True,
        )
        log.info("session_scheduled", time=f"{cron_hour:02d}:{cron_minute:02d}", original=run_time)

    return scheduler
