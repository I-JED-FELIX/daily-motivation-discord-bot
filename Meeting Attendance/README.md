# Discord Attendance Bot

Tracks attendance for ONE selected Discord voice channel during a meeting.

## Commands

### /meeting start
Choose:
- `name`: meeting name
- `channel`: the specific voice channel to track

The bot ignores all other voice channels.

### /meeting status
Shows everyone recorded so far, current attendance state, and accumulated time.

### /meeting end
Stops tracking, posts each person's total minutes and attendance percentage, and uploads a CSV.

## Important Discord settings

In the Discord Developer Portal for this bot:

1. Open **Bot**
2. Enable **SERVER MEMBERS INTENT**
3. Save changes

Voice state events do not require Message Content Intent.

## Invite permissions

The bot should have:
- View Channels
- Send Messages
- Attach Files
- Use Application Commands

It does NOT need to join the voice channel.

## Railway

Add Variables:

- `DISCORD_TOKEN` = bot token
- `GUILD_ID` = your Discord server ID

Using `GUILD_ID` makes slash commands appear much faster during setup/testing.

Start command:

```text
python bot.py
```

## Example

```text
/meeting start
name: AoO Strategy Meeting
channel: Meeting Room
```

Only members who are in **Meeting Room** are counted.

If someone leaves and rejoins, their sessions are combined into one total.
