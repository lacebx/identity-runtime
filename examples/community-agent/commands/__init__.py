import logging

import discord
from discord import app_commands
from discord.ext import commands

from services.identity import describe_identity

logger = logging.getLogger(__name__)


def setup(bot: commands.Bot) -> None:
    identity = bot.identity

    @bot.tree.command(name="about", description="Show identity information")
    async def about(interaction: discord.Interaction):
        text = describe_identity(identity)
        await interaction.response.send_message(text, ephemeral=False)

    @bot.tree.command(name="status", description="Show current team status summary")
    async def status_cmd(interaction: discord.Interaction):
        from services.summary import generate_team_summary
        text = generate_team_summary(identity)
        if len(text) > 1900:
            text = text[:1900] + "\n... (truncated)"
        await interaction.response.send_message(text, ephemeral=False)

    @bot.tree.command(name="digest", description="Generate a daily or weekly digest")
    @app_commands.describe(period="daily or weekly")
    @app_commands.choices(period=[
        app_commands.Choice(name="Daily", value="daily"),
        app_commands.Choice(name="Weekly", value="weekly"),
    ])
    async def digest_cmd(interaction: discord.Interaction, period: str = "daily"):
        from services.summary import generate_digest_message
        text = generate_digest_message(identity, period)
        if len(text) > 1900:
            text = text[:1900] + "\n... (truncated)"
        await interaction.response.send_message(text, ephemeral=False)

    @bot.tree.command(name="evidence", description="Show evidence for a specific entity")
    @app_commands.describe(entity_id="Entity ID to look up")
    async def evidence_cmd(interaction: discord.Interaction, entity_id: str):
        from services.identity import get_evidence_text
        text = get_evidence_text(identity, entity_id)
        if len(text) > 1900:
            text = text[:1900] + "\n... (truncated)"
        await interaction.response.send_message(text, ephemeral=False)

    @bot.tree.command(name="constitution", description="Show the IdentityOS Constitution")
    async def constitution_cmd(interaction: discord.Interaction):
        from services.identity import get_constitution_text
        text = get_constitution_text(identity)
        if len(text) > 1900:
            text = text[:1900] + "\n... (truncated)"
        await interaction.response.send_message(text, ephemeral=False)

    @bot.tree.command(name="reminders", description="Show pending reminders")
    async def reminders_cmd(interaction: discord.Interaction):
        reminders_list = identity.reminders(max_results=20)
        if not reminders_list:
            await interaction.response.send_message("No pending reminders.", ephemeral=False)
            return
        lines = ["## Pending Reminders", ""]
        for r in reminders_list:
            author = r.get("author_id", "unknown")
            label = r["label"].replace("_", " ").title()
            hours = r["hours_left"]
            lines.append(f"- **{author}:** {r['description']}")
            lines.append(f"  *{label} ({hours:.1f}h remaining)*")
        text = "\n".join(lines)
        if len(text) > 1900:
            text = text[:1900] + "\n... (truncated)"
        await interaction.response.send_message(text, ephemeral=False)

    logger.info("Slash commands registered")
