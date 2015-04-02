#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import zulip
import requests
import os
import parsley
import arrow
import json


class PingingBot():

    """ Create a Zulip PingingBot.

        Create a bot that runs in a server listening to Zulip messages. This
        bot waits to read something like "PingBot 2w some_message" to ping
        all participants of a stream-subject in Zulip from 2 weeks ago with
        some_message.

        Attributes:
            zulip_username: Username of the bot in Zulip (email).
            zulip_api_key: API key of the bot in Zulip.
            key_word: Word that triggers the bot's action.
            short_key_word: Alternative short key word.
            subscribed_streams: Streams to suscribe ([] = all streams)
    """

    CHUNK_SIZE = 5000  # size of the chunk of messages asked each time
    PING_INI = "@**"  # initial string required to ping a user name
    PING_END = "**"  # final string required to ping a user name

    def __init__(self, zulip_username, zulip_api_key, key_word, short_key_word,
                 subscribed_streams=[]):
        self.username = zulip_username
        self.api_key = zulip_api_key
        self.key_word = key_word.lower()
        self.short_key_word = short_key_word.lower()
        self.subscribed_streams = subscribed_streams

        self.client = zulip.Client(zulip_username, zulip_api_key)
        self.subscriptions = self.subscribe_to_streams()

    @property
    def streams(self):
        """ Standardizes a list of streams in the form [{'name': stream}]. """

        if not self.subscribed_streams:
            streams = [{'name': stream['name']}
                       for stream in self.get_all_zulip_streams()]
            return streams

        else:
            streams = [{'name': stream} for stream in self.subscribed_streams]
            return streams

    def get_all_zulip_streams(self):
        """ Call Zulip API to get a list of all streams. """

        response = requests.get('https://api.zulip.com/v1/streams',
                                auth=(self.username, self.api_key))

        if response.status_code == 200:
            return response.json()['streams']

        elif response.status_code == 401:
            raise RuntimeError('check yo auth')

        else:
            raise RuntimeError(':( we failed to GET streams.\n(%s)' % response)

    def subscribe_to_streams(self):
        """ Subscribes to zulip streams. """

        self.client.add_subscriptions(self.streams)

    def respond(self, msg):
        """ If key_word in msg, ping participants of the subject.

            Args:
                msg: Zulip message listen by the bot.
        """

        # decode message if not unicode
        if type(msg["content"]) is not unicode:
            msg["content"] = msg["content"].decode("utf-8", "ignore")

        first_word = msg['content'].split()[0].lower().strip()
        if self.key_word == first_word or self.short_key_word == first_word:

            # try to parse message looking for time string or participants num
            time, num_participants = None, None
            time, issuer_msg = self.parse_time(msg["content"])
            num_participants = self.parse_num_participants(msg["content"])

            # use time if succesful parsing
            if time:
                msgs = self.get_msgs(
                    time, msg["display_recipient"], msg["subject"])

                participants = self.get_participants(
                    msgs, msg["sender_full_name"])

                ping_msg = self.ping_participants_msg(msg, participants, time,
                                                      issuer_msg)

            # otherwise, participants number could be provided
            elif num_participants:
                participants = self.get_last_participants(
                    num_participants, msg["display_recipient"],
                    msg["subject"], msg["sender_full_name"])

                ping_msg = self.ping_last_participants_msg(msg, participants)

            # any other message formatting, triggers the maximum time range
            else:
                time = self._get_shifted_time(3, "m")

                msgs = self.get_msgs(
                    time, msg["display_recipient"], msg["subject"])

                participants = self.get_participants(
                    msgs, msg["sender_full_name"])

                ping_msg = self.ping_participants_msg(msg, participants, time)

            ping_msg["to"] = ping_msg["display_recipient"]

            self.client.send_message(ping_msg)

    def get_last_participants(self, num_particip, stream, subject, issuer):
        """ Get last participants in a stream-subject.

        Args:
            num_particip: Number of participants to be pinged.
            stream: Zulip stream of the participants.
            subject: Subject of the participants.
            issuer: Zulip participant that is pinging the others.
        """

        anchor = 18446744073709551615
        earliest = arrow.now()
        max_past_time = self._get_shifted_time(3, "m")

        participants = []
        while earliest > max_past_time and len(participants) < num_particip:
            msgs_chunk = self._get_msgs_chunk(self.CHUNK_SIZE, stream, anchor)

            timestamp = msgs_chunk[0]["timestamp"]
            earliest = arrow.get(timestamp)

            anchor = msgs_chunk[0]["id"]

            # reversed msgs_chunk start from earliest to latest
            for msg in reversed(msgs_chunk):
                pinged_particip = "".join([self.PING_INI,
                                           msg["sender_full_name"],
                                           self.PING_END])

                already = pinged_particip in participants
                is_bot = self._bot_msg(msg)
                same_person = issuer == msg["sender_full_name"]
                correct_subj = msg["subject"] == subject

                if (not already and not is_bot and not same_person and
                        correct_subj):
                    participants.append(pinged_particip)

                if len(participants) >= num_particip:
                    break

            # stop asking for messages if less than chunk size were retrieved
            if not msgs_chunk or len(msgs_chunk) < self.CHUNK_SIZE:
                break

        return participants

    @classmethod
    def parse_time(cls, msg_content):
        """ Try to parse a time string in message content.

        Args:
            msg_content: Content of a Zulip message to be parsed.
        """

        msg_split = msg_content.lower().split()

        if len(msg_split) > 1:

            # taking out the bot key word
            time_str = " ".join(msg_split[1:]).strip()

            grammar = parsley.makeGrammar("""
                today = 'today' ws -> (0, "d")
                this = 'this' ws <letter+>:freq -> (0, freq[0])

                min = 'min' letter* ws <digit*>:num -> (int(num or 0), "min")
                min2 = <digit*>:num ws 'min' letter* -> (int(num or 0), "min")

                t1 = <letter+>:freq ws <digit*>:num -> (int(num or 0), freq[0])
                t2 = <digit*>:num ws <letter+>:freq -> (int(num or 0), freq[0])

                time_expr = today | this | min | min2 | t1 | t2
                issuer_msg = ' ' ws <anything*>:msg -> msg

                message = time_expr:time issuer_msg?:msg -> (time, msg)
                """, {})

            # try to match for time first
            try:
                time, msg = grammar(time_str).message()
                num, freq = time
                shifted_time = cls._get_shifted_time(num, freq)

            except Exception as inst:
                print inst
                shifted_time = None
                msg = None

        else:
            shifted_time = None
            msg = None

        return shifted_time, msg

    @classmethod
    def parse_num_participants(cls, msg_content):
        """ Try to parse a number of participants to ping from message.

        Args:
            msg_content: Content of a Zulip message to be parsed.
        """

        msg_content_elems = msg_content.split()

        if len(msg_content_elems) > 1:

            # get number of participants
            num_participants = None
            try:
                num_participants = int(msg_content_elems[1].lower().strip())
            except Exception as inst:
                print inst

        else:
            num_participants = 0

        return num_participants

    @classmethod
    def _get_shifted_time(cls, num, freq):
        """ Create a timedelta from a number and a frequency.

        Args:
            num: Number of time units to shift from now.
            freq: Type or frequency of time units (s "seconds", min "minutes",
                h "hours", d "days", w "weeks", m "months")
        """

        # get anchors
        now = arrow.now()
        default_shifted_time = now.replace(months=-3).floor("month")

        freqs = {"s":  "second",
                 "min":  "minute",
                 "h":  "hour",
                 "d":  "day",
                 "w":  "week",
                 "m":  "month"}

        # calculate shifted time if frequency is valid
        if freq in freqs:
            replace = {freqs[freq] + "s": -num}
            shifted_time = now.replace(**replace).floor(freqs[freq])
        else:
            shifted_time = None

        # use default if invalid frequency or shifted time is too far in past
        if not shifted_time or shifted_time < default_shifted_time:
            shifted_time = default_shifted_time

        return shifted_time

    def get_msgs(self, time, stream, subject):
        """ Get all messages from a stream-subject after a certain "time".

        Args:
            time: Time from when collected messages will start.
            stream: Name of the zulip stream where to collect messages.
            subject: Name of the subject where to collect messages.
        """

        anchor = 18446744073709551615
        earliest = arrow.now()
        # print time

        messages = []
        while earliest > time:
            msgs_chunk = self._get_msgs_chunk(self.CHUNK_SIZE, stream, anchor)

            timestamp = msgs_chunk[0]["timestamp"]
            earliest = arrow.get(timestamp)

            anchor = msgs_chunk[0]["id"]
            msgs = []
            for msg in msgs_chunk:
                msg_time = arrow.get(msg["timestamp"])

                if msg["subject"] == subject and msg_time > time:
                    msgs.append(msg)

            messages.extend(msgs)

            # stop asking for messages if less than chunk size were retrieved
            if not msgs_chunk or len(msgs_chunk) < self.CHUNK_SIZE:
                break

        return messages

    def _get_msgs_chunk(self, chunk_size, stream, anchor=18446744073709551615):
        """ Retrieve a chunk of messages from a Zulip stream.

        Args:
            chunk_size: Maximum number of messages to retrieve.
            stream: Zulip stream where messages will be retrieved.
            anchor: Time anchor from where to retrieve messages going to the
                past. Default is a maximum 64-bit integer number meaning
                "last message".
        """

        print "chunk", chunk_size, "stream", stream, "anchor", anchor

        payload = {"anchor": anchor,
                   "narrow": "".join(['[{"operator":"stream","operand":"',
                                      unicode(stream), '"}]']),
                   "num_before": chunk_size,
                   "num_after": 0,
                   "apply_markdown": "false"}

        response = requests.get('https://api.zulip.com/v1/messages',
                                params=payload,
                                auth=(self.username, self.api_key))

        if response.status_code == 200:
            json_res = response.json()
            messages = json_res["messages"]

        else:
            print response.json()
            messages = None

        if messages:
            print "num messages retrieved", len(messages)

        return messages

    @classmethod
    def get_participants(cls, msgs, issuer):
        """ Extract a list of participants from a bunch of messages.

        Args:
            msgs: Messages from where to extract participant names.
            issuer: Participant that is pinging the other ones.
        """

        json.dump({"messages": msgs}, open("msg.json", "wb"))

        participants = []
        for msg in msgs:
            pinged_particip = "".join([cls.PING_INI,
                                       msg["sender_full_name"],
                                       cls.PING_END])

            bot_msg = cls._bot_msg(msg)
            autoping = issuer == unicode(msg["sender_full_name"])
            already_catched = pinged_particip not in participants

            if not bot_msg and not autoping and already_catched:
                participants.append(pinged_particip)

        return participants

    @classmethod
    def _bot_msg(cls, msg):
        return "-bot@students.hackerschool.com" in msg["sender_email"]

    @classmethod
    def ping_participants_msg(cls, msg, participants, time, issuer_msg=None):
        """ Create a message pinging participants.

        Args:
            msg: Zulip message retrieved.
            participants: Full name of participants to be pinged (list).
            time: Time the participants are pinged from.
            issuer_msg: Optional message wrote by issuer of the ping message.
        """

        t_format = "%m/%d/%y %H:%M:%S"

        # create main part of the message
        msg["content"] = "".join(["Pinging all participants from ",
                                  time.humanize(), " (",
                                  time.strftime(t_format), " to ",
                                  arrow.now().strftime(t_format), ")"
                                  "\n",
                                  " ".join(participants)])

        # create an optional message if issuer has added it
        if issuer_msg:
            issuer = msg["sender_full_name"]
            msg["content"] += "".join(["\n**", issuer,
                                       ":** ",
                                       issuer_msg])

        return msg

    def ping_last_participants_msg(self, msg, participants, issuer_msg=None):
        """ Create message pinging last number of participants.

        Args:
            msg: Zulip message retrieved.
            participants: Full name of participants to be pinged (list).
        """

        msg["content"] = "".join(["Pinging last ",
                                  str(len(participants)), " participants",
                                  "\n",
                                  " ".join(participants)])

        # create an optional message if issuer has added it
        if issuer_msg:
            issuer = msg["sender_full_name"]
            msg["content"] += "".join(["\n**", issuer, "** says: ",
                                       issuer_msg])

        return msg

    def main(self):
        """ Blocking call that runs forever.
            Calls self.respond() on every message received."""

        self.client.call_on_each_message(lambda msg: self.respond(msg))


def get_bot():
    """Create a Zulip pinging bot.

    Attributes:
        zulip_username: Username of the bot in Zulip (email).
        zulip_api_key: API key of the bot in Zulip.
        key_word: Word that triggers the bot's action.
        short_key_word: Alternative short key word.
        subscribed_streams: Streams to suscribe ([] = all streams)
    """

    zulip_username = os.environ['ZULIP_USR']
    zulip_api_key = os.environ['ZULIP_API']
    key_word = 'PingingBot'
    short_key_word = 'PingBot'

    subscribed_streams = []

    new_bot = PingingBot(zulip_username, zulip_api_key, key_word,
                         short_key_word, subscribed_streams)

    return new_bot

if __name__ == '__main__':
    get_bot().main()
