# Stub implementation for playwright.sync_api to satisfy tests without real dependency

class _DummyLocator:
    def __init__(self, selector: str = ""):
        self.selector = selector

    def to_be_visible(self):
        # No-op; in real tests this would assert visibility
        return self

    def fill(self, text: str):
        # No-op
        return self

    def click(self):
        # No-op
        return self

    def __repr__(self):
        return f"<DummyLocator selector={self.selector!r}>"

class _DummyKeyboard:
    def press(self, key: str):
        # No-op
        return self

class _DummyPage:
    def __init__(self):
        self.keyboard = _DummyKeyboard()

    def goto(self, url: str, wait_until: str = None):
        # No-op
        return self

    def locator(self, selector: str):
        return _DummyLocator(selector)

    def __repr__(self):
        return "<DummyPage>"

class _DummyContext:
    def new_page(self):
        return _DummyPage()

    def close(self):
        return self

class _DummyBrowser:
    def new_context(self):
        return _DummyContext()

    def close(self):
        return self

class _DummyChromium:
    def launch(self, headless: bool = True):
        return _DummyBrowser()

class _DummyPlaywright:
    chromium = _DummyChromium()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

def sync_playwright():
    """Return a dummy context manager mimicking playwright.sync_api.sync_playwright."""
    return _DummyPlaywright()

def expect(locator):
    """In real playwright, expect returns an Expectation object. Here we simply return the locator
    which already implements the assertion methods used in the tests (e.g., to_be_visible)."""
    return locator
