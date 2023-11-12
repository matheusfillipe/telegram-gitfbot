# GifBot
Telegram bot to combine gifs to make new gifs with subtitles.

## Use the bot
Live at [https://t.me/gifbotpuki_bot](https://t.me/gifbotpuki_bot)

## Self host
Copy the example `.env` file and fill in with your bot token.
```bash
git clone "?????"
pip install -U poetry
poetry install
cp .env-example .env
# Edit .env
poetry run python -m bot
```

## Contribute
```bash
git clone "?????"
pip install -U poetry pre-commit
poetry install
pre-commit install
./hotreload.sh
```
