from mailmap.content import extract_from_html, extract_urls_from_text, meaningful_link_domains, unwrap_tracking_url


def test_unwrap_tracking_url() -> None:
    wrapped = "https://click.example.com/?url=https%3A%2F%2Fgithub.com%2Fsettings"
    assert unwrap_tracking_url(wrapped) == "https://github.com/settings"


def test_extract_urls_from_html_and_text() -> None:
    text = "Reset here https://github.com/login and visit https://sendgrid.net/x"
    html = '<a href="https://click.example.com/?url=https%3A%2F%2Fdiscord.com%2Fapp">open</a>'
    html_text, html_urls = extract_from_html(html)
    text_urls = extract_urls_from_text(text)
    assert "open" in html_text
    assert "https://github.com/login" in text_urls
    assert "https://discord.com/app" in html_urls


def test_meaningful_link_domains_filters_noise() -> None:
    urls = ["https://discord.com/app", "https://sendgrid.net/x"]
    assert meaningful_link_domains(urls) == ["discord.com"]
