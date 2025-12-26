# Group Guardian 🛡️

![Version](https://img.shields.io/badge/version-1.0.0-blueviolet) ![Python](https://img.shields.io/badge/python-3.11+-blue) ![Flet](https://img.shields.io/badge/built%20with-Flet-00B0FF) ![License](https://img.shields.io/badge/license-MIT-green)

**Group Guardian** is a robust and stylish **VRChat Group Moderation Automation Tool**. Built with [Flet](https://flet.dev) and Python, it offers a cross-platform solution (Windows & Android) to manage your VRChat groups efficiently with a modern, cyberpunk-inspired interface.

---

## ✨ Features

### 📊 **Interactive Dashboard**
- View real-time statistics on active instances, pending join requests, and recent activity log.
- Quick navigation to key moderation tools.

### 👥 **Member Management**
- **Searchable Member List**: Quickly find users within your group.
- **Role Management**: Assign and revoke roles with ease.
- **Moderation Actions**: Kick or ban disruptive members directly from the app.

### 📝 **Join Request Handling**
- **Review Requests**: View detailed profiles of users requesting to join.
- **Auto-Screening**: (Planned) Automatically flag requests based on keyword matches.
- **Quick Actions**: Accept or reject requests efficiently.

### 🚫 **Ban Management**
- **Ban List**: View all banned users with reasons.
- **Unban**: Revoke bans when necessary.

### 📜 **Audit Logs**
- **Activity Tracking**: Keep an eye on all administrative actions and group events.
- **Filtering**: Filter logs by type for easy auditing.

### 📱 **Cross-Platform & Modern UI**
- **Flet Powered**: Seamless performance on both Desktop and Android.
- **Cyberpunk Aesthetic**: sleek dark mode with vibrant accents and glassmorphism elements.

### 🧪 **Demo Mode**
- **Try Before You Login**: Integrated **Demo Mode** populated with mock data (randomized users, bio, and stats) to explore the UI and features without needing a VRChat account login.

---

## 🛠️ Technology Stack

- **[Python](https://www.python.org/)** (3.11+)
- **[Flet](https://flet.dev/)** - UI Framework for Python
- **[HTTPX](https://www.python-httpx.org/)** - Asynchronous HTTP Client
- **[Pydantic](https://docs.pydantic.dev/)** - Data Validation
- **[Loguru](https://github.com/Delgan/loguru)** - Logging made easy

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11 or higher installed.

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/group-guardian.git
   cd group-guardian
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

### Running the Application

**Standard Mode (Requires VRChat Login):**
```bash
flet run src/main.py
```

**Demo Mode (Mock Data):**
```bash
python demo.py
```

---

## 🏗️ Project Structure

```
group_guardian/
├── src/
│   ├── api/            # VRChat API client and endpoints
│   ├── ui/             # Flet UI views and components
│   ├── services/       # Background services (auth, cache, etc.)
│   ├── models/         # Pydantic data models
│   └── main.py         # Application entry point
├── demo.py             # Demo mode launcher
├── pyproject.toml      # Project configuration and dependencies
└── requirements.txt    # Python dependencies
```

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

---

*Note: This tool is a third-party application and is not endorsed by or affiliated with VRChat Inc.*
