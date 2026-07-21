using CommunityToolkit.Mvvm.ComponentModel;

namespace AnvViberManager.Models
{
    public partial class ViberProfile : ObservableObject
    {
        [ObservableProperty]
        private bool _isSelected;

        [ObservableProperty]
        private int _index;

        [ObservableProperty]
        private string _name = string.Empty;

        [ObservableProperty]
        private string _phone = string.Empty;

        [ObservableProperty]
        [NotifyPropertyChangedFor(nameof(IsRunning))]
        private string _status = "Idle";

        [ObservableProperty]
        [NotifyPropertyChangedFor(nameof(BusinessText))]
        private bool _isBusiness;

        [ObservableProperty]
        [NotifyPropertyChangedFor(nameof(ScannedText))]
        private bool _isScanned;

        public bool IsRunning => Status == "Running";
        public string BusinessText => IsBusiness ? "Yes" : "No";
        public string ScannedText => IsScanned ? "Yes" : "No";
        public string Actions => Status == "Running" ? "Stop | Rename | Del" : "▶ | Rename | Del";
    }
}
