using System;
using System.IO;
using System.IO.Compression;
using System.Diagnostics;
using System.Collections.Generic;
using System.Linq;
using Microsoft.Data.Sqlite;

namespace AnvViberManager.Utils
{
    public static class ProfileHelper
    {
        public static string? DetectViberPath()
        {
            if (OperatingSystem.IsWindows())
            {
                // Mặc định Viber trên Windows thường cài trong AppData\Local
                var local = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
                var path = Path.Combine(local, "Viber", "Viber.exe");
                if (File.Exists(path)) return path;

                // Thử tìm trong Registry
                try
                {
                    using var key = Microsoft.Win32.Registry.CurrentUser.OpenSubKey(@"Software\Viber\Viber");
                    var val = key?.GetValue("InstallPath") as string;
                    if (!string.IsNullOrEmpty(val) && File.Exists(val)) return val;
                }
                catch { }
            }
            else // Linux
            {
                var home = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
                var searchLocations = new List<string>
                {
                    Path.Combine(home, "Downloads", "viber.AppImage"),
                    Path.Combine(home, "Downloads", "Viber.AppImage"),
                    Path.Combine(home, "Desktop", "viber.AppImage"),
                    Path.Combine(home, "Desktop", "Viber.AppImage"),
                    Path.Combine(home, "Applications", "viber.AppImage"),
                    Path.Combine(home, "Applications", "Viber.AppImage"),
                    Path.Combine(Directory.GetCurrentDirectory(), "viber.AppImage"),
                    "/usr/bin/viber",
                    "/usr/local/bin/viber",
                    "/opt/viber/viber",
                    "/snap/bin/viber"
                };

                foreach (var p in searchLocations)
                {
                    if (File.Exists(p)) return p;
                }

                // Tìm kiếm linh hoạt tất cả các file AppImage có chứa 'viber' trong Downloads hoặc Desktop
                try
                {
                    var downloadsDir = Path.Combine(home, "Downloads");
                    if (Directory.Exists(downloadsDir))
                    {
                        var files = Directory.GetFiles(downloadsDir, "*viber*.AppImage", SearchOption.TopDirectoryOnly);
                        if (files.Length > 0) return files[0];
                    }
                }
                catch { }
            }
            return null;
        }

        public static string GetProfilePhone(string profilesDir, string profileName)
        {
            var profilePath = Path.Combine(profilesDir, profileName);
            EnsureStandardProfileStructure(profilePath);

            // Cách 1: Đọc từ config.db (nơi lưu Session Accounts chính xác nhất của Viber)
            var configDb = Path.Combine(profilePath, "data", "Home", ".ViberPC", "config.db");
            if (File.Exists(configDb))
            {
                try
                {
                    using var conn = new SqliteConnection($"Data Source={configDb};Mode=ReadOnly");
                    conn.Open();
                    using var cmd = conn.CreateCommand();
                    cmd.CommandText = "SELECT PhoneNo FROM Accounts LIMIT 1;";
                    var res = cmd.ExecuteScalar();
                    if (res != null && !string.IsNullOrEmpty(res.ToString()))
                    {
                        var p = res.ToString()!;
                        if (p.StartsWith("84") && p.Length > 9) return "0" + p.Substring(2);
                        if (p.StartsWith("+84") && p.Length > 10) return "0" + p.Substring(3);
                        return p;
                    }
                }
                catch { }
            }

            var dbPath = GetViberDbPath(profilePath);
            if (string.IsNullOrEmpty(dbPath) || !File.Exists(dbPath)) return "—";

            string phone = "—";
            try
            {
                // Cách 2: Tên thư mục cha của viber.db (Ví dụ: .ViberPC/84912345678/viber.db)
                var parentDir = Path.GetFileName(Path.GetDirectoryName(dbPath));
                if (!string.IsNullOrEmpty(parentDir) && System.Text.RegularExpressions.Regex.IsMatch(parentDir, @"^\+?\d{8,15}$"))
                {
                    phone = parentDir;
                }
            }
            catch { }

            if (phone.StartsWith("84") && phone.Length > 9) return "0" + phone.Substring(2);
            if (phone.StartsWith("+84") && phone.Length > 10) return "0" + phone.Substring(3);

            return phone;
        }

        public static void EnsureStandardProfileStructure(string profilePath)
        {
            try
            {
                var home = Path.Combine(profilePath, "data", "Home");
                var viberPc = Path.Combine(home, ".ViberPC");
                var config = Path.Combine(home, ".config", "viber");
                var local = Path.Combine(home, ".local", "share");
                var tmp = Path.Combine(profilePath, "data", "Tmp");

                Directory.CreateDirectory(viberPc);
                Directory.CreateDirectory(config);
                Directory.CreateDirectory(local);
                Directory.CreateDirectory(tmp);
            }
            catch { }
        }

        public static string? GetViberDbPath(string profilePath)
        {
            var dataDir = Path.Combine(profilePath, "data");
            if (!Directory.Exists(dataDir)) return null;

            try
            {
                // Chỉ quét trong Home hoặc Roaming, tránh tuyệt đối thư mục Tmp có thể kẹt FUSE mount point AppImage
                var targetDir = Path.Combine(dataDir, "Home");
                if (OperatingSystem.IsWindows())
                {
                    targetDir = Path.Combine(dataDir, "Roaming");
                }

                if (!Directory.Exists(targetDir)) return null;

                var dbFiles = Directory.GetFiles(targetDir, "viber.db", SearchOption.AllDirectories);
                foreach (var f in dbFiles)
                {
                    if (f.Contains(".ViberPC") || f.Contains("ViberPC"))
                    {
                        return f;
                    }
                }
                return dbFiles.Length > 0 ? dbFiles[0] : null;
            }
            catch
            {
                return null;
            }
        }

        public static string? GetViberPcDir(string profilePath)
        {
            var dbPath = GetViberDbPath(profilePath);
            return dbPath != null ? Path.GetDirectoryName(dbPath) : null;
        }

        public static void PackProfile(string sourceDir, string zipPath)
        {
            if (File.Exists(zipPath)) File.Delete(zipPath);

            var viberPcSrc = Path.Combine(sourceDir, "data", "Home", ".ViberPC");
            if (!Directory.Exists(viberPcSrc))
                throw new DirectoryNotFoundException($"ViberPC dir not found: {viberPcSrc}");

            // Copy sang thư mục tạm để không đụng vào profile gốc
            var tempDir = Path.Combine(Path.GetTempPath(), "viber_pack_" + Guid.NewGuid().ToString("N"));
            try
            {
                CopyDirectorySafe(viberPcSrc, tempDir);

                // Nén tất cả content của .ViberPC/ vào zip, đường dẫn relative từ .ViberPC/
                // Đây là format chuẩn: config.db, SĐT/ ở root zip
                using var zf = new System.IO.Compression.ZipArchive(
                    File.OpenWrite(zipPath), ZipArchiveMode.Create, false);

                foreach (var file in Directory.EnumerateFiles(tempDir, "*", SearchOption.AllDirectories))
                {
                    var rel = Path.GetRelativePath(tempDir, file).Replace(Path.DirectorySeparatorChar, '/');
                    try
                    {
                        var entry = zf.CreateEntry(rel, CompressionLevel.Fastest);
                        using var src  = File.OpenRead(file);
                        using var dst  = entry.Open();
                        src.CopyTo(dst);
                    }
                    catch { /* bỏ qua file không đọc được */ }
                }
            }
            finally
            {
                try { Directory.Delete(tempDir, true); } catch { }
            }
        }

        // Copy an toàn, bỏ qua Tmp và .mount_viber (AppImage FUSE mount)
        private static void CopyDirectorySafe(string src, string dst)
        {
            Directory.CreateDirectory(dst);
            foreach (var file in Directory.GetFiles(src))
            {
                try { File.Copy(file, Path.Combine(dst, Path.GetFileName(file)), overwrite: true); } catch { }
            }
            foreach (var dir in Directory.GetDirectories(src))
            {
                var dname = Path.GetFileName(dir);
                if (dname.Equals("Tmp", StringComparison.OrdinalIgnoreCase)) continue;
                if (dname.StartsWith(".mount_viber", StringComparison.OrdinalIgnoreCase)) continue;
                try { CopyDirectorySafe(dir, Path.Combine(dst, dname)); } catch { }
            }
        }

        // Checkpoint WAL để flush dữ liệu vào file .db chính
        private static void CheckpointAllDatabases(string dir)
        {
            if (!Directory.Exists(dir)) return;
            foreach (var dbFile in Directory.GetFiles(dir, "*.db", SearchOption.AllDirectories))
            {
                try
                {
                    using var conn = new SqliteConnection($"Data Source={dbFile}");
                    conn.Open();
                    using var cmd = conn.CreateCommand();
                    cmd.CommandText = "PRAGMA wal_checkpoint(TRUNCATE);";
                    cmd.ExecuteNonQuery();
                }
                catch { }
            }
        }

        // Checkpoint một file .db cụ thể, trả về true nếu thành công
        private static bool CheckpointDatabase(string dbFile)
        {
            if (!File.Exists(dbFile)) return false;
            try
            {
                using var conn = new SqliteConnection($"Data Source={dbFile}");
                conn.Open();
                using var cmd = conn.CreateCommand();
                cmd.CommandText = "PRAGMA integrity_check(1);";
                var result = cmd.ExecuteScalar()?.ToString();
                if (result != "ok") return false;
                cmd.CommandText = "PRAGMA wal_checkpoint(TRUNCATE);";
                cmd.ExecuteNonQuery();
                return true;
            }
            catch { return false; }
        }

        public static void UnpackProfile(string zipPath, string destDir)
        {
            if (Directory.Exists(destDir)) Directory.Delete(destDir, true);

            var viberPcDst = Path.Combine(destDir, "data", "Home", ".ViberPC");
            EnsureStandardProfileStructure(destDir);

            // Giải nén thẳng vào .ViberPC/ — đây là chuẩn của file .viberprofile
            // Vì khi pack ta đã nén relative từ .ViberPC/, giải nén vào .ViberPC/ là đúng vị trí
            using var zip = ZipFile.OpenRead(zipPath);
            foreach (var entry in zip.Entries)
            {
                if (string.IsNullOrEmpty(entry.Name)) continue; // bỏ qua directory entries
                var destPath = Path.Combine(viberPcDst, entry.FullName.Replace('/', Path.DirectorySeparatorChar));
                Directory.CreateDirectory(Path.GetDirectoryName(destPath)!);
                try { entry.ExtractToFile(destPath, overwrite: true); } catch { }
            }
        }

        public static void NormalizeImportedProfile(string destDir)
        {
            // Không cần normalize nữa — UnpackProfile đã đặt file đúng vị trí
            EnsureStandardProfileStructure(destDir);
        }

        public static List<int> GetRunningPids(string profilesDir, string name)
        {
            var pids = new List<int>();
            var homeDir = Path.GetFullPath(Path.Combine(profilesDir, name, "data", "Home"));

            if (OperatingSystem.IsWindows())
            {
                // Trên Windows kiểm tra các tiến trình Viber.exe có cùng môi trường hoặc đơn giản
                var procs = Process.GetProcessesByName("Viber");
                foreach (var p in procs)
                {
                    try { pids.Add(p.Id); } catch { }
                }
            }
            else // Linux
            {
                if (!Directory.Exists("/proc")) return pids;
                
                foreach (var pidDir in Directory.GetDirectories("/proc"))
                {
                    var baseName = Path.GetFileName(pidDir);
                    if (!int.TryParse(baseName, out int pid)) continue;

                    try
                    {
                        var cmdline = File.ReadAllText(Path.Combine(pidDir, "cmdline")).ToLower();
                        if (!cmdline.Contains("viber")) continue;

                        var environ = File.ReadAllText(Path.Combine(pidDir, "environ"));
                        foreach (var var in environ.Split('\0'))
                        {
                            if (var.StartsWith("HOME=") && Path.GetFullPath(var.Substring(5)) == homeDir)
                            {
                                pids.Add(pid);
                                break;
                            }
                        }
                    }
                    catch { }
                }
            }
            return pids;
        }

        public static string SanitizeProfileName(string profilesDir, string name)
        {
            if (!name.Contains(' ')) return name;
            var safeName = name.Replace(' ', '_');
            var oldPath = Path.Combine(profilesDir, name);
            var newPath = Path.Combine(profilesDir, safeName);
            try
            {
                if (Directory.Exists(oldPath) && !Directory.Exists(newPath))
                {
                    Directory.Move(oldPath, newPath);
                    return safeName;
                }
                if (Directory.Exists(newPath)) return safeName;
            }
            catch { }
            return name;
        }

        public static void LaunchProfile(string viberPath, string profilesDir, string name)
        {
            var actualName = SanitizeProfileName(profilesDir, name);
            var home = Path.Combine(profilesDir, actualName, "data", "Home");
            var tmp = Path.Combine(profilesDir, actualName, "data", "Tmp");
            Directory.CreateDirectory(home);
            Directory.CreateDirectory(tmp);

            var startInfo = new ProcessStartInfo
            {
                FileName = viberPath,
                UseShellExecute = false,
                CreateNoWindow = true
            };

            // Cô lập môi trường
            startInfo.EnvironmentVariables["HOME"] = home;
            startInfo.EnvironmentVariables["TMPDIR"] = tmp;
            startInfo.EnvironmentVariables["TMP"] = tmp;
            startInfo.EnvironmentVariables["TEMP"] = tmp;
            startInfo.EnvironmentVariables["XDG_CONFIG_HOME"] = Path.Combine(home, ".config");
            startInfo.EnvironmentVariables["XDG_DATA_HOME"] = Path.Combine(home, ".local", "share");
            
            if (OperatingSystem.IsWindows())
            {
                startInfo.EnvironmentVariables["USERPROFILE"] = home;
                startInfo.EnvironmentVariables["APPDATA"] = Path.Combine(profilesDir, name, "data", "Roaming");
                startInfo.EnvironmentVariables["LOCALAPPDATA"] = Path.Combine(profilesDir, name, "data", "Local");
            }
            else
            {
                // Linux: AppImage
                if (viberPath.EndsWith(".AppImage", StringComparison.OrdinalIgnoreCase))
                {
                    startInfo.FileName = viberPath;
                }
            }

            Process.Start(startInfo);
        }

        public static void KillProfile(string profilesDir, string name)
        {
            var pids = GetRunningPids(profilesDir, name);
            foreach (var pid in pids)
            {
                try
                {
                    var p = Process.GetProcessById(pid);
                    p.Kill();
                }
                catch { }
            }
            
            // Xóa mount kẹt AppImage trên Linux
            if (!OperatingSystem.IsWindows())
            {
                var tmp = Path.Combine(profilesDir, name, "data", "Tmp");
                if (Directory.Exists(tmp))
                {
                    try
                    {
                        foreach (var item in Directory.GetDirectories(tmp))
                        {
                            if (Path.GetFileName(item).StartsWith(".mount_viber"))
                            {
                                using var p = Process.Start(new ProcessStartInfo
                                {
                                    FileName = "fusermount",
                                    Arguments = $"-u -z \"{item}\"",
                                    CreateNoWindow = true,
                                    UseShellExecute = false
                                });
                                p?.WaitForExit();
                            }
                        }
                    }
                    catch { }
                }
            }
        }

        public record ProfileMeta(bool IsBusiness = false, bool IsScanned = false);

        public static ProfileMeta LoadProfileMeta(string profilePath)
        {
            try
            {
                var jsonPath = Path.Combine(profilePath, "profile.json");
                if (File.Exists(jsonPath))
                {
                    var txt = File.ReadAllText(jsonPath);
                    var obj = System.Text.Json.JsonSerializer.Deserialize<ProfileMeta>(txt);
                    if (obj != null) return obj;
                }
            }
            catch { }
            return new ProfileMeta();
        }

        public static void SaveProfileMeta(string profilePath, ProfileMeta meta)
        {
            try
            {
                var jsonPath = Path.Combine(profilePath, "profile.json");
                var txt = System.Text.Json.JsonSerializer.Serialize(meta);
                File.WriteAllText(jsonPath, txt);
            }
            catch { }
        }
    }
}
