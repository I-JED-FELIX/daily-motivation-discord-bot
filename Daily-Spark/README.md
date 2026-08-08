# Daily Motivation Discord Bot

A lightweight Discord bot that posts an original motivational quote every day.

## Design

The bot is deliberately structured as a small "skill platform":

- `skills/` contains independent skills.
- `skills/motivation_skill.py` is the first skill.
- New skills can be added as new `*_skill.py` files.
- `database.py` stores per-server configuration in SQLite.
- `bot.py` contains the Discord interface and scheduler.
- No privileged Discord intents are required.

## Current commands

- `/setup` — choose the channel, time and timezone.
- `/quote` — post a motivational quote immediately.
- `/status` — view the current configuration.
- `/disable` — turn daily posting off.

## Local setup

1. Create a Discord application and bot in the Discord Developer Portal.
2. Copy the bot token. Never publish it or commit it to Git.
3. Copy `.env.example` to `.env`.
4. Put the token in `.env`.
5. Install Python 3.12+.
6. Create a virtual environment.
7. Install dependencies:
   `pip install -r requirements.txt`
8. Set the environment variable before running:
   Windows PowerShell:
   `$env:DISCORD_TOKEN="YOUR_TOKEN"`
   `python bot.py`

For local development, you can also use a `.env` loader such as python-dotenv, but production deployments should use the host's secret/environment-variable system.

## Discord permissions

The bot only needs enough access to:

- View the configured channel
- Send Messages
- Embed Links

The setup commands use Discord's application-command permission model.

## Invite

In the Discord Developer Portal, create an install/invite link for the application with:

- `bot` scope
- `applications.commands` scope
- View Channel
- Send Messages
- Embed Links

## Railway deployment

Railway works well for this always-on bot because it can deploy directly from GitHub or from the local project with `railway up`.

1. Put this project in a GitHub repository.
2. Create a Railway project from the repository.
3. Add the variable:
   `DISCORD_TOKEN = your token`
4. Optionally add:
   `DEFAULT_TIMEZONE = Asia/Kolkata`
5. Deploy.
6. Invite the bot to your Discord server.
7. Run `/setup`.

The SQLite database is fine for a simple single-instance bot. If this grows into a public paid product with many servers, migrate configuration to PostgreSQL.

## Adding a new skill

Create a file such as:

`skills/reminder_skill.py`

with a class named `Skill` and a unique `name`.

The loader automatically imports files matching `*_skill.py`.

For larger skills, keep the skill's logic in its own module/package and let `bot.py` handle only Discord lifecycle/scheduling.

## Security

Never put the bot token in:

- GitHub
- README files
- screenshots
- Discord messages
- source code committed to a repository

If the token is ever exposed, regenerate it immediately in the Discord Developer Portal.
