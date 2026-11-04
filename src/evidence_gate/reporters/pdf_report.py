"""PDF versions of the HTML reports. Chromium (already needed for the receipt checks) prints the page.
A PDF is a convenience: if it cannot be made, say so and carry on. It never changes a verdict."""

from pathlib import Path


def html_to_pdf(html_path, pdf_path, channel: str | None = None) -> Path:
    """Print an HTML file to an A4 PDF. Raises if there is no browser; callers use write() below."""
    from playwright.sync_api import sync_playwright  # imported here so the engine works without Playwright

    with sync_playwright() as playwright:
        options = {"headless": True}
        if channel:
            options["channel"] = channel  # e.g. "msedge", the same setting the browser adapter uses
        browser = playwright.chromium.launch(**options)
        try:
            page = browser.new_page()
            page.goto(Path(html_path).resolve().as_uri())
            page.pdf(path=str(pdf_path), format="A4", print_background=True, prefer_css_page_size=True)
        finally:
            browser.close()
    return Path(pdf_path)


def write(html_path, channel: str | None = None) -> tuple[Path | None, str | None]:
    """report.html -> report.pdf next to it. Returns (path, None) or (None, the reason it was not made)."""
    pdf_path = Path(html_path).with_suffix(".pdf")
    try:
        return html_to_pdf(html_path, pdf_path, channel), None
    except Exception as err:  # no browser installed, blocked download, locked file...
        first_line = (str(err).strip().splitlines() or [type(err).__name__])[0]
        return None, f"PDF not written: {first_line}"
