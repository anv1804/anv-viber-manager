# Tài liệu mô tả logic dự án - AnvViberManager

## 1. Giới thiệu dự án
`AnvViberManager` là một phần mềm quản lý đa tài khoản Viber (Multi-profile) được phát triển dựa trên nền tảng **C# / Avalonia UI (MVVM)**, hỗ trợ chạy song song đồng thời nhiều tài khoản Viber độc lập trên cùng một máy tính mà không bị xung đột hoặc ngắt kết nối.

---

## 2. Công nghệ sử dụng
* **Ngôn ngữ**: C# (.NET 8.0)
* **Giao diện**: Avalonia UI (XAML & MVVM CommunityToolkit)
* **Database cục bộ**: SQLite (`Microsoft.Data.Sqlite`) để đọc cấu hình định danh thiết bị của Viber.
* **Cấu hình app**: Định dạng JSON (`settings.json`).

---

## 3. Kiến trúc thư mục cấu trúc một Profile
Mỗi Profile Viber được cô lập hoàn toàn dữ liệu trong một thư mục riêng biệt nằm trong thư mục lưu trữ profile chung (mặc định là `viber_profiles`):
```text
[Profiles_Folder]/
  └── [Tên_Profile]/
      ├── profile.json            # File cấu hình phân loại profile (Business, Scanned...)
      └── data/
          ├── Home/
          │   └── .ViberPC/       # Nơi lưu dữ liệu Viber chính gốc (chứa config.db, avatars...)
          ├── Tmp/                # Thư mục tạm thời cô lập cho profile
          ├── Roaming/            # Thư mục Roaming Windows giả lập
          └── Local/              # Thư mục Local AppData Windows giả lập
```

---

## 4. Các Logic cốt lõi (Core Business Logics)

### 4.1. Khởi tạo & Cô lập môi trường (Environment Sandbox)
Để chạy các tài khoản song song không ảnh hưởng dữ liệu của nhau, ứng dụng can thiệp vào các biến môi trường hệ thống trước khi kích hoạt Viber:
* **Đối với Windows**:
  * Ép ghi đè đường dẫn môi trường hệ thống của Viber:
    * Gán `USERPROFILE` $\rightarrow$ `[Thư mục Profile]/data/Home`
    * Gán `APPDATA` $\rightarrow$ `[Thư mục Profile]/data/Roaming`
    * Gán `LOCALAPPDATA` $\rightarrow$ `[Thư mục Profile]/data/Local`
  * Gán các biến tạm thời `TMP`, `TEMP`, `TMPDIR` $\rightarrow$ `[Thư mục Profile]/data/Tmp`
* **Đối với Linux (dành cho môi trường Wine giả lập để test)**:
  * Thực hiện tự động ánh xạ thông qua `wine` và dịch các đường dẫn Linux sang ký tự ổ đĩa ảo Windows (ví dụ: `Z:\home\anv\viber_profiles\...`) tương thích 100% với Wine.

### 4.2. Chạy song song nhiều profile trùng số điện thoại (Device Virtualization)
Viber Server quản lý và đá kết nối (disconnect) nếu phát hiện cùng một tài khoản đăng nhập trên 2 thiết bị trùng mã định danh. Để khắc phục điều này:
1. **HOSTNAME & COMPUTERNAME Virtualization**: Can thiệp bằng cách gán tên thiết bị mạng ảo hóa riêng biệt cho mỗi tiến trình khi khởi chạy (ví dụ: `HOSTNAME = VIBER-PROFILE_1`).
2. **DeviceKey Manipulation**: Khi import/export hoặc chuyển đổi máy, hệ thống tự động kiểm tra và bảo toàn thuộc tính `DeviceKey` trong database `config.db` của Viber, đánh lừa máy chủ Viber nhận diện đây là các thiết bị phụ (Tablet/iPad) hợp lệ đang kết nối song song, giúp chạy nhiều cửa sổ cùng một số điện thoại không bị đá nhau.

### 4.3. Đóng gói & Nhập/Xuất Profile (Pack & Unpack Logic)
* **Xuất Profile (Export)**:
  * Thực hiện cơ chế **SQLite Checkpoint (Flush WAL)**: Ghi toàn bộ dữ liệu đang lưu tạm ở file ghi nhật ký `-wal` vào file database chính `config.db` để đảm bảo dữ liệu không bị hao hụt hoặc lỗi khi nén.
  * Sao chép thư mục `.ViberPC` ra một thư mục tạm (bỏ qua các thư mục FUSE mount tạm thời của AppImage để tránh lỗi phân quyền).
  * Nén ZIP tương thích tương đối (relative) trực tiếp từ thư mục gốc của `.ViberPC`. File nén lưu dưới đuôi `.viberprofile`.
* **Nhập Profile (Import)**:
  * Giải nén file `.viberprofile` trực tiếp vào thư mục đích `data/Home/.ViberPC/` của profile mới, đảm bảo tính nguyên bản của session Viber mà không làm mất cấu trúc thư mục.

### 4.4. Thay đổi thư mục lưu trữ tùy chỉnh (Custom Profiles Directory)
* Ứng dụng hỗ trợ thay đổi thư mục lưu trữ profile linh hoạt. 
* Cấu hình đường dẫn tuỳ chỉnh được lưu trữ vào file `settings.json` đặt cùng thư mục file chạy. Khi ứng dụng khởi động lại, nó sẽ tự động nạp cấu hình cũ mà người dùng không cần phải chọn lại.

---

## 5. Hướng dẫn đóng gói sản phẩm (.EXE Windows)
Sử dụng lệnh biên dịch single-file tự chứa môi trường chạy của .NET 8.0:
```bash
dotnet publish -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true -p:PublishReadyToRun=true -p:PublishTrimmed=false
```
* **Sản phẩm xuất ra**: File chạy duy nhất `AnvViberManager.exe` đặt trong thư mục `bin/Release/net8.0/win-x64/publish/`. Gửi duy nhất file này cho khách hàng chạy trên Windows.
