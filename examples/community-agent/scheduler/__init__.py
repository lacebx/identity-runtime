import logging
from datetime import datetime, timezone
from typing import Optional

import discord
from discord.ext import commands, tasks

logger = logging.getLogger(__name__)


def setup(bot: commands.Bot) -> None:
    identity = bot.identity
    config = bot.bot_config

    @tasks.loop(minutes=config.reminder_interval_minutes)
    async def check_reminders():
        if not bot.is_ready():
            return
        reminders_list = identity.reminders(max_results=10)
        overdue = [r for r in reminders_list if r["label"] == "overdue"]

        if not overdue:
            return

        # Find a general channel to send reminders
        channel = _find_default_channel(bot)
        if not channel:
            logger.warning("No suitable channel found for reminders")
            return

        for r in overdue[:3]:  # Max 3 per cycle to avoid spam
            author_id = r.get("author_id", "")
            mention = f"<@{author_id}>" if author_id else "someone"
            hours_over = abs(r["hours_left"])
            desc = r["description"]

            msg = (
                f"⏰ Hey {mention}, you mentioned you'd finish **{desc}** "
                f"and it's now {hours_over:.0f}h overdue. Any update?"
            )
            try:
                await channel.send(msg)
                logger.info("Reminder sent: %s — %s", author_id, desc)
            except Exception as e:
                logger.error("Failed to send reminder: %s", e)

    @tasks.loop(hours=24)
    async def daily_digest():
        if not bot.is_ready():
            return
        now = datetime.now(timezone.utc)
        target_time = config.digest_time_daily
        target_hour, target_min = map(int, target_time.split(":"))

        # Only run at the configured time
        if now.hour != target_hour or now.minute < target_min or now.minute > target_min + 5:
            return

        channel = _find_default_channel(bot)
        if not channel:
            logger.warning("No suitable channel found for daily digest")
            return

        from ..services.summary import generate_digest_message
        text = generate_digest_message(identity, period="daily")
        if len(text) > 1900:
            text = text[:1900] + "\n..."
        try:
            await channel.send(text)
            logger.info("Daily digest sent")
        except Exception as e:
            logger.error("Failed to send daily digest: %s", e)

    @tasks.loop(hours=24)
    async def weekly_digest():
        if not bot.is_ready():
            return
        now = datetime.now(timezone.utc)
        target_time = config.digest_time_weekly
        target_hour, target_min = map(int, target_time.split(":"))
        target_day = config.digest_day_weekly.lower()

        # Only run on the configured day and time
        if now.strftime("%A").lower() != target_day:
            return
        if now.hour != target_hour or now.minute < target_min or now.minute > target_min + 5:
            return

        channel = _find_default_channel(bot)
        if not channel:
            return

        from ..services.summary import generate_digest_message
        text = generate_digest_message(identity, period="weekly")
        if len(text) > 1900:
            text = text[:1900] + "\n..."
        try:
            await channel.send(text)
            logger.info("Weekly digest sent")
        except Exception as e:
            logger.error("Failed to send weekly digest: %s", e)

    @check_reminders.before_loop
    @daily_digest.before_loop
    @weekly_digest.before_loop
    async def before_loops():
        await bot.wait_until_ready()

    check_reminders.start()
    daily_digest.start()
    weekly_digest.start()

    logger.info(
        "Scheduler started: reminders every %dmin, daily digest at %s, weekly digest on %s at %s",
        config.reminder_interval_minutes,
        config.digest_time_daily,
        config.digest_day_weekly,
        config.digest_time_weekly,
    )


def _find_default_channel(bot: commands.Bot) -> Optional[discord.TextChannel]:
    """Find a reasonable channel to send automated messages to."""
    for guild in bot.guilds:
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                return channel
    return None
