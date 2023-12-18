from typing import Any, Optional, Union
import discord
from discord import app_commands
from discord.emoji import Emoji
from discord.enums import ButtonStyle

from discord.ext import commands
from discord.interactions import Interaction
from discord.partial_emoji import PartialEmoji

from operator import itemgetter
import json


intents = discord.Intents().all()
bot = commands.Bot(command_prefix="$", intents=intents)

intents.message_content = True
intents.guilds = True
intents.members = True

Bg = {"Tony":1000, "Clement":1000, "Arnaud":1000, "Florian":1000, "Kris":1000}


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
        #self.stop()

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
        self.max_elo_for_lower_k = 2000
        self.load_elo()

    def load_elo(self):
        try:
            with open('elo_score.json', "r") as f:
                self.players = json.load(f)
        except FileNotFoundError:
            pass

    def save_elo(self):
        with open('elo_score.json', "w") as f:
            json.dump(self.players, f)

    def calculate_team_points(self, team):
        return sum(self.players[player] for player in team) / len(team)
    
    def get_k_factor(self, player_elo):
        # Ajuster le coefficient K en fonction du classement Elo du joueur
        if player_elo >= self.max_elo_for_lower_k:
            return 20  # K diminue à 10 pour les joueurs avec plus de 2000 Elo
        else:
            return self.default_k
        
    def calculate_new_elo(self, player_elo, opponent_elo, result):
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
        for player in team2:
            player_elo = self.players[player]
            opponent_elo = self.calculate_team_points(team1)
            new_elo = self.calculate_new_elo(player_elo, opponent_elo, 1 - result)
            self.players[player] = new_elo
        self.save_elo()

class SimpleView(discord.ui.View):
    
    @discord.ui.button(label="Hello",
                       style=discord.ButtonStyle.success)

    async def hello(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("World")

@bot.event
async def on_ready():
    await bot.change_presence(
        status = discord.Status.dnd,
        activity = discord.Game(" an unfunny game")
    )
    print(f"{bot.user.name} est connecté !")

@bot.command()
async def button(ctx):
    view = SimpleView()
    button = discord.ui.Button(label="Click me")
    view.add_item(button)
    await ctx.send(view=view)

@bot.command()
async def ranked(ctx):
    elo = ELO(Bg)
    view = SurveyView(elo.players)
    await ctx.send(view=view)
    await view.wait()

    results = {
        "équipe 1": view.answer1,
        "équipe 2": view.answer2,
    }

    print(f"{results}")
    #await ctx.message.author.send("Bien oej mon lascar!")

bot.run("MTA0MjEzODg3ODgyOTY3NDU2Nw.Ga9ahm.Al0QZ9O49qHer3iiXLGeeLrDXLh58ZWy4Nf5Hw")