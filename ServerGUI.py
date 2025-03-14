import tkinter as tk
from tkinter import ttk, font
from tkinter import scrolledtext, messagebox
import os
import sys

import ServerConfig
import MinecraftServer

# import sv_ttk


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


class ServerGUI:
    def __init__(self):
        # Initialisation de la fenêtre principale
        self.root = tk.Tk()
        self.root.title("Panneau Serveur")
        self.root.geometry("1200x400")

        try:
            icon = resource_path("icon.ico")
            self.root.iconbitmap(icon)
        except:
            pass

        self.PWD = os.path.dirname(os.path.abspath(sys.argv[0]))
        self.config = ServerConfig.ServerConfig()

        os.chdir(self.PWD)

        # Définition des icônes
        self.load_icons()

        # Création des widgets
        self.create_widgets()

        # Création de l'instance du serveur
        self.server = MinecraftServer.MinecraftServer(
            self.root, self.config, self.console_text,
            self.start_button, self.stop_button, self.backup_button,
            self.kill_button,
            self.PWD, self.auto_scroll_var, self.command_entry, self.player_list_treeview
        )

        # self.server.log_message(str(font.families()))

        # Assignation des commandes aux boutons
        self.start_button.config(command=self.server.start_server)
        self.stop_button.config(command=self.server.stop_server)
        self.backup_button.config(command=self.server.backup_server)
        self.kill_button.config(command=self.server.kill_server)
        self.command_entry.bind("<Return>", self.server.send_command)

        self.context_menu.add_command(label="Kick", command=self.server.kick)
        self.context_menu.add_command(label="Ban", command=self.server.ban)

        # Gestion de la fermeture de la fenêtre
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def load_icons(self):
        """Charge les icônes en base64."""
        self.play_icon = tk.PhotoImage(
            data=r"iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAABGwAAARsBjfdO5QAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAACoSURBVEiJtdYxDkFBFIXhL0SpkagtQGUHNmELWiVL0KnFDmxBYgPYgF6JSqPwFEyieo13bvLXf+bO3HOHTy1wxwo9gTqg+nLFDJ0mBccfQeGMSVJQ2GOUFFR4YYtBSlB4YIluSlC4YIp2SlA4YZwUFHYYJgUVnlijnxLUDmqTgsIGWnV9+7Oq1AliLYpecuyZxgYtFhWxsIvGdWzhNLoy40t/jpvAt+UNOuYNyvRLu0EAAAAASUVORK5CYII=")
        self.stop_icon = tk.PhotoImage(
            data=r"iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAABGwAAARsBjfdO5QAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAABYSURBVEiJ7daxDYAwEAPAC2IV2H8GggQ7EQkKUiDqfPeW3Ppaw4odF+5BvVCx6OOjhv+tpWuzmLTSpbBMkeMJJJBAAgkk8AVa4H6bcAYCB++1qMbflg3LA3hOSYR/hMR9AAAAAElFTkSuQmCC")
        self.backup_icon = tk.PhotoImage(
            data=r"iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAAAsQAAALEBxi1JjQAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAAEcSURBVEiJ7dYxSgNBGMXxX0I60UaQgIUgCILY2mrhBYT01t4ilzC9J/ACSTSlFlpZRQSLYGUlNimMhbNmXWazu5AVBB98zML7eP8dZnZ2GubawZafegp1JK5rbIe6x2tOnx5mkeoGP+bNgtcNzy/YzQY3w5uf5ZErqI2rLKSJzSWEpyEj7KUBy9YGhgmkDkAC6WO9VdDYCOOoRE9WbewXAQ7Rkr9NF3nfDUWAR4xz/Ni3UwkgBCwMWaS6FvkfUF55i3yJC7yXzFnBKU6yRmwGN+jgoWS40NvBbdaIzWCID9xhtSTgDWsY4CBtxGYwDWPZ8HTvNGv8/V30K4BJjfmTpq+TsldD+DnG6Z9FcvQmV5XjioF98yvMs3DEfwKLwDPSZbz5mAAAAABJRU5ErkJggg==")

    def create_widgets(self):
        """Crée tous les widgets de l'interface."""

        self.header_frame = ttk.Frame(self.root)
        self.header_frame.pack(side="top", fill="x")

        self.title = tk.Label(self.header_frame, text=self.config.get("server-name"), font=("Arial", 20))
        self.title.pack(side="left", padx=5, pady=5)

        self.controls_frame = ttk.Frame(self.header_frame)
        self.controls_frame.pack(side="right", padx=5, pady=5)


        self.status_label = tk.Label(self.controls_frame, text="• Éteint", font=("arial", 14))
        self.status_label.pack(side="left", padx=15)

        # Boutons de contrôle du serveur
        self.start_button = ttk.Button(self.controls_frame, image=self.play_icon)
        self.start_button.pack(side="left")

        self.stop_button = ttk.Button(self.controls_frame, image=self.stop_icon, state=tk.DISABLED)
        self.stop_button.pack(side="left")

        self.backup_button = ttk.Button(self.controls_frame, image=self.backup_icon)
        self.backup_button.pack(side="left")

        self.kill_button = ttk.Button(self.controls_frame, image=self.stop_icon, state=tk.DISABLED)
        self.kill_button.pack(side="left")



        # Notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill="both")

        self.create_console_page()
        self.create_properties_page()

    def create_console_page(self):
        # Console page
        self.console_page_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.console_page_frame, text='Console')

        right_frame = ttk.Frame(self.console_page_frame)
        right_frame.pack(side="right", fill="both")

        # Liste des joueurs avec barre de défilement
        self.player_list_scrollbar = ttk.Scrollbar(right_frame)
        self.player_list_treeview = ttk.Treeview(right_frame, yscrollcommand=self.player_list_scrollbar.set,
                                                 show="tree")
        self.player_list_scrollbar.pack(side="right", fill="y")
        self.player_list_treeview.pack(fill="both", expand=True)
        self.player_list_scrollbar.configure(command=self.player_list_treeview.yview)

        self.player_list_treeview.tag_configure("op", background="red", foreground="white")

        # Associer le menu contextuel au clic droit sur la liste des joueurs
        self.player_list_treeview.bind("<Button-3>", self.ct_popup)

        left_frame = ttk.Frame(self.console_page_frame)
        left_frame.pack(side="left", fill="both", expand=True)

        bottom_frame = ttk.Frame(self.root)
        bottom_frame.pack(side="bottom", fill="both")

        # Menu contextuel
        self.context_menu = tk.Menu(self.root, tearoff=0)

        # Zone de texte pour afficher la console
        self.console_text = scrolledtext.ScrolledText(left_frame, wrap=tk.WORD, height=15, state=tk.DISABLED,
                                                      font=(self.config.get("console-font"), 11))
        self.console_text.pack(fill="both", expand=True)

        self.console_text.tag_config('INFO', foreground='green')
        self.console_text.tag_config('WARN', foreground='orange')
        self.console_text.tag_config('ERROR', foreground='red')
        self.console_text.tag_config('LOG', foreground='cyan4')

        # Champ de commande
        self.command_entry = ttk.Entry(left_frame)
        self.command_entry.pack(fill="x", side="left", expand=True)

        self.auto_scroll_var = tk.IntVar()
        self.auto_scroll_var.set(1)
        self.auto_scroll_checkbutton = ttk.Checkbutton(left_frame, text="Auto Scroll", variable=self.auto_scroll_var)
        self.auto_scroll_checkbutton.pack(side="right")
    def create_properties_page(self):
        """Crée les entrées pour la configuration du serveur."""

        # Properties page
        self.properties_page_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.properties_page_frame, text='Properties')

        first_column = ttk.Frame(self.properties_page_frame)
        first_column.pack(side="left", fill="both", padx=5, pady=5)

        ttk.Label(first_column, text="Chemin de Java").pack(side="left")
        self.java_path_entry = ttk.Entry(first_column)
        self.java_path_entry.pack(side="right")
        self.java_path_entry.insert(0, self.config.get("java_path"))

        second_column = ttk.Frame(self.properties_page_frame)
        second_column.pack(side="left", fill="both", padx=5, pady=5)

        ttk.Label(second_column, text="Ram").pack(side="left")
        self.ram_ammount_spinbox = ttk.Spinbox(second_column, from_=512, to=65536)
        self.ram_ammount_spinbox.pack(side="right")
        self.ram_ammount_spinbox.insert(0, "4096")

        third_column = ttk.Frame(self.properties_page_frame)
        third_column.pack(side="left", fill="both", padx=5, pady=5)

        ttk.Label(third_column, text="Chemin du Serveur").pack(side="left")
        self.server_path_entry = ttk.Entry(third_column)
        self.server_path_entry.pack(side="right")
        self.server_path_entry.insert(0, self.config.get("server_path"))

        fourth_column = ttk.Frame(self.properties_page_frame)
        fourth_column.pack(side="left", fill="both", padx=5, pady=5)

        ttk.Label(fourth_column, text="Chemin Du Jar du Serveur").pack(side="left")
        self.server_jar_entry = ttk.Entry(fourth_column)
        self.server_jar_entry.pack(side="right")
        self.server_jar_entry.insert(0, self.config.get("server_jar"))

    def ct_popup(self, event):
        """Affiche le menu contextuel sur clic droit."""
        item = self.player_list_treeview.identify('item',event.x,event.y)
        if item:
            self.context_menu.tk_popup(event.x_root, event.y_root)
            self.context_menu.grab_release()

    def on_close(self):
        """Sauvegarde, et demande confirmation d'arrêt"""
        self.config.save_config()
        if not self.server.server_process and messagebox.askokcancel("Quitter", "Voulez-vous quitter ?"):
            self.server.stop_server()
            self.root.destroy()

    def run(self):
        """Lance l'application."""
        # sv_ttk.set_theme("light")
        self.root.mainloop()
        self.server.kill_server()
