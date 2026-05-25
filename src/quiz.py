from pathlib import Path

import json5
from pydantic import BaseModel


class Answer(BaseModel):
    id: int
    text: str

    @classmethod
    def create(cls, id: int, text: str) -> "Answer":
        return cls(id=id, text=text)


class Question(BaseModel):
    id: int
    text: str
    default_answers: bool | None = None
    answers: list[int] | None = None
    _resolved_answers: list[Answer] | None = None

    @classmethod
    def create(cls, id: int, text: str) -> "Question":
        return cls(id=id, text=text)

    def get_answers(self, default_answer_ids: list[int], all_answers: list[Answer]) -> list[Answer]:
        if self._resolved_answers is not None:
            return self._resolved_answers

        answer_ids = self.answers if self.answers is not None else default_answer_ids
        self._resolved_answers = [a for a in all_answers if a.id in answer_ids]
        return self._resolved_answers


class IdeologyDef(BaseModel):
    full_name: str
    prefix: str | None = None
    base_name: str | None = None
    result_message: str | None = None
    idealogy_person: str | None = None


class QuizData(BaseModel):
    questions: list[Question]
    default_answers: list[int] | None = None
    answers: list[Answer] = []
    ideologies: dict[str, IdeologyDef] = {}
    ideology_images: dict[str, str] = {}

    @classmethod
    def create(cls, questions: list[Question]) -> "QuizData":
        return cls(questions=questions)

    def get_question_answers(self, question: Question) -> list[Answer]:
        default_ids = self.default_answers or []
        return question.get_answers(default_ids, self.answers)


QUIZ_DATA: QuizData = QuizData.create(
    [
        Question.create(1, "Nothing"),
    ]
)


def parse_quiz(text: str) -> QuizData:
    data = json5.loads(text)

    return QuizData.model_validate(data)


def open_quiz(file_path: str | Path) -> QuizData:
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if not path.is_file():
        raise ValueError(f"Path is pointing to directory not to file: {path}")

    with open(path, encoding="utf-8") as f:
        content = f.read()

    data = parse_quiz(content)

    return data


def load_quiz(file_path: str | Path):
    global QUIZ_DATA
    QUIZ_DATA = open_quiz(file_path)


def get_ideology_data(user_answers):
    # Конвертация: '1'(+2) ... '5'(-2)
    scores = {int(k): {1: 2, 2: 1, 3: 0, 4: -1, 5: -2}[int(v)] for k, v in user_answers.items()}

    # --- 1. Расчёт всех осей ---

    # Этатизм: вопросы 18, 19, 20 (макс +6, мин -6)
    statist_score = scores.get(18, 0) + scores.get(19, 0) + scores.get(20, 0)

    # Ось государства: чем выше — тем больше поддержка минимального государства
    # q1 (государство для защиты), q2 (налоги на полицию), q9 (выборы) — за государство
    # q3 (частные суды/полиция), q21 (прямые действия вместо выборов) — против государства
    state_axis = scores.get(1, 0) + scores.get(2, 0) + scores.get(9, 0) - scores.get(3, 0) - scores.get(21, 0)

    # Культурная ось:
    # Прогрессивные: q10 (борьба с дискриминацией), q13 (преодоление неравенства),
    #                q18 (социальные программы), q22 (равные возможности)
    # Традиционные: q11 (семья и традиции), q12 (право отказывать в обслуживании)
    culture_val = (
        scores.get(10, 0)
        + scores.get(13, 0)
        + scores.get(18, 0)
        + scores.get(22, 0)
        - (scores.get(11, 0) + scores.get(12, 0))
    )

    # Геоизм: q6 (ресурсы всем), q7 (плата за землю) — за геоизм
    # q5 (первозахват земли), q8 (налоги несправедливы) — против геоизма
    geo_score = scores.get(6, 0) + scores.get(7, 0) - scores.get(5, 0) - scores.get(8, 0)

    # Общий либертарианский показатель: q4 (свободная торговля), q14 (корпорации от гос-ва), q16 (монополии от лицензий)
    # q17 (наёмный труд — добровольный обмен)
    liberty_score = scores.get(4, 0) + scores.get(14, 0) + scores.get(16, 0) + scores.get(17, 0)

    # --- 2. Нелибертарианский блок: ТОЛЬКО при экстремальном этатизме ---
    # Порог >= 5 означает: нужно минимум два «Полностью согласен» и один «Скорее согласен»
    # на вопросы 18-20, что указывает на явное и сильное про-государственное мировоззрение
    if statist_score >= 5:
        res = {"geo": False, "paleo": False, "bleeding-heart": False}
        # Фашизм: только при максимальном коллективизме (q20 == +2)
        if scores.get(20, 0) >= 2:
            res.update(
                {
                    "display_name": QUIZ_DATA.ideologies["fascism"].full_name,
                    "ideology_key": "fascism",
                    "result_key": "fascism",
                }
            )
        # Коммунизм: максимальный дирижизм (q19 == +2)
        elif scores.get(19, 0) >= 2:
            res.update(
                {
                    "display_name": QUIZ_DATA.ideologies["communism"].full_name,
                    "ideology_key": "communism",
                    "result_key": "communism",
                }
            )
        # Социализм: сильный дирижизм (q19 >= +1) + сильный этатизм (q18 >= +2)
        elif scores.get(19, 0) >= 1 and scores.get(18, 0) >= 2:
            res.update(
                {
                    "display_name": QUIZ_DATA.ideologies["socialism"].full_name,
                    "ideology_key": "socialism",
                    "result_key": "socialism",
                }
            )
        # Социал-демократия: сильный этатизм (q18 >= +2)
        elif scores.get(18, 0) >= 2:
            res.update(
                {
                    "display_name": QUIZ_DATA.ideologies["social_democracy"].full_name,
                    "ideology_key": "social_democracy",
                    "result_key": "social_democracy",
                }
            )
        else:
            # По умолчанию для экстремального этатизма
            res.update(
                {
                    "display_name": QUIZ_DATA.ideologies["centrism"].full_name,
                    "ideology_key": "centrism",
                    "result_key": "centrism",
                }
            )
        return res

    # --- 3. Центризм ---
    # Если совокупная «идеологическая энергия» слишком мала, человек — центрист
    total_ideological_drive = abs(state_axis) + abs(culture_val) + abs(statist_score) + abs(liberty_score)
    if total_ideological_drive <= 4:
        return {
            "display_name": QUIZ_DATA.ideologies["centrism"].full_name,
            "ideology_key": "centrism",
            "result_key": "centrism",
            "geo": False,
            "paleo": False,
            "bleeding-heart": False,
        }

    # --- 4. Классификация внутри либертарианского спектра ---

    # Базовая идеология по оси государства
    if state_axis > 3:
        base_key = "classical_liberalism"
    elif state_axis > 0:
        base_key = "minarchism"
    else:
        base_key = "ancap"

    # Paleo и BHL — антонимы, взаимоисключающие
    is_paleo = culture_val <= -2
    is_bh = not is_paleo and culture_val >= 2

    # Анкап — радикальная форма без государства. Geo несовместим с анкапом.
    if base_key == "ancap":
        is_geo = False
        is_bh = False
    elif base_key == "classical_liberalism":
        # Классический либерализм — без модификаторов (нет соответствующих изображений)
        is_geo = False
        is_paleo = False
        is_bh = False
    else:
        is_geo = geo_score >= 3

    base_name = QUIZ_DATA.ideologies[base_key].base_name or QUIZ_DATA.ideologies[base_key].full_name

    # Сборка result_key из модификаторов
    key_parts = []
    if is_geo:
        key_parts.append("geo")
    if is_paleo:
        key_parts.append("paleo")
    if is_bh:
        key_parts.append("bleeding-heart")
    key_parts.append(base_key)
    result_key = "-".join(key_parts)

    # Сборка итогового названия из префиксов
    name_parts = []
    if is_geo and "geo" in QUIZ_DATA.ideologies:
        name_parts.append(QUIZ_DATA.ideologies["geo"].prefix)
    if is_paleo and "paleo" in QUIZ_DATA.ideologies:
        name_parts.append(QUIZ_DATA.ideologies["paleo"].prefix)
    if is_bh and "bleeding-heart" in QUIZ_DATA.ideologies:
        name_parts.append(QUIZ_DATA.ideologies["bleeding-heart"].prefix)

    name_parts.append(base_name)
    display_name = "-".join(name_parts)

    return {
        "display_name": display_name,
        "ideology_key": base_key,
        "result_key": result_key,
        "geo": is_geo,
        "paleo": is_paleo,
        "bleeding-heart": is_bh,
    }
