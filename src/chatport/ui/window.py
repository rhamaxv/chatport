"""The one window: a pill stepper across the top, the Android panel on the left, the iPhone panel on the
right, the step's content in the middle, and the Back / primary action footer."""
from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel, QMainWindow, QPushButton, QScrollArea,
                               QStackedWidget, QVBoxLayout, QWidget)

from chatport import i18n
from chatport.core.steps import STEPS
from chatport.i18n import t
from chatport.ui import theme
from chatport.ui.pages import PAGES
from chatport.ui.pages.base import Context, Page
from chatport.ui.panel_state import Situation, android_view, iphone_view
from chatport.ui.widgets.bridge import Bridge
from chatport.ui.widgets.phone_panel import PhonePanel
from chatport.ui.widgets.stepper import Stepper

log = logging.getLogger("chatport.ui")

# A phone went away while a job ran: the Connect page is the place to sort that out.
DISCONNECT_CODES = frozenset({"no_android", "android_unauthorized", "android_offline", "no_adb",
                              "no_iphone", "iphone_untrusted", "iphone_disconnected"})
# Jobs that move data between the phones and the computer: the only time the connector moves.
MOVING_JOBS = frozenset({"key", "copy", "backup", "build", "restore", "undo"})
COLUMN_GAP = 24
COMPACT_BELOW = 1000
SIDE_WIDTH = 220  # the top bar's left and right boxes, equal so the stepper sits in the centre


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
        self._needs_passcode = False
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
            page.busy_changed.connect(self.refresh_panels)
            page.panels_changed.connect(self.refresh_panels)
            page.advance.connect(self._advance)
            page.request_go.connect(self._go_back_to)
            self.stack.addWidget(self._scrollable(page))
        self._build_footer()
        runner.event.connect(self._on_event)
        runner.busy_changed.connect(self._refresh_footer)
        runner.busy_changed.connect(self.refresh_panels)
        QApplication.instance().focusChanged.connect(self._follow_focus)
        self.current = STEPS[0]
        self.retranslate()
        self.go(state.current())

    # ----- construction -------------------------------------------------------------------------

    def _build(self) -> None:
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        topbar = QWidget()
        topbar.setObjectName("topbar")
        tl = QHBoxLayout(topbar)
        tl.setContentsMargins(theme.PAGE_PADDING, 16, theme.PAGE_PADDING, 8)
        tl.setSpacing(0)
        left = QWidget()
        left.setFixedWidth(SIDE_WIDTH)
        ll = QHBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        self.brand = QLabel()
        self.brand.setProperty("role", "brand")
        ll.addWidget(self.brand, 0, Qt.AlignmentFlag.AlignVCenter)
        ll.addStretch(1)
        tl.addWidget(left)
        tl.addStretch(1)
        self.stepper = Stepper()
        tl.addWidget(self.stepper, 0, Qt.AlignmentFlag.AlignVCenter)
        tl.addStretch(1)
        right = QWidget()
        right.setFixedWidth(SIDE_WIDTH)
        rl = QHBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(4)
        rl.addStretch(1)
        self.lang_buttons: dict[str, QPushButton] = {}
        for code in i18n.LANGUAGES:
            button = QPushButton(code.upper())
            button.setProperty("variant", "text")
            button.setCheckable(True)
            button.setFocusPolicy(Qt.FocusPolicy.TabFocus)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _c=False, code=code: self.set_language(code))
            rl.addWidget(button)
            self.lang_buttons[code] = button
        rl.addSpacing(12)
        self.theme_button = QPushButton()
        self.theme_button.setProperty("variant", "text")
        self.theme_button.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.theme_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_button.clicked.connect(self.toggle_theme)
        rl.addWidget(self.theme_button)
        tl.addWidget(right)
        outer.addWidget(topbar)

        body = QWidget()
        bl = QHBoxLayout(body)
        bl.setContentsMargins(theme.PAGE_PADDING, 16, theme.PAGE_PADDING, 24)
        bl.setSpacing(0)
        self.android_panel = PhonePanel("android")
        self.iphone_panel = PhonePanel("iphone")
        bl.addWidget(self.android_panel)

        middle = QWidget()
        ml = QVBoxLayout(middle)
        ml.setContentsMargins(0, 0, 0, 0)
        ml.setSpacing(0)
        ml.addSpacing(20)
        self.bridge = Bridge()   # spans the two gaps too, so the dashes run from panel to panel
        ml.addWidget(self.bridge)
        ml.addSpacing(16)
        inner = QWidget()
        il = QVBoxLayout(inner)
        il.setContentsMargins(COLUMN_GAP, 0, COLUMN_GAP, 0)
        il.setSpacing(0)
        self.title_label = QLabel()
        self.title_label.setProperty("role", "title")
        self.title_label.setWordWrap(True)
        self.subtitle_label = QLabel()
        self.subtitle_label.setProperty("role", "subtitle")
        self.subtitle_label.setWordWrap(True)
        il.addWidget(self.title_label)
        il.addSpacing(6)
        il.addWidget(self.subtitle_label)
        il.addSpacing(24)
        self.stack = QStackedWidget()
        il.addWidget(self.stack, 1)
        ml.addWidget(inner, 1)
        bl.addWidget(middle, 1)
        bl.addWidget(self.iphone_panel)
        outer.addWidget(body, 1)
        self._outer = outer

    def _build_footer(self) -> None:
        """Built after the pages, so the Tab order runs top bar, page content, then Back and the action."""
        footer = QWidget()
        footer.setObjectName("footer")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(theme.PAGE_PADDING, 14, theme.PAGE_PADDING, 18)
        self.back_button = QPushButton()
        self.back_button.clicked.connect(self.back)
        self.continue_button = QPushButton()
        self.continue_button.setProperty("variant", "primary")
        self.continue_button.setDefault(True)
        self.continue_button.clicked.connect(self.proceed)
        fl.addWidget(self.back_button)
        fl.addStretch(1)
        fl.addWidget(self.continue_button)
        self._outer.addWidget(footer)

    @staticmethod
    def _scrollable(page: QWidget) -> QScrollArea:
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setFocusPolicy(Qt.FocusPolicy.NoFocus)   # Tab goes to the controls inside, never to the frame
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
        self._needs_passcode = False
        self.stack.setCurrentIndex(STEPS.index(step))
        self.stack.currentWidget().verticalScrollBar().setValue(0)
        self.title_label.setText(t(self.pages[step].title_key))
        self.subtitle_label.setText(t(self.pages[step].subtitle_key))
        self.centralWidget().setFocus()   # no control keeps a focus ring from the previous step
        self.pages[step].on_enter()
        self._refresh_stepper()
        self._refresh_footer()
        self.refresh_panels()
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
            self._refresh_stepper()

    def _on_event(self, event) -> None:
        page = self.page()
        if page.jobs and getattr(event, "job", None) not in page.jobs:
            log.debug("event for %s ignored on page %s", getattr(event, "job", "?"), page.step)
            return
        page.on_event(event)
        if event.kind == "need":
            self._needs_passcode = True
        elif event.kind in ("clear", "done", "error"):
            self._needs_passcode = False
        code = event.data.get("code") if event.kind == "error" else None
        if code in DISCONNECT_CODES and self.current != "connect":
            log.info("phone disconnected during %s, returning to connect", page.step)
            self.go("connect")
            self.pages["connect"].show_notice()
        self.refresh_panels()

    # ----- appearance ---------------------------------------------------------------------------

    def _refresh_stepper(self) -> None:
        done = {step for step in STEPS if self.state.done(step)}
        self.stepper.set_progress(self.current, done)

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
        self.theme_button.setText(t("header.light") if p.dark else t("header.dark"))
        self.theme_button.setToolTip(t("header.theme_light") if p.dark else t("header.theme_dark"))

    def refresh_panels(self, *_args) -> None:
        """Redraw the two phone panels and the connector for the current step and the last checks."""
        if not hasattr(self, "pages") or self.current not in self.pages:
            return
        busy = bool(self.runner.busy())
        prepare = self.pages.get("prepare")
        situation = Situation(step=self.current, connect=self.ctx.last_connect, ready=self.ctx.last_ready,
                              saved=self.state.get("connect") or {}, busy=busy, failed=self.page().error.isVisible(),
                              needs_passcode=self._needs_passcode,
                              checklist_done=bool(prepare and prepare.checklist.all_checked()))
        for panel, view in ((self.android_panel, android_view(situation)), (self.iphone_panel, iphone_view(situation))):
            panel.set_state(view.state, view.facts, view.status)
            panel.set_dimmed(view.dimmed)
        working = self.current != "welcome"
        self.android_panel.setVisible(working)
        self.iphone_panel.setVisible(working)
        self.bridge.setVisible(working)
        moving = busy and (self.runner.job_name() in MOVING_JOBS)
        self.bridge.set_active(moving)
        self.bridge.set_into_iphone(self.current == "restore")

    def set_language(self, code: str) -> None:
        i18n.set_language(code)
        if hasattr(self.state, "set_lang"):
            self.state.set_lang(code)
        self.retranslate()

    def retranslate(self) -> None:
        self.setWindowTitle(t("app.name"))
        self.brand.setText(t("app.name"))
        for code, button in self.lang_buttons.items():
            button.setChecked(code == i18n.language())
            button.setToolTip(t(f"header.lang.{code}"))
        self.stepper.retranslate()
        for page in self.pages.values():
            page.retranslate()
        if hasattr(self, "current"):
            page = self.page()
            self.title_label.setText(t(page.title_key))
            self.subtitle_label.setText(t(page.subtitle_key))
            self._refresh_stepper()
            self._refresh_footer()
            self.refresh_panels()

    def toggle_theme(self) -> None:
        app = QApplication.instance()
        theme.apply(app, not theme.current().dark)
        self.retranslate()

    def _follow_focus(self, _old, now) -> None:
        """Keyboard users tab onto controls below the fold: scroll the middle column to show them."""
        if now is None or not hasattr(self, "stack"):
            return
        area = self.stack.currentWidget()
        if isinstance(area, QScrollArea) and area.widget() is not None and area.widget().isAncestorOf(now):
            area.ensureWidgetVisible(now, 24, 24)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        compact = event.size().width() < COMPACT_BELOW
        self.android_panel.set_compact(compact)
        self.iphone_panel.set_compact(compact)

    def closeEvent(self, event) -> None:
        for page in self.pages.values():
            page.on_leave()
        super().closeEvent(event)
