# MC-Manager

![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white) ![Django](https://img.shields.io/badge/Django-092E20?style=flat&logo=django) ![SQLite](https://img.shields.io/badge/SQLite-003B57?style=flat&logo=sqlite&logoColor=white) ![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white) ![Docker Compose](https://img.shields.io/badge/Docker%20Compose-2496ED?style=flat&logo=docker&logoColor=white) ![Minecraft](https://img.shields.io/badge/Minecraft_Server-62B47A?style=flat)

MC-Manager is a web-based tool for managing Minecraft servers on a local home server. It is designed to make self-hosting as simple as possible, allowing you to create and manage Minecraft servers in just a few minutes at no cost other than your own hardware.

---

## Features

- Create Minecraft servers instantly through a simple web interface.
- Configure the Minecraft version, mod loader, and RAM allocation during creation.
- Start and stop servers with a single click from a centralized dashboard.
- Edit `server.properties` and update server settings from the browser.
- Share management access to specific servers with other accounts.
- Player data management (under development).

---

## Setup MC-Manager:

### Option 1: Running with Docker (Recommended) 🐳

This is the recommended installation method. It requires Docker Desktop (Windows/macOS) or Docker Engine with Docker Compose (Linux).

1. **Clone or download this repository** to your computer.
   ```bash
   git clone https://github.com/krishiv1545/MC-Manager.git
   ```

2. **Configure environmental variables**

   Copy the `.env.example` file and rename it to `.env`.

   For Windows:-
   ```bash
   copy .env.example .env
   ```
   For Linux/MacOS:-
   ```bash
   cp .env.example .env
   ```

   Open `.env` and set `HOST_MC_SERVER_HOME` to a folder on your computer where you want all your Minecraft servers to be saved (e.g., `C:\MCServers` on Windows, or `/srv/minecraft` on Linux).

   Set a secure `SECRET_PIN` (you will need this PIN to create an account).

3. **Start the app:**
   Open your terminal in the project folder and run:
   ```bash
   docker compose up -d
   ```

4. **Stop the app:**
   To shutdown MC-Manager (this does not lose your Minecraft Servers, progress or account data):
   ```bash
   docker compose down
   ```

5. **Access the Dashboard:**
   Open your browser and go to `http://localhost:8000`. You can now sign up using your secret PIN.

---

### Option 2: Running as a Standard Django App 🐍

If you prefer to run the Django application directly on your host machine (note: you **still need Docker installed** so MC-Manager can spin up the actual Minecraft servers):

1. **Install Python** (3.10+ recommended) and [Docker](https://docs.docker.com/engine/install/).

2. **Set up the project:**
   ```bash
   # Create a virtual environment
   python -m venv venv
   
   # Activate it (Windows)
   venv\Scripts\activate
   # Activate it (Mac/Linux)
   source venv/bin/activate
   
   # Install dependencies
   pip install -r requirements.txt
   ```

3. **Configure environmental variables**
   Copy the `.env.example` file and rename it to `.env`.

   For Windows:-
   ```bash
   copy .env.example .env
   ```
   For Linux/MacOS:-
   ```bash
   cp .env.example .env
   ```

   Open `.env` and set `HOST_MC_SERVER_HOME` to a folder on your computer where you want all your Minecraft servers to be saved (e.g., `C:\MCServers` on Windows, or `/srv/minecraft` on Linux).

   Set a secure `SECRET_PIN` (you will need this PIN to create an account).

4. **Apply database migrations:**
   ```bash
   cd backend
   python manage.py migrate
   ```

5. **Run the server:**
   ```bash
   python manage.py runserver
   ```
6. **Access the Dashboard:** 
   Go to `http://localhost:8000` in your web browser.

---

**Q: How to invite friends to manage a server?**  
A: Once you create a server, you are the "Owner". Click the gold **Manage Access** button on the dashboard next to your server to grant your friends access. They must have an account on your MC-Manager first.

**Q: If MC-Manager works but the Minecraft Server won't start**  
A: Check if the port (default is 25565) is already in use by another server on your machine, and ensure you have Docker running in the background. Port is displayed on the Dashboard under Address column as IP:PORT (for example 10.249.248.38:25566) where '25566' is the port.

**Q: Where are the server files actually located?**  
A: They are stored in the directory you specified in the `.env` file (`HOST_MC_SERVER_HOME` for Docker, or `MC_SERVER_HOME` for standard Django). Inside, you'll find a separate folder for each server, complete with a `data/` directory and its own `docker-compose.yml`.