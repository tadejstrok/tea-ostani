def test_settings_load():
    from django.conf import settings

    assert "petition" in settings.INSTALLED_APPS
    assert settings.REST_FRAMEWORK["PAGE_SIZE"] == 20
