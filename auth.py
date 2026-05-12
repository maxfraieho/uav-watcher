#!/usr/bin/env python3
"""Run once interactively to create Telethon session file."""
import asyncio, os
from dotenv import load_dotenv
from telethon import TelegramClient

load_dotenv()

async def main():
    client = TelegramClient(
        "uav_watcher",
        int(os.environ["TELEGRAM_API_ID"]),
        os.environ["TELEGRAM_API_HASH"]
    )
    await client.start(phone=os.environ["TELEGRAM_PHONE"])
    me = await client.get_me()
    print(f"Authorized as: {me.first_name} (@{me.username})")
    await client.disconnect()

asyncio.run(main())
