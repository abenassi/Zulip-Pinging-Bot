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
For using the bot in Zulip you just need to type `PingingBot time_string` or `PingingBot participants_number`.

The **time_string** is composed with a number and a letter (only `d` (days), `w` (weeks), `m` (months), `h` (hours), `min` (minutes) and `s` (seconds)). You can ping people that have participated in a conversation up to a maximum of 3 months old or a minimum of 1 second.

The **participants_number** is just a number with no letters after or before it. I allows you to ping a number of recent participants instead of a time range. Although this also has the 3 months limit.

*This will ping all participants in the subject for the last 3 months (the maximum)*
`PingingBot`

*This will ping all participants in the subject for the last 10 days*
`PingingBot 10d`


*This will ping all participants in the subject for the last 2 weeks*
`PingingBot 2w`


*This will ping all participants in the subject for the last 2 months*
`PingingBot 2m`

*This will ping all participants in the subject for the last 3 hours*
`PingingBot 3h`

*This will ping all participants in the subject for the last 30 minutes*
`PingingBot 30min`

*This will ping the last 10 participants in the subject*
`PingingBot 10`


## Credits
Thanks to [@midair](https://github.com/midair) for introducing me in the funny art of building Zulip bots and for the base code [Zulip-Voting-Bot](https://github.com/midair/Zulip-Voting-Bot) upon which I started the development of this bot.
Thanks to [@lfranchi](https://github.com/lfranchi) for his quick response about how to read Zulip stream old messages.
And last but not least, thanks to [@gnclmorais](https://github.com/gnclmorais) for all his help in deploying the bot to Heroku and showing a nice and consistent repo structure for Zulip bots with his [zulip-bot-kaomoji](https://github.com/gnclmorais/zulip-bot-kaomoji)

