# Makefile for Discordboy project

.PHONY: web scrape-channel scrape-server all

# Variables (edit as needed)
PYTHON=python
VENV=discvenv
ACTIVATE=.\$(VENV)\Scripts\activate

# 1. Lancer UNIQUEMENT le serveur web
ifdef SERVER
web:
	$(PYTHON) main.py --web-only --server $(SERVER)
else
web:
	$(PYTHON) main.py --web-only
endif

# 2. Lancer UNIQUEMENT la recherche de messages dans un channel
scrape-channel:
	$(PYTHON) main.py --scrape-channel $(CHANNEL)

# 3. Lancer UNIQUEMENT la recherche de messages dans un serveur entier
scrape-server:
ifdef SERVER
	$(PYTHON) main.py --scrape-server --server $(SERVER)
else
	$(PYTHON) main.py --scrape-server
endif

# 4. Lancer toute l'application (scrape serveur + web)
all:
	$(PYTHON) main.py --scrape-server --web

# Optionally, add a rule to activate the venv and install dependencies
install:
	$(PYTHON) -m venv $(VENV)
	$(ACTIVATE) && pip install -e .
