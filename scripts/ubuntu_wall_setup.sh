#!/bin/bash
# ==========================================================
# StudyOS — Ubuntu Wall Laptop Display Setup & Auto-Launch
# Old Ubuntu Laptop Hardware: Pentium Gold / 4 GB RAM / 1 TB
# ==========================================================

MAIN_LAPTOP_IP="192.168.0.102"  # Replace with actual Main Laptop Controller IP
PORT="8000"
TARGET_URL="http://${MAIN_LAPTOP_IP}:${PORT}/wall"

echo "[StudyOS] Configuring Ubuntu Wall Laptop for Always-On Kiosk Display..."

# 1. Install lightweight Chromium browser if not present
sudo apt update && sudo apt install x11-xserver-utils chromium-browser -y

# 2. Disable DPMS, Screen Blanking, and Auto-Suspend
xset s off
xset -dpms
xset s noblank

# Disable GNOME Power Saving / Screen Saver timeout
gsettings set org.gnome.desktop.session idle-delay 0
gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type 'nothing'
gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-battery-type 'nothing'

# 3. Create Auto-Start Desktop Entry for Kiosk Mode
AUTOSTART_DIR="$HOME/.config/autostart"
mkdir -p "$AUTOSTART_DIR"

cat << EOF > "$AUTOSTART_DIR/studyos-wall-kiosk.desktop"
[Desktop Entry]
Type=Application
Name=StudyOS Wall Kiosk
Exec=chromium-browser --kiosk --noerrdialogs --disable-infobars --autoplay-policy=no-user-gesture-required "$TARGET_URL"
X-GNOME-Autostart-enabled=true
EOF

echo "[StudyOS] Setup Completed Successfully!"
echo "[StudyOS] Rebooting will automatically open StudyOS Wall Display in fullscreen kiosk mode."
