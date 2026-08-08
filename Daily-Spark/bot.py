import asyncio
import logging
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands, tasks

from database import Database
from skills import load_skills

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("motivation-bot")

TOKEN = os.getenv("DISCORD_TOKEN")
DEFAULT_TIMEZONE = os.getenv("DEFAULT_TIMEZONE", "Asia/Kolkata")

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN environment variable is required.")

intents = discord.Intents.none()
intents.guilds = True


class MotivationBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None,
        )
        self.db = Database()
        self.skill_registry = {}

    async def setup_hook(self):
        await self.db.connect()
        self.skill_registry = await load_skills(self)
        synced = await self.tree.sync()
        log.info("Synced %s slash commands.", len(synced))
        daily_scheduler.start()

    async def close(self):
        daily_scheduler.cancel()
        await self.db.close()
        await super().close()


bot = MotivationBot()


@bot.event
async def on_ready():
    log.info("Logged in as %s (%s)", bot.user, bot.user.id)


@bot.tree.command(name="quote", description="Post a motivational quote now.")
async def quote(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message(
            "This command can only be used inside a server.",
            ephemeral=True,
        )
        return

    skill = bot.skill_registry.get("motivation")
    message = await skill.generate_message()
    await interaction.response.send_message(embed=message)


@bot.tree.command(name="setup", description="Configure the daily motivational quote.")
@app_commands.describe(
    channel="Channel where the daily quote should be posted.",
    time="24-hour time, e.g. 09:00 or 18:30.",
    timezone="IANA timezone, e.g. Asia/Kolkata or America/New_York.",
)
@app_commands.default_permissions(manage_guild=True)
async def setup(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    time: str = "09:00",
    timezone: str = DEFAULT_TIMEZONE,
):
    if not interaction.guild:
        await interaction.response.send_message("Use this command in a server.", ephemeral=True)
        return

    try:
        datetime.strptime(time, "%H:%M")
        ZoneInfo(timezone)
    except ValueError:
        await interaction.response.send_message(
            "Invalid time. Use HH:MM, for example `09:00`.",
            ephemeral=True,
        )
        return
    except Exception:
        await interaction.response.send_message(
            "Invalid timezone. Use an IANA timezone such as `Asia/Kolkata`.",
            ephemeral=True,
        )
        return

    await bot.db.set_guild(
        guild_id=interaction.guild.id,
        channel_id=channel.id,
        daily_time=time,
        timezone=timezone,
        enabled=True,
    )

    await interaction.response.send_message(
        f"Daily motivation is enabled in {channel.mention} at **{time} {timezone}**.",
        ephemeral=True,
    )


@bot.tree.command(name="status", description="Show the daily motivation configuration.")
async def status(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message("Use this command in a server.", ephemeral=True)
        return

    cfg = await bot.db.get_guild(interaction.guild.id)
    if not cfg or not cfg["enabled"]:
        await interaction.response.send_message(
            "Daily motivation is currently disabled.",
            ephemeral=True,
        )
        return

    channel = interaction.guild.get_channel(cfg["channel_id"])
    channel_name = channel.mention if channel else f"<#{cfg['channel_id']}>"
    await interaction.response.send_message(
        f"**Daily motivation:** enabled\n"
        f"**Channel:** {channel_name}\n"
        f"**Time:** {cfg['daily_time']} {cfg['timezone']}",
        ephemeral=True,
    )


@bot.tree.command(name="disable", description="Disable daily motivational quotes.")
@app_commands.default_permissions(manage_guild=True)
async def disable(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message("Use this command in a server.", ephemeral=True)
        return

    await bot.db.disable_guild(interaction.guild.id)
    await interaction.response.send_message(
        "Daily motivation has been disabled. Use `/setup` to enable it again.",
        ephemeral=True,
    )


@tasks.loop(minutes=1)
async def daily_scheduler():
    now_utc = datetime.now(ZoneInfo("UTC"))
    configs = await bot.db.get_enabled_guilds()

    for cfg in configs:
        try:
            tz = ZoneInfo(cfg["timezone"])
            local_now = now_utc.astimezone(tz)
            scheduled = datetime.strptime(cfg["daily_time"], "%H:%M").time()

            # Run once during the configured minute.
            if local_now.hour != scheduled.hour or local_now.minute != scheduled.minute:
                continue

            today_key = local_now.strftime("%Y-%m-%d")
            if cfg["last_posted_date"] == today_key:
                continue

            channel = bot.get_channel(cfg["channel_id"])
            if channel is None:
                try:
                    channel = await bot.fetch_channel(cfg["channel_id"])
                except Exception:
                    log.exception("Could not fetch channel %s", cfg["channel_id"])
                    continue

            skill = bot.skill_registry.get("motivation")
            embed = await skill.generate_message()
            await channel.send(embed=embed)
            await bot.db.mark_posted(cfg["guild_id"], today_key)
            log.info("Posted daily quote to guild %s.", cfg["guild_id"])

        except Exception:
            log.exception("Daily scheduler error for guild %s.", cfg["guild_id"])


@daily_scheduler.before_loop
async def before_scheduler():
    await bot.wait_until_ready()


if __name__ == "__main__":
    bot.run(TOKEN)
