from dotenv import load_dotenv
from config import Config

from dialogs.main import MainSG, start_command, main_dialog
from dialogs.quiz import quiz_dialog

from quiz import load_quiz

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart, ExceptionTypeFilter
from aiogram.fsm.storage.memory import MemoryStorage


from aiogram_dialog import (
    Dialog,
    DialogManager,
    ShowMode,
    StartMode,
    Window,
    setup_dialogs,
)
from aiogram_dialog.api.exceptions import UnknownIntent, UnknownState


logger = logging.getLogger(__name__)


async def on_unknown_intent(event, dialog_manager: DialogManager):
    # Example of handling UnknownIntent Error and starting new dialog.
    logger.error("Restarting dialog: %s", event.exception)
    await dialog_manager.start(
        MainSG.start,
        mode=StartMode.RESET_STACK,
        show_mode=ShowMode.SEND,
    )


async def on_unknown_state(event, dialog_manager: DialogManager):
    # Example of handling UnknownState Error and starting new dialog.
    logger.error("Restarting dialog: %s", event.exception)
    await dialog_manager.start(
        MainSG.start,
        mode=StartMode.RESET_STACK,
        show_mode=ShowMode.SEND,
    )


async def main():
    logging.basicConfig(level=logging.INFO)
    bot = Bot(token=Config.BOT_TOKEN)

    load_quiz(Config.QUIZ_PATH)

    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.message.register(start_command, CommandStart())
    dp.errors.register(
        on_unknown_intent,
        ExceptionTypeFilter(UnknownIntent),
    )
    dp.errors.register(
        on_unknown_state,
        ExceptionTypeFilter(UnknownState),
    )

    dp.include_router(main_dialog)
    dp.include_router(quiz_dialog)

    setup_dialogs(dp)

    await dp.start_polling(bot)


if __name__ == "__main__":
    load_dotenv()
    asyncio.run(main())
