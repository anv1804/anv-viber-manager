using System;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using System.Windows.Input;
using Avalonia.Controls;
using Avalonia.Markup.Xaml;
using AnvViberManager.ViewModels;
using AnvViberManager.Models;

namespace AnvViberManager.Views
{
    public partial class MainWindow : Window
    {
        public MainWindow()
        {
            InitializeComponent();
            var vm = new MainWindowViewModel();
            DataContext = vm;
        }

        protected override void OnDataContextChanged(EventArgs e)
        {
            base.OnDataContextChanged(e);
            if (DataContext is MainWindowViewModel vm)
            {
                vm.AskCreateProfileCallback = async (defaultName) =>
                {
                    return await AskCreateProfileDialogAsync(defaultName);
                };

                vm.AskEditProfileCallback = async (oldName, isBusiness, isScanned) =>
                {
                    return await AskEditProfileDialogAsync(oldName, isBusiness, isScanned);
                };

                vm.ConfirmDeleteCallback = async () =>
                {
                    return await ConfirmDialogAsync("Confirm Delete", "Are you sure you want to delete selected profiles?");
                };

                vm.ExportCallback = async (defaultName) =>
                {
                    if (defaultName != null) // Export 1 profile
                    {
                        var dialog = new SaveFileDialog
                        {
                            Title = $"Export Profile '{defaultName}'",
                            InitialFileName = $"{defaultName}.viberprofile",
                            DefaultExtension = "viberprofile"
                        };
                        dialog.Filters.Add(new FileDialogFilter { Name = "Viber Profile", Extensions = { "viberprofile" } });
                        return await dialog.ShowAsync(this);
                    }
                    else // Export nhiều profile
                    {
                        var dialog = new OpenFolderDialog
                        {
                            Title = "Select Directory to Export Profiles"
                        };
                        return await dialog.ShowAsync(this);
                    }
                };

                vm.ImportCallback = async () =>
                {
                    var dialog = new OpenFileDialog
                    {
                        Title = "Import Profiles",
                        AllowMultiple = true
                    };
                    dialog.Filters.Add(new FileDialogFilter { Name = "Viber Profile", Extensions = { "viberprofile" } });
                    return await dialog.ShowAsync(this);
                };
            }
        }

        private void InitializeComponent()
        {
            AvaloniaXamlLoader.Load(this);
        }

        // ──────────────────────────────────────── Event Handlers ─────────────────

        private async void OnCreateProfileClick(object? sender, Avalonia.Interactivity.RoutedEventArgs e)
        {
            if (DataContext is MainWindowViewModel vm)
            {
                await vm.CreateProfileAsync();
            }
        }

        private void OnLaunchSelectedClick(object? sender, Avalonia.Interactivity.RoutedEventArgs e)
        {
            if (DataContext is MainWindowViewModel vm)
            {
                vm.LaunchSelected();
            }
        }

        private void OnStopSelectedClick(object? sender, Avalonia.Interactivity.RoutedEventArgs e)
        {
            if (DataContext is MainWindowViewModel vm)
            {
                vm.StopSelected();
            }
        }

        private async void OnExportProfilesClick(object? sender, Avalonia.Interactivity.RoutedEventArgs e)
        {
            if (DataContext is MainWindowViewModel vm)
            {
                await vm.ExportProfilesAsync();
            }
        }

        private async void OnImportProfilesClick(object? sender, Avalonia.Interactivity.RoutedEventArgs e)
        {
            if (DataContext is MainWindowViewModel vm)
            {
                await vm.ImportProfilesAsync();
            }
        }

        private async void OnDeleteSelectedClick(object? sender, Avalonia.Interactivity.RoutedEventArgs e)
        {
            if (DataContext is MainWindowViewModel vm)
            {
                await vm.DeleteSelectedAsync();
            }
        }

        private async void OnBrowseProfilesDirClick(object? sender, Avalonia.Interactivity.RoutedEventArgs e)
        {
            if (DataContext is MainWindowViewModel vm)
            {
                var dialog = new OpenFolderDialog
                {
                    Title = "Select Custom Profiles Storage Folder"
                };
                var result = await dialog.ShowAsync(this);
                if (!string.IsNullOrEmpty(result))
                {
                    vm.ChangeProfilesDirectory(result);
                }
            }
        }

        private async void OnBrowseViberClick(object? sender, Avalonia.Interactivity.RoutedEventArgs e)
        {
            if (DataContext is MainWindowViewModel vm)
            {
                var dialog = new OpenFileDialog
                {
                    Title = "Select Viber Executable",
                    AllowMultiple = false
                };
                dialog.Filters.Add(new FileDialogFilter { Name = "Executable", Extensions = { "exe", "AppImage" } });
                var result = await dialog.ShowAsync(this);
                if (result != null && result.Length > 0)
                {
                    vm.ViberPath = result[0];
                }
            }
        }

        private void OnAutoDetectViberClick(object? sender, Avalonia.Interactivity.RoutedEventArgs e)
        {
            if (DataContext is MainWindowViewModel vm)
            {
                vm.AutoDetectViber();
            }
        }

        private void OnLaunchRowClick(object? sender, Avalonia.Interactivity.RoutedEventArgs e)
        {
            if (sender is Button btn && btn.DataContext is ViberProfile profile && DataContext is MainWindowViewModel vm)
            {
                vm.LaunchProfile(profile);
            }
        }

        private async void OnCopyPhoneClick(object? sender, Avalonia.Interactivity.RoutedEventArgs e)
        {
            if (sender is Button btn && btn.DataContext is ViberProfile profile && !string.IsNullOrEmpty(profile.Phone) && profile.Phone != "—")
            {
                var clipboard = TopLevel.GetTopLevel(this)?.Clipboard;
                if (clipboard != null)
                {
                    await clipboard.SetTextAsync(profile.Phone);
                    if (DataContext is MainWindowViewModel vm)
                    {
                        vm.StatusText = $"Copied phone {profile.Phone} to clipboard!";
                    }
                }
            }
        }

        private void OnTelegramClick(object? sender, Avalonia.Interactivity.RoutedEventArgs e)
        {
            try
            {
                System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo
                {
                    FileName = "https://t.me/anv184",
                    UseShellExecute = true
                });
            }
            catch { }
        }

        private async void OnRenameRowClick(object? sender, Avalonia.Interactivity.RoutedEventArgs e)
        {
            if (sender is Button btn && btn.DataContext is ViberProfile profile && DataContext is MainWindowViewModel vm)
            {
                await vm.RenameProfileAsync(profile);
            }
        }

        private void OnDataGridLoadingRow(object? sender, DataGridRowEventArgs e)
        {
            if (e.Row.DataContext is ViberProfile profile)
            {
                // Subscribe to profile property changed to toggle class instantly
                profile.PropertyChanged += (s, ev) =>
                {
                    if (ev.PropertyName == nameof(ViberProfile.IsRunning))
                    {
                        UpdateRowClasses(e.Row, profile);
                    }
                };
                UpdateRowClasses(e.Row, profile);
            }
        }

        private void UpdateRowClasses(DataGridRow row, ViberProfile profile)
        {
            if (profile.IsRunning)
            {
                if (!row.Classes.Contains("running"))
                    row.Classes.Add("running");
            }
            else
            {
                row.Classes.Remove("running");
            }
        }

        private async void OnDeleteRowClick(object? sender, Avalonia.Interactivity.RoutedEventArgs e)
        {
            if (sender is Button btn && btn.DataContext is ViberProfile profile && DataContext is MainWindowViewModel vm)
            {
                await vm.DeleteProfileAsync(profile);
            }
        }

        // ──────────────────────────────────────── Hộp thoại nhập Text ───────────

        public async Task<(string? Name, bool IsBusiness)?> AskCreateProfileDialogAsync(string defaultName)
        {
            (string? Name, bool IsBusiness)? result = null;
            var diag = new Window
            {
                Title = "Create Profile",
                Width = 320,
                Height = 200,
                WindowStartupLocation = WindowStartupLocation.CenterOwner,
                Background = Avalonia.Media.Brush.Parse("#FFFFFF"),
                CanResize = false,
                SystemDecorations = SystemDecorations.Full,
                FontFamily = FontFamily
            };

            var stack = new StackPanel { Spacing = 12, Margin = new Avalonia.Thickness(20) };
            stack.Children.Add(new TextBlock { Text = "Enter profile name:", Foreground = Avalonia.Media.Brush.Parse("#18181B"), FontWeight = Avalonia.Media.FontWeight.Medium, FontSize = 13 });
            
            var input = new TextBox { Text = defaultName, Width = 280, Height = 32, Background = Avalonia.Media.Brush.Parse("#FFFFFF"), Foreground = Avalonia.Media.Brush.Parse("#18181B"), BorderBrush = Avalonia.Media.Brush.Parse("#D4D4D8") };
            diag.Opened += (s, e) => { input.Focus(); if (!string.IsNullOrEmpty(input.Text)) input.SelectAll(); };
            stack.Children.Add(input);

            var chkBusiness = new CheckBox { Content = "Business Profile", IsChecked = false, Foreground = Avalonia.Media.Brush.Parse("#18181B") };
            stack.Children.Add(chkBusiness);

            var btn = new Button
            {
                Content = "Create",
                HorizontalAlignment = Avalonia.Layout.HorizontalAlignment.Stretch,
                HorizontalContentAlignment = Avalonia.Layout.HorizontalAlignment.Center,
                Background = Avalonia.Media.Brush.Parse("#E4E4E7"),
                Foreground = Avalonia.Media.Brush.Parse("#18181B"),
                FontWeight = Avalonia.Media.FontWeight.Bold,
                Height = 32
            };
            btn.Click += (s, e) => { result = (input.Text, chkBusiness.IsChecked ?? false); diag.Close(); };
            stack.Children.Add(btn);
            diag.Content = stack;
            await diag.ShowDialog(this);
            return result;
        }

        public async Task<(string? Name, bool IsBusiness, bool IsScanned)?> AskEditProfileDialogAsync(string oldName, bool isBusiness, bool isScanned)
        {
            (string? Name, bool IsBusiness, bool IsScanned)? result = null;
            var diag = new Window
            {
                Title = "Edit Profile",
                Width = 320,
                Height = 240,
                WindowStartupLocation = WindowStartupLocation.CenterOwner,
                Background = Avalonia.Media.Brush.Parse("#FFFFFF"),
                CanResize = false,
                SystemDecorations = SystemDecorations.Full,
                FontFamily = FontFamily
            };

            var stack = new StackPanel { Spacing = 10, Margin = new Avalonia.Thickness(20) };
            stack.Children.Add(new TextBlock { Text = "Enter profile name:", Foreground = Avalonia.Media.Brush.Parse("#18181B"), FontWeight = Avalonia.Media.FontWeight.Medium, FontSize = 13 });
            
            var input = new TextBox { Text = oldName, Width = 280, Height = 32, Background = Avalonia.Media.Brush.Parse("#FFFFFF"), Foreground = Avalonia.Media.Brush.Parse("#18181B"), BorderBrush = Avalonia.Media.Brush.Parse("#D4D4D8") };
            diag.Opened += (s, e) => { input.Focus(); if (!string.IsNullOrEmpty(input.Text)) input.SelectAll(); };
            stack.Children.Add(input);

            var chkBusiness = new CheckBox { Content = "Business Profile", IsChecked = isBusiness, Foreground = Avalonia.Media.Brush.Parse("#18181B") };
            var chkScanned = new CheckBox { Content = "Scanned Status", IsChecked = isScanned, Foreground = Avalonia.Media.Brush.Parse("#18181B") };
            stack.Children.Add(chkBusiness);
            stack.Children.Add(chkScanned);

            var btn = new Button
            {
                Content = "Save",
                HorizontalAlignment = Avalonia.Layout.HorizontalAlignment.Stretch,
                HorizontalContentAlignment = Avalonia.Layout.HorizontalAlignment.Center,
                Background = Avalonia.Media.Brush.Parse("#E4E4E7"),
                Foreground = Avalonia.Media.Brush.Parse("#18181B"),
                FontWeight = Avalonia.Media.FontWeight.Bold,
                Height = 32
            };
            btn.Click += (s, e) => { result = (input.Text, chkBusiness.IsChecked ?? false, chkScanned.IsChecked ?? false); diag.Close(); };
            stack.Children.Add(btn);
            diag.Content = stack;
            await diag.ShowDialog(this);
            return result;
        }

        private async Task<string?> AskTextDialogAsync(string title, string prompt, string defaultText = "")
        {
            string? result = null;
            var diag = new Window
            {
                Title = title,
                Width = 320,
                Height = 160,
                WindowStartupLocation = WindowStartupLocation.CenterOwner,
                Background = Avalonia.Media.Brush.Parse("#FFFFFF"),
                CanResize = false,
                SystemDecorations = SystemDecorations.Full,
                FontFamily = FontFamily
            };

            var stack = new StackPanel { Spacing = 12, Margin = new Avalonia.Thickness(20) };
            stack.Children.Add(new TextBlock { Text = prompt, Foreground = Avalonia.Media.Brush.Parse("#18181B"), FontWeight = Avalonia.Media.FontWeight.Medium, FontSize = 13 });
            
            var input = new TextBox 
            { 
                Text = defaultText, 
                Width = 280, 
                Height = 32, 
                Background = Avalonia.Media.Brush.Parse("#FFFFFF"), 
                Foreground = Avalonia.Media.Brush.Parse("#18181B"), 
                BorderBrush = Avalonia.Media.Brush.Parse("#D4D4D8") 
            };
            
            // Tự động focus và bôi đen toàn bộ tên cũ
            diag.Opened += (s, e) => 
            {
                input.Focus();
                if (!string.IsNullOrEmpty(input.Text))
                    input.SelectAll();
            };

            stack.Children.Add(input);

            var btn = new Button
            {
                Content = "Save",
                HorizontalAlignment = Avalonia.Layout.HorizontalAlignment.Stretch,
                HorizontalContentAlignment = Avalonia.Layout.HorizontalAlignment.Center,
                Background = Avalonia.Media.Brush.Parse("#E4E4E7"),
                Foreground = Avalonia.Media.Brush.Parse("#18181B"),
                FontWeight = Avalonia.Media.FontWeight.Bold,
                Height = 32
            };
            
            btn.Click += (s, e) =>
            {
                result = input.Text;
                diag.Close();
            };
            
            stack.Children.Add(btn);
            diag.Content = stack;
            
            await diag.ShowDialog(this);
            return result;
        }

        // ──────────────────────────────────────── Hộp thoại xác nhận ────────────

        private async Task<bool> ConfirmDialogAsync(string title, string message)
        {
            bool result = false;
            var diag = new Window
            {
                Title = title,
                Width = 340,
                Height = 150,
                WindowStartupLocation = WindowStartupLocation.CenterOwner,
                Background = Avalonia.Media.Brush.Parse("#FFFFFF"),
                CanResize = false,
                SystemDecorations = SystemDecorations.Full,
                FontFamily = FontFamily
            };

            var stack = new StackPanel { Spacing = 15, Margin = new Avalonia.Thickness(20) };
            stack.Children.Add(new TextBlock { Text = message, Foreground = Avalonia.Media.Brush.Parse("#18181B"), TextWrapping = Avalonia.Media.TextWrapping.Wrap, FontSize = 13 });
            
            var grid = new Grid();
            grid.ColumnDefinitions.Add(new ColumnDefinition(1, GridUnitType.Star));
            grid.ColumnDefinitions.Add(new ColumnDefinition(1, GridUnitType.Star));

            var btnYes = new Button
            {
                Content = "Yes",
                HorizontalAlignment = Avalonia.Layout.HorizontalAlignment.Stretch,
                HorizontalContentAlignment = Avalonia.Layout.HorizontalAlignment.Center,
                Background = Avalonia.Media.Brush.Parse("#FEE4E2"),
                Foreground = Avalonia.Media.Brush.Parse("#B42318"),
                FontWeight = Avalonia.Media.FontWeight.Bold,
                Margin = new Avalonia.Thickness(0, 0, 5, 0),
                Height = 32
            };
            btnYes.Click += (s, e) => { result = true; diag.Close(); };

            var btnNo = new Button
            {
                Content = "No",
                HorizontalAlignment = Avalonia.Layout.HorizontalAlignment.Stretch,
                HorizontalContentAlignment = Avalonia.Layout.HorizontalAlignment.Center,
                Background = Avalonia.Media.Brush.Parse("#E4E4E7"),
                Foreground = Avalonia.Media.Brush.Parse("#18181B"),
                Margin = new Avalonia.Thickness(5, 0, 0, 0),
                Height = 32
            };
            btnNo.Click += (s, e) => { result = false; diag.Close(); };

            Grid.SetColumn(btnYes, 0);
            Grid.SetColumn(btnNo, 1);
            grid.Children.Add(btnYes);
            grid.Children.Add(btnNo);
            
            stack.Children.Add(grid);
            diag.Content = stack;
            
            await diag.ShowDialog(this);
            return result;
        }
    }
}