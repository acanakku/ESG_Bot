from aiogram.fsm.state import State, StatesGroup


class IdeaForm(StatesGroup):
    title = State()
    category = State()
    problem = State()
    solution = State()
    impact = State()
    resources = State()
    review = State()


class SearchForm(StatesGroup):
    query = State()


class ModerationForm(StatesGroup):
    reject_comment = State()
