# Contributing to Chatport

Thanks for helping. Chatport is a graphical front end; the migration engine is
[wamove](https://github.com/rhamaxv/wamove). Bugs in how chats are converted belong there,
bugs in the window, the checks, packaging or texts belong here.

## Set up

```sh
git clone https://github.com/rhamaxv/chatport && cd chatport
python3.12 -m venv .venv && . .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python -m pytest -q
CHATPORT_FAKE=1 python -m chatport                     # the window with a pretend engine, no phones needed
```

## Rules of the house

- All user-facing text goes through `chatport.i18n.t()`. Add English in `i18n/en.py` and Indonesian in `i18n/id.py`. `tests/test_i18n.py` fails on missing keys.
- The 64-digit key never touches disk or logs. Logs never contain phone numbers.
- No network calls except the adb download in `tools/adb.py`.
- One responsibility per module. If a file passes 300 lines, split it.
- Run the tests before opening a pull request. CI runs them on Linux, macOS and Windows.

## Reporting a problem

Open an issue with your OS, Chatport version, the step where it failed, and the error title shown.
Attach the log from the "Copy log" button. Do not attach your chats, media, backups or key.
