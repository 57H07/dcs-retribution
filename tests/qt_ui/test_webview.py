from qt_ui.webview import page_query


def test_page_query_gives_the_page_its_server_and_key() -> None:
    assert page_query("[::1]:16880", "key") == "server=[::1]:16880&apiKey=key"
