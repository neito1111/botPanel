import asyncio
import sys

from bot.app import main
from bot.config import Settings
from bot.doctor import run_doctor


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "doctor":
        raise SystemExit(asyncio.run(run_doctor()))
    asyncio.run(main(Settings()))


