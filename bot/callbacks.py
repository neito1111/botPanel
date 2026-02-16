from aiogram.filters.callback_data import CallbackData


class AccessRequestCb(CallbackData, prefix="access"):
    action: str  # approve/reject
    tg_id: int


class FormReviewCb(CallbackData, prefix="form"):
    action: str  # approve/reject
    form_id: int


class FormEditCb(CallbackData, prefix="edit"):
    action: str  # open/send
    form_id: int


class TeamLeadMenuCb(CallbackData, prefix="tlm"):
    action: str  # banks/live/home


class BankCb(CallbackData, prefix="bank"):
    action: str  # open/edit/create
    bank_id: int | None = None


class BankEditCb(CallbackData, prefix="bankedit"):
    action: str  # instructions/required/templates/delete_templates/back
    bank_id: int


