from pathlib import Path
from aiogram import F
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
from aiogram_dialog.widgets.kbd import Start, Group, Button, Url
from aiogram_dialog.widgets.media import DynamicMedia
from aiogram.types import Message

from config import Config
from dialogs.quiz import QuizSG


class MainSG(StatesGroup):
    start = State()
    result = State()


async def restart_test(callback, button, manager: DialogManager):
    await manager.start(MainSG.start, mode=StartMode.RESET_STACK, show_mode=ShowMode.SEND)


async def on_dialog_result(start_data, result_data, manager: DialogManager):
    ideology = result_data.get("display_name", "")
    ideology_key = result_data.get("ideology_key", "")

    selected = result_data.get("selected_answers", {})
    flags = {
        "geo": result_data.get("geo", False),
        "paleo": result_data.get("paleo", False),
        "bleeding-heart": result_data.get("bleeding-heart", False),
        "agora": result_data.get("agora", False),
    }

    manager.dialog_data["ideology"] = ideology
    manager.dialog_data["ideology_key"] = ideology_key
    manager.dialog_data["selected_answers"] = selected
    manager.dialog_data["flags"] = flags

    await manager.switch_to(MainSG.result)


LIBERTARIAN_KEYS = {"classical_liberalism", "minarchism", "ancap"}


async def get_result_data(dialog_manager: DialogManager, **kwargs):
    from quiz import QUIZ_DATA
    from config import Config

    selected = dialog_manager.dialog_data.get("selected_answers", {})
    ideology = dialog_manager.dialog_data.get("ideology", "")
    ideology_key = dialog_manager.dialog_data.get("ideology_key", "")
    flags = dialog_manager.dialog_data.get("flags", {})

    desc_parts = []

    if ideology_key and QUIZ_DATA.ideologies and ideology_key in QUIZ_DATA.ideologies:
        desc_parts.append(f"{QUIZ_DATA.ideologies[ideology_key].description}")

    for key in ["paleo", "bleeding-heart", "geo", "agora"]:
        if flags.get(key) and QUIZ_DATA.ideologies and key in QUIZ_DATA.ideologies:
            desc_parts.append(f"{QUIZ_DATA.ideologies[key].description}")

    is_libertarian = ideology_key in LIBERTARIAN_KEYS

    descriptions = "\n\n".join(desc_parts)

    compound_parts = []
    for k in ["geo", "paleo", "bleeding-heart", "agora"]:
        if flags.get(k): compound_parts.append(k)
    if ideology_key: compound_parts.append(ideology_key)
    compound_key = "-".join(compound_parts)

    override_msg = QUIZ_DATA.result_message_overrides.get(compound_key)
    if not override_msg and "agora" in compound_parts:
        fallback_key = "-".join([p for p in compound_parts if p != "agora"])
        override_msg = QUIZ_DATA.result_message_overrides.get(fallback_key)

    if override_msg:
        final_result_text = override_msg.replace("{ideology}", ideology).replace("{descriptions}", descriptions)
    else:
        final_result_text = f"<b>Ваша идеология:</b> {ideology}\n\n{descriptions}"

    image_name = QUIZ_DATA.ideology_images.get(compound_key)
    default_img = QUIZ_DATA.ideology_images.get("default")

    # Если картинка не задана явно (отсутствует или равна default) и есть агоризм - ищем фолбэк
    if (not image_name or image_name == default_img) and "agora" in compound_parts:
        fallback_key = "-".join([p for p in compound_parts if p != "agora"])
        fb_img = QUIZ_DATA.ideology_images.get(fallback_key)
        if fb_img:
            image_name = fb_img

    if not image_name:
        image_name = default_img

    media_attachment = None

    if image_name:
        base_dir = Path(Config.QUIZ_PATH).parent if getattr(Config, 'QUIZ_PATH', None) else Path("data")
        image_path = base_dir / image_name

        if image_path.exists() and image_path.is_file():
            # Если файл существует локально - отправляем файл
            media_attachment = MediaAttachment(ContentType.PHOTO, path=str(image_path))
        else:
            # Если файла нет по такому пути, считаем, что это готовенький file_id
            media_attachment = MediaAttachment(ContentType.PHOTO, file_id=image_name)

    return {
        "selected_answers": str(selected),
        "final_result_text": final_result_text,
        "show_join_link": is_libertarian,
        "party_url": Config.PARTY_URL,
        "result_image": media_attachment,
    }


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
        #Format("\n<b><i>(DEBUG)</i>Выбранные ответы:</b>\n<code>{selected_answers}</code>\n"),
        Format("\nВам будут рады в Либертарианской Партии России. <a href=\"{party_url}\">Заполнить заявку на вступление</a>", when=F["show_join_link"]),
        Button(Const("Пройти еще раз"), id="restart", on_click=restart_test),
        state=MainSG.result,
        getter=get_result_data,
        parse_mode="HTML",
    ),
    on_process_result=on_dialog_result,
)


async def start_command(_message: Message, dialog_manager: DialogManager):
    await dialog_manager.start(MainSG.start, mode=StartMode.RESET_STACK)
