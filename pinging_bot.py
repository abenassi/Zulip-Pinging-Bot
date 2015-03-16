import zulip
import requests
import re
import pprint
import datetime
from calendar import monthrange
import os


class Bot():

    ''' bot takes a zulip username and api key, a word or phrase to respond to,
        a search string for giphy, an optional caption or list of captions, and
        a list of the zulip streams it should be active in. It then posts a
        caption and a randomly selected gif in response to zulip messages.
    '''

    CHUNK_SIZE = 100

    def __init__(self, zulip_username, zulip_api_key, key_word,
                 subscribed_streams=[]):
        self.username = zulip_username
        self.api_key = zulip_api_key
        self.key_word = key_word.lower()
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
        if self.key_word == first_word:
            print "\n\n----------------Time-----------------\n\n"
            time = self.parse_time(msg["content"])
            print time

            print "\n\n----------------Msgs-----------------\n\n"
            msgs = self.get_msgs(
                time, msg["display_recipient"], msg["subject"])
             #print msgs

            print "\n\n----------------Participants-----------------\n\n"
            participants = self.get_participants(msgs)
            print participants

            print "\n\n----------------PingMsg-----------------\n\n"
            ping_msg = self.ping_participants_msg(msg, participants, time)
            print ping_msg

            ping_msg["to"] = ping_msg["display_recipient"]
            self.client.send_message(ping_msg)

    def parse_time(self, msg_content):
        msg_content_elems = msg_content.split()

        delta_default = self._get_timedelta(3, "m")
        delta = delta_default

        if len(msg_content_elems) > 1:

            # get num and time frequency
            time_str = msg_content_elems[1].lower().strip()
            result = re.match("([0-9]+)([a-z])", time_str)
            # print time_str
            num = int(result.groups()[0])
            freq = result.groups()[1]

            delta = self._get_timedelta(num, freq)
            # print delta

            if delta > delta_default:
                delta = delta_default

        today = datetime.datetime.today().date()
        time = today - delta

        return time

    def _get_timedelta(self, num, freq):
        """Create a timedelta from a number and a frequency."""

        delta = datetime.timedelta(days=self._months_to_days(3))

        freq_to_delta = {"d": "days",
                         "w": "weeks",
                         "m": "months"}

        if freq in freq_to_delta:

            if freq != "m":
                delta_key = freq_to_delta[freq]
                # print delta_key, num
                delta_dict = {delta_key: num}

            else:
                eq_days = self._months_to_days(num)
                delta_dict = {"days": eq_days}

            # print delta_dict
            delta = datetime.timedelta(**delta_dict)

        return delta

    def _months_to_days(self, num):
        """Convert a number of months in equivalent days (last 3 months)."""

        today = datetime.datetime.date(datetime.datetime.today())
        year = today.year
        month = today.month
        days = 0

        for i_month in xrange(num):
            if month == 1:
                month = 12
                year -= 1
            else:
                month -= 1

            days += monthrange(year, month)[1]

        return days

    def get_msgs(self, time, stream, subject):
        print time, stream, subject

        anchor = 18446744073709551615
        earliest = datetime.datetime.today().date()

        messages = []
        while earliest > time:
            # print earliest, time, stream, subject
            msgs_chunk = self._get_msgs_chunk(self.CHUNK_SIZE, stream, anchor)
            timestamp = msgs_chunk[0]["timestamp"]
            earliest = datetime.datetime.fromtimestamp(timestamp).date()

            anchor = msgs_chunk[0]["id"]
            print "here -3"
            print "we are printing msgs chunk"
            print len(msgs_chunk)
            # print msgs_chunk
            msgs = []
            for msg in msgs_chunk:
                # print "adding msgs from chunk..."
                msg_time = datetime.datetime.fromtimestamp(
                    msg["timestamp"]).date()
                if msg["subject"] == subject and msg_time > time:
                    msgs.append(msg)

            messages.extend(msgs)
            print "here!"

        print "ending!"
        return messages

    def _get_msgs_chunk(self, chunk_size, stream, anchor=18446744073709551615):
        print chunk_size, stream, anchor

        payload = {"anchor": anchor,
                   "narrow": '[{"operator":"stream","operand":"' + str(stream) + '"}]',
                   "num_before": chunk_size,
                   "num_after": 0,
                   "apply_markdown": "false"}

        response = requests.get('https://api.zulip.com/v1/messages',
                                params=payload,
                                auth=(self.username, self.api_key))

        json_res = response.json()
        # print json_res
        messages = json_res["messages"]

        return messages

    def get_participants(self, msgs):
        """Extract a list of participants from a bunch of messages."""
        participants = ["@**" + msg["sender_full_name"] + "**" for msg in msgs]
        return set(participants)

    def ping_participants_msg(self, msg, participants, time):

        msg["content"] = "".join(["Pinging all participants from ",
                                  time.strftime("%m/%d/%y"), " to ",
                                  datetime.datetime.now().strftime("%m/%d/%y"),
                                  "\n",
                                  " ".join(participants)])

        return msg

    def main(self):
        ''' Blocking call that runs forever. Calls self.respond() on every
            message received.
        '''

        self.client.call_on_each_message(lambda msg: self.respond(msg))

    ''' The Customization Part!

    Create a zulip bot under "settings" on zulip.
    Zulip will give you a username and API key
    key_word is the text in Zulip you would like the bot to respond to. This
    may be a single word or a phrase.
    search_string is what you want the bot to search giphy for.
    caption may be one of: [] OR 'a single string'
    OR ['or a list', 'of strings']
    subscribed_streams is a list of the streams the bot should be active on.
    An empty list defaults to ALL zulip streams

'''


def get_bot():
    zulip_username = os.environ['ZULIP_USR']
    zulip_api_key = os.environ['ZULIP_API']
    key_word = 'PingingBot'

    subscribed_streams = []

    new_bot = Bot(zulip_username, zulip_api_key, key_word, subscribed_streams)

    return new_bot


def main():
    new_bot = get_bot()
    new_bot.main()

if __name__ == '__main__':
    main()
