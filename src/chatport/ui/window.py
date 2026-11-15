"""The one window: step rail on the left, header, the current page, and the Back / Continue footer."""
from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel, QMainWindow, QPushButton, QScrollArea,
                               QStackedWidget, QVBoxLayout, QWidget)

from chatport import i18n
from chatport.core.steps import STEPS

# A phone went away while a job ran: the Connect page is the place to sort that out.
DISCONNECT_CODES = frozenset({"no_android", "android_unauthorized", "android_offline", "no_adb",
                              "no_iphone", "iphone_untrusted", "iphone_disconnected"})
from chatport.i18n import t
from chatport.ui import icons, theme
from chatport.ui.pages import PAGES
from chatport.ui.pages.base import Context, Page
from chatport.ui.widgets.step_rail import StepRail

log = logging.getLogger("chatport.ui")


class MainWindow(QMainWindow):
    def __init__(self, runner, state, checks_fn: Callable[[], dict] | None, language: str = "en",
                 ready_checks_fn: Callable[[], dict] | None = None, cleanup: Callable[[bool], None] | None = None,
                 log_path: Path | None = None):
        super().__init__()
        i18n.set_language(language)
        self.runner = runner
        self.state = state
        self.ctx = Context(runner=runner, state=state, checks_fn=checks_fn, ready_checks_fn=ready_checks_fn,
                           cleanup=cleanup, log_path=log_path)
        self.setObjectName("root")
        self.resize(1080, 720)
        self.setMinimumSize(960, 640)
        self._build()
        self.pages: dict[str, Page] = {}
        for cls in PAGES:
            page = cls(self.ctx)
            self.pages[page.step] = page
            page.continue_changed.connect(self._refresh_footer)
            page.busy_changed.connect(self._refresh_footer)
            page.advance.connect(self._advance)
            page.request_go.connect(self._go_back_to)
            self.stack.addWidget(self._scrollable(page))
        runner.event.connect(self._on_event)
        runner.busy_changed.connect(self._refresh_footer)
        self.current = STEPS[0]
        self.retranslate()
        self.go(state.current())

    # ----- construction -------------------------------------------------------------------------

    def _build(self) -> None:
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self.rail = StepRail()
        outer.addWidget(self.rail)
        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(0)
        outer.addLayout(right, 1)

        header = QWidget()
        header.setObjectName("header")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(32, 18, 32, 0)
        self.step_label = QLabel()
        self.step_label.setProperty("role", "eyebrow")
        hl.addWidget(self.step_label, 0, Qt.AlignmentFlag.AlignVCenter)
        hl.addStretch(1)
        # Language switch and theme toggle share one pill group.
        self.lang_frame = QFrame()
        self.lang_frame.setObjectName("controls")
        ll = QHBoxLayout(self.lang_frame)
        ll.setContentsMargins(3, 3, 3, 3)
        ll.setSpacing(2)
        self.lang_buttons: dict[str, QPushButton] = {}
        for code in i18n.LANGUAGES:
            button = QPushButton(code.upper())
            button.setProperty("variant", "seg")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _c=False, code=code: self.set_language(code))
            ll.addWidget(button)
            self.lang_buttons[code] = button
        divider = QFrame()
        divider.setObjectName("divider")
        divider.setFixedWidth(1)
        ll.addSpacing(3)
        ll.addWidget(divider)
        ll.addSpacing(3)
        self.theme_button = QPushButton()
        self.theme_button.setProperty("variant", "icon")
        self.theme_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_button.clicked.connect(self.toggle_theme)
        ll.addWidget(self.theme_button)
        hl.addWidget(self.lang_frame, 0, Qt.AlignmentFlag.AlignVCenter)
        right.addWidget(header)

        self.stack = QStackedWidget()
        right.addWidget(self.stack, 1)

        footer = QWidget()
        footer.setObjectName("footer")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(32, 14, 32, 18)
        self.back_button = QPushButton()
        self.back_button.setProperty("variant", "quiet")
        self.back_button.clicked.connect(self.back)
        self.continue_button = QPushButton()
        self.continue_button.setProperty("variant", "primary")
        self.continue_button.setDefault(True)
        self.continue_button.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.continue_button.clicked.connect(self.proceed)
        fl.addWidget(self.back_button)
        fl.addStretch(1)
        fl.addWidget(self.continue_button)
        right.addWidget(footer)

    @staticmethod
    def _scrollable(page: QWidget) -> QScrollArea:
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setFrameShape(QFrame.Shape.NoFrame)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        area.setWidget(page)
        return area

    # ----- navigation ---------------------------------------------------------------------------

    def page(self) -> Page:
        return self.pages[self.current]

    def go(self, step: str) -> None:
        if step not in self.pages:
            step = STEPS[0]
        old = self.pages.get(self.current)
        if old is not None and old is not self.pages[step]:
            old.on_leave()
        self.current = step
        self.stack.setCurrentIndex(STEPS.index(step))
        self.stack.currentWidget().verticalScrollBar().setValue(0)
        self.pages[step].on_enter()
        self._refresh_rail()
        self._refresh_footer()
        log.info("page %s", step)

    def back(self) -> None:
        index = STEPS.index(self.current)
        if index == 0:
            return
        self._go_back_to(STEPS[index - 1])

    def _go_back_to(self, step: str) -> None:
        if step not in STEPS:
            return
        self.state.reset_from(step)
        self.go(step)

    def proceed(self) -> None:
        page = self.page()
        if page.can_continue() and not self.runner.busy():
            page.on_continue()

    def _advance(self) -> None:
        page = self.sender()
        if not isinstance(page, Page) or page is not self.page():
            return
        self.state.mark(page.step, **page.stats())
        index = STEPS.index(page.step)
        if index + 1 < len(STEPS):
            # After a detour back to Connect, resume where the user left off rather than redoing steps.
            resume = self.state.current()
            resume_index = STEPS.index(resume) if resume in STEPS else index + 1
            self.go(STEPS[max(index + 1, resume_index)])
        else:
            self._refresh_rail()

    def _on_event(self, event) -> None:
        page = self.page()
        if page.jobs and getattr(event, "job", None) not in page.jobs:
            log.debug("event for %s ignored on page %s", getattr(event, "job", "?"), page.step)
            return
        page.on_event(event)
        code = event.data.get("code") if event.kind == "error" else None
        if code in DISCONNECT_CODES and self.current != "connect":
            log.info("phone disconnected during %s, returning to connect", page.step)
            self.go("connect")
            self.pages["connect"].show_notice()

    # ----- appearance ---------------------------------------------------------------------------

    def _refresh_rail(self) -> None:
        done = {step for step in STEPS if self.state.done(step)}
        self.rail.set_progress(self.current, done)
        self.step_label.setText(t("header.step", n=STEPS.index(self.current) + 1, total=len(STEPS)).upper())

    def _refresh_footer(self, *_args) -> None:
        page = self.page() if hasattr(self, "pages") and self.current in self.pages else None
        if page is None:
            return
        busy = bool(self.runner.busy())
        self.back_button.setVisible(page.shows_back())
        self.back_button.setEnabled(not busy)
        self.back_button.setText(t("common.back"))
        self.continue_button.setText(t(page.continue_label_key()))
        self.continue_button.setEnabled(page.can_continue() and not busy)
        p = theme.current()
        self.back_button.setIcon(icons.icon("arrow-left", p.text_muted))
        self.continue_button.setIcon(icons.icon("arrow-right", p.accent_text))
        self.theme_button.setIcon(icons.icon("sun" if p.dark else "moon", p.text_muted))
        self.theme_button.setToolTip(t("header.theme_light") if p.dark else t("header.theme_dark"))

    def set_language(self, code: str) -> None:
        i18n.set_language(code)
        if hasattr(self.state, "set_lang"):
            self.state.set_lang(code)
        self.retranslate()

    def retranslate(self) -> None:
        self.setWindowTitle(t("app.name"))
        for code, button in self.lang_buttons.items():
            button.setChecked(code == i18n.language())
            button.setToolTip(t(f"header.lang.{code}"))
        self.lang_frame.setToolTip(t("header.language"))
        self.rail.retranslate()
        for page in self.pages.values():
            page.retranslate()
        if hasattr(self, "current"):
            self._refresh_rail()
            self._refresh_footer()

    def toggle_theme(self) -> None:
        app = QApplication.instance()
        theme.apply(app, not theme.current().dark)
        self.retranslate()

    def closeEvent(self, event) -> None:
        for page in self.pages.values():
            page.on_leave()
        super().closeEvent(event)
