import unittest
import nose
import datetime
import json
from pinging_bot import get_bot


class BotTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.new_bot = get_bot()

    @classmethod
    def tearDownClass(cls):
        del cls.new_bot

    def test_parse_time(self):

        # get samples
        d5 = self.new_bot.parse_time("PingingBot 5d")
        w5 = self.new_bot.parse_time("PingingBot 5w")
        m2 = self.new_bot.parse_time("PingingBot 2m")
        m7 = self.new_bot.parse_time("PingingBot 7m")
        non_valid = self.new_bot.parse_time("PingingBot 2q")

        today = datetime.datetime.today().date()

        # calculate expected results
        d5_exp = today - datetime.timedelta(days=5)
        w5_exp = today - datetime.timedelta(weeks=5)

        days = self.new_bot._months_to_days(2)
        m2_exp = today - datetime.timedelta(days=days)
        days = self.new_bot._months_to_days(3)
        m7_exp = today - datetime.timedelta(days=days)
        days = self.new_bot._months_to_days(3)
        non_valid_exp = today - datetime.timedelta(days=days)

        self.assertEqual(d5, d5_exp)
        self.assertEqual(w5, w5_exp)
        self.assertEqual(m2, m2_exp)
        self.assertEqual(m7, m7_exp)
        self.assertEqual(non_valid, non_valid_exp)

    def test_get_participants(self):

        with open("test_msgs.json") as f:
            data = json.load(f)

        test_msgs = data["msgs"]

        participants = self.new_bot.get_participants(test_msgs)
        participants_exp = ["@**Name1**", "@**Name2**", "@**Name3**",
                            "@**Name4**", "@**Name5**"]

        self.assertEqual(participants, participants_exp)

if __name__ == '__main__':
    nose.run(defaultTest=__name__)
