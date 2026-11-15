# Chatport conventions

- Python 3.12+, PySide6. Source in `src/chatport`, tests in `tests` (pytest, pytest-qt).
- Contracts other modules rely on (do not change without updating every user):
  `core/steps.py` (STEPS, JOBS), `core/events.py` (Event), `core/errors.py` (ErrorCode, ACTION),
  `i18n/__init__.py` (`t()`, key convention).
- The engine is `wamove.api` (fork at github.com/rhamaxv/wamove). Never call wamove's CLI; never print.
- All user-facing text goes through `i18n.t()`. English keys in `i18n/en.py`, Indonesian in `i18n/id.py`.
- Nothing is uploaded anywhere. The only network call is the adb download in `tools/adb.py`.
- The 64-digit key stays in memory. Logs never contain the key or phone numbers.
- No em dashes in any text, code comments or docs.
- Keep files focused; one page per module under `ui/pages`.
- Run `python -m pytest -q` before claiming anything works.
