import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext, messagebox
from tkinter.messagebox import showerror
from PIL import ImageTk, Image
import subprocess
import threading
import os
import shutil
from datetime import datetime
import sys
import re
import urllib.request
import io
import yaml

# Chemin vers le fichier du serveur Minecraft
PWD = os.path.dirname(os.path.abspath(sys.argv[0]))
CONFIG_PATH = os.path.join(PWD, "config.yml")
DEFAULT_CONFIG = {
    "java_path": "java",
    "server_path": "",
    "server_jar": "paper.jar",
    "ram": 4096
}
os.chdir(PWD)
players_heads = {}

# Global pour le processus du serveur
server_process = None

# Fonction pour démarrer le serveur
def start_server():
    global server_process
    if server_process is None:
        try:
            os.chdir(config["server_path"])

            server_process = subprocess.Popen(
                [config["java_path"], f"-Xmx{config["ram"]}M", "-jar", config["server_jar"], "nogui"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, creationflags = subprocess.CREATE_NO_WINDOW
            )
            log_message("Démarrage du serveur.", "LOG")
            start_button.config(state=tk.DISABLED)
            stop_button.config(state=tk.NORMAL)
            backup_button.config(state=tk.DISABLED)
            threading.Thread(target=read_server_output, daemon=True).start()
            os.chdir(PWD)
        except Exception as e:
            log_message(f"Erreur lors du démarrage du serveur : {e}", "WARN")
            messagebox.showerror("Erreur", "Impossible de démarrer le serveur.")
    else:
        log_message("Le serveur est déjà en cours d'exécution.", "WARN")

# Fonction pour arrêter le serveur
def stop_server():
    global server_process
    if server_process:
        send_command("stop")
        start_button.config(state=tk.NORMAL)
        stop_button.config(state=tk.DISABLED)
        backup_button.config(state=tk.NORMAL)
        log_message("Serveur Minecraft arrêté.", "LOG")
        server_process = None
    else:
        log_message("Aucun serveur n'est en cours d'exécution.", "WARN")

# Fonction pour arrêter le serveur
def kill_server():
    global server_process
    if server_process:
        server_process.kill()
        server_process = None
        log_message("Serveur Minecraft arrêté.", "LOG")
    else:
        log_message("Aucun serveur n'est en cours d'exécution.", "WARN")

def get_time(format: str = "%Y_%m_%d-%H_%M_%S") -> str:
    return datetime.now().strftime(format)

def backup_server():
    global server_process
    if server_process:
        showerror("Backup", "Le serveur est en fonctionnement, arretez le pour effetuer la backup")
        return

    log_message("Starting Backup Now", "LOG")
    backup_path = os.path.join(PWD, "..", "backup")
    if not os.path.exists(backup_path):
        os.mkdir(backup_path)
    now = get_time()
    shutil.make_archive(os.path.join(backup_path, f"Backup-{now}"), "zip", PWD)
    log_message("Server backed up", "LOG")

def on_close():
    global server_process

    save_config(config)

    if server_process:
        if messagebox.askokcancel("Quitter", "Voulez vous quitter ?"):
            stop_server()
            root.destroy()
            return
        return
    
    stop_server()
    root.destroy()
    return

def check_log_level(line: str) -> str:
    pattern_tag = re.compile(
        r"\[([0-9]+(:[0-9]+)+) (TRACE|DEBUG|INFO|NOTICE|WARN|WARNING|ERROR|SEVERE|FATAL)\]",
        re.IGNORECASE
    )
    if match := pattern_tag.match(line):
        return match.group(3)
    
    return "LOG"


def check_player(line):
    pattern_join = re.compile(
        r"\[[^\]]*\]: UUID of player ([A-Za-z]+) is ([0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12})",
        re.IGNORECASE
    )
    pattern_disconnect = re.compile(
        r"\[[^\]]*\]: ([A-Za-z]+) lost connection: .*", 
        re.IGNORECASE
    )

    match_disconnect = pattern_disconnect.match(line)
    match_join = pattern_join.match(line)

    if match_join:
        # Extraction des groupes capturants
        player_name = match_join.group(1)  # Pseudo du joueur
        uuid = match_join.group(2)         # UUID du joueur

        head = get_player_head(uuid)

        player_list.insert("", "end", text=player_name, image=head)
    elif match_disconnect:
        player_name = match_disconnect.group(1)

        for item in player_list.get_children():  # Parcours de tous les éléments
            if player_list.item(item, "text") == player_name:  # Comparaison du texte
                player_list.delete(item)  # Suppression de l'élément
                break  # Sort de la boucle après avoir trouvé l'élément

def get_player_head(uuid):
    with urllib.request.urlopen(f"https://mc-heads.net/avatar/{uuid}") as url:
        raw_data = url.read()

    head = Image.open(io.BytesIO(raw_data))
    head = head.resize((16, 16))
    tk_head = ImageTk.PhotoImage(head)
    players_heads[uuid] = tk_head
    return tk_head


# Lire la sortie du serveur dans une boucle
def read_server_output():
    global server_process

    if server_process:
        for line in server_process.stdout:
            line = line.strip()

            check_player(line)
            tag = check_log_level(line)
            log_message(line, tag, True)

# Fonction pour afficher un message dans la console
def log_message(message, tag = "LOG", mc_console: bool = False):
    if not mc_console:
        now = get_time("%H:%M:%S")
        time = f"[{now} {tag}]"
        message = f"{time}: {message}"

    console_text.config(state=tk.NORMAL)
    console_text.insert(tk.END, message + "\n", tag)
    console_text.config(state=tk.DISABLED)
    if auto_scroll_var.get() == 1:
        console_text.yview(tk.END)
    return


# Envoyer une commande au serveur
def send_command(command = None):
    global server_process
    if not command or type(command) != str:
        command = command_entry.get()
    if not server_process:
        log_message("Serveur non démarré.", "WARN")
    elif not command:
        log_message("Commande vide.", "WARN")
    else:
        try:
            server_process.stdin.write(command + "\n")
            server_process.stdin.flush()
            log_message(f"Commande envoyée : {command}", "INFO")
            command_entry.delete(0, tk.END)
        except Exception as e:
            log_message(f"Erreur d'envoi de commande : {e}", "WARN")

def kick():
    current_item = player_list.focus()
    player_name = player_list.item(current_item)["text"]
    send_command(f"kick {player_name}")     

def ban():
    current_item = player_list.focus()
    player_name = player_list.item(current_item)["text"]
    send_command(f"ban {player_name}")     


def ct_popup(event):
    try:
        context_menu.tk_popup(event.x_root, event.y_root)
    finally:
        context_menu.grab_release()

def load_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as file:
            return yaml.safe_load(file)
    else:
        save_config()
        return load_config()

def save_config(config: dict = DEFAULT_CONFIG) -> None:
    with open(CONFIG_PATH, 'w') as file:
        yaml.dump(config, file)
    return

config = load_config()

# Interface Tkinter
root = tk.Tk()
root.title("Panneau Serveur")
root.geometry("1200x400")
# root.iconbitmap("icon.ico")

top_frame = ttk.Frame(root)
top_frame.pack(side="top", fill="both", expand=True)

right_frame = ttk.Frame(top_frame)
right_frame.pack(side="right", fill="both")

top_right_frame = ttk.Frame(right_frame)
top_right_frame.pack(side="top", fill="x")

bottom_right_frame = ttk.Frame(right_frame)
bottom_right_frame.pack(side="bottom", fill="both", expand=True)

left_frame = ttk.Frame(top_frame)
left_frame.pack(side="left", fill="both", expand=True)

bottom_frame = ttk.Frame(root)
bottom_frame.pack(side="bottom", fill="both")


play_b64 = r"iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAABGwAAARsBjfdO5QAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAACoSURBVEiJtdYxDkFBFIXhL0SpkagtQGUHNmELWiVL0KnFDmxBYgPYgF6JSqPwFEyieo13bvLXf+bO3HOHTy1wxwo9gTqg+nLFDJ0mBccfQeGMSVJQ2GOUFFR4YYtBSlB4YIluSlC4YIp2SlA4YZwUFHYYJgUVnlijnxLUDmqTgsIGWnV9+7Oq1AliLYpecuyZxgYtFhWxsIvGdWzhNLoy40t/jpvAt+UNOuYNyvRLu0EAAAAASUVORK5CYII="
play_icon = tk.PhotoImage(data=play_b64)
start_button = ttk.Button(top_right_frame, image=play_icon, command=start_server)
start_button.grid(row=0, column=0)

stop_b64 = r"iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAABGwAAARsBjfdO5QAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAABYSURBVEiJ7daxDYAwEAPAC2IV2H8GggQ7EQkKUiDqfPeW3Ppaw4odF+5BvVCx6OOjhv+tpWuzmLTSpbBMkeMJJJBAAgkk8AVa4H6bcAYCB++1qMbflg3LA3hOSYR/hMR9AAAAAElFTkSuQmCC"
stop_icon = tk.PhotoImage(data=stop_b64)
stop_button = ttk.Button(top_right_frame, image=stop_icon, command=stop_server, state=tk.DISABLED)
stop_button.grid(row=0, column=1)

# # kill_icon = tk.PhotoImage(file="kill.png")
# # kill_button = ttk.Button(frame_buttons, image=kill_icon, command=kill_server)
# # kill_button.grid(row=0, column=2, sticky="N")

backup_b64 = r"iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAAAsQAAALEBxi1JjQAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAAEcSURBVEiJ7dYxSgNBGMXxX0I60UaQgIUgCILY2mrhBYT01t4ilzC9J/ACSTSlFlpZRQSLYGUlNimMhbNmXWazu5AVBB98zML7eP8dZnZ2GubawZafegp1JK5rbIe6x2tOnx5mkeoGP+bNgtcNzy/YzQY3w5uf5ZErqI2rLKSJzSWEpyEj7KUBy9YGhgmkDkAC6WO9VdDYCOOoRE9WbewXAQ7Rkr9NF3nfDUWAR4xz/Ni3UwkgBCwMWaS6FvkfUF55i3yJC7yXzFnBKU6yRmwGN+jgoWS40NvBbdaIzWCID9xhtSTgDWsY4CBtxGYwDWPZ8HTvNGv8/V30K4BJjfmTpq+TsldD+DnG6Z9FcvQmV5XjioF98yvMs3DEfwKLwDPSZbz5mAAAAABJRU5ErkJggg=="
backup_icon = tk.PhotoImage(data=backup_b64)
backup_button = ttk.Button(top_right_frame, image=backup_icon, command=backup_server)
backup_button.grid(row=0, column=3)



context_menu = tk.Menu(root, tearoff=0)
context_menu.add_command(label="Kick", command=kick)
context_menu.add_command(label="Ban", command=ban)


player_list_scrollbar = ttk.Scrollbar(bottom_right_frame)
player_list = ttk.Treeview(bottom_right_frame, yscrollcommand=player_list_scrollbar.set, show="tree")
player_list_scrollbar.pack(side="right", fill="y")
player_list.pack(fill="both", expand=True)
player_list_scrollbar.configure(command=player_list.yview)

player_list.bind("<Button-3>", ct_popup)

# # Zone de texte pour afficher la console du serveur
console_text = scrolledtext.ScrolledText(left_frame, wrap=tk.WORD, height=15, state=tk.DISABLED)
console_text.pack(fill="both", expand=True)

console_text.tag_config('INFO', foreground='green')
console_text.tag_config('WARN', foreground='orange')
console_text.tag_config('ERROR', foreground='red')
console_text.tag_config('LOG', foreground='cyan4')



command_entry = ttk.Entry(left_frame)
command_entry.pack(fill="x", side="left", expand=True)
command_entry.bind("<Return>", send_command)

auto_scroll_var = tk.IntVar()
auto_scroll_var.set(1)
auto_scroll_checkbutton = ttk.Checkbutton(left_frame, text="Auto Scroll", variable=auto_scroll_var)
auto_scroll_checkbutton.pack(side="right")


first_column = ttk.Frame(bottom_frame)
first_column.pack(side="left", fill="both", padx=5, pady=5)

java_path_label = ttk.Label(first_column, text="Chemin de Java")
java_path_label.pack(side="left")

java_path_entry = ttk.Entry(first_column)
java_path_entry.pack(side="right")
java_path_entry.insert(0, config["java_path"])



second_column = ttk.Frame(bottom_frame)
second_column.pack(side="left", fill="both", padx=5, pady=5)

ram_ammount_label = ttk.Label(second_column, text="Ram")
ram_ammount_label.pack(side="left")

ram_ammount_spinbox = ttk.Spinbox(second_column, from_=512, to=65536)
ram_ammount_spinbox.pack(side="right")
ram_ammount_spinbox.insert(0, 4096)



third_column = ttk.Frame(bottom_frame)
third_column.pack(side="left", fill="both", padx=5, pady=5)

server_path_label = ttk.Label(third_column, text="Chemin du Serveur")
server_path_label.pack(side="left")

server_path_entry = ttk.Entry(third_column)
server_path_entry.pack(side="right")
server_path_entry.insert(0, config["server_path"])


fourth_column = ttk.Frame(bottom_frame)
fourth_column.pack(side="left", fill="both", padx=5, pady=5)

server_jar_label = ttk.Label(fourth_column, text="Chemin Du Jar du Serveur")
server_jar_label.pack(side="left")

server_jar_entry = ttk.Entry(fourth_column)
server_jar_entry.pack(side="right")
server_jar_entry.insert(0, config["server_jar"])



root.protocol("WM_DELETE_WINDOW", on_close)
root.mainloop()
