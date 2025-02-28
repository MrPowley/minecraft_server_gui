import tkinter as tk
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


class MinecraftServer:
    def __init__(self, root, config, console_text, start_button, stop_button, backup_button, kill_button, PWD,
                 auto_scroll_var, command_entry):
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
        self.players_heads = {}
        self.auto_scroll_var = auto_scroll_var
        self.command_entry = command_entry

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
            threading.Thread(target=self.monitor_server_process, daemon=True).start()
            os.chdir(self.PWD)
        except Exception as e:
            self.log_message(f"Erreur lors du démarrage du serveur : {e}", "WARN")
            messagebox.showerror("Erreur", "Impossible de démarrer le serveur.")

    def monitor_server_process(self):
        """Surveille si le processus du serveur Minecraft est toujours actif et analyse les logs pour contextualiser
        un crash."""
        self.stop_requested = False  # Variable pour savoir si l'arrêt a été demandé

        crash_detected = False  # Variable pour savoir si on a détecté un crash dans les logs

        while self.server_process:
            # Vérification de l'état du processus via poll()
            exit_code = self.server_process.poll()

            # Vérification des logs en temps réel
            if self.server_process.stdout:
                for line in self.server_process.stdout:
                    line = line.strip()
                    if line:
                        content = extract_content(line)

                        self.check_player(line)
                        log_level = check_log_level(line)

                        if self.check_error(line):
                            self.log_message("⚠️ Erreur détectée", "ERROR")
                            crash_detected = True
                            break
                        elif not self.log_exclusion(line[17:]):
                            self.log_message(content, log_level, False)

            # Si le processus est terminé, analyse le code de sortie
            if exit_code is not None:  # Le processus s'est terminé
                if self.stop_requested:
                    self.log_message("✅ Le serveur s'est arrêté normalement.", "INFO")
                else:
                    if crash_detected:
                        self.log_message(f"⚠️ Le serveur a crashé (Code de sortie : {exit_code})", "ERROR")
                        messagebox.showerror("Crash détecté",
                                             f"Le serveur Minecraft s'est arrêté de manière inattendue (Code: {exit_code}).")

                self.server_process = None  # Réinitialise la variable
                self.start_button.config(state=tk.NORMAL)
                self.stop_button.config(state=tk.DISABLED)
                self.backup_button.config(state=tk.NORMAL)
                break  # Quitte la boucle de surveillance

            time.sleep(1)  # Vérification toutes les secondes

    def check_error(selfself, line):
        if "FAILED TO BIND TO PORT!" in line:
            return True

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
            # self.server_process = None
        else:
            self.log_message("Aucun serveur n'est en cours d'exécution.", "WARN")

    # Fonction pour arrêter le serveur
    def kill_server(self):
        if self.server_process:
            kill_process_tree(self.server_process.pid)
            self.server_process.wait()
            self.server_process = None
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

        self.console_text.config(state=tk.NORMAL)
        self.console_text.insert(tk.END, message + "\n", tag)
        self.console_text.config(state=tk.DISABLED)
        if self.auto_scroll_var.get() == 1:
            self.console_text.yview(tk.END)
        return

    def check_player(self, line):
        pattern_join = re.compile(
            r"\[[^]]*]: UUID of player ([A-Za-z]+) is ([0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-["
            r"0-9A-Fa-f]{12})",
            re.IGNORECASE
        )
        pattern_disconnect = re.compile(
            r"\[[^]]*]: ([A-Za-z]+) lost connection: .*",
            re.IGNORECASE
        )

        match_disconnect = pattern_disconnect.match(line)
        match_join = pattern_join.match(line)

        if match_join:
            # Extraction des groupes capturants
            player_name = match_join.group(1)  # Pseudo du joueur
            uuid = match_join.group(2)  # UUID du joueur

            head = self.get_player_head(uuid)

            self.player_list.insert("", "end", text=player_name, image=head)
        elif match_disconnect:
            player_name = match_disconnect.group(1)

            for item in self.player_list.get_children():  # Parcours de tous les éléments
                if self.player_list.item(item, "text") == player_name:  # Comparaison du texte
                    self.player_list.delete(item)  # Suppression de l'élément
                    break  # Sort de la boucle après avoir trouvé l'élément

    def get_player_head(self, uuid):
        with urllib.request.urlopen(f"https://mc-heads.net/avatar/{uuid}") as url:
            raw_data = url.read()

        head = Image.open(io.BytesIO(raw_data))
        head = head.resize((16, 16))
        tk_head = ImageTk.PhotoImage(head)
        self.players_heads[uuid] = tk_head
        return tk_head

    def log_exclusion(self, message: str) -> bool:
        if message in self.config.get_log_exceptions_absolute():
            return True
        elif any(self.config.get_log_exceptions_regex()):
            for pattern in self.config.get_log_exceptions_regex():
                re_pattern = re.compile(pattern, re.IGNORECASE)
                if re_pattern.match(message):
                    return True
        else:
            return False

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
        self.send_command(f"kick {player_name}")

    def ban(self):
        current_item = self.player_list.focus()
        player_name = self.player_list.item(current_item)["text"]
        self.send_command(f"ban {player_name}")
