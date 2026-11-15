"""One module per wizard step. `PAGES` lists the classes in step order."""
from chatport.ui.pages.backup import BackupPage
from chatport.ui.pages.build import BuildPage
from chatport.ui.pages.connect import ConnectPage
from chatport.ui.pages.copy import CopyPage
from chatport.ui.pages.done import DonePage
from chatport.ui.pages.key import KeyPage
from chatport.ui.pages.prepare import PreparePage
from chatport.ui.pages.restore import RestorePage
from chatport.ui.pages.welcome import WelcomePage

PAGES = (WelcomePage, ConnectPage, KeyPage, CopyPage, PreparePage, BackupPage, BuildPage, RestorePage, DonePage)

__all__ = ["PAGES"]
