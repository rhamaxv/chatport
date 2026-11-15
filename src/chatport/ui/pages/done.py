"""Step 9: verify in WhatsApp, undo if something is wrong, delete the private copies, finish."""
from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout

from chatport.i18n import t
from chatport.ui import format as fmt
from chatport.ui.pages.base import Context, Page
from chatport.ui.widgets.cards import Card, Chip, Tile
from chatport.ui.widgets.checklist import Checklist
from chatport.ui.widgets.progress_card import ProgressCard

VERIFY = ("done.verify.chats", "done.verify.groups", "done.verify.media", "done.verify.other")
TILES = (("messages", "copy.summary.messages"), ("chats", "copy.summary.chats"),
         ("media", "copy.summary.media"), ("stickers", "done.stats.stickers"))


def summary_numbers(build: dict | None, copy: dict | None) -> dict[str, int | None]:
    """What ended up on the iPhone, from the build result, falling back to what was copied from Android."""
    build = build or {}
    copy = copy or {}

    def pick(*candidates):
        for value in candidates:
            if value is not None:
                return int(value)
        return None

    chats = None
    if build.get("chats_created") is not None or build.get("chats_merged") is not None:
        chats = int(build.get("chats_created") or 0) + int(build.get("chats_merged") or 0)
    return {
        "messages": pick(build.get("messages_added"), copy.get("messages")),
        "chats": pick(chats, copy.get("chats")),
        "media": pick(build.get("media_found"), copy.get("media")),
        "stickers": pick(build.get("stickers_added")),
    }


class ActionCard(Card):
    def __init__(self, icon_name: str, hue: str, title_key: str, body_key: str, button_key: str, variant: str):
        super().__init__(padding=20, spacing=6)
        self.keys = (title_key, body_key, button_key)
        row = QHBoxLayout()
        row.setSpacing(16)
        self.icon = Chip(icon_name, 40, hue)
        col = QVBoxLayout()
        col.setSpacing(4)
        self.heading = QLabel()
        self.heading.setProperty("role", "heading")
        self.text = QLabel()
        self.text.setWordWrap(True)
        self.text.setProperty("role", "muted")
        col.addWidget(self.heading)
        col.addWidget(self.text)
        self.button = QPushButton()
        self.button.setProperty("variant", variant)
        row.addWidget(self.icon, 0)
        row.addLayout(col, 1)
        row.addWidget(self.button, 0)
        self.body.addLayout(row)

    def retranslate(self) -> None:
        self.heading.setText(t(self.keys[0]))
        self.text.setText(t(self.keys[1]))
        self.button.setText(t(self.keys[2]))
        self.icon.refresh()


class CleanupDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle(t("done.cleanup.confirm.title"))
        self.setMinimumWidth(440)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 24)
        layout.setSpacing(14)
        title = QLabel(t("done.cleanup.confirm.title"))
        title.setProperty("role", "heading")
        body = QLabel(t("done.cleanup.confirm.body"))
        body.setWordWrap(True)
        body.setProperty("role", "muted")
        self.also = QCheckBox(t("done.cleanup.also_backup"))
        layout.addWidget(title)
        layout.addWidget(body)
        layout.addWidget(self.also)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = QPushButton(t("common.cancel"))
        cancel.setProperty("variant", "quiet")
        cancel.clicked.connect(self.reject)
        ok = QPushButton(t("done.cleanup.confirm.button"))
        ok.setProperty("variant", "danger")
        ok.clicked.connect(self.accept)
        buttons.addWidget(cancel)
        buttons.addWidget(ok)
        layout.addLayout(buttons)


class DonePage(Page):
    step = "done"
    jobs = ("undo",)
    title_key = "done.title"
    subtitle_key = "done.subtitle"
    hero = "check"
    hero_card = True

    def __init__(self, ctx: Context):
        super().__init__(ctx)
        self.tiles_row = QHBoxLayout()
        self.tiles_row.setSpacing(12)
        self.tiles: dict[str, Tile] = {}
        for key, caption in TILES:
            tile = Tile(caption)
            self.tiles[key] = tile
            self.tiles_row.addWidget(tile, 1)
        self.head.extra.addLayout(self.tiles_row)
        self.verify_heading = QLabel()
        self.verify_heading.setProperty("role", "heading")
        self.body.addWidget(self.verify_heading)
        self.checklist = Checklist()
        for key in VERIFY:
            self.checklist.add(key, key)
        self.body.addWidget(self.checklist)
        self.track(self.checklist)
        self.progress = ProgressCard(cancellable=False)
        self.progress.setVisible(False)
        self.body.addWidget(self.progress)
        self.track(self.progress)
        self.undo_card = ActionCard("undo", "amber", "done.undo.title", "done.undo.body", "done.undo", "")
        self.undo_card.button.clicked.connect(self.undo)
        self.cleanup_card = ActionCard("trash", "rose", "done.cleanup.title", "done.cleanup.body", "done.cleanup", "danger")
        self.cleanup_card.button.clicked.connect(self.cleanup)
        self.body.addWidget(self.undo_card)
        self.body.addWidget(self.cleanup_card)
        self.track(self.undo_card)
        self.track(self.cleanup_card)
        self._busy = False
        self.retranslate()

    def retranslate(self) -> None:
        super().retranslate()
        self.verify_heading.setText(t("done.verify.title"))
        for tile in self.tiles.values():
            tile.retranslate()

    def on_enter(self) -> None:
        self.refresh_tiles()

    def refresh_tiles(self) -> None:
        numbers = summary_numbers(self.ctx.state.get("build"), self.ctx.state.get("copy"))
        for key, tile in self.tiles.items():
            value = numbers.get(key)
            tile.setVisible(value is not None)
            if value is not None:
                tile.set_value(fmt.number(value))

    def shows_back(self) -> bool:
        return False

    def continue_label_key(self) -> str:
        return "common.finish"

    def can_continue(self) -> bool:
        return not self._busy

    def on_continue(self) -> None:
        window = self.window()
        if window is not None:
            window.close()

    def undo(self) -> None:
        answer = QMessageBox.question(self, t("done.undo.confirm.title"), t("done.undo.confirm.body"),
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.start_job()

    def start_job(self) -> None:
        self.clear_error()
        self._set_busy(True)
        self.progress.reset()
        self.progress.setVisible(True)
        self.ctx.runner.undo(self.ctx.password)

    def on_event(self, event) -> None:
        if event.kind == "progress":
            self.progress.update_from(event)
        elif event.kind == "done":
            self.progress.setVisible(False)
            self._set_busy(False)
            self.undo_card.button.setEnabled(False)
            self.say(t("done.undo.done"), 10)
        elif event.kind == "error":
            self.progress.setVisible(False)
            self._set_busy(False)
            super().on_event(event)

    def cleanup(self) -> None:
        if self.ctx.cleanup is None:
            return
        dialog = CleanupDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        also_backup = dialog.also.isChecked()
        try:
            self.ctx.cleanup(also_backup)
        except Exception:
            self.show_error({"code": "unknown", "detail": t("done.cleanup.failed")})
            return
        self.cleanup_card.button.setEnabled(False)
        self.say(t("done.cleanup.done_all" if also_backup else "done.cleanup.done"), 10)

    def _set_busy(self, on: bool) -> None:
        self._busy = on
        self.undo_card.button.setEnabled(not on)
        self.cleanup_card.button.setEnabled(not on)
        self.busy_changed.emit(on)
        self.continue_changed.emit(self.can_continue())
