# Zulip-Pinging-Bot
Zulip bot to ping participants in a conversation inside certain time range.


## Installation
To work on this bot, follow the instructions to setup you environment:

1. `pip install virtualenv`
2. `virtualenv venv`
3. `source venv/bin/activate`
4. `pip install -r requirements.txt`

`$ deactivate` when you finish.


## Configuration
To run this bot, create a `config.sh` file with the following structure:
```
export ZULIP_USR=<your-bot-address>
export ZULIP_API=<your-bot-apy_key>
```
When having the file, load the variables: `source config.sh`.


## Using the bot in Zulip
For using the bot in Zulip you just need to type `PingBot time_string` or `PingBot participants_number`.

The **time_string** is composed with a number and a letter (only `d` (days), `w` (weeks), `m` (months), `h` (hours), `min` (minutes) and `s` (seconds)). You can ping people that have participated in a conversation up to a maximum of 3 months old or a minimum of 1 second.

The **participants_number** is just a number with no letters after or before it. I allows you to ping a number of recent participants instead of a time range. Although this also has the 3 months limit.

*This will ping all participants in the subject for the last 3 months (the maximum)*
`PingBot`

*This will ping all participants in the subject for the last 10 days*
`PingBot 10d`

*This will ping all participants in the subject for the last 2 weeks*
`PingBot 2w`

*This will ping all participants in the subject for the last 2 months*
`PingBot 2m`

*This will ping all participants in the subject for the last 3 hours*
`PingBot 3h`

*This will ping all participants in the subject for the last 30 minutes*
`PingBot 30min`

*This will ping the last 10 participants in the subject*
`PingBot 10`

### How are time deltas understood by PingingBot

Time deltas in PingBot are always considered as starting in the beginning of a unit. Calling "1d" at 6PM of today will ping all participants from 00:00:00 of yesterday until now. If you want to ping just today participants you can call "0d" or even better "today". Calling just a frequency is the same than calling it with 0 units ("0d" = "d"). If you actually want to ping participants from 6PM yesterday until now, you should call "24h". This works the same way with all the frequency units.

`PingBot 0w` or `PingBot this week` or `PingBot w` *called Tuesday will ping participants from Monday of this week (1 day ago).*

`PingBot 1w` *called Tuesday will ping participants from Monday of last week (8 days ago).*

### Alternative ways to express a time string

The following time strings are equivalent:

`0d` = `d0` = `d` = `day` = `today` = `this day`
`0w` = `w0` = `w` = `week` = `this week`


## Credits
Thanks to [@midair](https://github.com/midair) for introducing me in the funny art of building Zulip bots and for the base code [Zulip-Voting-Bot](https://github.com/midair/Zulip-Voting-Bot) upon which I started the development of this bot.
Thanks to [@lfranchi](https://github.com/lfranchi) for his quick response about how to read Zulip stream old messages.
And last but not least, thanks to [@gnclmorais](https://github.com/gnclmorais) for all his help in deploying the bot to Heroku and showing a nice and consistent repo structure for Zulip bots with his [zulip-bot-kaomoji](https://github.com/gnclmorais/zulip-bot-kaomoji)

