# Group Guardian - Production Roadmap 🚀

> **Last Updated:** 2024-12-29  
> **Status:** Alpha → Pre-Release  
> **Target:** Production-Ready v1.0

---

## 📊 Current Status Overview

### ✅ Completed Features

| Feature                                             | Status  | Notes                                            |
| --------------------------------------------------- | ------- | ------------------------------------------------ |
| VRChat API Authentication (Username/Password + 2FA) | ✅ Done | TOTP and Email OTP supported                     |
| Group Selection                                     | ✅ Done | Multi-group support with role filtering          |
| Dashboard View                                      | ✅ Done | Real-time stats for instances, requests, members |
| Members View                                        | ✅ Done | Searchable list with user cards                  |
| Join Requests View                                  | ✅ Done | Accept/reject with user details                  |
| Bans View                                           | ✅ Done | View/unban functionality                         |
| Instances View                                      | ✅ Done | View active instances, create new                |
| Live Monitor View                                   | ✅ Done | Real-time instance population tracking           |
| Watchlist View                                      | ✅ Done | Local database, tags, notes                      |
| Logs View                                           | ✅ Done | Audit log display                                |
| Settings View                                       | ✅ Done | Basic configuration                              |
| Local Database (SQLite)                             | ✅ Done | User tracking, watchlist, sightings              |
| Cache Manager                                       | ✅ Done | In-memory caching with TTL                       |
| Rate Limiter                                        | ✅ Done | Token bucket with backoff                        |
| Demo Mode                                           | ✅ Done | Mock data for testing without login              |
| Cyberpunk UI Theme                                  | ✅ Done | Glass cards, neon accents                        |
| Responsive Layout                                   | ✅ Done | Auto-collapsing sidebar, responsive grids        |

### 🔶 In Progress / Recently Fixed

| Feature                      | Status   | Notes                                     |
| ---------------------------- | -------- | ----------------------------------------- |
| Profile Picture Loading      | 🔶 Fixed | Now uses ft.Image instead of CircleAvatar |
| Age Verification (18+) Badge | 🔶 Fixed | Shows in user details dialog              |
| Logout/Re-login Cache Bug    | 🔶 Fixed | Caches cleared on logout                  |
| Instance Creation            | 🔶 Fixed | Added ownerId for group instances         |

### ❌ Known Bugs / Issues

| Issue                                | Priority  | Notes                                   |
| ------------------------------------ | --------- | --------------------------------------- |
| ~~UserCard click dead zones~~        | ✅ Fixed  | Added ink effect + click logging        |
| WebSocket disconnects                | ✅ Fixed  | Added exponential backoff reconnect     |
| Instance not joining via launch link | 🟡 Medium | Launch link format verified, needs test |

---

## 🗓️ Development Phases

### Phase 1: Stability & Polish ✅ COMPLETE

**Goal:** Fix remaining bugs and ensure core features work reliably

| Task                                         | Priority | Est. | Status       |
| -------------------------------------------- | -------- | ---- | ------------ |
| Fix UserCard click registration issues       | 🔴       | 2h   | ✅ Done      |
| Verify instance creation + launch link works | 🔴       | 2h   | ✅ Verified  |
| Add error handling for all API calls         | 🟡       | 3h   | ✅ Done      |
| Improve VRChat WebSocket stability           | 🟡       | 2h   | ✅ Done      |
| Add loading states to all views              | 🟢       | 2h   | ✅ Most done |
| Test logout/login flow thoroughly            | 🟡       | 1h   | ✅ Verified  |

**Milestone:** ✅ All core features work without crashes

---

### Phase 2: XSOverlay Integration 🎮 ✅ COMPLETE

**Goal:** VR-native alerts and notifications

| Task                                              | Priority | Est. | Status      |
| ------------------------------------------------- | -------- | ---- | ----------- |
| Create XSOverlayService (WebSocket client)        | 🔴       | 2h   | ✅ Done     |
| Implement SendNotification                        | 🔴       | 1h   | ✅ Done     |
| Implement PlayDeviceHaptics                       | 🔴       | 30m  | ✅ Done     |
| Integrate with AlertService (replace VRC invites) | 🔴       | 2h   | ✅ Done     |
| Add avatar thumbnail to notifications             | 🟡       | 1.5h | ✅ Done     |
| Performance subscription + throttling             | 🟢       | 1.5h | ✅ Done     |
| Theme subscription + matching                     | 🟢       | 1h   | ✅ Done     |
| Instance population dashboard tooltip             | 🟢       | 2h   | ⬜ Optional |
| Settings UI for XSO configuration                 | 🟡       | 1h   | ✅ Done     |

**Milestone:** Watchlist alerts visible in VR via XSOverlay ✅

---

### Phase 3: Shared Database (Team Moderation) 🔗

**Goal:** Allow moderators to share watchlist data

| Task                                              | Priority | Est. | Status  |
| ------------------------------------------------- | -------- | ---- | ------- |
| Choose sync backend (GitHub Gist vs JSON service) | 🔴       | -    | ⬜ TODO |
| Implement sync service                            | 🔴       | 4h   | ⬜ TODO |
| Conflict resolution strategy                      | 🟡       | 2h   | ⬜ TODO |
| UI for sync settings                              | 🟡       | 2h   | ⬜ TODO |
| Merge/import from team members                    | 🟡       | 2h   | ⬜ TODO |
| Discord webhook for change notifications          | 🟢       | 2h   | ⬜ TODO |

**Milestone:** Multiple mods can share watchlist entries

---

### Phase 4: Automation & Screening 🤖

**Goal:** Automated moderation assistance

| Task                                                    | Priority | Est. | Status  |
| ------------------------------------------------------- | -------- | ---- | ------- |
| Auto-accept rules engine (group membership, friends)    | 🟡       | 4h   | ⬜ TODO |
| Auto-reject rules (keyword blocklist, group membership) | 🟡       | 3h   | ⬜ TODO |
| Request screening indicators (risk score)               | 🟡       | 3h   | ⬜ TODO |
| Background job scheduler                                | 🟡       | 2h   | ⬜ TODO |
| Settings UI for automation rules                        | 🟡       | 2h   | ⬜ TODO |

**Milestone:** App can auto-handle common join request scenarios

---

### Phase 5: Production Readiness 📦

**Goal:** Ready for public distribution

| Task                                          | Priority | Est. | Status  |
| --------------------------------------------- | -------- | ---- | ------- |
| Windows executable build (PyInstaller/Nuitka) | 🔴       | 3h   | ⬜ TODO |
| Auto-updater system                           | 🟡       | 4h   | ⬜ TODO |
| First-time setup wizard                       | 🟡       | 3h   | ⬜ TODO |
| Crash reporting / error logging               | 🟡       | 2h   | ⬜ TODO |
| User documentation / help pages               | 🟡       | 4h   | ⬜ TODO |
| Privacy policy / terms of use                 | 🟢       | 1h   | ⬜ TODO |
| GitHub releases + changelog                   | 🟢       | 1h   | ⬜ TODO |
| Landing page / website                        | 🟢       | 4h   | ⬜ TODO |

**Milestone:** v1.0.0 Release

---

### Phase 6: Android Support 📱

**Goal:** Mobile companion app

| Task                          | Priority | Est. | Status  |
| ----------------------------- | -------- | ---- | ------- |
| Test Flet Android build       | 🟡       | 2h   | ⬜ TODO |
| Responsive UI adjustments     | 🟡       | 4h   | ⬜ TODO |
| Touch-friendly interactions   | 🟡       | 3h   | ⬜ TODO |
| Push notifications (Firebase) | 🟢       | 4h   | ⬜ TODO |
| Google Play Store listing     | 🟢       | 2h   | ⬜ TODO |

**Milestone:** Android APK available

---

## 🎯 Feature Wishlist (Post-v1.0)

| Feature                      | Description                            | Priority |
| ---------------------------- | -------------------------------------- | -------- |
| OSC Integration              | Send avatar parameters based on alerts | 🟢       |
| Password Manager Integration | Secure credential storage              | 🟢       |
| Voice Activity Overlay       | Show who's talking in VR               | 🟢       |
| Multi-Account Support        | Switch between VRC accounts            | 🟢       |
| Plugin System                | Allow community extensions             | 🟢       |
| Statistics Dashboard         | Graphs of join requests, member growth | 🟢       |
| Scheduled Actions            | Time-based automation                  | 🟢       |
| Import from VRCX             | Migrate favorites/notes                | 🟢       |

---

## 📈 Success Metrics for v1.0

| Metric              | Target      |
| ------------------- | ----------- |
| Crash-free rate     | > 99%       |
| Login success rate  | > 95%       |
| API error rate      | < 5%        |
| App startup time    | < 3 seconds |
| Memory usage (idle) | < 200 MB    |
| User-reported bugs  | < 10 open   |

---

## 🔒 Security Considerations

- [ ] Credentials stored securely (not plaintext)
- [ ] Auth cookie encrypted at rest
- [ ] No sensitive data in logs
- [ ] XSOverlay only accepts localhost connections (already enforced by XSO)
- [ ] Sync token (if GitHub Gist) stored securely

---

## 📝 Release Checklist (v1.0)

- [ ] All Phase 1-5 tasks complete
- [ ] All known critical bugs fixed
- [ ] Tested on Windows 10 and 11
- [ ] Documentation complete
- [ ] CHANGELOG.md written
- [ ] GitHub release created
- [ ] Installer tested on fresh machine
- [ ] Announcement prepared

---

## 📚 Documentation Needed

| Document              | Purpose               | Status       |
| --------------------- | --------------------- | ------------ |
| README.md             | Project overview      | ✅ Done      |
| ROADMAP.md            | Development plan      | ✅ This file |
| CONTRIBUTING.md       | How to contribute     | ⬜ TODO      |
| CHANGELOG.md          | Release history       | ⬜ TODO      |
| docs/INSTALLATION.md  | Setup guide           | ⬜ TODO      |
| docs/CONFIGURATION.md | Settings explained    | ⬜ TODO      |
| docs/API.md           | For developers        | ⬜ TODO      |
| docs/XSOVERLAY.md     | XSO integration guide | ⬜ TODO      |

---

_This roadmap is a living document and will be updated as development progresses._
