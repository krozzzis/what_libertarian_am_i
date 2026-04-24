from aiogram import F
from aiogram.fsm.state import State, StatesGroup
from aiogram_dialog import (
    Dialog,
    DialogManager,
    ShowMode,
    StartMode,
    Window,
)
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.kbd import Start, Group, Button, Url
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
    from quiz import IDEOLOGY_DESCRIPTIONS
    from config import Config

    selected = dialog_manager.dialog_data.get("selected_answers", {})
    ideology = dialog_manager.dialog_data.get("ideology", "")
    ideology_key = dialog_manager.dialog_data.get("ideology_key", "")
    flags = dialog_manager.dialog_data.get("flags", {})

    desc_parts = []

    if ideology_key and ideology_key in IDEOLOGY_DESCRIPTIONS:
        desc_parts.append(f"{IDEOLOGY_DESCRIPTIONS[ideology_key]}")

    for key in ["paleo", "bleeding-heart", "geo", "agora"]:
        if flags.get(key):
            text = IDEOLOGY_DESCRIPTIONS.get(key, "")
            if text:
                name = key.replace("-", " ").capitalize()
                desc_parts.append(f"{text}")

    is_libertarian = ideology_key in LIBERTARIAN_KEYS

    descriptions = "\n\n".join(desc_parts)

    return {
        "selected_answers": str(selected),
        "ideology": ideology,
        "descriptions": descriptions,
        "show_join_link": is_libertarian,
        "party_url": Config.PARTY_URL,
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
        Format("<b>Ваша идеология:</b> {ideology}\n\n{descriptions}"),
        Format("\n<b><i>(DEBUG)</i>Выбранные ответы:</b>\n<code>{selected_answers}</code>\n"),
        Format("Вам будут рады в Либертарианской Партии России. <a href=\"{party_url}\">Заполнить заявку на вступление</a>", when=F["show_join_link"]),
        Button(Const("Пройти еще раз"), id="restart", on_click=restart_test),
        state=MainSG.result,
        getter=get_result_data,
        parse_mode="HTML",
    ),
    on_process_result=on_dialog_result,
)


async def start_command(_message: Message, dialog_manager: DialogManager):
    await dialog_manager.start(MainSG.start, mode=StartMode.RESET_STACK)
