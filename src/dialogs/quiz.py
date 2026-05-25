from typing import Any, Optional
from aiogram import F
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery
from aiogram_dialog import (
    Window,
    Dialog,
    DialogManager,
    ShowMode,
    StartMode,
)
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.kbd import Group, Select
from aiogram_dialog.widgets.kbd import Button

from quiz import QuizData
import quiz
from quiz import get_ideology_data
from loguru import logger


class QuizSG(StatesGroup):
    question = State()


success = F["questions_data"]
fail = ~success


async def get_quiz_data(dialog_manager: DialogManager, **kwargs):
    quiz_data: Optional[quiz.QuizData] = quiz.QUIZ_DATA
    current_index: int = dialog_manager.dialog_data.get("current_index", 0)

    current_index = max(0, min(current_index, len(quiz_data.questions)))

    question = quiz_data.questions[current_index]
    answers = quiz_data.get_question_answers(question)
    answers_data = [a.model_dump() for a in answers]

    return {
        "question_text": question.text,
        "question_id": question.id,
        "question_index": current_index+1,
        "question_total": len(quiz_data.questions),
        "answers": answers_data,
        "has_prev": current_index > 0,
        "back_button_text": "Назад ←" if current_index == 0 else "Назад ←",
    }


async def go_prev(callback, button: Button, manager: DialogManager):
    current = manager.dialog_data.get("current_index", 0)
    if current == 0:
        from dialogs.main import MainSG
        await manager.start(MainSG.start, mode=StartMode.RESET_STACK, show_mode=ShowMode.SEND)
    else:
        manager.dialog_data["current_index"] = current - 1
        await manager.update(data=manager.dialog_data)


async def choose_answer(callback: CallbackQuery, widget: Any, manager: DialogManager, item_id: str):
    current = manager.dialog_data.get("current_index", 0)
    question = quiz.QUIZ_DATA.questions[current]

    start_data = manager.start_data or {}
    if "selected_answers" not in manager.dialog_data:
        manager.dialog_data["selected_answers"] = start_data.get("selected_answers", {})
    manager.dialog_data["selected_answers"][question.id] = item_id

    quiz_data: Optional[QuizData] = quiz.QUIZ_DATA
    total = len(quiz_data.questions)

    # Log the choice
    answers = quiz_data.get_question_answers(question)
    selected_answer = next((a for a in answers if str(a.id) == item_id), None)
    answer_text = selected_answer.text if selected_answer else f"ID: {item_id}"
    logger.info(
        "Selected answer for question {}/{}: '{}' (Choice: {})",
        current + 1,
        total,
        question.text,
        answer_text
    )

    if current < total-1:
        manager.dialog_data["current_index"] = current + 1
        await manager.update(data=manager.dialog_data)
    else:
        answers = manager.dialog_data["selected_answers"]
        results = get_ideology_data(answers)
        results["selected_answers"] = answers
        results["start_data"] = manager.start_data
        await manager.done(result=results)


quiz_dialog = Dialog(
    Window(
        Format("<b>Вопрос {question_index}/{question_total}</b>\n"),
        Format("{question_text}"),
        Group(
            Select(
                Format("{item[text]}"),
                id="select_answer",
                item_id_getter=lambda item: item["id"],
                items="answers",
                on_click=choose_answer,
            ),
            width=1,
        ),
        Button(
            Format("{back_button_text}"),
            id="go_prev",
            on_click=go_prev,
        ),
        state=QuizSG.question,
        getter=get_quiz_data,
        parse_mode="HTML",
    ),
)
