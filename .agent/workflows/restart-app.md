---
description: Reminder to restart the app after code changes
---

# IMPORTANT REMINDER

**After making ANY code changes, you MUST restart the application to test them!**

## Steps:

// turbo-all

1. Stop any running Python processes:

```powershell
Stop-Process -Name "python" -Force -ErrorAction SilentlyContinue
```

2. Wait a moment for graceful shutdown:

```powershell
Start-Sleep -Seconds 2
```

3. Start the application:

```powershell
py src/main.py
```

## Why This Matters

- Python doesn't hot-reload code changes
- The user won't see your changes until the app restarts
- Always verify your changes work by running the app

**DO NOT FORGET THIS STEP!**
