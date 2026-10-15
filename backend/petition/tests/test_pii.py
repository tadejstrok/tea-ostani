from petition.pii import find_pii


def test_clean_text_is_clean():
    assert find_pii("Odstopi takoj, gospod Mijič.") == []


def test_empty_and_none_are_clean():
    assert find_pii("") == []
    assert find_pii(None) == []


def test_email_is_found():
    assert find_pii("pisi mi na ana.novak@example.com") == ["email"]


def test_slovenian_phone_forms_are_found():
    assert find_pii("poklici 041 234 567") == ["phone"]
    assert find_pii("+386 41 234 567") == ["phone"]
    assert find_pii("041234567") == ["phone"]
    assert find_pii("00386 1 234 56") == ["phone"]


def test_plain_numbers_are_not_phones():
    # Goal figures and years must not trip the phone pattern.
    assert find_pii("zbrali smo 15458 podpisov") == []
    assert find_pii("leta 2026 in 3000 podpisov") == []


def test_additional_slovenian_phone_forms_are_found():
    # Bare country code and parentheses formats.
    assert find_pii("386 41 234 567") == ["phone"]
    assert find_pii("(041) 234 567") == ["phone"]
    assert find_pii("+386 (0)41 234 567") == ["phone"]


def test_dates_are_not_phones():
    # Dates with periods should not match as phone numbers.
    assert find_pii("24. 07. 2026") == []


def test_url_is_found():
    assert find_pii("poglej https://spam.example") == ["url"]
    assert find_pii("obisci www.spam.si") == ["url"]


def test_signoff_with_name_is_found():
    assert find_pii("Odstopi.\nLep pozdrav, Ana") == ["signoff"]
    assert find_pii("Hvala, Marko") == ["signoff"]
    assert find_pii("S spoštovanjem, Špela") == ["signoff"]


def test_signoff_without_punctuation_is_found():
    # Plain whitespace is enough separator between salutation and name.
    assert find_pii("Lep pozdrav Ana") == ["signoff"]
    assert find_pii("Hvala Marko") == ["signoff"]


def test_signoff_without_a_name_is_clean():
    # Real message from the live data: a bare sign-off, then a single initial.
    assert find_pii("Dragi Janša,\nTi si strupen.\nLep pozdrav \nK") == []
    assert find_pii("Odstopi. Lep pozdrav") == []


def test_signoff_followed_by_lowercase_is_not_a_name():
    # Guards the case-sensitivity of the name class: a global IGNORECASE flag
    # would make [A-ZČŠŽ] match "odstopi" here.
    assert find_pii("Lep pozdrav, odstopi takoj") == []


def test_addressing_a_politician_is_not_a_signoff():
    assert find_pii("Dragi Janša, odstopi takoj.") == []


def test_multiple_kinds_are_sorted_and_deduped():
    assert find_pii("mail ana@example.com in www.spam.si") == ["email", "url"]


def test_legal_footnote_enumerations_are_not_phones():
    # Parenthesized numbers without a leading zero (legal/footnote style)
    # must not match as phone numbers.
    assert find_pii("glej opombo (12) 345 67 v besedilu") == []
    assert find_pii("clen (1) 234 56 ustave") == []
    assert find_pii("tocka (3) 456 78 zakona") == []


def test_cyrillic_balkan_uppercase_initials_are_found():
    # Ć and Đ must be reachable as a name's first letter, not just as
    # lowercase tails — a large share of Slovenian names are of
    # Bosnian/Croatian/Serbian origin.
    assert find_pii("Lp, Ćira") == ["signoff"]
    assert find_pii("Lp, Đorđe") == ["signoff"]


def test_bare_trailing_name_is_found():
    # The commonest way people sign a message: just their name, alone, on
    # the last line, with no salutation at all.
    assert find_pii("Odstopi takoj.\n\nAna Novak") == ["trailing-name"]


def test_widened_salutations_are_found():
    # "lepo" != "lep ", so a naive \blep pozdrav\b misses this form.
    assert find_pii("Odstopi.\nLepo pozdravljeni, Ana") == ["signoff"]
    # "pozdrav" alone, not paired with "lep", must also count as a salutation.
    assert find_pii("Odstopi.\nPozdrav, Ana") == ["signoff"]


def test_filler_words_between_salutation_and_name_are_found():
    assert find_pii("Hvala za vse, Marko") == ["signoff"]
