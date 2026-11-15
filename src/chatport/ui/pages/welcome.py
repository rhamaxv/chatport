"""Step 1: what will happen, what stays safe, what is needed."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy

from chatport.i18n import t
from chatport.ui.pages.base import Context, Page
from chatport.ui.widgets.cards import Card, IconLabel


class InfoCard(Card):
    def __init__(self, icon_name: str, title_key: str, body_key: str):
        super().__init__(padding=22, spacing=10)
        self.title_key, self.body_key = title_key, body_key
        self.icon = IconLabel(icon_name, 26, "accent")
        self.heading = QLabel()
        self.heading.setProperty("role", "heading")
        self.heading.setWordWrap(True)
        self.text = QLabel()
        self.text.setWordWrap(True)
        self.text.setProperty("role", "muted")
        self.text.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.body.addWidget(self.icon)
        self.body.addSpacing(4)
        self.body.addWidget(self.heading)
        self.body.addWidget(self.text, 1)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    def retranslate(self) -> None:
        self.heading.setText(t(self.title_key))
        self.text.setText(t(self.body_key))
        self.icon.refresh()


class WelcomePage(Page):
    step = "welcome"
    title_key = "welcome.title"
    subtitle_key = "welcome.subtitle"

    def __init__(self, ctx: Context):
        super().__init__(ctx)
        row = QHBoxLayout()
        row.setSpacing(16)
        for card in (
            InfoCard("arrow-right", "welcome.what.title", "welcome.what.body"),
            InfoCard("shield", "welcome.safe.title", "welcome.safe.body"),
            InfoCard("phone-android", "welcome.need.title", "welcome.need.body"),
        ):
            row.addWidget(card, 1)
            self.track(card)
        self.body.addLayout(row)
        self.privacy = QLabel()
        self.privacy.setProperty("role", "muted")
        self.privacy.setWordWrap(True)
        self.body.addWidget(self.privacy)
        self.retranslate()

    def retranslate(self) -> None:
        super().retranslate()
        self.privacy.setText(t("welcome.privacy"))

    def continue_label_key(self) -> str:
        return "welcome.continue"

    def shows_back(self) -> bool:
        return False
