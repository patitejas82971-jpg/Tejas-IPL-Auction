# 📱 IPL Auction Simulator - Android App

The official Android mobile client for the **IPL Auction Simulator**. Built with Kotlin, Material 3, and an enhanced Android WebView bridge with hardware acceleration, WebSocket live bidding support, native haptic feedback, and offline resilience.

---

## ✨ Features

- **⚡ Real-Time Live Bidding**: Synchronized WebSocket bidding via Socket.IO directly inside the mobile experience.
- **📳 Native Haptic & Vibration Feedback**:
  - Haptic tap feedback upon placing a bid.
  - Distinct celebration vibration pattern when a player is **SOLD**.
  - Warning alert pulses when the auction countdown timer is running low (< 5s).
- **🔄 Swipe-to-Refresh**: Native pull-to-refresh (`SwipeRefreshLayout`) dynamically enabled when scrolled to the top of the page.
- **📡 In-App Server Switcher**: Easily switch between **Android Emulator** (`http://10.0.2.2:5000`), **Local Wi-Fi LAN** (`http://192.168.x.x:5000`), or **Production URL** directly from the top settings icon without recompiling.
- **🚫 Offline Fallback View**: Graceful error screen with one-tap **Retry** and server configuration buttons when disconnected.
- **📥 Native Squad Downloads**: Downloads exported squad CSV and JSON files directly into the Android device's `Downloads` directory via Android's `DownloadManager`.
- **🎨 Cricket Dark Theme**: Custom dark Material 3 theme matching official IPL colors (Navy Blue `#0A0E27`, Gold `#F5B841`, Neon Green `#00E676`).
- **🔙 Smart Back Button Handling**: Navigates browser history smoothly and requires double-tap back to exit from the root screen.

---

## 🏗️ Architecture

```
android/
├── app/
│   ├── build.gradle.kts          # App dependencies & SDK configuration (minSdk 26, targetSdk 34)
│   ├── proguard-rules.pro        # ProGuard keeping AndroidBridge interface intact
│   └── src/main/
│       ├── AndroidManifest.xml   # Permissions, cleartext traffic & network security config
│       ├── java/com/iplauction/app/
│       │   ├── MainActivity.kt        # Primary activity, WebView configuration & lifecycle
│       │   ├── WebAppInterface.kt     # JavaScript <-> Native Android bridge (vibration, toast, share)
│       │   ├── ServerConfigDialog.kt  # In-app server URL switcher & presets
│       │   └── NetworkUtils.kt        # Network capability helper
│       └── res/
│           ├── layout/
│           │   ├── activity_main.xml         # Toolbar, ProgressBar, SwipeRefreshLayout & WebView
│           │   ├── dialog_server_config.xml  # Server switcher modal layout
│           │   └── layout_offline.xml        # Offline connection error layout
│           ├── values/
│           │   ├── colors.xml   # IPL dark cricket color palette
│           │   ├── strings.xml  # Localized strings
│           │   └── themes.xml   # Material 3 dark themes
│           └── xml/
│               ├── network_security_config.xml # Cleartext HTTP permissions for dev servers
│               └── file_paths.xml              # FileProvider paths
├── build.gradle.kts              # Top-level Gradle build configuration
├── settings.gradle.kts           # Repository & project includes
├── gradle.properties             # AndroidX & JVM memory settings
└── README.md                     # Documentation
```

---

## 🚀 Getting Started

### 1. Prerequisites
- **Android Studio** (Hedgehog, Iguana, Koala, Ladybug, or later)
- **JDK 17+** (bundled with Android Studio)
- **Android SDK API 34** (or installed via Android Studio SDK Manager)
- **Python 3.10+** (running the Flask backend in the root `IPL-Auction` directory)

---

### 2. Start the Flask Backend Server

In your project root (`IPL-Auction/`):

```bash
# Activate your Python virtual environment
venv\Scripts\activate   # Windows
source venv/bin/activate # macOS/Linux

# Start the Flask + Socket.IO server
python run.py
```

The server will start listening on `http://0.0.0.0:5000`.

---

### 3. Open and Run in Android Studio

1. Open **Android Studio**.
2. Select **File > Open...** and navigate to `IPL-Auction/android`.
3. Allow Gradle to sync the project dependencies.
4. Choose an emulator or connected physical Android device from the device dropdown.
5. Click **Run ('app')** (or press `Shift + F10`).

---

### 4. Connecting to Your Backend

Depending on whether you are running on an emulator or a physical device:

#### A. Running on Android Emulator
- The app defaults to `http://10.0.2.2:5000`.
- `10.0.2.2` is the special Android Emulator alias that points to `localhost` on your host development PC.
- No extra setup is required!

#### B. Running on a Physical Android Device (over Wi-Fi)
1. Make sure your Android phone and development PC are connected to the **same Wi-Fi network**.
2. Find your PC's local IP address:
   - **Windows**: Run `ipconfig` in PowerShell/Command Prompt (look for `IPv4 Address`, e.g. `192.168.1.15`).
   - **macOS/Linux**: Run `ifconfig` or `ip addr`.
3. Open the **IPL Auction** app on your phone.
4. Tap the **Settings icon** (⚙️) in the top-right toolbar.
5. Enter: `http://<YOUR_PC_IP>:5000` (e.g. `http://192.168.1.15:5000`).
6. Tap **Connect**.

#### C. Running against a Deployed Production Server
- If your backend is deployed (e.g., Render, Railway, AWS, Vercel), enter `https://your-production-domain.com` in the server settings dialog.

---

### 5. Building the APK from Command Line

To build the debug APK using Gradle:

```bash
cd android

# On Windows:
.\gradlew.bat assembleDebug

# On macOS / Linux:
./gradlew assembleDebug
```

The generated APK will be located at:
`android/app/build/outputs/apk/debug/app-debug.apk`

You can install it directly onto any connected device with `adb`:
```bash
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

---

## 🔌 JavaScript Bridge API

The web application communicates with the native Android app using `window.AndroidBridge`:

| Bridge Method | Description |
|---|---|
| `window.AndroidBridge.isAndroidApp()` | Returns `true` if running inside the Android app |
| `window.AndroidBridge.vibrate(ms)` | Triggers a native haptic pulse for the specified milliseconds |
| `window.AndroidBridge.vibratePattern(pattern)` | Executes a waveform vibration pattern (e.g., `"0,80,100,120"`) |
| `window.AndroidBridge.onBidPlaced(amount, player)` | Fires immediate bid haptic feedback |
| `window.AndroidBridge.onPlayerSold(team, price)` | Fires player sold celebration vibration |
| `window.AndroidBridge.showToast(message)` | Displays a native Android Toast |
| `window.AndroidBridge.shareText(text, title)` | Opens the native Android system share dialog |

---

## 🛡️ Network Security Note
The app includes `network_security_config.xml` configured to allow cleartext HTTP traffic to `10.0.2.2`, `localhost`, and LAN IP addresses for smooth local development. In production release builds, HTTPS is enforced.
