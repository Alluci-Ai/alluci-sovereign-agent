# Task A4 — Xcode Project + HealthKit Entitlements
## Complete Step-by-Step Guide

**Scope:** This document covers Task A4 only — creating the Xcode project,
adding the six existing Swift source files, enabling HealthKit, creating
`Info.plist`, creating the `.entitlements` file, generating placeholder
icons, and verifying the build.

**Prerequisite:** macOS with Xcode 15.0 or later installed.  
**Time required:** 3–4 hours.

---

## Background — Why This Step Is Needed

The `watchos/AlluciWatch/` directory contains six complete, correct Swift
source files:

```
watchos/AlluciWatch/
├── AlluciWatchApp.swift
├── Managers/
│   ├── HealthKitManager.swift
│   └── NetworkManager.swift
├── Models/
│   └── TelemetrySample.swift
└── Views/
    ├── ContentView.swift
    └── PairingView.swift
```

These files cannot be compiled or deployed to an Apple Watch without an
Xcode project file (`.xcodeproj`). The project file tells Xcode:

- Which files belong to which build target
- What capabilities are enabled (HealthKit requires an explicit entitlement)
- What the bundle identifier is (`ai.alluci.AlluciWatch`)
- What the minimum watchOS version is (10.0)
- How to sign the app for real device deployment

Without `AlluciWatch.xcodeproj`, the entire watchOS layer is inert source
code that cannot be built, tested, or deployed.

---

## Step 1 — Verify Your Starting State

Before opening Xcode, confirm the six source files exist exactly as listed:

```bash
find watchos/AlluciWatch -name "*.swift" | sort
```

Expected output — exactly these six files, nothing more:

```
watchos/AlluciWatch/AlluciWatchApp.swift
watchos/AlluciWatch/Managers/HealthKitManager.swift
watchos/AlluciWatch/Managers/NetworkManager.swift
watchos/AlluciWatch/Models/TelemetrySample.swift
watchos/AlluciWatch/Views/ContentView.swift
watchos/AlluciWatch/Views/PairingView.swift
```

If you see a different set, stop and reconcile before continuing.

---

## Step 2 — Create the Xcode Project (GUI)

This step must be performed in the Xcode GUI. There is no reliable
command-line path for creating a new watchOS app project.

### 2.1 — Open Xcode and start a new project

```
1. Open Xcode 15 (or later).

2. From the menu bar: File → New → Project
   (keyboard shortcut: Shift + Cmd + N)

3. The template chooser window appears.
```

### 2.2 — Select the correct template

```
1. At the top of the template chooser, click the "watchOS" tab.
   (The tabs are: iOS | macOS | watchOS | tvOS | visionOS | Other)

2. In the grid of templates, select "App".
   — Do NOT select "Watch App for iOS App" — that creates a paired
     iOS + watchOS project which adds unnecessary complexity.
   — The plain "App" template creates a standalone watchOS app, which
     is exactly what AlluciWatch needs.

3. Click "Next".
```

### 2.3 — Fill in the project options

A form appears asking for project details. Fill in each field exactly:

```
Product Name:        AlluciWatch
Team:                (Select your Apple Developer account if you have one.
                      If you do not have one, select "None" — the project
                      will still build for the simulator without a team.)
Organization Identifier:  ai.alluci
Bundle Identifier:   ai.alluci.AlluciWatch
                     (This auto-fills from Product Name + Org Identifier.
                      Verify it reads exactly "ai.alluci.AlluciWatch".)
Interface:           SwiftUI
Language:            Swift
Include Tests:       YES  (check this box)
```

> **Important:** The Bundle Identifier `ai.alluci.AlluciWatch` must match
> exactly. It is used in the entitlements file and in any future App Store
> submission.

```
4. Click "Next".
```

### 2.4 — Choose the save location

```
1. The file-save dialog opens, asking where to save the project.

2. Navigate to the "watchos" folder inside your repository root.
   The path should look like:
   /path/to/alluci-sovereign-agent-main/watchos/

3. Make sure "Create Git repository on my Mac" is UNCHECKED.
   (The repository already has its own Git history.)

4. Click "Create".
```

Xcode creates the project and opens it. You will see a default project
structure with auto-generated `ContentView.swift` and `AlluciWatchApp.swift`
files. You will replace these with the repository's existing files.

---

## Step 3 — Delete the Auto-Generated Source Files

Xcode created placeholder files that conflict with the existing source files.
Delete them now.

```
1. In the Project Navigator (left panel), expand the
   "AlluciWatch Watch App" folder.

2. You will see at minimum:
   - AlluciWatchApp.swift  (auto-generated placeholder)
   - ContentView.swift     (auto-generated placeholder)
   - Assets.xcassets       (keep this — you will populate it in Step 6)

3. Click on AlluciWatchApp.swift to select it.

4. Hold Cmd and also click ContentView.swift to select both.

5. Press the Delete key (or right-click → Delete).

6. A dialog appears: "Do you want to move the files to the Trash,
   or only remove the references?"
   Click "Move to Trash".
   (You want them gone entirely, not just unreferenced.)
```

---

## Step 4 — Add the Six Existing Source Files

Now add the repository's actual Swift files to the project.

### 4.1 — Add AlluciWatchApp.swift (root file)

```
1. In the Project Navigator, right-click on the
   "AlluciWatch Watch App" group (folder icon).

2. Select "Add Files to 'AlluciWatch Watch App'..."

3. In the file picker, navigate to:
   watchos/AlluciWatch/

4. Select "AlluciWatchApp.swift" (the root-level file).

5. In the options panel at the bottom of the file picker:
   - "Copy items if needed":  UNCHECKED
     (The file is already in the right location inside the repo.
      Copying would create a duplicate outside the watchos/ folder.)
   - "Create groups":         SELECTED  (radio button)
   - "Add to targets":        AlluciWatch Watch App  ✓  (checkbox checked)

6. Click "Add".
```

### 4.2 — Add the Managers/ folder

```
1. Right-click on the "AlluciWatch Watch App" group again.

2. Select "Add Files to 'AlluciWatch Watch App'..."

3. Navigate to: watchos/AlluciWatch/

4. Single-click on the "Managers" folder to select the entire folder.
   Do not expand it or select individual files — select the folder itself.

5. Options panel:
   - "Copy items if needed":  UNCHECKED
   - "Create groups":         SELECTED
   - "Add to targets":        AlluciWatch Watch App  ✓

6. Click "Add".

   Result: A "Managers" group appears in the Project Navigator containing
   HealthKitManager.swift and NetworkManager.swift.
```

### 4.3 — Add the Models/ folder

```
1. Right-click on the "AlluciWatch Watch App" group.

2. Select "Add Files to 'AlluciWatch Watch App'..."

3. Navigate to: watchos/AlluciWatch/

4. Single-click on the "Models" folder.

5. Options panel:
   - "Copy items if needed":  UNCHECKED
   - "Create groups":         SELECTED
   - "Add to targets":        AlluciWatch Watch App  ✓

6. Click "Add".

   Result: A "Models" group appears containing TelemetrySample.swift.
```

### 4.4 — Add the Views/ folder

```
1. Right-click on the "AlluciWatch Watch App" group.

2. Select "Add Files to 'AlluciWatch Watch App'..."

3. Navigate to: watchos/AlluciWatch/

4. Single-click on the "Views" folder.

5. Options panel:
   - "Copy items if needed":  UNCHECKED
   - "Create groups":         SELECTED
   - "Add to targets":        AlluciWatch Watch App  ✓

6. Click "Add".

   Result: A "Views" group appears containing ContentView.swift
   and PairingView.swift.
```

### 4.5 — Verify the Project Navigator structure

After all additions, the Project Navigator should look exactly like this:

```
AlluciWatch
└── AlluciWatch Watch App
    ├── AlluciWatchApp.swift
    ├── Managers
    │   ├── HealthKitManager.swift
    │   └── NetworkManager.swift
    ├── Models
    │   └── TelemetrySample.swift
    ├── Views
    │   ├── ContentView.swift
    │   └── PairingView.swift
    ├── Assets.xcassets         ← keep (you will fill this in Step 6)
    └── AlluciWatch Watch App.entitlements  ← will appear after Step 5
```

If any file is missing from the Navigator, repeat the add-files step for
that file or folder.

### 4.6 — Verify membership in the build target

Click on any of the added Swift files (e.g., `AlluciWatchApp.swift`).
In the right panel (File Inspector), look for "Target Membership".
The checkbox next to "AlluciWatch Watch App" must be **checked**. If it is
not checked, check it now. Repeat this verification for all six files.

---

## Step 5 — Enable HealthKit Capability and Configure Build Settings

### 5.1 — Open the target settings

```
1. Click on the blue "AlluciWatch" project icon at the very top of the
   Project Navigator (the root item, not a folder).

2. In the editor area, the project/targets sidebar appears on the left.
   Under "TARGETS", click "AlluciWatch Watch App".

3. You are now viewing the target settings.
   There are tabs across the top: General | Signing & Capabilities |
   Resource Tags | Info | Build Settings | Build Phases | Build Rules
```

### 5.2 — Set deployment target and Swift version

```
Click the "General" tab.

Under "Deployment Info":
  - watchOS:  10.0   (type this in the minimum version field)

Scroll down to "Frameworks, Libraries, and Embedded Content".
No changes needed here — HealthKit is added via the capability, not
by manually adding a framework.
```

### 5.3 — Enable HealthKit

```
Click the "Signing & Capabilities" tab.

You will see a section called "Signing" at the top, and below it a
"+ Capability" button.

1. Click the "+ Capability" button (top-left of the capability area).

2. A search popover appears. Type "HealthKit".

3. Double-click "HealthKit" in the results list.

   HealthKit now appears as a capability card in the list.

4. Inside the HealthKit capability card:
   - "Clinical Health Records":  UNCHECKED  (leave off — not needed)
   - The basic HealthKit toggle itself should be enabled automatically.
```

After adding HealthKit:

- Xcode automatically creates
  `AlluciWatch Watch App/AlluciWatch Watch App.entitlements`
  with the basic HealthKit key.
- This file appears in the Project Navigator under the target folder.

### 5.4 — Set bundle identifier and Swift version

```
Click the "Build Settings" tab.
Use the filter at the top right to search for each setting.

Search: "PRODUCT_BUNDLE_IDENTIFIER"
  Set to: ai.alluci.AlluciWatch

Search: "SWIFT_VERSION"
  Set to: 5.9

Search: "WATCHOS_DEPLOYMENT_TARGET"
  Confirm it is: 10.0  (matches what you set in General)
```

---

## Step 6 — Replace the .entitlements File Content

Xcode auto-generated the entitlements file with basic HealthKit keys. You
need to add the `healthkit.background-delivery` key now because it is
required by Task A6 (background HRV collection). Adding it now avoids
having to modify the file again later.

### 6.1 — Locate the file

In the Project Navigator, look for:
`AlluciWatch Watch App.entitlements`

It should be inside the `AlluciWatch Watch App` group. Click it to open it
in the editor.

### 6.2 — Replace the file content

Xcode shows entitlements files as a key-value property list editor. You can
edit it directly there, or replace the underlying XML file on disk. The
disk approach is more reliable — use this method:

Close the entitlements file in Xcode. In your terminal:

```bash
# Find the exact path Xcode created
find watchos/AlluciWatch -name "*.entitlements" | head -5
```

The path will be something like:
`watchos/AlluciWatch/AlluciWatch Watch App/AlluciWatch Watch App.entitlements`

Write the correct content to that exact path:

```bash
ENTITLEMENTS_PATH=$(find watchos/AlluciWatch -name "*.entitlements" | head -1)
echo "Writing to: $ENTITLEMENTS_PATH"

cat > "$ENTITLEMENTS_PATH" << 'XML'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>

    <!-- Required: basic HealthKit read access -->
    <key>com.apple.developer.healthkit</key>
    <true/>

    <!-- Required: specifies which HealthKit data types the app accesses.
         An empty array means all types declared in Info.plist typesToRead
         are permitted. Populate with specific type identifiers if you want
         to restrict access at the entitlement level. -->
    <key>com.apple.developer.healthkit.access</key>
    <array/>

    <!-- Required for Task A6: allows HealthKit to wake the app in the
         background when new samples arrive for observed types.
         Without this key, HKObserverQuery only fires in the foreground. -->
    <key>com.apple.developer.healthkit.background-delivery</key>
    <true/>

</dict>
</plist>
XML

echo "Entitlements file written."
cat "$ENTITLEMENTS_PATH"
```

Reopen the file in Xcode by clicking it in the Project Navigator. You should
see three keys in the property list editor:

| Key | Type | Value |
|-----|------|-------|
| HealthKit | Boolean | YES |
| Health Records | — | (not present — correct) |
| `com.apple.developer.healthkit.background-delivery` | Boolean | YES |

> **Note on `background-delivery`:** Apple requires that any app declaring
> this entitlement actually calls `enableBackgroundDelivery(for:frequency:)`
> at runtime. Task A6 implements those calls. If you submit to the App Store
> with this key present but without the corresponding runtime calls, review
> may flag it. For development and simulator builds it is harmless.

---

## Step 7 — Create Info.plist with HealthKit Usage Strings

Apple's privacy framework requires that any app accessing HealthKit data
declares human-readable usage descriptions in `Info.plist`. Without these
strings, the app terminates immediately when it calls
`requestAuthorization(toShare:read:)` — there is no error, just a crash
with no log output.

### 7.1 — Check whether Xcode auto-generated an Info.plist

Modern Xcode projects (Xcode 13+) do not always create a visible `Info.plist`
file. The keys may be inlined into the build settings instead.

```bash
find watchos/AlluciWatch -name "Info.plist" | head -5
```

**If a file is found:** open it in a text editor and add the missing keys
(Step 7.3 below).

**If no file is found:** the keys are managed through the Xcode target Info
tab. Use Step 7.2.

### 7.2 — Adding keys via the Xcode Info tab (no Info.plist file)

```
1. In Xcode, with the "AlluciWatch Watch App" target selected,
   click the "Info" tab.

2. You see a table of "Custom watchOS Target Properties".

3. Hover over any existing row and click the "+" button that appears
   at the right end of the row. A new row is added.

4. In the Key column, type:
   NSHealthShareUsageDescription
   Press Tab to move to the Value column.
   Type:
   Alluci reads Heart Rate and HRV to adapt your AI agent to your
   physiological state in real time.
   Press Return.

5. Repeat: click "+", add a second key:
   Key:   NSHealthUpdateUsageDescription
   Value: Alluci does not write health data.
   Press Return.
```

### 7.3 — Creating the Info.plist file directly (preferred for version control)

Whether or not Xcode has an Info.plist, create this file explicitly so it
is tracked in git and readable without Xcode:

**File path:**
`watchos/AlluciWatch/AlluciWatch Watch App/Info.plist`

```bash
TARGET_DIR=$(find watchos/AlluciWatch -maxdepth 2 -type d -name "AlluciWatch Watch App" | head -1)

if [ -z "$TARGET_DIR" ]; then
  # Xcode may have named the folder differently — find the folder
  # containing AlluciWatchApp.swift
  TARGET_DIR=$(dirname $(find watchos/AlluciWatch -name "AlluciWatchApp.swift" | head -1))
fi

echo "Target directory: $TARGET_DIR"

cat > "$TARGET_DIR/Info.plist" << 'XML'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>

    <!-- App identity -->
    <key>CFBundleDevelopmentRegion</key>
    <string>$(DEVELOPMENT_LANGUAGE)</string>

    <key>CFBundleDisplayName</key>
    <string>Alluci</string>

    <key>CFBundleExecutable</key>
    <string>$(EXECUTABLE_NAME)</string>

    <key>CFBundleIdentifier</key>
    <string>$(PRODUCT_BUNDLE_IDENTIFIER)</string>

    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>

    <key>CFBundleName</key>
    <string>$(PRODUCT_NAME)</string>

    <key>CFBundlePackageType</key>
    <string>$(PRODUCT_BUNDLE_PACKAGE_TYPE)</string>

    <key>CFBundleShortVersionString</key>
    <string>1.0</string>

    <key>CFBundleVersion</key>
    <string>1</string>

    <!-- Required: HealthKit privacy usage descriptions.
         Apple's privacy framework reads these strings and displays them
         in the system permission dialog when requestAuthorization is called.
         Without both keys the app crashes immediately at the authorization call. -->

    <!-- Shown when requesting READ access to health data -->
    <key>NSHealthShareUsageDescription</key>
    <string>Alluci reads Heart Rate and HRV to adapt your AI agent to
your physiological state in real time.</string>

    <!-- Shown when requesting WRITE access (we request none, but the
         key must still be present or the system authorization call fails) -->
    <key>NSHealthUpdateUsageDescription</key>
    <string>Alluci does not write health data.</string>

    <!-- watchOS app marker -->
    <key>WKWatchKitApp</key>
    <true/>

</dict>
</plist>
XML

echo "Info.plist written to $TARGET_DIR/Info.plist"
```

### 7.4 — Link Info.plist to the target in Xcode

If you created the file via the terminal, Xcode will not automatically
know about it. Link it:

```
1. In Xcode, select the "AlluciWatch Watch App" target.

2. Click the "Build Settings" tab.

3. Search for: "INFOPLIST_FILE"

4. Set the value to the relative path of your Info.plist, for example:
   AlluciWatch Watch App/Info.plist

5. Also search for: "GENERATE_INFOPLIST_FILE"
   If this is set to YES, set it to NO — you are providing your own file.
```

---

## Step 8 — Generate Placeholder App Icons

The `Assets.xcassets/AppIcon.appiconset/` catalog must contain icon images
at specific sizes, or the build produces warnings and device deployment fails.
Run this Python script from the repository root to generate minimal teal
placeholder icons. Replace them with real brand assets before any App Store
submission.

```bash
python3 - << 'PYEOF'
"""
Generates minimal solid-colour PNG icons for the Alluci watchOS app.
Colour: Alluci teal  rgb(11, 122, 138)  =  #0B7A8A

All PNG files are created using only Python standard library (struct + zlib).
No Pillow, ImageMagick, or other dependencies required.

Run from the repository root.
"""
import struct
import zlib
from pathlib import Path


def make_png(size: int, r: int, g: int, b: int) -> bytes:
    """
    Creates a minimal, valid, solid-colour RGB PNG of the given size.
    Uses only Python standard library: struct and zlib.
    """
    def chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFF_FFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    # IHDR: width, height, bit depth (8), colour type (2 = RGB), compression,
    # filter method, interlace method
    ihdr_data = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)

    # IDAT: one filter byte (0x00 = None) per row, followed by RGB pixels
    raw_rows = b""
    for _ in range(size):
        raw_rows += b"\x00" + bytes([r, g, b] * size)

    idat_data = zlib.compress(raw_rows)

    return (
        b"\x89PNG\r\n\x1a\n"          # PNG signature
        + chunk(b"IHDR", ihdr_data)
        + chunk(b"IDAT", idat_data)
        + chunk(b"IEND", b"")
    )


# Locate the Assets.xcassets directory created by Xcode
assets_candidates = list(Path("watchos").rglob("AppIcon.appiconset"))
if assets_candidates:
    icon_dir = assets_candidates[0]
    print(f"Found existing AppIcon.appiconset: {icon_dir}")
else:
    # Xcode may not have created it yet — create the full path
    icon_dir = Path(
        "watchos/AlluciWatch/AlluciWatch Watch App/"
        "Assets.xcassets/AppIcon.appiconset"
    )
    icon_dir.mkdir(parents=True, exist_ok=True)
    print(f"Created AppIcon.appiconset: {icon_dir}")

# Alluci teal: rgb(11, 122, 138)
R, G, B = 11, 122, 138

# watchOS requires these specific sizes (points × scale = pixels):
#   44pt @2x = 88px  — Apple Watch Series 4/5/6/SE (40mm)
#   50pt @2x = 100px — Apple Watch Series 4/5/6/SE (44mm)
#   86pt @2x = 172px — Apple Watch Series 7/8/9 (41mm)
#   98pt @2x = 196px — Apple Watch Series 7/8/9 (45mm)
#  108pt @2x = 216px — Apple Watch Ultra / Ultra 2 (49mm)
# 1024pt @1x = 1024px — App Store marketing image
icons = [
    ("icon_88.png",   88),
    ("icon_100.png", 100),
    ("icon_172.png", 172),
    ("icon_196.png", 196),
    ("icon_216.png", 216),
    ("icon_1024.png", 1024),
]

for filename, size in icons:
    path = icon_dir / filename
    path.write_bytes(make_png(size, R, G, B))
    print(f"  Created {path} ({size}×{size}px)")

# Write Contents.json — tells Xcode which image file maps to which slot
contents = """{
  "images": [
    {
      "filename": "icon_88.png",
      "idiom": "watch",
      "role": "appLauncher",
      "scale": "2x",
      "subtype": "40mm"
    },
    {
      "filename": "icon_88.png",
      "idiom": "watch",
      "role": "appLauncher",
      "scale": "2x",
      "subtype": "41mm"
    },
    {
      "filename": "icon_100.png",
      "idiom": "watch",
      "role": "appLauncher",
      "scale": "2x",
      "subtype": "44mm"
    },
    {
      "filename": "icon_100.png",
      "idiom": "watch",
      "role": "appLauncher",
      "scale": "2x",
      "subtype": "45mm"
    },
    {
      "filename": "icon_216.png",
      "idiom": "watch",
      "role": "appLauncher",
      "scale": "2x",
      "subtype": "49mm"
    },
    {
      "filename": "icon_172.png",
      "idiom": "watch",
      "role": "quickLook",
      "scale": "2x",
      "subtype": "41mm"
    },
    {
      "filename": "icon_196.png",
      "idiom": "watch",
      "role": "quickLook",
      "scale": "2x",
      "subtype": "45mm"
    },
    {
      "filename": "icon_216.png",
      "idiom": "watch",
      "role": "quickLook",
      "scale": "2x",
      "subtype": "49mm"
    },
    {
      "filename": "icon_1024.png",
      "idiom": "watch-marketing",
      "scale": "1x",
      "size": "1024x1024"
    }
  ],
  "info": {
    "author": "alluci-script",
    "version": 1
  }
}
"""

contents_path = icon_dir / "Contents.json"
contents_path.write_text(contents)
print(f"  Created {contents_path}")

print()
print("Done. Replace these placeholder icons with real brand")
print("assets before any App Store or TestFlight submission.")
PYEOF
```

After running this script, verify the icons were created:

```bash
find watchos -name "*.png" | sort
find watchos -name "Contents.json" | sort
```

---

## Step 9 — Verify the Final File Structure

At this point the `watchos/AlluciWatch/` directory should contain:

```
watchos/AlluciWatch/
├── AlluciWatch.xcodeproj/               ← created by Xcode in Step 2
│   ├── project.pbxproj
│   └── project.xcworkspace/
├── AlluciWatch Watch App/               ← created by Xcode in Step 2
│   ├── AlluciWatchApp.swift             ← existing file, added in Step 4
│   ├── Managers/
│   │   ├── HealthKitManager.swift       ← existing file, added in Step 4
│   │   └── NetworkManager.swift         ← existing file, added in Step 4
│   ├── Models/
│   │   └── TelemetrySample.swift        ← existing file, added in Step 4
│   ├── Views/
│   │   ├── ContentView.swift            ← existing file, added in Step 4
│   │   └── PairingView.swift            ← existing file, added in Step 4
│   ├── Assets.xcassets/
│   │   └── AppIcon.appiconset/
│   │       ├── Contents.json            ← created in Step 8
│   │       ├── icon_88.png              ← created in Step 8
│   │       ├── icon_100.png             ← created in Step 8
│   │       ├── icon_172.png             ← created in Step 8
│   │       ├── icon_196.png             ← created in Step 8
│   │       ├── icon_216.png             ← created in Step 8
│   │       └── icon_1024.png            ← created in Step 8
│   ├── Info.plist                       ← created in Step 7
│   └── AlluciWatch Watch App.entitlements ← created/replaced in Step 6
└── AlluciWatch Watch AppTests/          ← created by Xcode (keep)
    └── AlluciWatch_Watch_AppTests.swift
```

---

## Step 10 — First Build in Xcode (Sanity Check)

Before running the command-line build, do a quick GUI build to catch
Xcode-level configuration problems with clear error messages.

```
1. In Xcode, select a simulator destination from the toolbar at the top.
   Click the device selector (it shows the current destination, e.g.
   "My Mac (Mac Catalyst)") and choose:
   "Apple Watch Series 9 (45mm)" or "Apple Watch Ultra 2 (49mm)"
   from the watchOS Simulators section.

2. Press Cmd + B to build.

3. Watch the activity indicator in the toolbar and the Issue Navigator
   (the warning triangle icon in the left panel).
```

---

## Step 11 — Command-Line Build Verification

Once the GUI build passes in Step 10, run this command-line build. This is
the exact command used by the CI pipeline (Task C2) and must pass cleanly.

```bash
xcodebuild build \
  -project watchos/AlluciWatch/AlluciWatch.xcodeproj \
  -scheme "AlluciWatch Watch App" \
  -destination "platform=watchOS Simulator,name=Apple Watch Series 9 (45mm)" \
  CODE_SIGNING_ALLOWED=NO \
  ONLY_ACTIVE_ARCH=NO \
  2>&1 | tee /tmp/alluci_watch_build.log | grep -E "error:|warning:|BUILD SUCCEEDED|BUILD FAILED"
```

---

## Step 12 — Commit the New Files

The Xcode project file and all supporting files should be committed to git.

```bash
git add watchos/AlluciWatch/AlluciWatch.xcodeproj/
git add watchos/AlluciWatch/AlluciWatch\ Watch\ App/Info.plist
git add watchos/AlluciWatch/AlluciWatch\ Watch\ App/AlluciWatch\ Watch\ App.entitlements
git add watchos/AlluciWatch/AlluciWatch\ Watch\ App/Assets.xcassets/
git status
```
