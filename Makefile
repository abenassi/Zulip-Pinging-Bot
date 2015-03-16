run:
	python pinging_bot.py

push:
	git push heroku master

log:
	heroku logs --tail

activate:
	heroku ps:scale worker=1

deactivate:
	heroku ps:scale worker=0

von:
	source venv/bin/activate

voff:
	deactivate