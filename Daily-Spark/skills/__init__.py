import importlib
from pathlib import Path


async def load_skills(bot):
    registry = {}
    package_dir = Path(__file__).parent

    for path in package_dir.glob("*_skill.py"):
        module_name = f"skills.{path.stem}"
        module = importlib.import_module(module_name)
        skill = module.Skill(bot)
        registry[skill.name] = skill

    return registry
