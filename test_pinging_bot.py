import unittest
import nose
import arrow
import json
import pinging_bot
from mock import Mock


class BotTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.new_bot = pinging_bot.PingingBot

    @classmethod
    def tearDownClass(cls):
        del cls.new_bot

    # @freeze_time()
    def test_parse_time(self):

        arrow.now = Mock(return_value=arrow.get(2015, 3, 18, 17, 10, 14))

        # get samples
        d5 = self.new_bot.parse_time("PingingBot 5d")[0]
        w5 = self.new_bot.parse_time("PingingBot 5w")[0]
        m2 = self.new_bot.parse_time("PingingBot 2m")[0]
        m2_rev = self.new_bot.parse_time("PingingBot m2")[0]
        m7 = self.new_bot.parse_time("PingingBot 7m")[0]
        non_valid = self.new_bot.parse_time("PingingBot 2q")[0]
        min10 = self.new_bot.parse_time("PingingBot 10min")[0]
        h10 = self.new_bot.parse_time("PingingBot 10h")[0]
        s300 = self.new_bot.parse_time("PingingBot 300s")[0]

        today = self.new_bot.parse_time("PingingBot today")[0]
        d0 = self.new_bot.parse_time("PingingBot 0d")[0]
        d0_rev = self.new_bot.parse_time("PingingBot d0")[0]
        just_d = self.new_bot.parse_time("PingingBot d")[0]
        just_w = self.new_bot.parse_time("PingingBot w")[0]
        w0 = self.new_bot.parse_time("PingingBot 0w")[0]
        this_week = self.new_bot.parse_time("PingingBot this week")[0]

        # get the anchor for expected results
        now = arrow.now()
        assert now == arrow.get(2015, 3, 18, 17, 10, 14)

        # calculate expected results
        d5_exp = now.replace(days=-5).floor("day")
        w5_exp = now.replace(weeks=-5).floor("week")
        m2_exp = now.replace(months=-2).floor("month")
        m7_exp = now.replace(minutes=-7).floor("minute")
        non_valid_exp = now.replace(months=-3).floor("month")
        h10_exp = now.replace(hours=-10).floor("hour")
        min10_exp = now.replace(minutes=-10).floor("minute")
        s300_exp = now.replace(seconds=-300).floor("second")

        today_exp = now.replace(days=0).floor("day")
        d0_exp = now.replace(days=0).floor("day")
        just_d_exp = now.replace(days=0).floor("day")
        just_w_exp = now.replace(weeks=0).floor("week")
        w0_exp = now.replace(weeks=0).floor("week")
        this_week_exp = now.replace(weeks=0).floor("week")

        # assertions
        self.assertEqual(d5, d5_exp)
        self.assertEqual(w5, w5_exp)
        self.assertEqual(m2, m2_exp)
        self.assertEqual(m2_rev, m2_exp)
        self.assertEqual(m7, m7_exp)
        self.assertEqual(non_valid, non_valid_exp)
        self.assertEqual(min10, min10_exp)
        self.assertEqual(h10, h10_exp)
        self.assertEqual(s300, s300_exp)

        self.assertEqual(today, today_exp)
        self.assertEqual(d0, d0_exp)
        self.assertEqual(d0_rev, d0_exp)
        self.assertEqual(just_d, just_d_exp)
        self.assertEqual(just_w, just_w_exp)
        self.assertEqual(w0, w0_exp)
        self.assertEqual(this_week, this_week_exp)

    def test_get_participants(self):

        with open("test_msgs.json") as f:
            data = json.load(f)

        test_msgs = data["msgs"]

        issuer = "my name"
        participants = self.new_bot.get_participants(test_msgs, issuer)
        participants_exp = ["@**Name1**", "@**Name2**", "@**Name3**",
                            "@**Name4**", "@**Name5**"]

        self.assertEqual(participants, participants_exp)

    def test_get_last_participants(self):

        with open("test_msgs.json") as f:
            data = json.load(f)
        test_msgs = data["msgs"]

        self.new_bot._get_msgs_chunk = Mock(return_value=test_msgs)
        self.new_bot.__init__ = Mock(return_value=None)

        stream = test_msgs[0]["display_recipient"]
        subject = test_msgs[0]["subject"]
        issuer = "Name1"

        participants = self.new_bot().get_last_participants(2, stream, subject,
                                                            issuer)

        self.assertEqual(len(participants), 2)

    def test_bot_msg(self):

        msg = {"sender_email": "pinging-bot@students.hackerschool.com"}
        self.assertTrue(self.new_bot._bot_msg(msg))

        msg = {"sender_email": "someone@gmail.com"}
        self.assertFalse(self.new_bot._bot_msg(msg))

    def test_ping_participants_msg(self):

        # create new ping msg
        msg = {"sender_full_name": "me", "content": None}
        participants = ["@**Name1**", "@**Name2**", "@**Name3**",
                            "@**Name4**", "@**Name5**"]
        time = arrow.get(2015, 1, 1, 0, 0, 0)
        issuer_msg = "I'm sending a message to pinged participants!"

        ping_msg = self.new_bot.ping_participants_msg(msg, participants, time,
                                                 issuer_msg)
        # expected new ping msg
        with open("exp_ping_msg.txt", "r") as f:
            exp_ping_msg = f.read()

        self.assertEqual(ping_msg["content"], exp_ping_msg)


if __name__ == '__main__':
    nose.run(defaultTest=__name__)
