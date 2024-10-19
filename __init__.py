"""
Uses Anki's API
"""
from aqt import gui_hooks

from .wakaTime import handle_activity

# Showing question and answer like 'editing a file'
gui_hooks.reviewer_did_show_question.append(lambda card: handle_activity(card, False))
gui_hooks.reviewer_did_show_answer.append(lambda card: handle_activity(card, False))

# Answering the card like 'writing to a file'
gui_hooks.reviewer_did_answer_card.append(lambda card: handle_activity(card, True))
