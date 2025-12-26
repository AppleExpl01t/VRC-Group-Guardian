---
description: Build and release a new version of Group Guardian
---

# Build New Release Workflow

Follow these steps EXACTLY when building a new release:

## 1. Read Current Version
- Open `src/services/updater.py`
- Find `CURRENT_VERSION = "X.Y.Z"`
- Note the current version

## 2. Bump Version
- Increment the patch version (e.g., 1.0.1 → 1.0.2)
- Or increment minor/major as appropriate
- Update the `CURRENT_VERSION` string in updater.py

## 3. Build the EXE
// turbo
```powershell
$env:PYTHONPATH="src"; F:\Python\Scripts\flet.exe pack src/main.py --name GroupGuardian --icon src/assets/icon.ico --add-data "src/assets;assets" --product-name "Group Guardian" --product-version "X.Y.Z" --copyright "Copyright (c) 2025" --hidden-import "api" --hidden-import "ui" --hidden-import "services" --hidden-import "services.updater" --hidden-import "models" --hidden-import "utils"
```
- Answer "y" to both prompts about deleting build/dist directories

## 4. Commit and Push Version Bump
// turbo
```powershell
git add src/services/updater.py
git commit -m "Bump version to X.Y.Z"
git push
```

## 5. CRITICAL: Tell User the Release Tag

After EVERY successful build, display this message in BIG BOLD TEXT:

```
# 🚨 RELEASE TAG REMINDER 🚨

## When creating your GitHub release, use this EXACT tag:

# `vX.Y.Z`

### Copy and paste this tag into the "Tag version" field!

EXE Location: dist/GroupGuardian.exe
```

Replace X.Y.Z with the actual version number you just built.

## Notes
- The tag MUST match the version embedded in the EXE
- Without the correct tag, the auto-updater will not work properly
- Users running this version will see "You are up to date" only if the tag matches
