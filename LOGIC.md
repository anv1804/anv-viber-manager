# ANV Viber Manager — Logic & Architecture Document

> Tài liệu này mô tả toàn bộ luồng hoạt động, kiến trúc, và logic của ứng dụng **ANV Viber Manager** trước khi viết lại.

---

## 1. Mục Đích Chính

**ANV Viber Manager** là công cụ cho phép chạy **nhiều tài khoản Viber cùng lúc** trên một máy Linux/Windows bằng cách tạo ra các **profile độc lập** (nhân bản Viber).

Mỗi profile có thư mục `data/Home` và `data/Tmp` riêng biệt → Viber được khởi động với biến môi trường `HOME` và `TMPDIR` trỏ vào từng profile → mỗi instance Viber hoàn toàn tách biệt nhau.

---

## 2. Cấu Trúc Thư Mục

```
clone-viber/
├── main.py                    # Entry point
├── config.py                  # Cấu hình: Supabase URL/Key, Telegram Bot Token/Chat ID, màu sắc theme
├── session.json               # Lưu session đăng nhập (username, password hash, remember)
├── .backup_history.json       # Cache local: lưu message_id Telegram của backup gần nhất mỗi profile
├── gui/
│   ├── login_window.py        # Cửa sổ đăng nhập
│   ├── main_window.py         # Cửa sổ chính quản lý profile
│   ├── main_window_ui.py      # Build UI layout (tách riêng khỏi logic)
│   └── icons.py               # Icon helper (PIL ImageTk)
├── services/
│   ├── supabase.py            # Wrapper REST API Supabase (không dùng SDK)
│   ├── telegram.py            # Upload/download/delete file qua Telegram Bot API
│   └── backup_manager.py      # Quản lý auto-backup: detect thay đổi, nén, mã hóa, tải lên Telegram
├── utils/
│   ├── profile.py             # Detect Viber path, đọc số điện thoại, pack/unpack ZIP profile
│   ├── crypto.py              # AES-128 encrypt/decrypt file ZIP
│   └── hwid.py                # Tính HWID (Hardware ID) của máy
└── viber_profiles/
    └── {username}/
        └── {profile_name}/
            └── data/
                ├── Home/      # Thư mục HOME riêng của Viber instance này (Linux)
                │   └── .ViberPC/{phone_number}/  # Dữ liệu Viber thực: viber.db, Backgrounds, ...
                └── Tmp/       # Thư mục TMP riêng của Viber instance này
```

---

## 3. Database Supabase

### Bảng `users`
| Cột | Kiểu | Mô tả |
|-----|------|--------|
| id | uuid | Primary key |
| username | text | Tên đăng nhập |
| password_hash | text | SHA-256 hash mật khẩu |
| role | text | `admin` hoặc `user` |
| status | text | `active` hoặc `blocked` |
| created_at | timestamp | Ngày tạo |

> Lưu ý: Bảng hiện tại **không có** cột `hwid` và `expires_at`. Cần thêm nếu muốn dùng HWID lock và license expiry.

### Bảng `client_profiles`
| Cột | Kiểu | Mô tả |
|-----|------|--------|
| user_id | uuid | FK → users.id |
| profile_name | text | Tên profile (tên thư mục) |
| phone_number | text | Số điện thoại đã đăng nhập |
| status | text | `running` hoặc `idle` |
| updated_at | timestamp | Lần cập nhật cuối |
| telegram_file_id | text | Composite: `"{file_id}\|{message_id}"` — link backup trên Telegram |

### Bảng `remote_commands`
| Cột | Kiểu | Mô tả |
|-----|------|--------|
| id | uuid | Primary key |
| user_id | uuid | FK → users.id |
| profile_name | text | Profile liên quan |
| command | text | `UPLOAD_PROFILE` hoặc `DOWNLOAD_PROFILE` |
| status | text | `pending` → `processing` → `completed`/`failed` |
| telegram_file_id | text | File ID khi command hoàn thành |
| created_at | timestamp | Thời gian tạo |

---

## 4. Luồng Đăng Nhập

```
[User nhập username + password]
        ↓
[SHA-256 hash password]
        ↓
[GET /rest/v1/users?username=eq.{username}]
        ↓
[Kiểm tra: user tồn tại? → password_hash khớp? → status != blocked? → chưa hết hạn?]
        ↓
[Nếu HWID column tồn tại: bind HWID lần đầu / kiểm tra thiết bị cũ]
        ↓
[Login thành công → mở MainWindow với (user_id, username, expires_info, role)]
```

---

## 5. Luồng Nhân Bản Viber (Chạy Profile)

### 5.1 Tạo Profile
```
[Nhập tên profile]
        ↓
[Tạo thư mục: viber_profiles/{username}/{profile_name}/data/Home/]
        ↓
[Sync danh sách lên Supabase (client_profiles)]
```

### 5.2 Khởi động Profile (Launch)
```
[Chọn profile → bấm Play]
        ↓
[Tạo: viber_profiles/{username}/{profile_name}/data/Home/ và /Tmp/]
        ↓
[Set biến môi trường:
    HOME  = .../data/Home
    TMPDIR = .../data/Tmp
    TMP   = .../data/Tmp]
        ↓
[subprocess.Popen(viber_path, env=custom_env)]
        → Mỗi Viber instance dùng HOME/Tmp riêng → hoàn toàn tách biệt
        ↓
[Theo dõi PID qua /proc/{pid}/environ → HOME matching]
```

### 5.3 Dừng Profile
```
[Đọc /proc/{pid}/environ]
        ↓
[Tìm tất cả PID có HOME = profile_home_dir]
        ↓
[kill -9 {pid}]
```

---

## 6. Luồng Đồng Bộ Dữ Liệu (Sync)

### 6.1 Background Sync Loop (chạy ngầm mỗi 15 giây)
```
while True:
    1. Kiểm tra remote_commands pending
       → Nếu có UPLOAD_PROFILE: nén + mã hóa + tải lên Telegram → cập nhật DB
       → Nếu có DOWNLOAD_PROFILE: tải về Telegram → giải mã → giải nén vào profile
    2. Đọc danh sách profile local
    3. Sync danh sách lên Supabase (client_profiles)
    4. Ngủ 15 giây
```

### 6.2 Sync All (thủ công — bấm nút Sync All)

**Mục đích**: Đồng bộ dữ liệu Viber thực tế (database, tin nhắn) từ máy này sang máy khác.

```
[Bấm Sync All]
        ↓
[GET client_profiles của user → lấy danh sách profile_name]
        ↓
[Với mỗi profile_name:]
    [POST remote_commands: {command: "UPLOAD_PROFILE", profile_name, status: "pending"}]
        ↓
    [Máy có dữ liệu nhận lệnh → nén .ViberPC/ → mã hóa AES-128 → tải lên Telegram]
    [Cập nhật command status = "completed", lưu telegram_file_id]
        ↓
    [Poll command mỗi 2 giây, timeout 90 giây]
        ↓
    [Khi có file_id: tải file về từ Telegram → giải mã → giải nén vào profile local]
        ↓
    [Xóa command khỏi DB]
        ↓
[Reload UI]
```

---

## 7. Luồng Backup / Restore Qua Telegram

### Upload (UPLOAD_PROFILE)
```
viber_profiles/{username}/{name}/data/Home/.ViberPC/
        ↓
[pack_profile_to_zip(viber_pc_dir, zip_path)]   → ZIP toàn bộ .ViberPC/
        ↓
[encrypt_file(zip_path, key)]                    → AES-128 encrypt
  key = SHA-256(user_id + profile_name)
        ↓
[tg.upload_file(zip_path, caption, filename)]   → Telegram Bot sendDocument
        ↓
Returns: (file_id, message_id)
        ↓
[Lưu vào client_profiles.telegram_file_id = "{file_id}|{message_id}"]
        ↓
[Xóa message Telegram cũ (nếu có) để tránh spam chat]
```

### Download (DOWNLOAD_PROFILE)
```
[Lấy telegram_file_id từ command hoặc DB]
        ↓
[tg.download_file(file_id, dest_path)]          → Telegram Bot getFile + download
        ↓
[decrypt_file(dest_path, key)]                  → AES-128 decrypt
        ↓
[unpack_profile_zip(zip_path, profile_path)]    → Giải nén vào:
    Linux:   .../data/Home/.ViberPC/
    Windows: .../data/Roaming/ViberPC/
        ↓
[Reload UI + sync danh sách lên Supabase]
```

---

## 8. Mã Hóa (Crypto)

- Thuật toán: **AES-128-CBC**
- Key: `SHA-256(user_id + profile_name)[:16]` bytes
- IV: 16 bytes đầu của file mã hóa
- File mã hóa: `[16 bytes IV][AES ciphertext]`

---

## 9. Cấu Hình (config.py)

```python
SUPABASE_URL       = "https://hqbsupczeujqgrkvrdjx.supabase.co"
SUPABASE_KEY       = "sb_publishable_..."
TELEGRAM_BOT_TOKEN = "8590170680:AAF..."
TELEGRAM_CHAT_ID   = "7962221453"
```

---

## 10. Phát Hiện Số Điện Thoại

Đọc từ thư mục `.ViberPC/`:
- Duyệt các thư mục con
- Tìm thư mục có tên là **chuỗi số** (VD: `84366278942`)
- Kiểm tra các marker file: `Backgrounds/`, `Temporary/`, `viber.db`, `QmlUrlCache/`
- Nếu khớp → đó là số ĐT: format lại thành `+84366278942`

---

## 11. Phát Hiện Viber Path (Linux)

Thứ tự ưu tiên:
1. `~/Downloads/viber.AppImage`
2. `~/Downloads/Viber.AppImage`
3. `/usr/bin/viber`
4. `/opt/viber/Viber`
5. `/snap/bin/viber`
6. `which viber`

---

## 12. Quản Lý Tiến Trình

- Theo dõi PID qua `/proc/{pid}/environ`
- Lọc bằng `HOME=` environment variable khớp với `profile_path/data/Home`
- Background check mỗi 1000ms để cập nhật trạng thái Running/Idle trên UI

---

## 13. Export / Import Profile

### Export
- Nén thư mục `.ViberPC/` thành file `.viberprofile` (không mã hóa khi export thủ công)
- Cho phép lưu ra đường dẫn tùy chọn

### Import
- Giải nén file `.viberprofile` vào thư mục profile mới
- Reload UI

---

## 14. Admin Panel

- Chỉ hiển thị với `role = "admin"`
- Quản lý users: tạo, sửa, xóa, reset HWID, khóa tài khoản
- Xem danh sách client_profiles của từng user
- Gửi lệnh UPLOAD/DOWNLOAD từ xa đến client

---

## 15. Các Vấn Đề Đã Biết (Cần Fix Khi Viết Lại)

1. **Bảng `users` thiếu cột `hwid` và `expires_at`** → HWID binding không hoạt động
2. **Tài khoản `admin` dùng bcrypt**, code dùng SHA-256 → không đăng nhập được bằng `admin`
3. **Auto-backup đã bị tắt** → chỉ sync khi bấm nút Sync All
4. **`viber_profiles/` bị commit vào git** → đã fix bằng `.gitignore`
5. **Lỗi TclError** khi đóng cửa sổ progress → đã fix bằng `winfo_exists()`
