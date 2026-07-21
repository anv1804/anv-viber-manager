using System;
using System.IO;
using System.Linq;
using System.Collections.ObjectModel;
using System.Threading.Tasks;
using System.Windows.Input;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using AnvViberManager.Models;
using AnvViberManager.Utils;

namespace AnvViberManager.ViewModels
{
    public partial class MainWindowViewModel : ViewModelBase
    {
        private string _profilesDir;

        [ObservableProperty]
        private string? _viberPath;

        [ObservableProperty]
        private string _customProfilesDir = string.Empty;

        [ObservableProperty]
        private string _statusText = "Ready";

        [ObservableProperty]
        private string _titleText = "Profiles List (0)";


        // Filters
        [ObservableProperty]
        private string _filterName = string.Empty;

        [ObservableProperty]
        private string _filterPhone = string.Empty;

        [ObservableProperty]
        private string _filterStatus = "All Status";

        [ObservableProperty]
        private string _filterBusiness = "All Business";

        [ObservableProperty]
        private string _filterScanned = "All Scanned";

        private bool _isUpdatingSelection;

        [ObservableProperty]
        private bool? _isAllSelected = false;

        [ObservableProperty]
        private bool _hasSelection;

        [ObservableProperty]
        private string _appVersion = "v1.0.27";

        public ObservableCollection<string> StatusOptions { get; } = new() { "All Status", "Running", "Idle" };
        public ObservableCollection<string> BusinessOptions { get; } = new() { "All Business", "Business: Yes", "Business: No" };
        public ObservableCollection<string> ScannedOptions { get; } = new() { "All Scanned", "Scanned: Yes", "Scanned: No" };

        public ObservableCollection<ViberProfile> Profiles { get; } = new();
        private readonly ObservableCollection<ViberProfile> _allProfiles = new();

        // Callbacks from View to ViewModel for interactive dialogs
        public Func<string, Task<string?>>? AskNameCallback { get; set; }
        public Func<string, Task<string?>>? AskRenameCallback { get; set; }
        public Func<string, Task<(string? Name, bool IsBusiness, int Quantity)?>>? AskCreateProfileCallback { get; set; }
        public Func<string, bool, bool, Task<(string? Name, bool IsBusiness, bool IsScanned)?>>? AskEditProfileCallback { get; set; }
        public Func<Task<bool>>? ConfirmDeleteCallback { get; set; }
        public Func<string?, Task<string?>>? ExportCallback { get; set; }
        public Func<Task<string[]?>>? ImportCallback { get; set; }

        public ICommand CreateProfileCommand { get; }
        public ICommand LaunchSelectedCommand { get; }
        public ICommand StopSelectedCommand { get; }
        public ICommand DeleteSelectedCommand { get; }
        public ICommand ExportProfilesCommand { get; }
        public ICommand ImportProfilesCommand { get; }
        public ICommand BrowseViberCommand { get; }
        public ICommand AutoDetectViberCommand { get; }
        public ICommand ToggleSelectAllCommand { get; }
        public ICommand ClearFilterCommand { get; }
        public ICommand BrowseProfilesDirCommand { get; }

        public ICommand LaunchProfileCommand { get; }
        public ICommand RenameProfileCommand { get; }
        public ICommand DeleteProfileCommand { get; }
        public ICommand SyncNamesCommand { get; }

        private class AppSettings
        {
            public string ViberPath { get; set; } = string.Empty;
            public string CustomProfilesDir { get; set; } = string.Empty;
        }

        private static string SettingsFilePath => Path.Combine(AppContext.BaseDirectory, "settings.json");

        private void LoadSettings()
        {
            try
            {
                if (File.Exists(SettingsFilePath))
                {
                    var json = File.ReadAllText(SettingsFilePath);
                    var settings = System.Text.Json.JsonSerializer.Deserialize<AppSettings>(json);
                    if (settings != null)
                    {
                        ViberPath = settings.ViberPath;
                        CustomProfilesDir = settings.CustomProfilesDir;
                    }
                }
            }
            catch { }
        }

        private void SaveSettings()
        {
            try
            {
                var settings = new AppSettings
                {
                    ViberPath = ViberPath ?? string.Empty,
                    CustomProfilesDir = CustomProfilesDir ?? string.Empty
                };
                var json = System.Text.Json.JsonSerializer.Serialize(settings, new System.Text.Json.JsonSerializerOptions { WriteIndented = true });
                File.WriteAllText(SettingsFilePath, json);
            }
            catch { }
        }

        public void ChangeProfilesDirectory(string newPath)
        {
            if (string.IsNullOrEmpty(newPath) || !Directory.Exists(newPath)) return;
            CustomProfilesDir = newPath;
            _profilesDir = newPath;
            SaveSettings();
            LoadProfiles();
            SetStatus($"Switched profiles data folder to: {newPath}");
        }

        public MainWindowViewModel()
        {
            // Tải cấu hình đã lưu
            LoadSettings();

            // Xác định thư mục lưu trữ profile:
            if (!string.IsNullOrEmpty(CustomProfilesDir) && Directory.Exists(CustomProfilesDir))
            {
                _profilesDir = CustomProfilesDir;
            }
            else
            {
                var currentDir = Directory.GetCurrentDirectory();
                var devProfilesPath = Path.Combine(currentDir, "viber_profiles");
                
                if (Directory.Exists(devProfilesPath))
                {
                    _profilesDir = devProfilesPath;
                }
                else
                {
                    _profilesDir = Path.Combine(AppContext.BaseDirectory, "viber_profiles");
                }
                CustomProfilesDir = _profilesDir;
            }
            
            Directory.CreateDirectory(_profilesDir);

            if (string.IsNullOrEmpty(ViberPath) || !File.Exists(ViberPath))
            {
                ViberPath = ProfileHelper.DetectViberPath();
            }

            CreateProfileCommand = new AsyncRelayCommand(CreateProfileAsync);
            LaunchSelectedCommand = new RelayCommand(LaunchSelected);
            StopSelectedCommand = new RelayCommand(StopSelected);
            DeleteSelectedCommand = new AsyncRelayCommand(DeleteSelectedAsync);
            ExportProfilesCommand = new AsyncRelayCommand(ExportProfilesAsync);
            ImportProfilesCommand = new AsyncRelayCommand(ImportProfilesAsync);
            BrowseViberCommand = new RelayCommand<string>(path => { 
                if (path != null) {
                    ViberPath = path; 
                    SaveSettings();
                }
            });
            BrowseProfilesDirCommand = new RelayCommand<string>(path => {
                if (path != null) ChangeProfilesDirectory(path);
            });
            AutoDetectViberCommand = new RelayCommand(() => {
                AutoDetectViber();
                SaveSettings();
            });
            ToggleSelectAllCommand = new RelayCommand<bool>(ToggleSelectAll);
            ClearFilterCommand = new RelayCommand(ClearFilter);

            LaunchProfileCommand = new RelayCommand<ViberProfile>(LaunchProfile);
            RenameProfileCommand = new AsyncRelayCommand<ViberProfile>(RenameProfileAsync);
            DeleteProfileCommand = new AsyncRelayCommand<ViberProfile>(DeleteProfileAsync);
            SyncNamesCommand = new RelayCommand(SyncNames);

            LoadProfiles();
            StartMonitoring();
        }

        public void SyncNames()
        {
            var activeProfiles = Profiles.ToList();
            if (!activeProfiles.Any()) return;

            // Dừng mọi profile đang chạy trước khi rename
            foreach (var p in activeProfiles)
            {
                if (p.Status == "Running")
                {
                    ProfileHelper.KillProfile(_profilesDir, p.Name);
                }
            }

            // Để tránh xung đột trùng tên thư mục trung gian khi đổi hàng loạt,
            // ta rename sang tên tạm thời kèm GUID trước
            var tempMappings = new System.Collections.Generic.List<(string oldPath, string tempPath, string finalName)>();
            for (int i = 0; i < activeProfiles.Count; i++)
            {
                var oldName = activeProfiles[i].Name;
                var finalName = $"Profile_{i + 1}";
                var oldPath = Path.Combine(_profilesDir, oldName);
                var tempPath = Path.Combine(_profilesDir, $"temp_sync_{Guid.NewGuid().ToString("N")}");
                
                if (Directory.Exists(oldPath))
                {
                    try
                    {
                        Directory.Move(oldPath, tempPath);
                        tempMappings.Add((oldPath, tempPath, finalName));
                    }
                    catch (Exception ex)
                    {
                        SetStatus($"Sync error at temp rename: {ex.Message}");
                        return;
                    }
                }
            }

            // Đổi từ tên tạm sang tên Profile_1, Profile_2... chính thức
            foreach (var map in tempMappings)
            {
                var finalPath = Path.Combine(_profilesDir, map.finalName);
                try
                {
                    if (Directory.Exists(finalPath))
                    {
                        Directory.Delete(finalPath, true);
                    }
                    Directory.Move(map.tempPath, finalPath);
                }
                catch (Exception ex)
                {
                    SetStatus($"Sync error at final rename: {ex.Message}");
                    return;
                }
            }

            LoadProfiles();
            SetStatus("Synchronized profile names sequentially!");
        }

        // ──────────────────────────────────────── Load & Filters ──────────────────

        public void LoadProfiles()
        {
            _allProfiles.Clear();
            if (Directory.Exists(_profilesDir))
            {
                var dirs = Directory.GetDirectories(_profilesDir).OrderBy(d => Directory.GetCreationTime(d));
                foreach (var dir in dirs)
                {
                    var rawName = Path.GetFileName(dir);
                    var name = ProfileHelper.SanitizeProfileName(_profilesDir, rawName);
                    var pids = ProfileHelper.GetRunningPids(_profilesDir, name);
                    var status = pids.Count > 0 ? "Running" : "Idle";
                    var phone = ProfileHelper.GetProfilePhone(_profilesDir, name);
                    var meta = ProfileHelper.LoadProfileMeta(Path.Combine(_profilesDir, name));

                    _allProfiles.Add(new ViberProfile
                    {
                        Name = name,
                        Phone = phone,
                        Status = status,
                        IsBusiness = meta.IsBusiness,
                        IsScanned = meta.IsScanned
                    });
                }
            }
            ApplyFilter();
        }

        public void ApplyFilter()
        {
            var selectedBefore = Profiles.Where(p => p.IsSelected).Select(p => p.Name).ToHashSet();
            
            // Unsubscribe existing profiles to prevent memory leaks
            foreach (var p in Profiles)
            {
                p.PropertyChanged -= OnProfilePropertyChanged;
            }
            Profiles.Clear();

            var fn = FilterName.Trim().ToLower();
            var fp = FilterPhone.Trim();
            var fs = FilterStatus;
            var fb = FilterBusiness;
            var fsc = FilterScanned;

            int idx = 1;
            foreach (var p in _allProfiles)
            {
                if (!string.IsNullOrEmpty(fn) && !p.Name.ToLower().Contains(fn)) continue;
                if (!string.IsNullOrEmpty(fp) && !p.Phone.Contains(fp)) continue;
                if (fs != "All Status" && p.Status != fs) continue;

                if (fb == "Business: Yes" && !p.IsBusiness) continue;
                if (fb == "Business: No" && p.IsBusiness) continue;

                if (fsc == "Scanned: Yes" && !p.IsScanned) continue;
                if (fsc == "Scanned: No" && p.IsScanned) continue;

                p.Index = idx++;
                p.IsSelected = selectedBefore.Contains(p.Name);
                
                // Subscribe to detect manual checkbox clicking
                p.PropertyChanged += OnProfilePropertyChanged;
                Profiles.Add(p);
            }

            TitleText = $"Profiles List ({_allProfiles.Count})";
            UpdateIsAllSelectedState();
        }

        private void ClearFilter()
        {
            FilterName = string.Empty;
            FilterPhone = string.Empty;
            FilterStatus = "All Status";
            FilterBusiness = "All Business";
            FilterScanned = "All Scanned";
            ApplyFilter();
        }

        partial void OnFilterNameChanged(string value) => ApplyFilter();
        partial void OnFilterPhoneChanged(string value) => ApplyFilter();
        partial void OnFilterStatusChanged(string value) => ApplyFilter();
        partial void OnFilterBusinessChanged(string value) => ApplyFilter();
        partial void OnFilterScannedChanged(string value) => ApplyFilter();

        partial void OnIsAllSelectedChanged(bool? value)
        {
            if (_isUpdatingSelection) return;
            _isUpdatingSelection = true;
            bool target = value ?? false;
            foreach (var p in Profiles)
            {
                p.IsSelected = target;
            }
            HasSelection = target && Profiles.Count > 0;
            _isUpdatingSelection = false;
        }

        private void OnProfilePropertyChanged(object? sender, System.ComponentModel.PropertyChangedEventArgs e)
        {
            if (e.PropertyName == nameof(ViberProfile.IsSelected))
            {
                UpdateIsAllSelectedState();
            }
        }

        private void UpdateIsAllSelectedState()
        {
            if (Profiles.Count == 0)
            {
                _isUpdatingSelection = true;
                IsAllSelected = false;
                HasSelection = false;
                _isUpdatingSelection = false;
                return;
            }

            if (_isUpdatingSelection) return;
            
            _isUpdatingSelection = true;
            var selectedCount = Profiles.Count(p => p.IsSelected);
            HasSelection = selectedCount > 0;

            if (selectedCount == 0)
            {
                IsAllSelected = false;
            }
            else if (selectedCount == Profiles.Count)
            {
                IsAllSelected = true;
            }
            else
            {
                IsAllSelected = null; // Indeterminate
            }
            _isUpdatingSelection = false;
        }

        private void ToggleSelectAll(bool isChecked)
        {
            IsAllSelected = isChecked;
        }

        // ──────────────────────────────────────── Actions ─────────────────────────

        public async Task CreateProfileAsync()
        {
            // Ép buộc đồng bộ tên theo số thứ tự của các profile hiện tại trước khi tạo mới để tránh trùng đè/sai lệch
            SyncNames();

            int nextNo = _allProfiles.Count + 1;
            string defaultName = "Profile";
            
            string baseName = defaultName;
            bool isBusiness = false;
            int quantity = 1;

            if (AskCreateProfileCallback != null)
            {
                var res = await AskCreateProfileCallback(defaultName);
                if (res == null || string.IsNullOrEmpty(res.Value.Name)) return;
                baseName = res.Value.Name;
                isBusiness = res.Value.IsBusiness;
                quantity = res.Value.Quantity;
            }
            else return;

            var safeBaseName = string.Concat(baseName.Select(c => char.IsLetterOrDigit(c) || c == '-' || c == '_' ? c : '_')).Trim('_');
            if (string.IsNullOrEmpty(safeBaseName)) safeBaseName = "Profile";

            int createdCount = 0;
            for (int i = 0; i < quantity; i++)
            {
                int currentNumber = nextNo + i;
                string finalName = $"{safeBaseName}_{currentNumber}";
                var dest = Path.Combine(_profilesDir, finalName);
                
                // Nếu trùng thư mục, tự động tăng chỉ số số thứ tự lên tiếp cho đến khi trống
                while (Directory.Exists(dest))
                {
                    currentNumber++;
                    finalName = $"{safeBaseName}_{currentNumber}";
                    dest = Path.Combine(_profilesDir, finalName);
                }

                try
                {
                    Directory.CreateDirectory(Path.Combine(dest, "data", "Home"));
                    ProfileHelper.SaveProfileMeta(dest, new ProfileHelper.ProfileMeta(isBusiness, false));
                    createdCount++;
                }
                catch { }
            }

            LoadProfiles();
            SetStatus($"Created {createdCount} profile(s) successfully!");
        }

        public void LaunchSelected()
        {
            var selected = Profiles.Where(p => p.IsSelected).ToList();
            if (!selected.Any()) return;
            if (string.IsNullOrEmpty(ViberPath) || !File.Exists(ViberPath)) return;

            foreach (var p in selected)
            {
                ProfileHelper.LaunchProfile(ViberPath, _profilesDir, p.Name);
            }
            LoadProfiles();
        }

        public void StopSelected()
        {
            var selected = Profiles.Where(p => p.IsSelected).ToList();
            foreach (var p in selected)
            {
                ProfileHelper.KillProfile(_profilesDir, p.Name);
            }
            LoadProfiles();
        }

        public async Task DeleteSelectedAsync()
        {
            var selected = Profiles.Where(p => p.IsSelected).ToList();
            if (!selected.Any()) return;

            if (ConfirmDeleteCallback != null && await ConfirmDeleteCallback())
            {
                foreach (var p in selected)
                {
                    ProfileHelper.KillProfile(_profilesDir, p.Name);
                    try { Directory.Delete(Path.Combine(_profilesDir, p.Name), true); } catch { }
                }
                LoadProfiles();
                SetStatus("Deleted selected profiles.");
            }
        }

        public async Task ExportProfilesAsync()
        {
            if (ExportCallback == null) return;
            var selected = Profiles.Where(p => p.IsSelected).ToList();
            if (!selected.Any()) return;

            if (selected.Count == 1)
            {
                var name = selected[0].Name;
                var savePath = await ExportCallback(name);
                if (string.IsNullOrEmpty(savePath)) return;

                var profilePath = Path.Combine(_profilesDir, name);
                var vd = ProfileHelper.GetViberPcDir(profilePath);
                if (string.IsNullOrEmpty(vd) || !Directory.Exists(vd))
                {
                    SetStatus("Export failed: Profile has no session data.");
                    return;
                }

                ProfileHelper.PackProfile(profilePath, savePath);
                SetStatus($"Exported {name} successfully.");
            }
            else
            {
                // Export multiple profiles to folder
                var savePath = await ExportCallback(null);
                if (string.IsNullOrEmpty(savePath) || !Directory.Exists(savePath)) return;

                int ok = 0;
                foreach (var p in selected)
                {
                    var pDir = Path.Combine(_profilesDir, p.Name);
                    var vd = ProfileHelper.GetViberPcDir(pDir);
                    if (!string.IsNullOrEmpty(vd) && Directory.Exists(vd))
                    {
                        ProfileHelper.PackProfile(pDir, Path.Combine(savePath, $"{p.Name}.viberprofile"));
                        ok++;
                    }
                }
                SetStatus($"Exported {ok}/{selected.Count} profiles.");
            }
        }

        public async Task ImportProfilesAsync()
        {
            if (ImportCallback == null) return;
            var paths = await ImportCallback();
            if (paths == null || !paths.Any()) return;

            int ok = 0;
            foreach (var p in paths)
            {
                var baseName = StringExtensions.GetFileNameWithoutMatches(Path.GetFileName(p));
                var safeName = string.Concat(baseName.Where(c => char.IsLetterOrDigit(c) || c == '-' || c == '_' || c == ' ')).Trim();
                
                var dest = Path.Combine(_profilesDir, safeName);
                int count = 1;
                while (Directory.Exists(dest))
                {
                    dest = Path.Combine(_profilesDir, $"{safeName}_{count}");
                    count++;
                }

                try
                {
                    ProfileHelper.UnpackProfile(p, dest);
                    ok++;
                }
                catch { }
            }
            LoadProfiles();
            SetStatus($"Imported {ok} profile(s).");
        }

        public void AutoDetectViber()
        {
            var p = ProfileHelper.DetectViberPath();
            if (!string.IsNullOrEmpty(p))
            {
                ViberPath = p;
                SetStatus($"Auto-detected Viber executable at: {p}");
            }
            else
            {
                SetStatus("Could not auto-detect Viber. Please select file manually via Browse.");
            }
        }

        public void LaunchProfile(ViberProfile? p)
        {
            if (p == null) return;
            if (p.Status == "Running")
            {
                ProfileHelper.KillProfile(_profilesDir, p.Name);
                SetStatus($"Stopped profile {p.Name}.");
            }
            else
            {
                if (string.IsNullOrEmpty(ViberPath) || !File.Exists(ViberPath))
                {
                    SetStatus("Viber executable path not found.");
                    return;
                }
                ProfileHelper.LaunchProfile(ViberPath, _profilesDir, p.Name);
                SetStatus($"Launched profile {p.Name}.");
            }
            LoadProfiles();
        }

        public async Task RenameProfileAsync(ViberProfile? p)
        {
            if (p == null) return;
            string newName = p.Name;
            bool isBusiness = p.IsBusiness;
            bool isScanned = p.IsScanned;

            if (AskEditProfileCallback != null)
            {
                var res = await AskEditProfileCallback(p.Name, p.IsBusiness, p.IsScanned);
                if (res == null || string.IsNullOrEmpty(res.Value.Name)) return;
                newName = res.Value.Name;
                isBusiness = res.Value.IsBusiness;
                isScanned = res.Value.IsScanned;
            }
            else if (AskRenameCallback != null)
            {
                var input = await AskRenameCallback(p.Name);
                if (string.IsNullOrEmpty(input)) return;
                newName = input;
            }

            var safeName = string.Concat(newName.Select(c => char.IsLetterOrDigit(c) || c == '-' || c == '_' ? c : '_')).Trim('_');
            if (string.IsNullOrEmpty(safeName)) return;

            var oldPath = Path.Combine(_profilesDir, p.Name);
            var newPath = Path.Combine(_profilesDir, safeName);

            if (oldPath != newPath && Directory.Exists(oldPath) && !Directory.Exists(newPath))
            {
                try
                {
                    if (p.Status == "Running")
                    {
                        ProfileHelper.KillProfile(_profilesDir, p.Name);
                    }

                    Directory.Move(oldPath, newPath);
                }
                catch (Exception ex)
                {
                    SetStatus($"Rename failed: {ex.Message}");
                }
            }

            var targetPath = Directory.Exists(newPath) ? newPath : oldPath;
            ProfileHelper.SaveProfileMeta(targetPath, new ProfileHelper.ProfileMeta(isBusiness, isScanned));
            LoadProfiles();
        }

        public async Task DeleteProfileAsync(ViberProfile? p)
        {
            if (p == null) return;
            if (ConfirmDeleteCallback != null && await ConfirmDeleteCallback())
            {
                ProfileHelper.KillProfile(_profilesDir, p.Name);
                try
                {
                    Directory.Delete(Path.Combine(_profilesDir, p.Name), true);
                    SetStatus($"Deleted profile {p.Name}.");
                    LoadProfiles();
                }
                catch (Exception ex)
                {
                    SetStatus($"Delete failed: {ex.Message}");
                }
            }
        }

        // ──────────────────────────────────────── Monitoring ──────────────────────

        private void StartMonitoring()
        {
            Task.Run(async () =>
            {
                while (true)
                {
                    await Task.Delay(1500);
                    // Cập nhật trạng thái running
                    bool changed = false;
                    foreach (var p in _allProfiles)
                    {
                        var pids = ProfileHelper.GetRunningPids(_profilesDir, p.Name);
                        var isNowRunning = pids.Count > 0;
                        var wasRunning = p.Status == "Running";
                        if (isNowRunning != wasRunning)
                        {
                            p.Status = isNowRunning ? "Running" : "Idle";
                            changed = true;
                        }
                    }
                    if (changed)
                    {
                        Avalonia.Threading.Dispatcher.UIThread.Post(ApplyFilter);
                    }
                }
            });
        }

        private void SetStatus(string msg)
        {
            StatusText = msg;
            Task.Delay(2500).ContinueWith(_ => StatusText = "Ready");
        }
    }

    public static class StringExtensions
    {
        public static string GetFileNameWithoutMatches(string filename)
        {
            var idx = filename.LastIndexOf('.');
            return idx > 0 ? filename.Substring(0, idx) : filename;
        }
    }
}
