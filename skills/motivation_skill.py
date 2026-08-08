import random
import discord


QUOTES = [
    "Small progress is still progress. Keep moving.",
    "You do not need a perfect day to make meaningful progress.",
    "Discipline carries you forward when motivation takes a day off.",
    "Start where you are. Improve one thing today.",
    "Your future is built by the choices you repeat.",
    "Do not wait for confidence. Build it through action.",
    "A difficult chapter is not the whole story.",
    "Consistency turns ordinary effort into extraordinary results.",
    "Focus on the next useful step, not the entire staircase.",
    "You are allowed to begin again—and begin better.",
    "Dreams become plans when you give them a date and a first step.",
    "Protect your attention; it is one of your most valuable resources.",
    "Progress rarely feels dramatic while it is happening. Keep going.",
    "Make today slightly better than yesterday.",
    "Courage is often just taking the next step while still uncertain.",
]


class Skill:
    name = "motivation"

    def __init__(self, bot):
        self.bot = bot

    async def generate_message(self):
        quote = random.choice(QUOTES)
        embed = discord.Embed(
            title="🌟 Daily Motivation",
            description=f"**{quote}**",
        )
        embed.set_footer(text="Take the next step. You've got this.")
        return embed
