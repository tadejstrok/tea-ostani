from petition.moderation import screen


def test_clean_text_not_flagged():
    assert screen("Odstopi takoj, gospod Mijič.") is False


def test_empty_and_none_not_flagged():
    assert screen("") is False
    assert screen(None) is False


def test_url_is_flagged():
    assert screen("Poglej https://spam.example") is True
    assert screen("obisci www.spam.si") is True
    assert screen("HTTP://LOUD.example") is True
