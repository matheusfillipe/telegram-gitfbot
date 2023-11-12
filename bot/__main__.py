#!/usr/bin/env python
# pylint: disable=unused-argument

import logging
import os
import pathlib
import tempfile
from collections import defaultdict
from typing import DefaultDict
from typing import Optional

from dotenv import load_dotenv
from telegram import Document
from telegram import ForceReply
from telegram import Update
from telegram.ext import Application
from telegram.ext import CallbackContext
from telegram.ext import CommandHandler
from telegram.ext import ContextTypes
from telegram.ext import ExtBot
from telegram.ext import MessageHandler
from telegram.ext import filters

from bot.constants import MAX_FILESIZE
from bot.video_data import VideoData

# Enable logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


class ChatData:
    def __init__(self) -> None:
        self.usermap: DefaultDict[int, VideoData] = defaultdict(VideoData)


# The [ExtBot, dict, ChatData, dict] is for type checkers like mypy
class CustomContext(CallbackContext[ExtBot, dict, ChatData, dict]):
    """Custom class for context."""

    def __init__(
        self,
        application: Application,
        chat_id: Optional[int] = None,
        user_id: Optional[int] = None,
    ):
        super().__init__(application=application, chat_id=chat_id, user_id=user_id)
        self._user_id: Optional[int] = user_id

    @property
    def data(self) -> VideoData | None:
        if not self._user_id or not self.chat_data:
            return None
        return self.chat_data.usermap[self._user_id]


async def downloader(document: Document, context: CustomContext) -> pathlib.Path:
    with tempfile.NamedTemporaryFile(delete=False) as f:
        file = await context.bot.get_file(document)
        if file is None or file.file_size is None:
            raise ValueError("Failed to get file size")
        if file.file_size > MAX_FILESIZE:
            raise ValueError(f"File is too big: {file.file_size} > {MAX_FILESIZE}")
        await file.download_to_drive(f.name)
        return pathlib.Path(f.name)


# Define a few command handlers. These usually take the two arguments update and
# context.
async def start(update: Update, context: CustomContext) -> None:
    """Send a message when the command /start is issued."""
    if update.message is None:
        return
    user = update.effective_user
    if user is None:
        return

    await context.application.bot.set_my_commands(
        [("new", "Start creating a new MEME"), ("end", "Finish creating a new MEME")]
    )
    await update.message.reply_html(
        rf"Hi {user.mention_html()}!",
        reply_markup=ForceReply(selective=True),
    )


async def help_command(update: Update, context: CustomContext) -> None:
    """Send a message when the command /help is issued."""
    if update.message is None:
        return
    await update.message.reply_text("Help!")


async def new_video_command(update: Update, context: CustomContext) -> None:
    """Echo the user message."""
    if update.message is None or context.data is None:
        return
    if context.data.is_new_video:
        await update.message.reply_text("I am already creating a new MEME. Please send gifs with the some text label.")
        return

    await update.message.reply_text("Ok. I will start creating a new MEME. Please send gifs with the some text label.")
    context.data.is_new_video = True


async def end_command(update: Update, context: CustomContext) -> None:
    if update.message is None or context.data is None:
        return
    if not context.data.is_new_video:
        await update.message.reply_text("I will ignore that. Please send /new command to start creating a new MEME")
        return
    await update.message.reply_text("Ok. Rendering...")
    context.data.is_new_video = False
    with tempfile.NamedTemporaryFile(suffix=".mp4") as f:
        await context.data.render(pathlib.Path(f.name))
        await update.message.reply_video(video=open(f.name, "rb"))
        await context.data.cleanup()


async def video_message_handler(update: Update, context: CustomContext) -> None:
    if await video_edit_handler(update, context):
        return
    if update.message is None or context.data is None:
        return
    if not context.data.is_new_video:
        await update.message.reply_text("I will ignore that. Please send /new command to start creating a new MEME")
        return

    if update.message.document is None:
        await update.message.reply_text("Please send gifs with the some text label.")
        return

    try:
        context.data.add_segment(
            update.message.message_id, await downloader(update.message.document, context), update.message.caption
        )
        await update.message.reply_text("Got video! Give me more or send /end to finish.")
    except ValueError as e:
        await update.message.reply_text(f"Error: {e}")


async def video_edit_handler(update: Update, context: CustomContext) -> bool:
    if update.edited_message is None or context.data is None or not context.data.is_new_video:
        return False

    try:
        context.data.edit_caption(update.edited_message.message_id, update.edited_message.caption)
    except ValueError:
        pass
    return True


async def missing_video_handler(update: Update, context: CustomContext) -> None:
    if update.message is None or context.data is None:
        return
    if context.data.is_new_video:
        await update.message.reply_text("I will ignore that. Please send messages with video")


def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TOKEN environment variable is not set")

    context_types = ContextTypes(context=CustomContext, chat_data=ChatData)
    application = Application.builder().token(token).context_types(context_types).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("new", new_video_command))
    application.add_handler(CommandHandler("end", end_command))
    application.add_handler(MessageHandler(filters.VIDEO | filters.ANIMATION, video_message_handler))

    # on non command i.e message - echo the message on Telegram
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, missing_video_handler))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
