#!/usr/bin/env python
# -*- coding: utf-8 -*-

import zulip
import requests
import os
import parsley
import arrow
import json


class Bot():

    ''' bot takes a zulip username and api key, a word or phrase to respond to,
        a search string for giphy, an optional caption or list of captions, and
        a list of the zulip streams it should be active in. It then posts a
        caption and a randomly selected gif in response to zulip messages.
    '''

    CHUNK_SIZE = 5000
    PING_INI = "@**"
    PING_END = "**"

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
        ''' Standardizes a list of streams in the form [{'name': stream}]
        '''
        if not self.subscribed_streams:
            streams = [{'name': stream['name']}
                       for stream in self.get_all_zulip_streams()]
            return streams
        else:
            streams = [{'name': stream} for stream in self.subscribed_streams]
            return streams

    def get_all_zulip_streams(self):
        ''' Call Zulip API to get a list of all streams
        '''
        response = requests.get('https://api.zulip.com/v1/streams',
                                auth=(self.username, self.api_key))

        if response.status_code == 200:
            return response.json()['streams']

        elif response.status_code == 401:
            raise RuntimeError('check yo auth')

        else:
            raise RuntimeError(':( we failed to GET streams.\n(%s)' % response)

    def subscribe_to_streams(self):
        ''' Subscribes to zulip streams
        '''
        self.client.add_subscriptions(self.streams)

    def respond(self, msg):
        '''If key_word in msg, ping participants of the subject.'''

        first_word = msg['content'].split()[0].lower().strip()
        if self.key_word == first_word or self.short_key_word == first_word:

            time, num_participants = None, None
            time = self.parse_time(msg["content"])
            num_participants = self.parse_num_participants(msg["content"])

            if time:
                msgs = self.get_msgs(
                    time, msg["display_recipient"], msg["subject"])

                participants = self.get_participants(
                    msgs, msg["sender_full_name"])

                ping_msg = self.ping_participants_msg(msg, participants, time)

            elif num_participants:
                participants = self.get_last_participants(
                    num_participants, msg["display_recipient"],
                    msg["subject"], msg["sender_full_name"])

                ping_msg = self.ping_last_participants_msg(msg, participants)

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
        """Get last participants in a stream-subject.

        Args:
            num_particip: Number of participants to be pinged.
            stream: Zulip stream of the participants.
            subject: Subject of the participants.
            issuer: Zulip participant that is pinging the others.
        """

        anchor = 18446744073709551615
        earliest = arrow.now()
        max_past_time = arrow.now().replace(months=-3).floor("month")

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

        msg_split = msg_content.lower().split()

        if len(msg_split) > 1:

            # taking out the bot key word
            time_str = " ".join(msg_split[1:]).strip()

            grammar = parsley.makeGrammar("""
                today = 'today' ws -> (0, "d")
                this = 'this' ws <letter+>:freq -> (0, freq[0])

                min = 'min' letter* ws <digit*>:num -> (int(num or 0), "min")
                min2 = <digit*>:num ws 'min' letter* -> (int(num or 0), "min")

                t1 = <digit*>:num ws <letter+>:freq -> (int(num or 0), freq[0])
                t2 = <letter+>:freq ws <digit*>:num -> (int(num or 0), freq[0])

                time_params = today | this | min | min2 | t1 | t2
                """, {})

            # try to match for time first
            try:
                num, freq = grammar(time_str).time_params()
                shifted_time = cls._get_shifted_time(num, freq)

            except Exception as inst:
                print inst
                shifted_time = None

        else:
            shifted_time = None

        return shifted_time

    @classmethod
    def parse_num_participants(cls, msg_content):
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
        """Create a timedelta from a number and a frequency."""

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
        """Get all messages from a stream-subject after a certain "time".

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

                if msg["subject"] == subject:
                    print msg["sender_full_name"].encode("utf-8", "ignore")
                if msg["subject"] == subject and msg_time > time:
                    print "appending msg"
                    msgs.append(msg)

            messages.extend(msgs)

            # stop asking for messages if less than chunk size were retrieved
            if not msgs_chunk or len(msgs_chunk) < self.CHUNK_SIZE:
                break

        return messages

    def _get_msgs_chunk(self, chunk_size, stream, anchor=18446744073709551615):

        print "chunk", chunk_size, "stream", stream, "anchor", anchor

        payload = {"anchor": anchor,
                   "narrow": '[{"operator":"stream","operand":"' + str(stream) + '"}]',
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
        """Extract a list of participants from a bunch of messages."""

        json.dump({"messages": msgs}, open("msg.json", "wb"))

        participants = []
        # print "issuer", issuer.encode("utf-8", "ignore")
        for msg in msgs:
            pinged_particip = "".join([cls.PING_INI,
                                       msg["sender_full_name"],
                                       cls.PING_END])

            # print not issuer == msg["sender_full_name"]

            bot_msg = cls._bot_msg(msg)
            autoping = issuer == unicode(msg["sender_full_name"])
            already_catched = pinged_particip not in participants

            # print issuer.encode("utf-8", "ignore"), msg["sender_full_name"].encode("utf-8", "ignore")
            # print "bot_msg", bot_msg, "autoping", autoping,
            # "already_catched", already_catched
            if not bot_msg and not autoping and already_catched:

                # print "appending", participant
                participants.append(pinged_particip)

        return participants

    @classmethod
    def _bot_msg(cls, msg):
        return "-bot@students.hackerschool.com" in msg["sender_email"]

    def ping_participants_msg(self, msg, participants, time):
        t_format = "%m/%d/%y %H:%M:%S"
        msg["content"] = "".join(["Pinging all participants from ",
                                  time.humanize(), " (",
                                  time.strftime(t_format), " to ",
                                  arrow.now().strftime(t_format), ")"
                                  "\n",
                                  " ".join(participants)])

        return msg

    def ping_last_participants_msg(self, msg, participants):
        msg["content"] = "".join(["Pinging last ",
                                  str(len(participants)), " participants",
                                  "\n",
                                  " ".join(participants)])

        return msg

    def main(self):
        ''' Blocking call that runs forever. Calls self.respond() on every
            message received.
        '''

        self.client.call_on_each_message(lambda msg: self.respond(msg))


def get_bot():
    '''Create a Zulip bot

    1. Create a zulip bot under "settings" on zulip.
    2. Zulip will give you a username and API key
    3. key_word is the text in Zulip you would like the bot to respond to. This
    may be a single word or a phrase.
    4. subscribed_streams is a list of the streams the bot should be active on.
    An empty list defaults to ALL zulip streams
    '''

    zulip_username = os.environ['ZULIP_USR']
    zulip_api_key = os.environ['ZULIP_API']
    key_word = 'PingingBot'
    short_key_word = 'PingBot'

    subscribed_streams = []

    new_bot = Bot(zulip_username, zulip_api_key, key_word, short_key_word,
                  subscribed_streams)

    return new_bot


def main():
    new_bot = get_bot()
    new_bot.main()

if __name__ == '__main__':
    main()
