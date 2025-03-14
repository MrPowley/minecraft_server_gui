import tkinter
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter.messagebox import showerror
from PIL import ImageTk, Image
import threading
import os
import subprocess
from datetime import datetime
import shutil
import re
import urllib.request
import io
import atexit
import psutil
import time
import json


def get_time(format: str = "%Y_%m_%d-%H_%M_%S") -> str:
    return datetime.now().strftime(format)


def kill_process_tree(pid):
    """Tue un processus et tous ses enfants."""
    try:
        parent = psutil.Process(pid)
        for child in parent.children(recursive=True):  # Récupère tous les processus enfants
            child.terminate()
        parent.terminate()
    except psutil.NoSuchProcess:
        pass


def extract_content(message: str) -> str:
    pattern_tag = re.compile(
        r"\[([0-9]+(:[0-9]+)+) (TRACE|DEBUG|INFO|NOTICE|WARN|WARNING|ERROR|SEVERE|FATAL)]: ",
        re.IGNORECASE
    )

    return pattern_tag.sub("", message).strip()


def check_log_level(line: str) -> str:
    pattern_tag = re.compile(
        r"\[([0-9]+(:[0-9]+)+) (TRACE|DEBUG|INFO|NOTICE|WARN|WARNING|ERROR|SEVERE|FATAL)]",
        re.IGNORECASE
    )
    if match := pattern_tag.match(line):
        return match.group(3)

    return "LOG"


def is_op(server_path, uuid):
    with open(server_path+"/ops.json", "r") as f:
        data = json.load(f)
    for player in data:
        if player["uuid"] == uuid:
            return True
    return False


class MinecraftServer:
    def __init__(self, root, config, console_text, start_button, stop_button, backup_button, kill_button, PWD,
                 auto_scroll_var, command_entry, player_list):
        self.stop_requested = None
        self.server_process = None
        self.root = root
        self.config = config
        self.console_text = console_text
        self.start_button = start_button
        self.stop_button = stop_button
        self.kill_button = kill_button
        self.backup_button = backup_button
        self.PWD = PWD
        self.auto_scroll_var = auto_scroll_var
        self.command_entry = command_entry
        self.player_list = player_list
        self.players = {}

    def start_server(self):
        if self.server_process is not None:
            self.log_message("Le serveur est déjà en cours d'exécution.", "WARN")
            return
        try:
            if self.config.get("server_path"):
                os.chdir(self.config.get("server_path"))

            self.server_process = subprocess.Popen(
                [self.config.get("java_path"), f"-Xmx{self.config.get("ram")}M", "-jar", self.config.get("server_jar"),
                 "nogui"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            atexit.register(self.server_process.kill)

            self.log_message("Démarrage du serveur.", "LOG")
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.kill_button.config(state=tk.NORMAL)
            self.backup_button.config(state=tk.DISABLED)

            server_log_parser = ServerLogParser(self.server_process, self.log_message, self.player_list, self.players, self.config)
            threading.Thread(target=server_log_parser.monitor_server_process, daemon=True).start()
            os.chdir(self.PWD)
        except Exception as e:
            self.log_message(f"Erreur lors du démarrage du serveur : {e}", "WARN")
            messagebox.showerror("Erreur", "Impossible de démarrer le serveur.")

    def stop_server(self):
        if self.server_process:
            self.stop_requested = True
            self.send_command("stop")
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.kill_button.config(state=tk.DISABLED)
            self.backup_button.config(state=tk.NORMAL)
            self.log_message("Serveur Minecraft arrêté.", "LOG")
            self.server_process.wait()
            self.server_process = None
        else:
            self.log_message("Aucun serveur n'est en cours d'exécution.", "WARN")

    # Fonction pour arrêter le serveur
    def kill_server(self):
        if self.server_process:
            kill_process_tree(self.server_process.pid)
            self.server_process.wait()
            self.server_process = None
            try:
                self.start_button.config(state=tk.NORMAL)
                self.stop_button.config(state=tk.DISABLED)
                self.kill_button.config(state=tk.DISABLED)
                self.backup_button.config(state=tk.NORMAL)
            except tkinter.TclError:
                pass
            self.log_message("Processus Java tué", "LOG")
            self.log_message("Serveur Minecraft arrêté.", "LOG")
        else:
            self.log_message("Aucun serveur n'est en cours d'exécution.", "WARN")

    def backup_server(self):
        if self.server_process:
            showerror("Backup", "Le serveur est en fonctionnement, arretez le pour effetuer la backup")
            return

        self.log_message("Starting Backup Now", "LOG")
        backup_path = os.path.join(self.PWD, "..", "backup")
        if not os.path.exists(backup_path):
            os.mkdir(backup_path)
        now = get_time()
        shutil.make_archive(os.path.join(backup_path, f"Backup-{now}"), "zip", self.PWD)
        self.log_message("Server backed up", "LOG")

    def log_message(self, message, tag="LOG", mc_console: bool = False):
        if not mc_console:
            now = get_time("%H:%M:%S")
            time = f"[{now} {tag}]"
            message = f"{time}: {message}"

        try:
            self.console_text.config(state=tk.NORMAL)
            self.console_text.insert(tk.END, message + "\n", tag)
            self.console_text.config(state=tk.DISABLED)
            if self.auto_scroll_var.get() == 1:
                self.console_text.yview(tk.END)
            return
        except tkinter.TclError:
            pass

    def send_command(self, command=None):
        if not command or not isinstance(command, str):
            command = self.command_entry.get()
        if not self.server_process:
            self.log_message("Serveur non démarré.", "WARN")
        elif not command:
            self.log_message("Commande vide.", "WARN")
        else:
            try:
                self.server_process.stdin.write(command + "\n")
                self.server_process.stdin.flush()
                self.log_message(f"Commande envoyée : {command}", "INFO")
                self.command_entry.delete(0, tk.END)
            except Exception as e:
                self.log_message(f"Erreur d'envoi de commande : {e}", "WARN")

    def kick(self):
        current_item = self.player_list.focus()
        player_name = self.player_list.item(current_item)["text"]
        if player_name:
            self.send_command(f"kick {player_name}")

    def ban(self):
        current_item = self.player_list.focus()
        player_name = self.player_list.item(current_item)["text"]
        if player_name:
            self.send_command(f"ban {player_name}")


class ServerLogParser:
    def __init__(self, server_process, log_message, player_treeview: ttk.Treeview, players, config):
        """
        :param server_process: The running Minecraft server process.
        :param log_message: Reference to the existing logging function (self.log_message).
        """
        self.stop_requested = None
        self.server_process = server_process
        self.log_message = log_message  # Use your existing logging function

        self.players_heads = {}
        self.player_treeview = player_treeview
        self.config = config

        # Define regex patterns for parsing different events
        self.log_patterns = [
            {"pattern": r"UUID of player (\w+) is ([a-f0-9\-]+)", "handler": self.handle_player_uuid},
            {"pattern": r"(\w+)\[\/([\d\.]+):\d+\] logged in with entity id (\d+) at \(\[([\w]+)\]([\d\.\-]+), ([\d\.\-]+), ([\d\.\-]+)\)", "handler": self.handle_player_login},
            {"pattern": r"(\w+) issued server command: (.+)", "handler": self.handle_command},
            {"pattern": r"(\w+) was slain by (\w+)", "handler": self.handle_death},
            {"pattern": r"(\w+) left the game", "handler": self.handle_player_leave},
            {"pattern": r"ERROR\]: (.+)", "handler": self.handle_server_error},
            {"pattern": r"\[\d{2}:\d{2}:\d{2} INFO\]: \[@: The entity UUID provided is in an invalid format\]",
             "handler": self.handle_exclusion},
            {"pattern": r"\[@: Given ([A-Za-z\s]+) \(ID (\d+)\) \* (\d+) to ([A-Za-z0-9]+) for (\d+) seconds\]",
             "handler": self.handle_effect},
            {"pattern": r"Changing to (\w+)\sweather", "handler": self.handle_exclusion},
            {"pattern": r"(?<=Opped\s)(\w+)", "handler": self.handle_opped},
            {"pattern": r"(?<=De-opped\s)(\w+)", "handler": self.handle_deopped}
        ]

    def handle_player_uuid(self, match):
        player_name, uuid = match.groups()

        # noinspection PyRedundantParentheses
        tags = "op" if is_op(self.config.get("server_path"), uuid) else ""

        head = self.get_player_head(uuid)

        self.player_treeview.insert("", "end", text=player_name, image=head, tags=tags)

        self.log_message(f"🟢 Player Joined: {player_name} (UUID: {uuid})", "INFO")

    def handle_player_login(self, match):
        player_name, ip, entity_id, world, x, y, z = match.groups()
        self.log_message(f"🌍 {player_name} logged in from {ip} (Entity ID: {entity_id}) at {world} ({x}, {y}, {z})",
                         "INFO")

    def handle_command(self, match):
        player_name, command = match.groups()
        self.log_message(f"🛠 Command Executed: {player_name} -> {command}", "COMMAND")

    def handle_death(self, match):
        victim, killer = match.groups()
        self.log_message(f"☠️ Death: {victim} was killed by {killer}", "DEATH")

    def handle_player_leave(self, match):
        player_name = match.group(1)

        for item in self.player_treeview.get_children():  # Parcours de tous les éléments
            if self.player_treeview.item(item, "text") == player_name:  # Comparaison du texte
                self.player_treeview.delete(item)  # Suppression de l'élément
                break

        self.log_message(f"👋 {player_name} left the game", "INFO")

    def handle_server_error(self, match):
        error_message = match.group(1)
        self.log_message(f"🚨 Server Error: {error_message}", "ERROR")

    def handle_exclusion(self, match):
        pass

    def handle_effect(self, match):
        pass

    def handle_opped(self, match):
        player_name = match.group(1)

        for item in self.player_treeview.get_children():  # Parcours de tous les éléments
            if self.player_treeview.item(item, "text") == player_name:  # Comparaison du texte
                self.player_treeview.item(item, tags="op")

    def handle_deopped(self, match):
        player_name = match.group(1)

        for item in self.player_treeview.get_children():  # Parcours de tous les éléments
            if self.player_treeview.item(item, "text") == player_name:  # Comparaison du texte
                self.player_treeview.item(item, tags="")

    def process_log_line(self, line):
        """Check the line against all patterns and execute the matched handler."""
        for entry in self.log_patterns:
            match = re.search(entry["pattern"], line)

            if match:
                entry["handler"](match)
                return

        self.log_message(line, mc_console=True)

    def monitor_server_process(self):
        """Monitor the Minecraft server console in real-time and parse events."""
        self.stop_requested = False
        crash_detected = False

        while self.server_process:
            exit_code = self.server_process.poll()  # Check if the server has stopped

            # Process server console output
            if self.server_process.stdout:
                for line in self.server_process.stdout:
                    line = line.strip()
                    if line:
                        self.process_log_line(line)  # Use regex-based log parsing

            if exit_code is not None:  # The server has stopped
                if self.stop_requested:
                    self.log_message("✅ The server stopped normally.", "INFO")
                else:
                    if crash_detected:
                        self.log_message(f"⚠️ The server crashed (Exit code: {exit_code})", "ERROR")
                        # Add GUI pop-up or additional handling here if needed

                self.server_process = None
                break

            time.sleep(1)  # Check logs every second

    def get_player_head(self, uuid):
        with urllib.request.urlopen(f"https://mc-heads.net/avatar/{uuid}") as url:
            raw_data = url.read()

        head = Image.open(io.BytesIO(raw_data))
        head = head.resize((16, 16))
        tk_head = ImageTk.PhotoImage(head)
        self.players_heads[uuid] = tk_head
        return tk_head
