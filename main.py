import os
import json
import asyncio
import discord
from discord import Embed

from discord.ext import commands

from dotenv import load_dotenv

load_dotenv()
token = os.getenv('DISCORD_TOKEN')

intents = discord.Intents().all()
bot = commands.Bot(command_prefix="€", intents=intents)

intents.message_content = True
intents.guilds = True
intents.members = True

class SurveyView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.answer1 = None
        self.answer2 = None
        self.message = None
        self.score_team1 = None
        self.score_team2 = None
        self.elo = ELO()
        self.elo.load_elo()
        self.team1select = Team1Select(list(self.elo.players.keys()))
        self.add_item(self.team1select)

    async def handle_team1select(self, interaction:discord.Interaction, select_item : discord.ui.select):
        await interaction.response.defer()
        self.answer1 = select_item.values
        self.team1select.disabled= True
        channel = bot.get_channel(interaction.channel.id)
        remaining_players = [player for player in self.elo.players if player not in self.answer1]
        if remaining_players:
            if len(remaining_players) == 1:
                self.answer2 = remaining_players
                elo = ELO()
                if len(self.answer1) > 1:
                    gamers = ' et '.join(f"**{player}** : **{elo.players[player]}** d'ELO" for player in self.answer1)
                else:
                    gamers = f"**{self.answer1[0]}** : **{elo.players[self.answer1[0]]}** d'ELO"
                team_points = elo.calculate_team_points(self.answer1)
                self.content = f"__*Équipe 1*__ :\n\n{gamers}, \nMoyenne d'ELO : **{int(team_points)}** pts d'ELO"
                team_points2 = elo.calculate_team_points(self.answer2)
                self.message = await channel.send(f"{self.content}\n\n                           ***CONTRE***\n\n__*Équipe 2*__ :\n\n**{self.answer2[0]}** : **{elo.players[self.answer2[0]]}** d'ELO, \nMoyenne d'ELO : **{int(team_points2)}** pts d'ELO")
                score_team1_select = ScoreTeam1Select()
                score_team2_select = ScoreTeam2Select()
                self.add_item(score_team1_select)
                self.add_item(score_team2_select)
            else:
                team2 = Team2Select(remaining_players)
                self.add_item(team2)
                elo = ELO()
                if len(self.answer1) > 1:
                    gamers = ' et '.join(f"**{player}** : **{elo.players[player]}** d'ELO" for player in self.answer1)
                else:
                    gamers = f"**{self.answer1[0]}** : **{elo.players[self.answer1[0]]}** d'ELO"
                team_points = elo.calculate_team_points(self.answer1)
                self.content = f"__*Équipe 1*__ :\n\n{gamers}, \nMoyenne d'ELO : **{int(team_points)}** pts d'ELO"
                self.message = await channel.send(f"{self.content}")
        else:
            self.message = await channel.send("Il n'y a plus de joueurs disponibles pour le second sélecteur. La commande a été annulée.")
            if isinstance(self.children[-1], Team2Select):
                self.remove_item(self.children[-1])
            return
        await interaction.message.edit(view=self)

    async def respond_to_answer2(self, interaction : discord.Interaction, choices):
        await interaction.response.defer()
        self.answer2 = choices
        self.children[1].disabled= True
        elo = ELO()
        if len(self.answer2) > 1:
            gamers2 = ' et '.join(f"**{player}** : **{elo.players[player]}** d'ELO" for player in self.answer2)
        else:
            gamers2 = f"**{self.answer2[0]}** : **{elo.players[self.answer2[0]]}** d'ELO"
        team_points2 = elo.calculate_team_points(self.answer2)
        await self.message.edit(content=f"{self.content}\n\n                           ***CONTRE***\n\n__*Équipe 2*__ :\n\n{gamers2}, \nMoyenne d'ELO : **{int(team_points2)}** pts d'ELO")
        score_team1_select = ScoreTeam1Select()
        score_team2_select = ScoreTeam2Select()
        self.add_item(score_team1_select)
        self.add_item(score_team2_select)
        await interaction.message.edit(view=self)

    async def determine_winner(self, interaction: discord.Interaction):
        if self.score_team1 is None or self.score_team2 is None:
            return
        if self.score_team1 > self.score_team2:
        # Team 1 wins
            winners_list = self.answer1
            losers = self.answer2
        elif self.score_team2 > self.score_team1:
        # Team 2 wins
            winners_list = self.answer2
            losers = self.answer1

        if len(winners_list) > 1:
            winners = ' et '.join(winners_list)
        else:
            winners = winners_list[0]

        if self.score_team1 == 0 or self.score_team2 == 0:
            K = 11
        elif self.score_team1 == -1 or self.score_team2 == -1:
            K = 12
        else:
            K = abs(self.score_team1 - self.score_team2)
        print(K)
        original_scores = {player: self.elo.players[player] for player in winners_list + losers}
        self.elo.update_elo(winners_list, losers, 1, K)
        updated_scores = '\n'.join(
            f"**{player}** :   **{self.elo.players[player]}** ({'+' if self.elo.players[player] - original_scores[player] >= 0 else ''}*{self.elo.players[player] - original_scores[player]}*)"
            for player in winners_list + losers)
        if K > 10:
            await interaction.followup.send(content=f"GG {winners} ***Bonus de Perf*** !\n\n__Changement d'ELO:__\n{updated_scores}\nhttps://tenor.com/view/wednesday-morning-happy-dance-good-morning-excited-dance-gif-7904785868772184234")
        else:
            await interaction.followup.send(content=f"GG {winners} !\n\n__Changement d'ELO:__\n{updated_scores}")
        self.stop()
class Team1Select(discord.ui.Select):
    def __init__(self, all_players):
        options = [discord.SelectOption(label=player, value=player) for player in all_players]
        super().__init__(options=options, placeholder="Joueur(s) équipe 1", max_values=2)

    async def callback(self, interaction:discord.Interaction):
        await self.view.handle_team1select(interaction, self)

class Team2Select(discord.ui.Select):
    def __init__(self, remaining_players):
        options = [discord.SelectOption(label=player, value=player) for player in remaining_players]
        super().__init__(options=options, placeholder="Joueur(s) équipe 2", max_values=2)

    async def callback(self, interaction:discord.Interaction):
        await self.view.respond_to_answer2(interaction, self.values)

class ScoreTeam1Select(discord.ui.Select):
    def __init__(self, placeholder="Score équipe 1", min_score=-1, max_score=11):
        options = [discord.SelectOption(label=str(i), value=str(i)) for i in range(min_score, max_score+1)]
        super().__init__(placeholder=placeholder, options=options, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        self.view.score_team1 = int(self.values[0])
        self.disabled = True
        await interaction.response.edit_message(view=self.view)
        if self.view.score_team2 is not None:
            interaction.response.defer()
            await self.view.determine_winner(interaction)
            print(self.view.score_team1, self.view.score_team2)

class ScoreTeam2Select(discord.ui.Select):
    def __init__(self, placeholder="Score équipe 2", min_score=-1, max_score=11):
        options = [discord.SelectOption(label=str(i), value=str(i)) for i in range(min_score, max_score+1)]
        super().__init__(placeholder=placeholder, options=options, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        self.view.score_team2 = int(self.values[0])
        self.disabled = True
        await interaction.response.edit_message(view=self.view)
        if self.view.score_team1 is not None:
            await self.view.determine_winner(interaction)
            print(self.view.score_team1, self.view.score_team2)
class ELO:
    def __init__(self,):
        self.players = {} # {player: elo}
        self.default_k = 38
        self.max_elo_for_lower_k = 1600
        self.games_played = {}
        self.games_won = {}
        self.load_elo()

    def load_elo(self):
        try:
            with open('elo_score.json', "r", encoding='utf-8') as f:
                data = json.load(f)
                self.players = data.get('players', {})
                self.games_played = data.get('games_played', {})
                self.games_won = data.get('games_won', {})
        except FileNotFoundError:
            print("elo_score n'a pas été trouvé.")

    def save_elo(self):
        try:
            with open('elo_score.json', "w", encoding='utf-8') as f:
                data = {
                    'players': self.players,
                    'games_played': self.games_played,
                    'games_won': self.games_won,
                }
                json.dump(data, f)
        except IOError:
            print("Error writing to 'elo_score.json'.")

    def calculate_team_points(self, team):
        if isinstance(team, list):
            return sum(self.players[player] for player in team) / len(team)
        elif isinstance(team, str):
            return self.players.get(team, 0)
        else:
            raise TypeError("Erreur 'team' doit être une liste ou une chaîne de caractères")
    
    def get_k_factor(self, player_elo):
        # Ajuster le coefficient K en fonction du classement Elo du joueur
        if player_elo >= self.max_elo_for_lower_k:
            return 20  # K diminue à 20 pour les joueurs avec plus de 1600 Elo
        else:
            return self.default_k
        
    def k_diff(self, k):
        if k == 12:
            return 24
        elif k == 11:
            return 15
        elif k <= 2:
            return 0
        else:
            return k
        
    def calculate_new_elo(self, player_elo, opponent_elo, result, K):
        expected_score = 1 / (1 + 10 ** ((opponent_elo - player_elo) / 400))
        k_factor = self.get_k_factor(player_elo) + self.k_diff(K)
        new_elo = player_elo + k_factor * (result - expected_score)
        return round(new_elo)
    
    def update_elo(self, team1, team2, result, K):
        for player in team1:
            player_elo = self.players[player]
            opponent_elo = self.calculate_team_points(team2)
            new_elo = self.calculate_new_elo(player_elo, opponent_elo, result, K)
            self.players[player] = new_elo
            self.games_played[player] += 1
            if result == 1:
                self.games_won[player] += 1
        for player in team2:
            player_elo = self.players[player]
            opponent_elo = self.calculate_team_points(team1)
            new_elo = self.calculate_new_elo(player_elo, opponent_elo, 1 - result, K)
            self.players[player] = new_elo
            self.games_played[player] += 1
            if result == 0:
                self.games_won[player] += 1
        self.save_elo()

@bot.event
async def on_ready():
    await bot.change_presence(
        status = discord.Status.online,
        activity = discord.Game(" €ajout | €ranked | €classement")
    )
    print(f"{bot.user.name} est connecté !")

@bot.command()
async def ajout(ctx, *, player_name: str = None):
    if not player_name:
        await ctx.send("Insère un pseudo c*nnard.")
        return
    data = {}
    if os.path.exists('elo_score.json'):
        with open('elo_score.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        print("elo_score.json n'a pas été trouvé. Création d'un nouveau fichier.")

    if 'players' not in data:
        data['players'] = {}
    if 'games_played' not in data:
        data['games_played'] = {}
    if 'games_won' not in data:
        data['games_won'] = {}

    if player_name in data['players']:
        await ctx.send(f"\"**{player_name}**\" existe déjà.")
    else:
        data['players'][player_name] = 1200
        data['games_played'][player_name] = 0
        data['games_won'][player_name] = 0

        with open('elo_score.json', 'w', encoding='utf-8') as f:
            json.dump(data, f)

        await ctx.send(f"Bienvenue **{player_name}** au kicker du [@KLEPTOKICK](https://www.tiktok.com/@KLEPTOKICK).")

@bot.command()
async def supprimer(ctx, *, player_name: str = None):
    if not player_name:
        await ctx.send("Insère un pseudo c*nnard.")
        return
    data = {}
    if os.path.exists('elo_score.json'):
        with open('elo_score.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        await ctx.send("elo_score.json n'a pas été trouvé.")
        return

    if player_name in data['players']:
        del data['players'][player_name]
        del data['games_played'][player_name]
        del data['games_won'][player_name]

        with open('elo_score.json', 'w') as f:
            json.dump(data, f)

        await ctx.send(f"**{player_name}** a été retiré du kicker du [@KLEPTOKICK](https://www.tiktok.com/@KLEPTOKICK).")
    else:
        await ctx.send(f"\"**{player_name}**\" n'existe pas. Réessaye sans faute.")

@bot.command()
async def classement(ctx):
    if not os.path.exists('elo_score.json'):
        await ctx.send("Il n'y a pas de classement pour le moment.\n||Faites la commande $ajout pour ajouter des joueurs.||\n||Sinon contactez le goat.||")
        return
    
    with open('elo_score.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    players = data['players']
    games_played = data['games_played']
    games_won = data['games_won']
    sorted_players = sorted(players.items(), key=lambda item: item[1], reverse=True)

    embed = Embed(title="Classement des joueurs", color=discord.Color.from_rgb(255, 255, 0))
    embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1102545992240345129/1202270216709746788/alxgucci.png?ex=65ccd864&is=65ba6364&hm=4e85d3e35137b49946d7b3dca424d41f6df76bb86919c40f670c7ee409a6f29c&")
    for rank, (player, score) in enumerate(sorted_players):
        played = games_played.get(player, 0)
        won = games_won.get(player, 0)
        winrate = won / played * 100 if played > 0 else 0
        embed.add_field(name=f"- {rank+1}. {player}", value=f"  *ELO* : **{score}**\n   *Parties jouées* : **{played}**\n   *Parties gagnées* : **{won}**\n *Winrate* : **{winrate:.2f}** %", inline=False)

    await ctx.send(embed=embed)

@bot.command()
async def ranked(ctx):
    if not os.path.exists('elo_score.json'):
        await ctx.send("Il n'y a pas de joueurs pour le moment.\n||Faites la commande $ajout pour ajouter des joueurs.||\n||Sinon contactez le goat.||")
        return

    with open('elo_score.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    players = data['players']

    if len(players) < 2:
        await ctx.send("Il faut au moins deux joueurs pour commencer une ranked.")
        return
    
    cancel_emoji = "❌"
    view = SurveyView()
    message = await ctx.send("Omg la vilaine ranked en cours...", view=view)
    await message.add_reaction(cancel_emoji)

    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) == cancel_emoji

    try:
        reaction, user = await bot.wait_for("reaction_add", timeout=300.0, check=check)
        await message.delete()
        await ctx.send("Commande annulée.")
    except asyncio.TimeoutError:
        await message.clear_reactions()

bot.run(token)