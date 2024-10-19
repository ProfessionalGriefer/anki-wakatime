"""
Uses Anki's API
"""
from aqt import mw, gui_hooks
from aqt.qt import *
from aqt.utils import showInfo

from .wakaTime import handle_activity

ankiConfig = mw.addonManager.getConfig(__name__)


class ApiDialogWidget(QInputDialog):
    """
    Used within the ApiKey class to get the API key from the user if none has been found in the config
    Must be a class because it is displaying a new QtWidget
    :return: API key
    """

    def __init__(self, parent=None):
        super().__init__(parent)

    def prompt(self) -> str | None:
        promptText = "Enter the WakaTime API Key"
        wakaKeyTemplate = "waka_XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"
        key, ok = QInputDialog.getText(self, promptText, wakaKeyTemplate)

        if ok and key:
            # Save the text to addon's config
            ankiConfig["wakaTime-api-key"] = key
            mw.addonManager.writeConfig(__name__, ankiConfig)

            # Optionally show a message confirming it was saved
            showInfo("Your new API key has been saved")

            return key

        return None


# Showing question and answer like 'editing a file'
gui_hooks.reviewer_did_show_question.append(lambda card: handle_activity(card, False))
gui_hooks.reviewer_did_show_answer.append(lambda card: handle_activity(card, False))

# Answering the card like 'writing to a file'
gui_hooks.reviewer_did_answer_card.append(lambda card: handle_activity(card, True))
