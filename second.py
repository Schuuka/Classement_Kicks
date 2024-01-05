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
bot = commands.Bot(command_prefix="$", intents=intents)

intents.message_content = True
intents.guilds = True
intents.members = True

Bg = {"Tony":1200, "Clement":1200, "Arnaud":1200, "Florian":1200, "Kris":1200,"Oli":1200,"Barney":1200, "Jackos":1200}


class SurveyView(discord.ui.View):
    def __init__(self, Bg):
        super().__init__()
        self.all_players = Bg
        self.answer1 = None
        self.answer2 = None
        self.message = None
        self.elo = ELO(self.all_players)
        self.team1select = Team1Select(list(self.all_players.keys()))
        self.add_item(self.team1select)

    async def handle_team1select(self, interaction:discord.Interaction, select_item : discord.ui.select):
        await interaction.response.defer()
        self.answer1 = select_item.values
        self.team1select.disabled= True
        channel = bot.get_channel(interaction.channel.id)
        remaining_players = [player for player in self.all_players if player not in self.answer1]
        team2 = Team2Select(remaining_players)
        self.add_item(team2)
        elo = ELO(self.all_players)
        if len(self.answer1) > 1:
            gamers = ' et '.join(f"**{player}** : **{elo.players[player]}** d'ELO" for player in self.answer1)
        else:
            gamers = f"**{self.answer1[0]}** : **{elo.players[self.answer1[0]]}** d'ELO"
        team_points = elo.calculate_team_points(self.answer1)
        self.content = f"__*Équipe 1*__ :\n\n{gamers}, \nMoyenne d'ELO : **{int(team_points)}** pts d'ELO"
        self.message = await channel.send(f"{self.content}")
        await interaction.message.edit(view=self)

    async def respond_to_answer2(self, interaction : discord.Interaction, choices):
        await interaction.response.defer()
        self.answer2 = choices
        self.children[1].disabled= True
        bt1 = ButtonT1(self, self.elo)
        bt2 = ButtonT2(self, self.elo)
        self.add_item(bt1)
        self.add_item(bt2)
        elo = ELO(self.all_players)
        if len(self.answer2) > 1:
            gamers2 = ' et '.join(f"**{player}** : **{elo.players[player]}** d'ELO" for player in self.answer2)
        else:
            gamers2 = f"**{self.answer2[0]}** : **{elo.players[self.answer2[0]]}** d'ELO"
        team_points2 = elo.calculate_team_points(self.answer2)
        await self.message.edit(content=f"{self.content}\n\n                           ***CONTRE***\n\n__*Équipe 2*__ :\n\n{gamers2}, \nMoyenne d'ELO : **{int(team_points2)}** pts d'ELO")
        await interaction.message.edit(view=self)

class ButtonT1(discord.ui.Button):
    def __init__(self, survey_view: SurveyView, elo, label="Win team 1", custom_id="winT1", style=discord.ButtonStyle.blurple):
        super().__init__(style=style, label=label, custom_id=custom_id)
        self.survey_view = survey_view
        self.elo = elo

    async def callback(self, interaction: discord.Interaction):
        if len(self.survey_view.answer1) > 1:
            winners = ' et '.join(self.survey_view.answer1)
        else:
            winners = self.survey_view.answer1[0]
        original_scores = {player: self.elo.players[player] for player in self.survey_view.answer1 + self.survey_view.answer2}
        self.elo.update_elo(self.survey_view.answer1, self.survey_view.answer2, 1)
        updated_scores = '\n'.join(
            f"**{player}** :   **{self.elo.players[player]}** ({'+' if self.elo.players[player] - original_scores[player] >= 0 else ''}*{self.elo.players[player] - original_scores[player]}*)"
            for player in self.survey_view.answer1 + self.survey_view.answer2)
        await interaction.response.send_message(f"GG {winners} !\n\n__Changement d'ELO:__\n{updated_scores}")
        self.survey_view.stop()

class ButtonT2(discord.ui.Button):
    def __init__(self, survey_view: SurveyView, elo, label="Win team 2", custom_id="winT2", style=discord.ButtonStyle.blurple):
        super().__init__(style=style, label=label, custom_id=custom_id)
        self.survey_view = survey_view
        self.elo = elo

    async def callback(self, interaction: discord.Interaction):
        if len(self.survey_view.answer2) > 1:
            winners = ' et '.join(self.survey_view.answer2)
        else:
            winners = self.survey_view.answer2[0]
        original_scores = {player: self.elo.players[player] for player in self.survey_view.answer1 + self.survey_view.answer2}
        self.elo.update_elo(self.survey_view.answer2, self.survey_view.answer1, 1)
        updated_scores = '\n'.join(
            f"**{player}** :   **{self.elo.players[player]}** ({'+' if self.elo.players[player] - original_scores[player] >= 0 else ''}*{self.elo.players[player] - original_scores[player]}*)"
            for player in self.survey_view.answer1 + self.survey_view.answer2)
        await interaction.response.send_message(f"GG {winners} !\n\n__Changement d'ELO:__\n{updated_scores}")
        self.survey_view.stop()

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

class ELO:
    def __init__(self, players):
        self.players = players  # {player: elo}
        self.default_k = 40
        self.max_elo_for_lower_k = 1600
        self.games_played = {player: 0 for player in players}
        self.games_won = {player: 0 for player in players}
        self._load_elo()

    def _load_elo(self):
        try:
            with open('elo_score.json', "r") as f:
                data = json.load(f)
                self.players = data.get('players', {})
                self.games_played = data.get('games_played', {})
                self.games_won = data.get('games_won', {})
        except FileNotFoundError:
            print("elo_score n'a pas été trouvé. Création d'un nouveau fichier.")
            bg_players = Bg.keys()
            self.players = {player: 1200 for player in bg_players}
            self.games_played = {player: 0 for player in bg_players}
            self.games_won = {player: 0 for player in bg_players}
            self._save_elo()
        except json.JSONDecodeError:
            print("erreur de décodage JSON.")
            self.players = {}
            self.games_played = {}
            self.games_won = {}
            raise Exception("Erreur de décodage JSON. Veuillez vérifier les messages d'erreurs.")

    def _save_elo(self):
        try:
            with open('elo_score.json', "w") as f:
                data = {
                    'players': self.players,
                    'games_played': self.games_played,
                    'games_won': self.games_won,
                }
                json.dump(data, f)
        except IOError:
            raise Exception("Erreur d'écriture vers 'elo_score.json'.")

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
            return 20  # K diminue à 10 pour les joueurs avec plus de 2000 Elo
        else:
            return self.default_k
        
    def calculate_new_elo(self, player_elo, opponent_elo, result):
        """
        Pré-condition : 
        - 'player_elo' et 'opponent_elo' doivent être des nombres (int ou float)
        - 'result' doit être 0 ou 1

        Post-condition :
        - Retourne le nouvel ELO du joueur après le match
        """
        assert isinstance(player_elo, (int, float)), "'player_elo' doit être un nombre"
        assert isinstance(opponent_elo, (int, float)), "'opponent_elo' doit être un nombre"
        assert result in [0, 1], "'result' doit être 0 ou 1"

        expected_score = 1 / (1 + 10 ** ((opponent_elo - player_elo) / 400))
        k_factor = self.get_k_factor(player_elo)
        new_elo = player_elo + k_factor * (result - expected_score)
        return round(new_elo)
    
    def update_elo(self, team1, team2, result):
        for player in team1:
            player_elo = self.players[player]
            opponent_elo = self.calculate_team_points(team2)
            new_elo = self.calculate_new_elo(player_elo, opponent_elo, result)
            self.players[player] = new_elo
            self.games_played[player] += 1
            if result == 1:
                self.games_won[player] += 1
        for player in team2:
            player_elo = self.players[player]
            opponent_elo = self.calculate_team_points(team1)
            new_elo = self.calculate_new_elo(player_elo, opponent_elo, 1 - result)
            self.players[player] = new_elo
            self.games_played[player] += 1
            if result == 0:
                self.games_won[player] += 1
        self._save_elo()

@bot.event
async def on_ready():
    await bot.change_presence(
        status = discord.Status.dnd,
        activity = discord.Game(" $ranked \n $classement")
    )
    print(f"{bot.user.name} est connecté !")

@bot.command()
async def classement(ctx):
    with open('elo_score.json', 'r') as f:
        data = json.load(f)
    players = data['players']
    games_played = data['games_played']
    games_won = data['games_won']
    sorted_players = sorted(players.items(), key=lambda item: item[1], reverse=True)

    embed = Embed(title="Classement des joueurs", color=discord.Color.from_rgb(255, 255, 0))
    embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/700340614960775279/1189381521933611028/406121614_878703493725424_8584499380096395993_n.png?ex=659df4dc&is=658b7fdc&hm=7647828955e97cb4f6f844e7665efd28d2edf95fce619b7f532643cbb682fe4f&")
    for rank, (player, score) in enumerate(sorted_players):
        played = games_played.get(player, 0)
        won = games_won.get(player, 0)
        winrate = won / played * 100 if played > 0 else 0
        embed.add_field(name=f"- {rank+1}. {player}", value=f"  *ELO* : **{score}**\n   *Parties jouées* : **{played}**\n   *Parties gagnées* : **{won}**\n *Winrate* : **{winrate:.2f}** %", inline=False)

    await ctx.send(embed=embed)

@bot.command()
async def ranked(ctx):
    cancel_emoji = "❌"
    try:
        elo = ELO(Bg)
    except Exception as e:
        await ctx.send(str(e))
        return
    view = SurveyView(elo.players)
    message = await ctx.send("Omg la vilaine ranked en cours...", view=view)
    await message.add_reaction(cancel_emoji)

    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) == cancel_emoji

    try:
        await bot.wait_for("reaction_add", timeout=300.0, check=check)
        await message.delete()
        await ctx.send("Commande annulée.")
    except asyncio.TimeoutError:
        await message.clear_reactions()

bot.run(token)