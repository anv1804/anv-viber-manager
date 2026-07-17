"""
services/telegram.py
Telegram Bot API helpers for uploading and downloading profile zip files.
"""
import os
import requests

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


def upload_file(zip_path: str, caption: str, filename: str) -> tuple[str, int]:
    """
    Upload *zip_path* to the configured Telegram chat as a document.

    Returns ``(file_id, message_id)`` of the uploaded document.
    Raises RuntimeError on failure.
    """
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
    with open(zip_path, "rb") as f:
        files = {"document": (filename, f)}
        data = {"chat_id": TELEGRAM_CHAT_ID, "caption": caption}
        resp = requests.post(url, data=data, files=files, timeout=60)

    if resp.status_code != 200:
        raise RuntimeError(f"Telegram upload failed: {resp.text}")

    result = resp.json()["result"]
    return result["document"]["file_id"], result["message_id"]


def delete_message(message_id: int) -> None:
    """
    Delete a Telegram message by its *message_id* (silently ignores errors
    such as message already deleted or too old to delete).
    """
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/deleteMessage"
    try:
        requests.post(
            url,
            json={"chat_id": TELEGRAM_CHAT_ID, "message_id": message_id},
            timeout=10,
        )
    except Exception:
        pass  # Non-critical: old message stays but new one is still uploaded


def download_file(file_id: str, dest_path: str) -> None:
    """
    Download a previously uploaded file (identified by *file_id*) and save it
    to *dest_path*.

    Raises RuntimeError if the Telegram API call fails.
    """
    # Step 1: resolve file path
    get_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile?file_id={file_id}"
    info_resp = requests.get(get_url, timeout=20)
    if info_resp.status_code != 200:
        raise RuntimeError(f"Telegram getFile failed: {info_resp.text}")

    tg_path = info_resp.json()["result"]["file_path"]
    download_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{tg_path}"

    # Step 2: stream download
    with requests.get(download_url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
