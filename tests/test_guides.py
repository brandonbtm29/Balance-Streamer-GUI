"""Settings > Balance Guides."""

from balance_streamer.guides import GUIDES


def test_every_brand_in_a_tab_has_a_guide(window):
    tab = window.tab_objects[0]
    brands = [tab.combo_brand.itemText(i) for i in range(tab.combo_brand.count())]
    assert brands
    for brand in brands:
        assert brand in GUIDES


def test_show_guide_opens_the_brand_page(window):
    settings = window.settings_tab
    page = settings.show_guide("Lachoi")
    assert settings.stack.currentWidget() is settings.guides_page
    assert settings.guides_page.tabs.currentWidget() is page
    assert "C5-0" in page.toPlainText()  # continuous output setting
    assert settings.show_guide("Some Other Brand") is settings.guides_page.pages["Start here"]


def test_guides_give_the_settings_the_app_uses(window):
    pages = window.settings_tab.guides_page.pages
    for title, page in pages.items():
        text = page.toPlainText()
        assert text.strip(), title
        if title != "Other balances":
            assert "9600" in text, title
    assert "05-ErA" in pages["Bonvoisin"].toPlainText()  # zero tracking
    assert "09-odE" in pages["Bonvoisin"].toPlainText()
    assert "DATA" in pages["Ohaus Adventurer"].toPlainText()  # AR leaves the factory at 7 data bits


def test_help_points_to_the_guides(window):
    settings = window.settings_tab
    titles = [settings.sidebar.item(i).text() for i in range(settings.sidebar.count())]
    assert any("Balance Guides" in t for t in titles)
    assert titles[-1].endswith("Help & About")
