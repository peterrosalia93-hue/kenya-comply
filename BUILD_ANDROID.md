# KenyaComply Android APK Build Guide

## Prerequisites

1. **Node.js** installed
2. **Expo account** (expo.dev)
3. **GitHub** repository (already done)

---

## Build Steps

### Step 1: Install EAS CLI

```bash
npm install -g eas-cli
```

### Step 2: Login to Expo

```bash
eas login
# Enter your Expo credentials
```

### Step 3: Configure Project

```bash
cd kenya-comply
eas build:configure --platform android
```

This creates `eas.json` configuration file.

### Step 4: Build APK

```bash
# For development build (faster)
eas build --platform android --profile development

# For production build (smaller, optimized)
eas build --platform android --profile preview
```

### Step 5: Download APK

After build completes, you'll get a download link:
- `*.apk` file
- Install directly on Android devices

---

## Upload to Google Play Store

### 1. Create Google Play Console Account
- Go to [play.google.com/console](https://play.google.com/console)
- Pay $25 one-time registration fee

### 2. Create App
- App name: KenyaComply
- Category: Business

### 3. Upload APK
- Go to Release → Production
- Upload your APK
- Fill in store listing details

### 4. Test with Internal Testing
- Upload to Internal Testing track
- Add up to 100 testers via email
- No review needed for internal testing

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Build fails | Run `npm install` first |
| APK too large | Use `--profile preview` |
| Signing issues | Check `app.json` package name |

---

## Alternative: Local Build

If EAS fails, build locally:

```bash
cd android
./gradlew assembleDebug
```

APK will be at: `android/app/build/outputs/apk/debug/*.apk`

---

*Generated: 2026-04-04*
*KenyaComply by Mwakulomba* 🎥📜