import os
import csv
from datetime import datetime, timezone
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

# One active meeting per Discord server.
# {
#   guild_id: {
#       "name": str,
#       "channel_id": int,
#       "channel_name": str,
#       "started_at": datetime,
#       "participants": {
#           user_id: {
#               "display_name": str,
#               "username": str,
#               "joined_at": datetime | None,
#               "seconds": float
#           }
#       }
#   }
# }
active_meetings = {}


def utcnow():
    return datetime.now(timezone.utc)


def format_duration(seconds: float) -> str:
    total_minutes = int(round(seconds / 60))
    hours, minutes = divmod(total_minutes, 60)
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def safe_filename(value: str) -> str:
    return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in value).strip("_")


def ensure_participant(meeting, member: discord.Member):
    uid = member.id
    if uid not in meeting["participants"]:
        meeting["participants"][uid] = {
            "display_name": member.display_name,
            "username": str(member),
            "joined_at": None,
            "seconds": 0.0,
        }
    else:
        # Keep names fresh in case nickname changes.
        meeting["participants"][uid]["display_name"] = member.display_name
        meeting["participants"][uid]["username"] = str(member)
    return meeting["participants"][uid]


def start_session(meeting, member: discord.Member):
    participant = ensure_participant(meeting, member)
    if participant["joined_at"] is None:
        participant["joined_at"] = utcnow()


def end_session(meeting, member: discord.Member):
    participant = ensure_participant(meeting, member)
    if participant["joined_at"] is not None:
        participant["seconds"] += (utcnow() - participant["joined_at"]).total_seconds()
        participant["joined_at"] = None


def current_seconds(participant):
    seconds = participant["seconds"]
    if participant["joined_at"] is not None:
        seconds += (utcnow() - participant["joined_at"]).total_seconds()
    return seconds


@bot.event
async def on_ready():
    try:
        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
            print(f"Synced {len(synced)} commands to guild {GUILD_ID}")
        else:
            synced = await bot.tree.sync()
            print(f"Synced {len(synced)} global commands")
    except Exception as e:
        print(f"Command sync failed: {e}")

    print(f"Logged in as {bot.user} ({bot.user.id})")


meeting_group = app_commands.Group(name="meeting", description="Voice meeting attendance tracking")


@meeting_group.command(name="start", description="Start attendance tracking for one voice channel")
@app_commands.describe(
    name="Meeting name",
    channel="Only this voice channel will be tracked"
)
async def meeting_start(
    interaction: discord.Interaction,
    name: str,
    channel: discord.VoiceChannel
):
    if interaction.guild is None:
        await interaction.response.send_message("This command must be used inside a server.", ephemeral=True)
        return

    guild_id = interaction.guild.id

    if guild_id in active_meetings:
        current = active_meetings[guild_id]
        await interaction.response.send_message(
            f"A meeting is already active: **{current['name']}** in <#{current['channel_id']}>.\n"
            "End it first with `/meeting end`.",
            ephemeral=True,
        )
        return

    meeting = {
        "name": name,
        "channel_id": channel.id,
        "channel_name": channel.name,
        "started_at": utcnow(),
        "participants": {},
    }

    # Count people already in the selected channel when tracking starts.
    for member in channel.members:
        if not member.bot:
            start_session(meeting, member)

    active_meetings[guild_id] = meeting

    await interaction.response.send_message(
        f"✅ **Meeting started:** {name}\n"
        f"🎙️ Tracking only: {channel.mention}\n"
        f"👥 Already present: {len([m for m in channel.members if not m.bot])}\n\n"
        "All other voice channels are ignored."
    )


@meeting_group.command(name="status", description="Show current attendance for the active meeting")
async def meeting_status(interaction: discord.Interaction):
    if interaction.guild is None or interaction.guild.id not in active_meetings:
        await interaction.response.send_message("There is no active meeting.", ephemeral=True)
        return

    meeting = active_meetings[interaction.guild.id]
    rows = []

    for uid, participant in meeting["participants"].items():
        member = interaction.guild.get_member(uid)
        in_channel = (
            member is not None
            and member.voice is not None
            and member.voice.channel is not None
            and member.voice.channel.id == meeting["channel_id"]
        )
        rows.append(
            (
                participant["display_name"],
                current_seconds(participant),
                "🟢 In meeting" if in_channel else "⚪ Left",
            )
        )

    rows.sort(key=lambda x: x[1], reverse=True)

    if not rows:
        body = "No attendees recorded yet."
    else:
        body = "\n".join(
            f"• **{name}** — {format_duration(seconds)} — {state}"
            for name, seconds, state in rows[:40]
        )

    await interaction.response.send_message(
        f"📋 **{meeting['name']}**\n"
        f"🎙️ Channel: <#{meeting['channel_id']}>\n"
        f"⏱️ Running: {format_duration((utcnow() - meeting['started_at']).total_seconds())}\n\n"
        f"{body}"
    )


@meeting_group.command(name="end", description="End the meeting and export attendance")
async def meeting_end(interaction: discord.Interaction):
    if interaction.guild is None or interaction.guild.id not in active_meetings:
        await interaction.response.send_message("There is no active meeting.", ephemeral=True)
        return

    guild_id = interaction.guild.id
    meeting = active_meetings[guild_id]

    # Close any open sessions.
    for uid, participant in meeting["participants"].items():
        if participant["joined_at"] is not None:
            participant["seconds"] += (utcnow() - participant["joined_at"]).total_seconds()
            participant["joined_at"] = None

    ended_at = utcnow()
    meeting_seconds = max(1, (ended_at - meeting["started_at"]).total_seconds())

    date_str = ended_at.strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{safe_filename(meeting['name'])}_{date_str}.csv"
    filepath = DATA_DIR / filename

    rows = []
    for uid, participant in meeting["participants"].items():
        seconds = participant["seconds"]
        attendance_pct = min(100.0, (seconds / meeting_seconds) * 100)
        rows.append({
            "discord_user_id": uid,
            "display_name": participant["display_name"],
            "username": participant["username"],
            "meeting_name": meeting["name"],
            "voice_channel": meeting["channel_name"],
            "meeting_started_utc": meeting["started_at"].isoformat(),
            "meeting_ended_utc": ended_at.isoformat(),
            "minutes_attended": round(seconds / 60, 2),
            "attendance_percent": round(attendance_pct, 2),
        })

    rows.sort(key=lambda r: r["minutes_attended"], reverse=True)

    with filepath.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "discord_user_id",
                "display_name",
                "username",
                "meeting_name",
                "voice_channel",
                "meeting_started_utc",
                "meeting_ended_utc",
                "minutes_attended",
                "attendance_percent",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    active_meetings.pop(guild_id, None)

    if rows:
        summary = "\n".join(
            f"• **{r['display_name']}** — {r['minutes_attended']:.1f} min ({r['attendance_percent']:.1f}%)"
            for r in rows[:40]
        )
    else:
        summary = "No attendees recorded."

    await interaction.response.send_message(
        f"🏁 **Meeting ended: {meeting['name']}**\n"
        f"🎙️ Channel: <#{meeting['channel_id']}>\n"
        f"⏱️ Meeting length: {format_duration(meeting_seconds)}\n\n"
        f"{summary}",
        file=discord.File(filepath),
    )


@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    if member.bot:
        return

    meeting = active_meetings.get(member.guild.id)
    if not meeting:
        return

    tracked_channel_id = meeting["channel_id"]
    before_id = before.channel.id if before.channel else None
    after_id = after.channel.id if after.channel else None

    # Joined the tracked channel.
    if before_id != tracked_channel_id and after_id == tracked_channel_id:
        start_session(meeting, member)
        return

    # Left the tracked channel or moved to another voice channel.
    if before_id == tracked_channel_id and after_id != tracked_channel_id:
        end_session(meeting, member)
        return

    # Mute/deafen/video changes while remaining in the same channel do not
    # start/stop attendance.


bot.tree.add_command(meeting_group)

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is missing. Add it to your .env file or Railway Variables.")

bot.run(TOKEN)
