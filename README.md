# SlaveLabourBot
Telegram bot for r/slavelabour that notifies when a new post is uploaded on slavelabour.

## Secrets
Before running the bot you must create a file `secrets.py` containing token and keys for telegram/reddit. An example file is provided as `secrets.py.example`.

## Dependencies
`requirements.txt` lists the packages to install with pip.

## Commands
```
start - Start receiving tasks
add_keyword - Add a keyword to mark tasks
remove_keyword - Remove a keyword
list_keywords - List keywords
stop - Stop receiving tasks
```

## Allowed users
By default the bot can be started only by whitelisted users. Add your username to `allowed_users.txt` to start using the bot.

## Systemd service
`SlaveLabourBotService.service` is a systemd service for the bot. Check the paths in the file before copying it to `/etc/systemd/system/`.

