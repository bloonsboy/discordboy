# Discordboy

This project analyzes activity from a Discord server and displays it in an interactive web dashboard.

## Installation & Setup

This project uses a `pyproject.toml` file to manage dependencies. Follow these steps to create a clean environment and install the required packages.

### Prerequisites

- Python 3.10 or newer
- `pip` and `venv` (usually included with Python)

### 1. Create a Virtual Environment

First, create a virtual environment in your project folder. This keeps the project's dependencies isolated from your main system.

```sh
# From your project's root directory (where pyproject.toml is)
python -m venv discvenv
```

### 2. Activate the Virtual Environment

Next, you need to activate the environment in your terminal session.

**On Windows (PowerShell/CMD):**

```sh
.\discvenv\Scripts\activate
```

**On macOS / Linux (Bash/Zsh):**

```sh
source discordboy/bin/activate
```

### 3. Install Dependencies

With the virtual environment active, use pip. pip will automatically read the pyproject.toml file and install all listed dependencies.

```sh
pip install -e .
```

### 4. Launch the Application

Make sure you have a .env file at the root of your project containing your DISCORD_TOKEN, and then run the main script:

```sh
python main.py
```
