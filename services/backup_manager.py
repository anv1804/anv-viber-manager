"""
services/backup_manager.py
BackupManager — handles real-time mtime calculations, encryption, Telegram upload,
and deletes older backup messages using a local caching system.
"""
import os
import time
import json
import threading

from utils.profile import get_viber_pc_dir, pack_profile_to_zip
from utils.crypto import get_profile_key, encrypt_file
import services.supabase as db
import services.telegram as tg

class BackupManager:
    def __init__(self, script_dir: str, profiles_dir: str, user_id: str, username: str):
        self.script_dir = script_dir
        self.profiles_dir = profiles_dir
        self.user_id = user_id
        self.username = username

        # Cache variables
        self.upload_mtimes = {}      # profile_name -> mtime at last upload
        self.upload_timestamps = {}  # profile_name -> time of last upload
        self.uploading_profiles = set()
        self.cooldown_seconds = 300  # 5 minutes

    def get_dir_mtime(self, dirpath: str) -> float:
        """Return the latest modification time across all files in *dirpath*."""
        latest = 0.0
        try:
            for root, _dirs, files in os.walk(dirpath):
                for f in files:
                    try:
                        mt = os.path.getmtime(os.path.join(root, f))
                        if mt > latest:
                            latest = mt
                    except OSError:
                        pass
        except Exception:
            pass
        return latest

    def auto_upload_profile(self, name: str, viber_pc_dir: str, mtime: float, headers: dict):
        """Pack, encrypt, upload; delete previous Telegram message if exists, then update DB."""
        self.uploading_profiles.add(name)
        zip_path = os.path.join(self.script_dir, f"{name}_autobackup.zip")
        try:
            # 1. Fetch current profile record to get existing message_id to delete
            existing_msg_id = None
            try:
                db_profiles = db.get_client_profiles(self.user_id, headers)
                for p in db_profiles:
                    if p["profile_name"] == name:
                        comp_val = p.get("telegram_file_id")
                        if comp_val and "|" in comp_val:
                            _, msg_id_str = comp_val.split("|", 1)
                            if msg_id_str.isdigit():
                                existing_msg_id = int(msg_id_str)
                        break
            except Exception:
                pass

            # Fallback to local cache
            cache_file = os.path.join(self.script_dir, ".backup_history.json")
            cache_data = {}
            if os.path.exists(cache_file):
                try:
                    with open(cache_file) as f:
                        cache_data = json.load(f)
                except Exception:
                    pass

            if not existing_msg_id:
                existing_msg_id = cache_data.get(f"{self.user_id}_{name}")

            # 2. Pack and encrypt
            pack_profile_to_zip(viber_pc_dir, zip_path)
            key = get_profile_key(self.user_id, name)
            encrypt_file(zip_path, key)

            # 3. Upload new backup
            file_id, message_id = tg.upload_file(
                zip_path,
                caption=f"AutoBackup: {self.username}/{name}",
                filename=f"{name}.viberprofile",
            )
            os.remove(zip_path)

            # 4. Save combined format: "file_id|message_id" to the only available column
            composite_value = f"{file_id}|{message_id}"
            try:
                db.update_profile_file_id(self.user_id, name, composite_value, headers)
            except Exception:
                pass  # Ignore RLS block for admins

            # Write to local cache
            cache_data[f"{self.user_id}_{name}"] = message_id
            try:
                with open(cache_file, "w") as f:
                    json.dump(cache_data, f)
            except Exception:
                pass

            self.upload_mtimes[name] = mtime
            self.upload_timestamps[name] = time.time()

            # 5. Delete previous backup message to avoid spamming Telegram chat
            if existing_msg_id:
                threading.Thread(
                    target=lambda: tg.delete_message(existing_msg_id),
                    daemon=True
                ).start()

        except Exception:
            if os.path.exists(zip_path):
                try:
                    os.remove(zip_path)
                except Exception:
                    pass
        finally:
            self.uploading_profiles.discard(name)
