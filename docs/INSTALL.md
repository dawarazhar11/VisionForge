# Installing the VisionForge App

The app is a client — it talks to a VisionForge backend. After installing, set
the **Backend URL** on the login screen to your server (LAN IP, NetBird/VPN IP,
or a hosted URL).

## Android — download & install (no account, no fee)

This is the simplest path and works for everyone.

1. Go to the repo's **[Releases](../../releases)** page.
2. Download the latest **`app-release.apk`**.
3. Open it on your Android phone. When prompted, allow **"install from unknown
   sources"** for your browser/files app (one-time).
4. Open the app, set the **Backend URL**, and sign in.

> The APK is built automatically by GitHub Actions on each release (see
> `.github/workflows/build-android.yml`) — no Android SDK or store account
> needed to produce or install it.

## iOS — the honest options

Apple does **not** allow installing an app from a downloaded file. There is no
free way to put an iOS build on someone else's iPhone. Your options:

### A. Build it yourself (free)
For anyone with a Mac. Each person signs with their **own free Apple ID**:

```bash
git clone https://github.com/dawarazhar11/VisionForge.git
cd VisionForge/flutter_app
flutter pub get
open ios/Runner.xcworkspace      # Xcode → Signing & Capabilities → select your team
flutter run --release            # installs on your connected iPhone
```

Free Apple IDs expire the build after 7 days — just re-run to refresh. Needs a
Mac + Xcode, so this is for technical users. **Full step-by-step with
troubleshooting: [IOS_TESTING.md](IOS_TESTING.md).**

### B. TestFlight (requires paid Apple Developer Program — $99/yr)
The only way to give non-technical users a simple install link on iOS. With a
paid account: archive the app, upload to App Store Connect, and share a
TestFlight link (installs on any iPhone, up to 10,000 testers).

### C. Ad Hoc (paid account, fixed devices)
Installs only on iPhones whose UDIDs are pre-registered (max 100).

## Recommendation

- **Reach the most users for free → ship the Android APK** via GitHub Releases.
- **iOS for non-technical users → only via TestFlight** (paid).
- **iOS for developers → build-it-yourself** with a free Apple ID.
