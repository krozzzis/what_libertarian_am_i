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


class QuizData(BaseModel):
    questions: List[Question]
    default_answers: Optional[List[int]] = None
    answers: List[Answer] = []

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


from enum import Enum
from dataclasses import dataclass

class Ideology(Enum):
    COMMUNISM = "Коммунизм"
    SOCIALISM = "Социализм"
    SOCIAL_DEMOCRACY = "Социал-демократия"
    LIBERALISM = "Либерализм"
    CONSERVATISM = "Консерватизм"
    FASCISM = "Фашизм"
    CLASSICAL_LIBERALISM = "Классический либерализм"
    MINARCHISM = "Минархизм"
    ANCAP = "Анкап"
    STATISM = "Этатизм"
    BLEEDING_HEART = "Сострадательное либертарианство"
    CENTRISM = "Центризм"


IDEOLOGY_DESCRIPTIONS = {
    "paleo": "<b>Палеолибертарианство</b>: Сочетание либертарианской экономики (свободный рынок, минимальное государство) с консервативными культурными и социальными ценностями.",
    "bleeding-heart": "<b>Сострадательное либертарианство</b>: Направление, утверждающее, что свободный рынок и гражданские свободы являются наилучшими инструментами для помощи уязвимым слоям общества, делая акцент на эмпатии и добровольной благотворительности.",
    "geo": "<b>Геолибертарианство</b>: Идеология, считающая землю общим достоянием. Выступает за налогообложение стоимости земли вместо налогов на труд и капитал, сочетая это с либертарианскими принципами.",
    "agora": "<b>Агоризм</b>: Революционная форма рыночного анархизма, которая стремится к уничтожению государства через создание теневой экономики ('контрэкономики'), неподконтрольной властям.",
    "ancap": "<b>Анархо-капитализм</b>: Радикальная идеология, выступающая за полную ликвидацию государства. Все функции, включая безопасность и суд, должны выполняться частными компаниями на свободном рынке.",
    "minarchism": "<b>Минархизм</b>: Поддерживает идею 'государства — ночного сторожа', функции которого ограничены защитой граждан (армия, полиция, суды). Все остальное должно быть в частных руках.",
    "classical_liberalism": "<b>Классический либерализм</b>: Идеология, основанная на принципах индивидуальной свободы, ограниченного правительства, верховенства закона и свободного рынка с минимальным вмешательством государства.",
    "fascism": "<b>Фашизм</b>: Идеология, характеризующаяся диктаторской властью, крайним национализмом, милитаризмом и подавлением личности во имя интересов государства и нации.",
    "communism": "<b>Коммунизм</b>: Ультралевая идеология, целью которой является построение бесклассового общества с общественной собственностью на средства производства, часто через однопартийное правление и плановую экономику.",
    "socialism": "<b>Социализм</b>: Идеология, выступающая за общественную или государственную собственность на средства производства для достижения социального равенства и справедливого распределения благ.",
    "social_democracy": "<b>Социал-демократия</b>: Идеология, сочетающая капиталистическую экономику с сильными социальными программами (образование, здравоохранение) и государственным регулированием для сокращения неравенства.",
    "statism": "<b>Этатизм</b>: Убеждение в том, что государство должно иметь значительный централизованный контроль над экономическими и социальными вопросами общества. Поддерживает активное государственное вмешательство.",
    "centrism": "<b>Центризм</b>: Политическая позиция, которая стремится к балансу между различными идеологиями, избегая крайних взглядов. Центристы часто поддерживают смешанную экономику и прагматичные решения, основанные на компромиссе.",
}

def get_ideology_data(user_answers):
    # Конвертация: '1'(+2) ... '5'(-2)
    scores = {int(k): {1: 2, 2: 1, 3: 0, 4: -1, 5: -2}[int(v)] for k, v in user_answers.items()}

    # --- 1. Расчет всех осей и показателей ---
    statist_score = scores.get(21, 0) + scores.get(22, 0) + scores.get(23, 0)
    # Ось государства (чем выше, тем больше поддержка государства)
    # Вопрос 3 инвертирован
    state_axis = scores.get(1, 0) + scores.get(2, 0) - scores.get(3, 0)
    # Культурная ось (положительный - прогрессивизм, отрицательный - традиционализм)
    culture_val = (scores.get(13, 0) + scores.get(16, 0)) - (scores.get(14, 0) + scores.get(15, 0))
    # Показатель геоизма
    geo_score = scores.get(6, 0) + scores.get(7, 0)
    # Показатель агоризма
    agora_score = scores.get(10, 0) + scores.get(11, 0)

    # --- 2. Проверка на ярко выраженные этатистские идеологии ---
    if statist_score >= 3:
        # Эти идеологии по определению теста исключают либертарианство
        res = {"geo": False, "paleo": False, "bleeding-heart": False, "agora": False}
        if scores.get(23, 0) >= 1 and scores.get(4, 0) >= 1:
            res.update({"display_name": "Фашизм", "ideology": Ideology.FASCISM, "ideology_key": "fascism"})
        elif scores.get(22, 0) >= 2:
            res.update({"display_name": "Коммунизм", "ideology": Ideology.COMMUNISM, "ideology_key": "communism"})
        elif scores.get(22, 0) >= 1:
            res.update({"display_name": "Социализм", "ideology": Ideology.SOCIALISM, "ideology_key": "socialism"})
        elif scores.get(21, 0) >= 1:
            res.update({"display_name": "Социал-демократия", "ideology": Ideology.SOCIAL_DEMOCRACY, "ideology_key": "social_democracy"})
        else:
            # Итог по умолчанию для высокого показателя этатизма
            res.update({"display_name": "Этатизм", "ideology": Ideology.STATISM, "ideology_key": "statism"})
        return res

    # --- 3. Проверка на центризм ---
    # Сумма абсолютных значений по ключевым осям для оценки общей радикальности взглядов
    total_ideological_drive = abs(state_axis) + abs(culture_val) + abs(statist_score)
    if total_ideological_drive <= 3:
        return {
            "display_name": "Центризм",
            "ideology": Ideology.CENTRISM,
            "ideology_key": "centrism",
            "geo": False, "paleo": False, "bleeding-heart": False, "agora": False
        }

    # --- 4. Классификация внутри либертарианства ---
    is_paleo = culture_val <= -2
    is_bh = culture_val >= 2
    is_geo = geo_score >= 2
    is_agora = agora_score >= 2

    # Определение базовой идеологии
    if state_axis > 3:
        base_ideology = Ideology.CLASSICAL_LIBERALISM
        base_key = "classical_liberalism"
        base_name = base_ideology.value
    elif state_axis > 0:
        base_ideology = Ideology.MINARCHISM
        base_key = "minarchism"
        base_name = base_ideology.value
    else:
        base_ideology = Ideology.ANCAP
        base_key = "ancap"
        base_name = base_ideology.value

    # Сборка итогового названия из префиксов
    name_parts = []
    if is_paleo: name_parts.append("Палео")
    if is_bh: name_parts.append("Сострадательный")
    if is_geo: name_parts.append("Гео")
    # Агоризм здесь не добавляется в название

    name_parts.append(base_name)
    display_name = "-".join(name_parts)

    return {
        "display_name": display_name,
        "ideology": base_ideology,
        "ideology_key": base_key,
        "geo": is_geo,
        "paleo": is_paleo,
        "bleeding-heart": is_bh,
        "agora": is_agora, # Флаг агоризма сохраняется
    }
