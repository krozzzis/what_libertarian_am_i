import json5
from pydantic import BaseModel, model_validator
from typing import Dict, List, Optional
from pathlib import Path


class Answer(BaseModel):
    id: int
    text: str

    @classmethod
    def create(cls, id: int, text: str) -> "Answer":
        return cls(id=id, text=text)


class Question(BaseModel):
    id: int
    text: str
    default_answers: Optional[bool] = None
    answers: Optional[List[int]] = None
    _resolved_answers: Optional[List[Answer]] = None

    @classmethod
    def create(cls, id: int, text: str) -> "Question":
        return cls(id=id, text=text)

    def get_answers(self, default_answer_ids: List[int], all_answers: List[Answer]) -> List[Answer]:
        if self._resolved_answers is not None:
            return self._resolved_answers

        answer_ids = self.answers if self.answers is not None else default_answer_ids
        self._resolved_answers = [a for a in all_answers if a.id in answer_ids]
        return self._resolved_answers


class IdeologyDef(BaseModel):
    full_name: str
    prefix: Optional[str] = None
    base_name: Optional[str] = None
    result_message: Optional[str] = None
    idealogy_person: Optional[str] = None


class QuizData(BaseModel):
    questions: List[Question]
    default_answers: Optional[List[int]] = None
    answers: List[Answer] = []
    ideologies: Dict[str, IdeologyDef] = {}
    ideology_images: Dict[str, str] = {}

    @classmethod
    def create(cls, questions: List[Question]) -> "QuizData":
        return cls(questions=questions)

    def get_question_answers(self, question: Question) -> List[Answer]:
        default_ids = self.default_answers or []
        return question.get_answers(default_ids, self.answers)


QUIZ_DATA: QuizData = QuizData.create([
    Question.create(1, "Nothing"),
])


def parse_quiz(text: str) -> QuizData:
    data = json5.loads(text)

    return QuizData.model_validate(data)


def open_quiz(file_path: str | Path) -> QuizData:
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if not path.is_file():
        raise ValueError(f"Path is pointing to directory not to file: {path}")

    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    data = parse_quiz(content)

    return data


def load_quiz(file_path: str | Path):
    global QUIZ_DATA
    QUIZ_DATA = open_quiz(file_path)


def get_ideology_data(user_answers):
    # Конвертация: '1'(+2) ... '5'(-2)
    scores = {int(k): {1: 2, 2: 1, 3: 0, 4: -1, 5: -2}[int(v)] for k, v in user_answers.items()}

    # --- 1. Расчет всех осей и показателей ---
    # Этатизм: вопросы 18, 19, 20
    statist_score = scores.get(18, 0) + scores.get(19, 0) + scores.get(20, 0)
    # Ось государства (чем выше, тем больше поддержка государства)
    state_axis = scores.get(1, 0) + scores.get(2, 0) - scores.get(3, 0)
    # Культурная ось (положительный - прогрессивизм, отрицательный - традиционализм)
    # Вопросы 10 (борьба с расизмом), 13 (истинная свобода) — прогрессивизм
    # Вопросы 11 (традиционные институты), 12 (частные владельцы отказывают) — традиционализм
    culture_val = (scores.get(10, 0) + scores.get(13, 0)) - (scores.get(11, 0) + scores.get(12, 0))
    # Показатель геоизма
    geo_score = scores.get(6, 0) + scores.get(7, 0)

    # --- 2. Проверка на ярко выраженные этатистские идеологии ---
    if statist_score >= 3:
        # Эти идеологии по определению теста исключают либертарианство
        res = {"geo": False, "paleo": False, "bleeding-heart": False}
        if scores.get(20, 0) >= 1 and scores.get(4, 0) >= 1:
            res.update({"display_name": QUIZ_DATA.ideologies["fascism"].full_name, "ideology_key": "fascism", "result_key": "fascism"})
        elif scores.get(19, 0) >= 2:
            res.update({"display_name": QUIZ_DATA.ideologies["communism"].full_name, "ideology_key": "communism", "result_key": "communism"})
        elif scores.get(19, 0) >= 1:
            res.update({"display_name": QUIZ_DATA.ideologies["socialism"].full_name, "ideology_key": "socialism", "result_key": "socialism"})
        elif scores.get(18, 0) >= 1:
            res.update({"display_name": QUIZ_DATA.ideologies["social_democracy"].full_name, "ideology_key": "social_democracy", "result_key": "social_democracy"})
        else:
            # Итог по умолчанию для высокого показателя этатизма
            res.update({"display_name": QUIZ_DATA.ideologies["centrism"].full_name, "ideology_key": "centrism", "result_key": "centrism"})
        return res

    # --- 3. Проверка на центризм ---
    total_ideological_drive = abs(state_axis) + abs(culture_val) + abs(statist_score)
    if total_ideological_drive <= 3:
        return {
            "display_name": QUIZ_DATA.ideologies["centrism"].full_name,
            "ideology_key": "centrism",
            "result_key": "centrism",
            "geo": False, "paleo": False, "bleeding-heart": False
        }

    # --- 4. Классификация внутри либертарианства ---
    is_agora = False  # Агоризм убран

    # Определение базовой идеологии
    if state_axis > 3:
        base_key = "classical_liberalism"
    elif state_axis > 0:
        base_key = "minarchism"
    else:
        base_key = "ancap"

    # Paleo и BHL — антонимы, взаимоисключающие
    is_paleo = culture_val <= -2
    is_bh = not is_paleo and culture_val >= 2

    # Ancap — радикальная форма без государства.
    # Geo несовместим с анкапом.
    if base_key == "ancap":
        is_geo = False
        is_bh = False
    elif base_key == "classical_liberalism":
        is_geo = False
        is_paleo = False
        is_bh = False
    else:
        is_geo = geo_score >= 2

    base_name = QUIZ_DATA.ideologies[base_key].base_name or QUIZ_DATA.ideologies[base_key].full_name

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