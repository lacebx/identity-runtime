import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    discord_token: str = os.getenv("DISCORD_TOKEN", "")
    guild_id: int = int(os.getenv("GUILD_ID", "0"))
    identity_id: str = os.getenv("IDENTITY_ID", "community-agent")
    identity_storage_path: str = os.getenv("IDENTITY_STORAGE_PATH", ".identity_store")
    reminder_interval_minutes: int = int(os.getenv("REMINDER_INTERVAL_MINUTES", "30"))
    digest_time_daily: str = os.getenv("DIGEST_TIME_DAILY", "09:00")
    digest_time_weekly: str = os.getenv("DIGEST_TIME_WEEKLY", "09:00")
    digest_day_weekly: str = os.getenv("DIGEST_DAY_WEEKLY", "monday")
    timezone: str = os.getenv("TIMEZONE", "UTC")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


config = Config()
