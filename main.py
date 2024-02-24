"""
End-User License Agreement (EULA)

1. This script is provided as-is, without any warranties or guarantees.
2. You may use, modify, and distribute this script for personal or educational purposes.
3. Commercial use or distribution without explicit permission is prohibited.
4. The author is not responsible for any damages or liabilities resulting from the use of this script.

By using this script, you agree to abide by the terms of this license.

"""
import discord
import asyncio
import datetime
import os
from typing import Dict, Any
import logging
from logging.handlers import RotatingFileHandler
from colorama import Fore, Style, init
from tqdm.asyncio import tqdm

init(autoreset=True)

log_formatter = logging.Formatter('[vindicate] %(message)s')
log_file = 'vindicate.log'

log_handler = RotatingFileHandler(log_file, mode='a', maxBytes=5*1024*1024, backupCount=2, encoding=None, delay=0)
log_handler.setFormatter(log_formatter)
log_handler.setLevel(logging.INFO)

logging.basicConfig(handlers=[log_handler], level=logging.INFO, format='%(message)s')

CYAN = Fore.CYAN
DARK_RED = Fore.RED
GREEN = Fore.GREEN

RATE_LIMIT_WINDOW = 120  # 2 minutes
RATE_LIMIT_MESSAGES = 15  # Max 15 messages per window
RATE_LIMIT_COUNTDOWN = 15  # 15 seconds countdown

bk: Dict[int, Dict[str, Any]] = {}

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def banner():
    clear()
    ascii = DARK_RED + r"""
     :::           :::     ::: ::::::::::: ::::    ::: :::::::::  :::::::::::  ::::::::      :::     ::::::::::: :::::::::: 
  :+:+:+:+:        :+:     :+:     :+:     :+:+:   :+: :+:    :+:     :+:     :+:    :+:   :+: :+:       :+:     :+:        
+:+  +:+           +:+     +:+     +:+     :+:+:+  +:+ :+:    :+:     +:+     +:+         +:+   +:+      +:+     +:+        
  +#++:++#+        +#+     +:+     +#+     +#+ +:+ +#+ +#+    +#+     +#+     +#+        +#++:++#++:     +#+     +#++:++#   
     +#+ +#+        +#+   +#+      +#+     +#+  +#+#+# +#+    +#+     +#+     +#+        +#+     +#+     +#+     +#+        
  #+#+#+#+#          #+#+#+#       #+#     #+#   #+#+# #+#    #+#     #+#     #+#    #+# #+#     #+#     #+#     #+#        
     ###               ###     ########### ###    #### #########  ###########  ########  ###     ###     ###     ########## 
    """ + Style.RESET_ALL
    print(ascii)

class RateLimiter:
    """Manages rate limiting for message deletion."""

    @staticmethod
    def get_user_limit(user_id: int) -> Dict[str, Any]:
        """Gets or initializes the rate limit information for a user."""
        if user_id not in bk:
            bk[user_id] = {"last_reset": datetime.datetime.now(), "count": 0}
        return bk[user_id]

    @staticmethod
    async def handle_rate_limit(user_id: int):
        """Handles rate limiting by waiting when the limit is exceeded."""
        limit_info = RateLimiter.get_user_limit(user_id)
        now = datetime.datetime.now()

        if (now - limit_info["last_reset"]).seconds >= RATE_LIMIT_WINDOW:
            limit_info["last_reset"] = now
            limit_info["count"] = 0

        while limit_info["count"] >= RATE_LIMIT_MESSAGES:
            logging.warning(f"{DARK_RED}Rate limit exceeded. Waiting for cooldown...{Style.RESET_ALL}")
            for i in range(RATE_LIMIT_COUNTDOWN, 0, -1):
                print(f"{DARK_RED}Retry in {i} seconds...{Style.RESET_ALL}", end="\r")
                await asyncio.sleep(1)
            limit_info["last_reset"] = now
            limit_info["count"] = 0

class Vindicate(discord.Client):
    """A client for deleting messages in Discord channels."""

    async def on_ready(self):
        """Event handler for when Vindicate has successfully logged in."""
        banner()
        logging.info(f"Logged in as: {self.user}")

        while True:
            clear()
            banner()
            target_channel_id = input(f"{CYAN}Enter Channel ID (or 'exit' to quit): {Style.RESET_ALL}").strip()

            if target_channel_id.lower() == "exit":
                break

            try:
                target_channel_id = int(target_channel_id)
                target_channel = self.get_channel(target_channel_id)

                if target_channel:
                    desc = "Clearing DM" if isinstance(target_channel, discord.DMChannel) else \
                           f"Purging messages in #{target_channel.name}" if isinstance(target_channel, discord.TextChannel) else \
                           "Purging messages in group chat" if isinstance(target_channel, discord.GroupChannel) else \
                           "Unsupported channel type"
                    await self.remove_messages(target_channel, self.user.id, desc)
                else:
                    logging.error("Channel not found. Please try again.")
            except ValueError:
                logging.error("Please enter a valid channel ID.")

    async def remove_messages(self, channel: discord.abc.Messageable, user_id: int, desc: str):
        """Deletes messages from a specified channel."""
        await RateLimiter.handle_rate_limit(user_id)
        
        message_count = 0
        
        async for message in channel.history(limit=None):
            if message.author.id == user_id:
                message_count += 1

        logging.info(f"Total messages to delete: {message_count}")
        if message_count > 0:
            progress = tqdm(total=message_count, desc=desc, bar_format="{desc}: {n_fmt}/{total_fmt} {bar}")
            async for message in channel.history(limit=None):
                if message.author.id == user_id:
                    try:
                        await message.delete()
                        bk[user_id]["count"] += 1
                        progress.update(1)
                        await asyncio.sleep(1)
                    except discord.Forbidden:
                        logging.error("Permission Error: Cannot delete messages.")
                        break
                    except discord.HTTPException:
                        logging.error("HTTP Exception: Error deleting message.")
                        continue
            progress.close()
        else:
            logging.info("No messages found to delete.")

if __name__ == "__main__":
    banner()
    token = input(f"{CYAN}Enter User Token: {Style.RESET_ALL}").strip()
    client = Vindicate()
    client.run(token)
    clear()
