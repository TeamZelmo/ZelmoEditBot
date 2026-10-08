import os
import sys
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl import types
from telethon.errors import FloodWaitError

# Environment Variables se settings read hongi
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
STRING_SESSION = os.environ.get("STRING_SESSION", "")
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", 0))
OLD_LINK = os.environ.get("OLD_LINK", "")
NEW_LINK = os.environ.get("NEW_LINK", "")
DELAY_SECONDS = int(os.environ.get("DELAY_SECONDS", 2))

if not (API_ID and API_HASH and STRING_SESSION and CHANNEL_ID and OLD_LINK and NEW_LINK):
    print("[-] Missing Environment Variables! Render dashboard me Environment variables check karein.")
    sys.exit(1)

client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

def update_button_markup(reply_markup, old_url, new_url):
    if not reply_markup or not hasattr(reply_markup, "rows"):
        return None

    updated_rows = []
    has_changes = False

    for row in reply_markup.rows:
        new_buttons = []
        for btn in row.buttons:
            if isinstance(btn, types.KeyboardButtonUrl):
                if old_url in btn.url:
                    replaced_url = btn.url.replace(old_url, new_url)
                    new_buttons.append(types.KeyboardButtonUrl(text=btn.text, url=replaced_url))
                    has_changes = True
                else:
                    new_buttons.append(btn)
            else:
                new_buttons.append(btn)
        updated_rows.append(types.KeyboardButtonRow(buttons=new_buttons))

    if has_changes:
        return types.ReplyInlineMarkup(rows=updated_rows)
    return None

async def main():
    await client.start()
    print("[+] Connected to Telegram via StringSession.")

    try:
        channel = await client.get_entity(CHANNEL_ID)
        print(f"[+] Channel connected: {getattr(channel, 'title', CHANNEL_ID)}")
    except Exception as e:
        print(f"[-] Channel entity fetch error: {e}")
        return

    print("[*] Posts scan shuru...")
    scanned_count = 0
    updated_count = 0

    async for message in client.iter_messages(channel):
        scanned_count += 1
        content = message.text or message.caption or ""
        needs_edit = False

        new_text = None
        if OLD_LINK in content:
            new_text = content.replace(OLD_LINK, NEW_LINK)
            needs_edit = True

        new_markup = update_button_markup(message.reply_markup, OLD_LINK, NEW_LINK)
        if new_markup is not None:
            needs_edit = True

        if needs_edit:
            while True:
                try:
                    await client.edit_message(
                        entity=channel,
                        message=message.id,
                        text=new_text if new_text is not None else content,
                        buttons=new_markup if new_markup is not None else message.reply_markup
                    )
                    updated_count += 1
                    print(f"[✓] Updated Message ID: {message.id}")
                    await asyncio.sleep(DELAY_SECONDS)
                    break
                except FloodWaitError as e:
                    print(f"[!] FloodWait mila: {e.seconds} seconds wait kar rahe hain...")
                    await asyncio.sleep(e.seconds + 2)
                except Exception as e:
                    print(f"[-] Error editing message ID {message.id}: {e}")
                    break

    print("------------------------------------------")
    print(f"Total scanned: {scanned_count} | Total updated: {updated_count}")
    print("[✓] Process complete!")

if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())
