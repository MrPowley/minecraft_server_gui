import re

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
                break 