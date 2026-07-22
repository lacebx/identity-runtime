import logging
import re
from typing import Optional

import discord
from discord.ext import commands

from services.conversation import process_message
from services.intentions import detect_and_create_intentions, complete_authors_intention
from services.meetings import detect_and_create_meeting

logger = logging.getLogger(__name__)

_FINISHED_PATTERNS = re.compile(
    r"^(?:I\s+)?(?:finished|done|completed|all\s+done|all\s+set|got\s+it|"
    r"that'?s?\s+done|just\s+finished|just\s+completed|wrapped\s+(?:up|it)|"
    r"it'?s?\s+done|completed|resolved|fixed|deployed|shipped)\b",
    re.IGNORECASE,
)

_MEETING_OUTCOME_PATTERNS = re.compile(
    r"(?:we\s+decided|decision|decided\s+to|agreed\s+on|summary|"
    r"outcome|conclusion|action\s+items|next\s+steps|result)",
    re.IGNORECASE,
)

_ASK_EVIDENCE = re.compile(
    r"(?:why\s+do\s+you\s+think|what'?s?\s+the\s+evidence|"
    r"how\s+do\s+you\s+know|prove\s+it|evidence\s+for|"
    r"show\s+me\s+the\s+evidence)",
    re.IGNORECASE,
)

_ASK_SUMMARY = re.compile(
    r"(?:what\s+(?:are|is)\s+(?:we|everyone|the\s+team)\s+(?:working\s+on|doing|up\s+to)|"
    r"what'?s?\s+the\s+status|status\s+update|"
    r"what\s+are\s+we\s+behind\s+on|"
    r"what'?s?\s+pending|what\s+is\s+pending)",
    re.IGNORECASE,
)


def setup(bot: commands.Bot) -> None:
    identity = bot.identity

    @bot.event
    async def on_message(message: discord.Message):
        if message.author.bot:
            return
        if not message.guild:
            return

        content = message.content.strip()
        author_id = str(message.author.id)
        channel_id = str(message.channel.id)

        # Map Discord threads/channels to IdentityOS sessions
        session_id = f"discord:{message.guild.id}:{channel_id}"

        # --- Step 1: Detect commitments ------------------------------------------------
        intentions = detect_and_create_intentions(identity, content, author_id, channel_id)

        # --- Step 2: Detect meeting proposals -----------------------------------------
        meetings = detect_and_create_meeting(identity, content, author_id, channel_id)

        # --- Step 3: Detect completion ("I finished") ---------------------------------
        completed = None
        if _FINISHED_PATTERNS.match(content):
            completed = complete_authors_intention(identity, author_id, content)

        # --- Step 4: Detect meeting outcomes ------------------------------------------
        if _MEETING_OUTCOME_PATTERNS.search(content):
            from services.meetings import record_meeting_outcome
            record_meeting_outcome(
                identity,
                participants=[author_id],
                summary=content,
                decisions=[content],
            )

        # --- Step 5: Handle "why?" / evidence questions --------------------------------
        if _ASK_EVIDENCE.search(content):
            _handle_evidence_question(identity, message, content)
            return

        # --- Step 6: Handle "what is everyone working on?" -----------------------------
        if _ASK_SUMMARY.search(content):
            await _send_team_summary(identity, message)
            return

        # --- Step 7: Normal chat with session isolation -------------------------------
        with identity.session(session_id=session_id) as session:
            reply = session.chat(content)

        # --- Step 8: Add context about detected items ---------------------------------
        context_parts = []
        if intentions:
            names = [i["description"][:40] for i in intentions]
            context_parts.append(f"Tracked: {', '.join(names)}")
        if meetings:
            context_parts.append("Meeting recorded.")
        if completed:
            context_parts.append(f"Completed: {completed['description'][:40]}")
        if context_parts:
            reply += "\n\n*(" + " | ".join(context_parts) + ")*"

        if len(reply) > 1900:
            reply = reply[:1900] + "..."

        await message.channel.send(reply)

    logger.info("Conversation listener registered")


async def _send_team_summary(identity, message: discord.Message) -> None:
    from services.summary import generate_team_summary
    text = generate_team_summary(identity)
    if len(text) > 1900:
        text = text[:1900] + "\n... (truncated)"
    await message.channel.send(text)


def _handle_evidence_question(identity, message: discord.Message, content: str) -> None:
    """Try to figure out what entity the user is asking about and show evidence."""
    entity_id = None

    intentions = identity.intentions(status="active")
    for i in intentions:
        desc = i.get("description", "").lower()
        for word in content.lower().split():
            if len(word) > 3 and word in desc:
                entity_id = i["id"]
                break
        if entity_id:
            break

    if not entity_id:
        recent = identity.timeline(limit=5)
        if recent:
            entity_id = recent[-1]["id"]

    if entity_id:
        from services.identity import get_evidence_text
        text = get_evidence_text(identity, entity_id)
        text = f"*Evidence-backed response:*\n{text}"
    else:
        text = "I couldn't determine what you're asking about. Try `/evidence <entity_id>`."

    if len(text) > 1900:
        text = text[:1900] + "..."
    import asyncio
    asyncio.ensure_future(message.channel.send(text))
