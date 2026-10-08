import os
import sys
import re
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl import types
from telethon.errors import FloodWaitError

# Environment Variables
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
STRING_SESSION = os.environ.get("STRING_SESSION", "")
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", 0))
OLD_LINK = os.environ.get("OLD_LINK", "").strip()
NEW_LINK = os.environ.get("NEW_LINK", "").strip()
DELAY_SECONDS = int(os.environ.get("DELAY_SECONDS", 2))

if not (API_ID and API_HASH and STRING_SESSION and CHANNEL_ID and OLD_LINK and NEW_LINK):
    print("[-] Missing Environment Variables! Values check karein.")
    sys.exit(1)

# Protocol prefixes hata kar raw domain/path extract karein taaki matching miss na ho
CLEAN_OLD_LINK = re.sub(r"^https?://", "", OLD_LINK).rstrip("/")
CLEAN_NEW_LINK = NEW_LINK

print(f"[*] Target search pattern: '{CLEAN_OLD_LINK}'")
print(f"[*] Replace with: '{CLEAN_NEW_LINK}'")

client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

def update_button_markup(reply_markup, target_pattern, new_url):
    """Inline buttons check aur replace karta hai."""
    if not reply_markup or not hasattr(reply_markup, "rows"):
        return None

    updated_rows = []
    has_changes = False

    for row in reply_markup.rows:
        new_buttons = []
        for btn in row.buttons:
            if isinstance(btn, types.KeyboardButtonUrl):
                clean_btn_url = re.sub(r"^https?://", "", btn.url).rstrip("/")
                if target_pattern.lower() in clean_btn_url.lower():
                    # Exact replace with regex
                    replaced_url = re.sub(re.escape(target_pattern), new_url, btn.url, flags=re.IGNORECASE)
                    new_buttons.append(types.KeyboardButtonUrl(text=btn.text, url=replaced_url))
                    has_changes = True
                    print(f"    [Button Match] Old: {btn.url} -> New: {replaced_url}")
                else:
                    new_buttons.append(btn)
            else:
                new_buttons.append(btn)
        updated_rows.append(types.KeyboardButtonRow(buttons=new_buttons))

    if has_changes:
        return types.ReplyInlineMarkup(rows=updated_rows)
    return None

def update_hyperlink_entities(entities, target_pattern, new_url):
    """Text ke andar ke hyperlinks ko update karta hai."""
    if not entities:
        return False

    has_changes = False
    for entity in entities:
        if isinstance(entity, types.MessageEntityTextUrl):
            clean_entity_url = re.sub(r"^https?://", "", entity.url).rstrip("/")
            if target_pattern.lower() in clean_entity_url.lower():
                old_u = entity.url
                entity.url = re.sub(re.escape(target_pattern), new_url, entity.url, flags=re.IGNORECASE)
                has_changes = True
                print(f"    [Entity Match] Old: {old_u} -> New: {entity.url}")
    return has_changes

async def main():
    await client.start()
    print("[+] Connected to Telegram.")

    try:
        channel = await client.get_entity(CHANNEL_ID)
        print(f"[+] Channel target: {getattr(channel, 'title', CHANNEL_ID)}")
    except Exception as e:
        print(f"[-] Channel entity fetch error: {e}")
        return

    print("[*] Scan shuru kar rahe hain...")
    scanned_count = 0
    updated_count = 0

    async for message in client.iter_messages(channel):
        scanned_count += 1

        if not isinstance(message, types.Message):
            continue

        content = message.raw_text or ""
        needs_edit = False
        new_text = None

        # 1. Plain text / caption me search
        clean_content = re.sub(r"^https?://", "", content)
        if re.search(re.escape(CLEAN_OLD_LINK), content, flags=re.IGNORECASE):
            new_text = re.sub(re.escape(CLEAN_OLD_LINK), CLEAN_NEW_LINK, content, flags=re.IGNORECASE)
            needs_edit = True
            print(f"[+] Found match in Message ID {message.id} text/caption")

        # 2. Buttons me search
        new_markup = update_button_markup(message.reply_markup, CLEAN_OLD_LINK, CLEAN_NEW_LINK)
        if new_markup is not None:
            needs_edit = True

        # 3. Formatted Markdown links me search
        entities = list(message.entities) if message.entities else []
        if update_hyperlink_entities(entities, CLEAN_OLD_LINK, CLEAN_NEW_LINK):
            needs_edit = True

        # Agar kahi match mila toh update karein
        if needs_edit:
            while True:
                try:
                    await client.edit_message(
                        entity=channel,
                        message=message.id,
                        text=new_text if new_text is not None else content,
                        formatting_entities=entities if entities else None,
                        buttons=new_markup if new_markup is not None else message.reply_markup
                    )
                    updated_count += 1
                    print(f"[✓] Successfully Updated Message ID: {message.id}")
                    await asyncio.sleep(DELAY_SECONDS)
                    break
                except FloodWaitError as e:
                    wait_time = e.seconds + 2
                    print(f"[!] FloodWait mila: {wait_time}s wait kar rahe hain...")
                    await asyncio.sleep(wait_time)
                except Exception as e:
                    print(f"[-] Edit fail hua Message ID {message.id}: {e}")
                    break

    print("------------------------------------------")
    print(f"Total Scanned: {scanned_count} | Total Updated: {updated_count}")
    print("[✓] Process complete!")

if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())
