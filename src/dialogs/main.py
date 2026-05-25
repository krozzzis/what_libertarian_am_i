from pathlib import Path

import asyncio
from loguru import logger

from aiogram import Bot, F
from aiogram.enums import ContentType
from aiogram.fsm.state import State, StatesGroup
from aiogram_dialog import (
    Dialog,
    DialogManager,
    ShowMode,
    StartMode,
    Window,
)
from aiogram_dialog.api.entities import MediaAttachment
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.kbd import Start, Group, Button
from aiogram_dialog.widgets.media import DynamicMedia
from aiogram.types import FSInputFile, Message, BotCommand

from config import Config
from dialogs.quiz import QuizSG, quiz_dialog


class MainSG(StatesGroup):
    start = State()
    result = State()


async def restart_test(callback, button, manager: DialogManager):
    await manager.start(MainSG.start, mode=StartMode.RESET_STACK, show_mode=ShowMode.SEND)


async def on_dialog_result(start_data, result_data, manager: DialogManager):
    ideology = result_data.get("display_name", "")
    ideology_key = result_data.get("ideology_key", "")
    result_key = result_data.get("result_key", "")

    logger.info("Quiz completed! Resulting Ideology: '{}' (Key: {})", ideology, result_key)

    manager.dialog_data["ideology"] = ideology
    manager.dialog_data["ideology_key"] = ideology_key
    manager.dialog_data["result_key"] = result_key

    await manager.switch_to(MainSG.result)


def _build_image_name(result_key: str, base_key: str, images: dict) -> str | None:
    """Ищет изображение: сначала по точному имени, затем по базовому ключу."""
    if images is None:
        return None
    if result_key in images:
        return images[result_key]
    if base_key in images:
        return images[base_key]
    return images.get("default")


async def get_result_data(dialog_manager: DialogManager, **kwargs):
    from quiz import QUIZ_DATA

    ideology = dialog_manager.dialog_data.get("ideology", "")
    ideology_key = dialog_manager.dialog_data.get("ideology_key", "")
    result_key = dialog_manager.dialog_data.get("result_key", "")

    ideology_def = None
    if QUIZ_DATA.ideologies:
        if result_key:
            ideology_def = QUIZ_DATA.ideologies.get(result_key)
        if not ideology_def:
            ideology_def = QUIZ_DATA.ideologies.get(ideology_key)

    result_message = ideology_def.result_message if ideology_def else None

    if result_message:
        person_name = ideology_def.idealogy_person if ideology_def and ideology_def.idealogy_person else ideology
        final_result_text = (
            result_message
            .replace("%ideology_name%", ideology)
            .replace("%idealogy_person%", person_name)
            .replace("%party_url%", Config.PARTY_URL)
        )
    else:
        final_result_text = (
            f"Результаты вашего тестирования: {ideology}\n\n"
            f"Вам будут рады в Либертарианской Партии России. {Config.PARTY_URL}"
        )

    image_name = _build_image_name(result_key, ideology_key, QUIZ_DATA.ideology_images)

    media_attachment = None

    if image_name:
        base_dir = (
            Path(Config.QUIZ_PATH).parent
            if getattr(Config, "QUIZ_PATH", None)
            else Path("data")
        )
        image_path = base_dir / image_name

        if image_path.exists() and image_path.is_file():
            media_attachment = MediaAttachment(ContentType.PHOTO, path=str(image_path))
        else:
            media_attachment = MediaAttachment(ContentType.PHOTO, file_id=image_name)

    return {
        "final_result_text": final_result_text,
        "result_image": media_attachment,
    }


async def show_all(message: Message):
    """Админская команда: вывод всех возможных результатов тестирования."""
    from quiz import QUIZ_DATA

    if message.from_user.id not in Config.ADMIN_IDS:
        return

    results = []

    for image_key in QUIZ_DATA.ideology_images:
        if image_key == "default":
            continue

        base_key = image_key.split("-")[-1]
        if image_key == "classical_liberalism":
            base_key = "classical_liberalism"
        elif image_key == "social_democracy":
            base_key = "social_democracy"

        ideology_def = QUIZ_DATA.ideologies.get(image_key)
        if not ideology_def:
            ideology_def = QUIZ_DATA.ideologies.get(base_key)

        if not ideology_def:
            continue

        base_def = QUIZ_DATA.ideologies.get(base_key)
        base_name = base_def.base_name or base_def.full_name if base_def else ideology_def.full_name

        name_parts = []
        if "geo" in image_key:
            name_parts.append(QUIZ_DATA.ideologies["geo"].prefix)
        if "paleo" in image_key:
            name_parts.append(QUIZ_DATA.ideologies["paleo"].prefix)
        if "bleeding-heart" in image_key:
            name_parts.append(QUIZ_DATA.ideologies["bleeding-heart"].prefix)
        name_parts.append(base_name)
        display_name = "-".join(name_parts)

        results.append((display_name, base_key, ideology_def, image_key))

    # Отправка
    total = len(results)
    for i, (display_name, base_key, ideology_def, image_key) in enumerate(results):
        result_msg = ideology_def.result_message if ideology_def else None
        if result_msg:
            person_name = ideology_def.idealogy_person if ideology_def.idealogy_person else display_name
            text = (
                result_msg
                .replace("%ideology_name%", display_name)
                .replace("%idealogy_person%", person_name)
                .replace("%party_url%", Config.PARTY_URL)
            )
        else:
            text = (
                f"Результаты вашего тестирования: {display_name}\n\n"
                f"Вам будут рады в Либертарианской Партии России. {Config.PARTY_URL}"
            )

        img = _build_image_name(display_name, image_key, QUIZ_DATA.ideology_images)
        if img:
            base_dir = (
                Path(Config.QUIZ_PATH).parent
                if getattr(Config, "QUIZ_PATH", None)
                else Path("data")
            )
            image_path = base_dir / img
            if image_path.exists() and image_path.is_file():
                await message.answer_photo(FSInputFile(image_path), caption=text)
            else:
                await message.answer_photo(img, caption=text)
        else:
            await message.answer(text)

        if i < total - 1:
            await asyncio.sleep(0.5)


async def setup_bot_commands(bot: Bot):
    """Автоматическая регистрация пользовательских команд в меню бота."""
    commands: list[BotCommand] = [
        BotCommand(command="start", description="Начать тест"),
    ]

    await bot.set_my_commands(commands)


async def start_command(_message: Message, dialog_manager: DialogManager):
    await dialog_manager.start(MainSG.start, mode=StartMode.RESET_STACK)


main_dialog = Dialog(
    Window(
        Const("Приветствуем вас на тесте политических координат от ЛПР.Урал"),
        Group(
            Start(Const("Начать тест"), id="set", state=QuizSG.question, data={"selected_answers": {}}),
            width=1,
        ),
        state=MainSG.start,
        parse_mode="HTML",
    ),
    Window(
        DynamicMedia("result_image", when=F["result_image"]),
        Format("{final_result_text}"),
        # Format("\n<b><i>(DEBUG)</i>Выбранные ответы:</b>\n<code>{selected_answers}</code>\n"),
        Button(Const("Пройти еще раз"), id="restart", on_click=restart_test),
        state=MainSG.result,
        getter=get_result_data,
        parse_mode="HTML",
    ),
    on_process_result=on_dialog_result,
)
