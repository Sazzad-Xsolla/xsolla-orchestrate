#!/bin/bash
set -euo pipefail
SKILL_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUTPUT_DIR="${1:-$SKILL_ROOT/../outputs}"
mkdir -p "$OUTPUT_DIR"
OUTPUT_DIR="$(cd "$OUTPUT_DIR" && pwd)"
APP="$OUTPUT_DIR/Xsolla Field Team.app"
BUILD_DIR="$OUTPUT_DIR/field-team-build"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources/runtime" "$BUILD_DIR/cache" "$BUILD_DIR/tmp"
export TMPDIR="$BUILD_DIR/tmp/"
python3 "$SKILL_ROOT/scripts/build_view.py"
swiftc "$SKILL_ROOT/desktop/BridgeResponse.swift" "$SKILL_ROOT/desktop/MotionPose.swift" "$SKILL_ROOT/desktop/MotionState.swift" "$SKILL_ROOT/desktop/FieldTeam.swift" -o "$APP/Contents/MacOS/FieldTeam" -module-cache-path "$BUILD_DIR/cache" -framework AppKit -framework WebKit -O
cp "$SKILL_ROOT/desktop/bridge.py" "$APP/Contents/Resources/bridge.py"
cp "$SKILL_ROOT/assets/field-team/cozy-motion.png" "$APP/Contents/Resources/cozy-motion.png"
printf '%s\n' "$SKILL_ROOT" > "$APP/Contents/Resources/skill-path.txt"
for folder in scripts assets config profiles references prototypes; do
    mkdir -p "$APP/Contents/Resources/runtime/$folder"
    cp -R "$SKILL_ROOT/$folder/." "$APP/Contents/Resources/runtime/$folder/"
done
cp "$SKILL_ROOT/SKILL.md" "$APP/Contents/Resources/runtime/"
cat > "$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleName</key><string>Xsolla Field Team</string>
<key>CFBundleDisplayName</key><string>Xsolla Field Team</string>
<key>CFBundleIdentifier</key><string>local.xsolla.fieldteam</string>
<key>CFBundleExecutable</key><string>FieldTeam</string>
<key>CFBundleVersion</key><string>3</string>
<key>CFBundleShortVersionString</key><string>0.3.0</string>
<key>CFBundlePackageType</key><string>APPL</string>
<key>LSUIElement</key><true/>
<key>NSHighResolutionCapable</key><true/>
<key>LSMinimumSystemVersion</key><string>12.0</string>
<key>NSAppTransportSecurity</key><dict><key>NSAllowsLocalNetworking</key><true/></dict>
</dict></plist>
PLIST
codesign --force --sign - "$APP"
printf 'Built: %s\n' "$APP"
