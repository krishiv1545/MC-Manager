# MC-Manager

MC-Manager is a tool meant to organize a local homeserver for Minecraft. The goal of development has steadily been ease-of-use. It should merely take minutes before you can hop on your own local Minecraft server for no cost aside for your own hardware.

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

We offer a few ways to run MC-Manager. Running via **Docker** is the recommended method because it's the absolute easiest and keeps everything contained safely.

### Option 1: Running with Docker (Recommended) 🐳

This method is super simple. You just need to have [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker Engine) installed on your computer.

1. **Clone or download this repository** to your computer.
   ```bash
   git clone https://github.com/krishiv1545/MC-Manager.git
   ```

2. **Set up your environment variables:**

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

4. **Access the Dashboard:**
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

3. **Configure your `.env` file:**
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
A: Once you create a server, you are the "Owner". Click the gold **🔑 Manage Access** button on the dashboard next to your server to grant your friends access. They must have an account on your MC-Manager first.

**Q: If MC-Manager works but the Minecraft Server won't start**  
A: Check if the port (default is 25565) is already in use by another server on your machine, and ensure you have Docker running in the background. Port is displayed on the Dashboard under Address column as IP:PORT (for example 10.249.248.38:25566) where '25566' is the port.

**Q: Where are the server files actually located?**  
A: They are stored in the directory you specified in the `.env` file (`HOST_MC_SERVER_HOME` for Docker, or `MC_SERVER_HOME` for standard Django). Inside, you'll find a separate folder for each server, complete with a `data/` directory and its own `docker-compose.yml`.

---

*Built with ❤️ using Django and Docker.*
