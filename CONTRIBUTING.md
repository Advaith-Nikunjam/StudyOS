# Contributing to StudyOS

Thank you for your interest in contributing to StudyOS! This document provides guidelines and instructions for contributing to the repository.

---

## 🛠️ Development Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/StudyOS.git
   cd StudyOS
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize database & start local server**:
   ```bash
   python -m app.db.init_db
   python main.py
   ```

---

## 🧪 Running Tests

StudyOS uses `pytest` and `pytest-asyncio` for test suites.

```bash
pytest
```
Ensure all tests pass before submitting a pull request.

---

## 📋 Pull Request Process

1. Fork the repository and create your branch from `main`:
   ```bash
   git checkout -b feature/my-new-feature
   ```
2. Write clean, readable Python code adhering to standard conventions (PEP 8).
3. Ensure no sensitive keys, `.env` files, or `.sqlite` files are committed.
4. Run tests and verify the wall display kiosk endpoints respond properly.
5. Push to your branch and open a Pull Request describing your changes.

---

## 🛡️ Action Safety Guidelines

When adding commands to JARVIS, ensure risk tiers are respected:
- **SAFE**: Non-destructive read/log commands.
- **MODERATE**: Requires confirmation preview before mutation.
- **HIGH-RISK**: Requires explicit double confirmation (e.g. deleting logs or resetting sprint state).
