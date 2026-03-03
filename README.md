# Discordboy

uh oh discord data hmmm virgule only for now i guess

## What you need

- Python 3.10+
- pip

## Installation

### Windows

```powershell
python -m venv discvenv
.\discvenv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .
```

### Linux

```bash
python3 -m venv discvenv
source discvenv/bin/activate
python -m pip install --upgrade pip
pip install -e .
```

## Config

`.env`
```env
DISCORD_TOKEN=your_discord_token_here
```

## Launch

```bash
python main.py --scrape-server --web
```

Or dashboard :

```bash
python main.py --web-only
```
python main.py
```
