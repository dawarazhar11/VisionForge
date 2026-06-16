# Build on your Mac, run on your iPhone (free)

This is the developer-testing path: install the app on **your own iPhone**
using a **free Apple ID** — no paid Apple Developer account. Each developer
signs with their own Apple ID; builds last 7 days and are refreshed by simply
re-running.

> No paid account is needed for *your own* devices. A paid account ($99/yr) is
> only required to distribute to *other people's* iPhones (TestFlight). For
> Android, anyone can install the APK directly — see [INSTALL.md](INSTALL.md).

## Prerequisites

- **macOS** with **Xcode** (from the App Store) + command-line tools
- **Flutter** (`flutter doctor` should pass for iOS)
- An **Apple ID** (free) added in **Xcode → Settings → Accounts**
- iPhone connected by **USB** (more reliable than wireless for the first run),
  unlocked, "Trust This Computer" accepted

## One-time setup

1. **Add your Apple ID** in Xcode → Settings → Accounts → **+** → Apple ID. A
   free "Personal Team" appears under the account.

2. **Select your team** for signing:
   ```bash
   cd flutter_app
   open ios/Runner.xcworkspace
   ```
   In Xcode: select the **Runner** target → **Signing & Capabilities** →
   check **Automatically manage signing** → pick **your team** in the
   **Team** dropdown. Wait until the signing errors clear.

3. **Install the iOS device-support platform** (Xcode prompts for this on the
   first physical-device build; it's a few GB, one-time):
   ```bash
   xcodebuild -downloadPlatform iOS
   ```

## Run it

```bash
cd flutter_app
flutter pub get
flutter run --release -d <your-iphone>     # `flutter devices` lists the id
```

- Use `--release` for a build that **runs standalone** (tap the icon, no laptop
  tether). A plain debug `flutter run` keeps the app tied to your Mac and
  closes if you launch it from the home screen without the debugger.
- First launch: iOS blocks the unverified developer. Go to
  **Settings → General → VPN & Device Management → [your Apple ID] → Trust**,
  then reopen the app.

## In-app

Set the **Backend URL** on the login screen (LAN IP, NetBird/VPN IP, or hosted),
sign in, and you're in. The URL is editable right on the login screen and is
remembered.

## Troubleshooting (real issues, with fixes)

| Symptom | Cause & fix |
|---------|-------------|
| `pod install` hangs forever / iOS build never finishes | CocoaPods 1.16 on Homebrew Ruby crashes on a Unicode error, *or* the `TensorFlowLiteSwift` pod tries to clone the multi-GB tensorflow repo. Run pods with `LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8 RUBYOPT="-EUTF-8" pod install`; this repo already pins the TFLite pod to a tarball to avoid the giant clone. |
| `iOS 26.x is not installed. Please download the platform` | Run `xcodebuild -downloadPlatform iOS` (one-time, several GB). |
| `No Account for Team` / `No profiles for '<bundle>' were found` | Apple ID/team not selected. Do the **Signing & Capabilities → Team** step above; if the dropdown is empty, re-add the Apple ID in Xcode → Settings → Accounts. |
| App installs but **closes immediately** when tapped | You installed a **debug** build and opened it without the `flutter run` host. Build with `--release` (self-contained). |
| `Build succeeded but ... Runner.app not found` | Xcode put it in `build/ios/Release-iphoneos/`. Install it directly: `xcrun devicectl device install app --device <id> "build/ios/Release-iphoneos/Runner.app"`. |
| Wireless install times out (`tunnel was interrupted`) | Keep the phone unlocked and on the same Wi-Fi; prefer **USB** for installs. Retry — the tunnel is flaky over Wi-Fi. |
| App can't reach the backend | The Mac's Wi-Fi IP changes often. Use a stable address — a **NetBird/Tailscale VPN IP** works across networks (both phone and Mac must be connected to the VPN). Set it in the app's Backend URL. |
| "No active model" in Detect after downloading | Re-download in the *current* install (reinstalling changes the iOS container path). Download → **Set Active** → open Detect. |
