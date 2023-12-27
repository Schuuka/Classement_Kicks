import json

class ELO:
    def __init__(self, players):
        self.players = {player: 1200 for player in players}  # Tous les joueurs commencent avec 1200 ELO

    def calculate_team_points(self, team):
        return sum(self.players[player] for player in team) / len(team)

    def calculate_new_elo(self, player_elo, opponent_elo, result):
        expected_score = 1 / (1 + 10 ** ((opponent_elo - player_elo) / 400))
        k_factor = 40  # Utiliser un facteur K constant pour le MVP
        new_elo = player_elo + k_factor * (result - expected_score)
        return round(new_elo)

    def update_elo(self, team1, team2, result):
        for player in team1:
            player_elo = self.players[player]
            opponent_elo = self.calculate_team_points(team2)
            new_elo = self.calculate_new_elo(player_elo, opponent_elo, result)
            self.players[player] = new_elo
        for player in team2:
            player_elo = self.players[player]
            opponent_elo = self.calculate_team_points(team1)
            new_elo = self.calculate_new_elo(player_elo, opponent_elo, 1 - result)
            self.players[player] = new_elo

class Terminal:
    def get_players():
        return ["Tony", "Clement", "Arnaud", "Florian", "Kris", "Oli", "Barney", "Jackos"]

    def get_teams(players):
        print("Liste des joueurs :")
        for i, player in enumerate(players, start=1):
            print(f"{i}. {player}")
        team1 = input("Entrez les numéros des joueurs de l'équipe 1, séparés par des virgules : ").split(',')
        team1 = [players[int(i)-1] for i in team1]
        team2 = [player for player in players if player not in team1]
        return team1, team2

def get_winner():
    return input("Qui a gagné ? Entrez 1 pour l'équipe 1, 2 pour l'équipe 2 : ")

def main():
    players = Terminal.get_players()
    elo = ELO(players)
    while True:
        team1, team2 = Terminal.get_teams(players)
        winner = get_winner()
        if winner == '1':
            elo.update_elo(team1, team2, 1)
        elif winner == '2':
            elo.update_elo(team2, team1, 1)
        else:
            print("Entrée non valide. Veuillez réessayer.")

if __name__ == "__main__":
    main()