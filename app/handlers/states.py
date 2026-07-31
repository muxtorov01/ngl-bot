from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class AnonymousSendStates(StatesGroup):
    waiting_message = State()  # guest is composing an anonymous message


class ReplyStates(StatesGroup):
    waiting_reply = State()  # receiver is composing a reply to a specific message


class ReportStates(StatesGroup):
    waiting_reason = State()


class AdminBroadcastStates(StatesGroup):
    waiting_content = State()
    waiting_confirm = State()


class AdminPriceStates(StatesGroup):
    waiting_price = State()


class AdminManageStates(StatesGroup):
    waiting_admin_id = State()
