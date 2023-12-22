import unittest
from unittest.mock import patch, mock_open
import json
from main import MyClass, ELO, SurveyView
from unittest.mock import AsyncMock, patch, asyncio

class TestSurveyView(unittest.TestCase):
    @patch("main.ELO")
    @patch("main.Team1Select")
    @patch("main.bot.get_channel")
    def test_handle_team1select(self, mock_get_channel, mock_Team1Select, mock_ELO):
        # Arrange
        players = {"player1": 1200, "player2": 1300}
        survey_view = SurveyView(players)
        interaction = AsyncMock()
        interaction.channel.id = 123
        select_item = AsyncMock()
        select_item.values = ["player1"]
        mock_ELO_instance = mock_ELO.return_value
        mock_ELO_instance.players = players
        mock_ELO_instance.calculate_team_points.return_value = 1200
        mock_channel = mock_get_channel.return_value
        mock_channel.send = AsyncMock()

        # Act
        asyncio.run(survey_view.handle_team1select(interaction, select_item))

        # Assert
        self.assertEqual(survey_view.answer1, ["player1"])
        self.assertTrue(survey_view.team1select.disabled)
        mock_get_channel.assert_called_once_with(123)
        mock_ELO.assert_called_once_with(players)
        mock_ELO_instance.calculate_team_points.assert_called_once_with(["player1"])
        mock_channel.send.assert_called_once()

class TestELO(unittest.TestCase):
    @patch("builtins.open", new_callable=mock_open, read_data=json.dumps({"players": {"player1": 1200}, "games_played": {"player1": 0}, "games_won": {"player1": 0}}))
    def test_load_elo(self, mock_file):
        players = {"player1": 1200}
        elo = ELO(players)
        elo.load_elo()
        self.assertEqual(elo.players, {"player1": 1200})
        self.assertEqual(elo.games_played, {"player1": 0})
        self.assertEqual(elo.games_won, {"player1": 0})

    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump")
    def test_save_elo(self, mock_json_dump, mock_file):
        players = {"player1": 1200}
        elo = ELO(players)
        elo.save_elo()
        mock_file.assert_called_once_with('elo_score.json', "w")
        mock_json_dump.assert_called_once_with({'players': {'player1': 1200}, 'games_played': {'player1': 0}, 'games_won': {'player1': 0}}, mock_file())

    def test_calculate_team_points(self):
        players = {"player1": 1200, "player2": 1300}
        elo = ELO(players)
        team_points = elo.calculate_team_points(["player1", "player2"])
        self.assertEqual(team_points, 1250)

    def test_get_k_factor(self):
        players = {"player1": 1200}
        elo = ELO(players)
        k_factor = elo.get_k_factor(2100)
        self.assertEqual(k_factor, 20)

    def test_calculate_new_elo(self):
        players = {"player1": 1200}
        elo = ELO(players)
        new_elo = elo.calculate_new_elo(1200, 1300, 1)
        self.assertEqual(new_elo, 1220)

    @patch("main.ELO.save_elo")
    def test_update_elo(self, mock_save_elo):
        players = {"player1": 1200, "player2": 1300, "player3": 1400, "player4": 1500}
        games_played = {"player1": 1, "player2": 1, "player3": 1, "player4": 1}
        games_won = {"player1": 0, "player2": 0, "player3": 0, "player4": 0}
        elo = ELO(players, games_played, games_won)
        elo.update_elo(["player1", "player2"], ["player3", "player4"], 1)
        self.assertNotEqual(elo.players["player1"], 1200)
        self.assertNotEqual(elo.players["player2"], 1300)
        self.assertNotEqual(elo.players["player3"], 1400)
        self.assertNotEqual(elo.players["player4"], 1500)
        self.assertEqual(elo.games_played["player1"], 2)
        self.assertEqual(elo.games_played["player2"], 2)
        self.assertEqual(elo.games_played["player3"], 2)
        self.assertEqual(elo.games_played["player4"], 2)
        self.assertEqual(elo.games_won["player1"], 1)
        self.assertEqual(elo.games_won["player2"], 1)
        self.assertEqual(elo.games_won["player3"], 0)
        self.assertEqual(elo.games_won["player4"], 0)
        mock_save_elo.assert_called_once()

if __name__ == '__main__':
    unittest.main()