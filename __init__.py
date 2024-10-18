"""
Uses the Anki API
Anki is not exactly a text editor.
Nevertheless, it is pretty cool to track the time spent reviewing different decks.

Seeing the front- and backside of card is 'Editing a file': --is-write=False
while pressing on one of the buttons is considered 'Saving a file': --is-write=True

The different 'projects' are represented by different available decks,
while each card represents a different 'file'
"""
from aqt import mw, gui_hooks
from aqt.qt import *
from aqt.utils import showInfo

ankiConfig = mw.addonManager.getConfig(__name__)
"""Used to get access to the WakaTime API Key"""


class ApiDialogWidget(QInputDialog):
    """
    Used within the ApiKey class to get the API key from the user if none has been found in the config
    Must be a class because it is displaying a new QtWidget
    :return: API key, empty if there is an error
    """

    def __init__(self, parent=None):
        super().__init__(parent)

    def prompt(self) -> str:
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

        return ""


# Refer to Anki's repo for the full of list of available hooks
# https://github.com/ankitects/anki/blob/main/qt/tools/genhooks_gui.py
# 'File' changed
gui_hooks.reviewer_did_show_answer.append(lambda card: ApiDialogWidget().prompt())


# gui_hooks.reviewer_did_show_question.append()

# 'File' edited
# gui_hooks.reviewer_did_answer_card.append()


# --- Test Function --- #
# We're going to add a menu item below. First we want to create a function to
# be called when the menu item is activated.

def testFunction() -> None:
    # get the number of cards in the current collection, which is stored in
    # the main window
    cardCount = mw.col.cardCount()
    # show a message box
    showInfo("Card count: %d" % cardCount)


# create a new menu item, "test"
action = QAction("test", mw)
# set it to call testFunction when it's clicked
qconnect(action.triggered, testFunction)
# and add it to the tools menu
mw.form.menuTools.addAction(action)
