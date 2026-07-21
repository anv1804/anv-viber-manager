using Avalonia;
using System;

namespace AnvViberManager;

sealed class Program
{
    // Initialization code. Don't use any Avalonia, third-party APIs or any
    // SynchronizationContext-reliant code before AppMain is called: things aren't initialized
    // yet and stuff might break.
    [STAThread]
    public static void Main(string[] args)
    {
        try
        {
            BuildAvaloniaApp()
                .StartWithClassicDesktopLifetime(args);
        }
        catch (Exception ex)
        {
            if (OperatingSystem.IsWindows())
            {
                // Gọi Win32 MessageBox để thông báo lỗi thay vì silent crash
                System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo
                {
                    FileName = "powershell",
                    Arguments = $"-Command \"[System.Windows.Forms.MessageBox]::Show('An error occurred during startup: {ex.Message.Replace("'", "''")}\\n\\nDetails: {ex.ToString().Replace("'", "''")}', 'Startup Crash Error')\"",
                    CreateNoWindow = true,
                    UseShellExecute = false
                });
            }
            else
            {
                Console.WriteLine("CRASH EXCEPTION: " + ex);
            }
        }
    }

    // Avalonia configuration, don't remove; also used by visual designer.
    public static AppBuilder BuildAvaloniaApp()
        => AppBuilder.Configure<App>()
            .UsePlatformDetect()
            .WithInterFont()
            .LogToTrace();
}
