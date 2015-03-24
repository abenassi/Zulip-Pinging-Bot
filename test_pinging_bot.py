import unittest
import nose
import datetime
import json
import pinging_bot
from mock import Mock
from freezegun import freeze_time


class BotTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.new_bot = pinging_bot.Bot

    @classmethod
    def tearDownClass(cls):
        del cls.new_bot

    @freeze_time(datetime.datetime(2015, 3, 18, 17, 10, 14))
    def test_parse_time(self):

        # get samples
        d5 = self.new_bot.parse_time("PingingBot 5d")
        w5 = self.new_bot.parse_time("PingingBot 5w")
        m2 = self.new_bot.parse_time("PingingBot 2m")
        m7 = self.new_bot.parse_time("PingingBot 7m")
        non_valid = self.new_bot.parse_time("PingingBot 2q")
        min10 = self.new_bot.parse_time("PingingBot 10min")
        h10 = self.new_bot.parse_time("PingingBot 10h")
        s300 = self.new_bot.parse_time("PingingBot 300s")

        now = datetime.datetime.now()

        # calculate expected results
        d5_exp = now - datetime.timedelta(days=5)
        w5_exp = now - datetime.timedelta(weeks=5)

        days = self.new_bot._months_to_days(2)
        m2_exp = now - datetime.timedelta(days=days)

        days = self.new_bot._months_to_days(3)
        m7_exp = now - datetime.timedelta(days=days)

        days = self.new_bot._months_to_days(3)
        non_valid_exp = now - datetime.timedelta(days=days)

        h10_exp = now - datetime.timedelta(hours=10)
        min10_exp = now - datetime.timedelta(minutes=10)
        s300_exp = now - datetime.timedelta(seconds=300)

        self.assertEqual(d5, d5_exp)
        self.assertEqual(w5, w5_exp)
        self.assertEqual(m2, m2_exp)
        self.assertEqual(m7, m7_exp)
        self.assertEqual(non_valid, non_valid_exp)
        self.assertEqual(min10, min10_exp)
        self.assertEqual(h10, h10_exp)
        self.assertEqual(s300, s300_exp)

    def test_get_participants(self):

        with open("test_msgs.json") as f:
            data = json.load(f)

        test_msgs = data["msgs"]

        issuer = "my name"
        participants = self.new_bot.get_participants(test_msgs, issuer)
        participants_exp = set(["@**Name1**", "@**Name2**", "@**Name3**",
                                "@**Name4**", "@**Name5**"])

        self.assertEqual(participants, participants_exp)

    def test_get_last_participants(self):

        with open("test_msgs.json") as f:
            data = json.load(f)
        test_msgs = data["msgs"]

        self.new_bot._get_msgs_chunk = Mock(return_value=test_msgs)
        self.new_bot.__init__ = Mock(return_value=None)

        stream = test_msgs[0]["display_recipient"]
        subject = test_msgs[0]["subject"]

        participants = self.new_bot().get_last_participants(2, stream, subject)

        self.assertEqual(len(participants), 2)

    def test_bot_msg(self):

        msg = {"sender_email": "pinging-bot@students.hackerschool.com"}
        self.assertTrue(self.new_bot._bot_msg(msg))

        msg = {"sender_email": "someone@gmail.com"}
        self.assertFalse(self.new_bot._bot_msg(msg))


if __name__ == '__main__':
    nose.run(defaultTest=__name__)
