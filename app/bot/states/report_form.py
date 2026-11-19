"""
Finite State Machine states for the graffiti report creation flow.

States flow:
  waiting_for_photo
      ↓
  waiting_for_location
      ↓
  waiting_for_description
      ↓
  confirm_submission  (shows preview, waits for Confirm / Cancel)
"""

from aiogram.fsm.state import State, StatesGroup


class ReportForm(StatesGroup):
    """FSM states for multi-step graffiti report submission."""

    waiting_for_photo = State()
    waiting_for_location = State()
    waiting_for_description = State()
    confirm_submission = State()
