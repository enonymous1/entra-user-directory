from app.directory import DirectoryUser, parse_bool, parse_datetime


def test_parse_bool_is_none_safe():
    assert parse_bool(None) is False
    assert parse_bool("") is False
    assert parse_bool("True") is True
    assert parse_bool("TRUE") is True
    assert parse_bool("False") is False


def test_parse_datetime_blank_and_bad():
    assert parse_datetime("") is None
    assert parse_datetime("not-a-date") is None
    assert parse_datetime("2025-01-06 09:00:00") is not None


def test_is_licensed_always_bool():
    assert DirectoryUser(licenses="").is_licensed is False
    assert DirectoryUser(licenses="Unlicensed").is_licensed is False
    assert DirectoryUser(licenses="Example Plan A").is_licensed is True


def test_is_external_via_ext_and_via_user_type():
    assert DirectoryUser(user_principal_name="a_b.com#EXT#@example.org").is_external_user
    assert DirectoryUser(user_principal_name="a@example.org", user_type="Guest").is_external_user
    assert not DirectoryUser(user_principal_name="a@example.org").is_external_user


def test_license_list_splits_plus_joined():
    user = DirectoryUser(licenses="Example Plan A+Example Plan B")
    assert user.license_list == ["Example Plan A", "Example Plan B"]
    assert DirectoryUser(licenses="Unlicensed").license_list == []
