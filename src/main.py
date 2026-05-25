from dotenv import load_dotenv
load_dotenv()

from config import Config

from dialogs.main import MainSG, start_command, show_all, main_dialog, setup_bot_commands
from dialogs.quiz import quiz_dialog

from quiz import load_quiz

import asyncio
import logging
import sys
from loguru import logger
from typing import Callable, Dict, Any, Awaitable
from contextvars import ContextVar

from aiogram import Bot, Dispatcher, BaseMiddleware
from aiogram.types import TelegramObject
from aiogram.filters import CommandStart, Command, ExceptionTypeFilter
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


class InterceptHandler(logging.Handler):
    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

current_user_info = ContextVar("current_user_info", default=None)

def patch_record(record):
    info = current_user_info.get()
    if info:
        if "user_id" not in record["extra"]:
            record["extra"]["user_id"] = info.get("user_id")
        if "username" not in record["extra"]:
            record["extra"]["username"] = info.get("username")

def log_formatter(record):
    format_str = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan>"
    
    user_id = record["extra"].get("user_id")
    username = record["extra"].get("username")
    
    if user_id or username:
        user_info = []
        if user_id:
            user_info.append(f"id:{user_id}")
        if username:
            user_info.append(f"@{username}")
        format_str += f" | <yellow>[{', '.join(user_info)}]</yellow>"
        
    format_str += " - <level>{message}</level>\n"
    if record["exception"]:
        format_str += "{exception}\n"
        
    return format_str

def setup_logging():
    logging.basicConfig(handlers=[InterceptHandler()], level=logging.INFO, force=True)
    logger.remove()
    
    # Configure global patcher
    logger.configure(patcher=patch_record)
    
    logger.add(sys.stderr, level=Config.LOG_LEVEL, format=log_formatter)
    if Config.LOG_FILE:
        logger.add(
            Config.LOG_FILE,
            rotation=Config.LOG_ROTATION,
            retention=Config.LOG_RETENTION,
            level=Config.LOG_LEVEL,
            format=log_formatter,
            enqueue=True,
        )

class LoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user:
            current_user_info.set({"user_id": user.id, "username": user.username})
            
            # Log incoming updates safely
            from aiogram.types import Update, Message, CallbackQuery
            inner_event = event.event if isinstance(event, Update) else event
            if isinstance(inner_event, Message):
                logger.info("Received message: '{}'", inner_event.text or inner_event.caption or "[media]")
            elif isinstance(inner_event, CallbackQuery):
                logger.info("Received callback: '{}'", inner_event.data)
                
            with logger.contextualize(user_id=user.id, username=user.username):
                return await handler(event, data)
        return await handler(event, data)

async def on_unknown_intent(event, dialog_manager: DialogManager):
    logger.error("Restarting dialog (UnknownIntent): {}", event.exception)
    await dialog_manager.start(
        MainSG.start,
        mode=StartMode.RESET_STACK,
        show_mode=ShowMode.SEND,
    )


async def on_unknown_state(event, dialog_manager: DialogManager):
    logger.error("Restarting dialog (UnknownState): {}", event.exception)
    await dialog_manager.start(
        MainSG.start,
        mode=StartMode.RESET_STACK,
        show_mode=ShowMode.SEND,
    )


async def main():
    setup_logging()
    bot = Bot(token=Config.BOT_TOKEN)

    load_quiz(Config.QUIZ_PATH)

    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    dp.update.outer_middleware(LoggingMiddleware())

    dp.errors.register(on_unknown_intent, ExceptionTypeFilter(UnknownIntent))
    dp.errors.register(on_unknown_state, ExceptionTypeFilter(UnknownState))

    dp.message.register(start_command, CommandStart())
    dp.message.register(show_all, Command("show_all"))

    dp.include_router(main_dialog)
    dp.include_router(quiz_dialog)

    setup_dialogs(dp)
    await setup_bot_commands(bot)

    await dp.start_polling(bot)


if __name__ == "__main__":
    load_dotenv()
    asyncio.run(main())