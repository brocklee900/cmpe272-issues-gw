from app.pagination import parse_link_header

SAMPLE_LINK = (
    '<https://api.github.com/repos/o/r/issues?page=2>; rel="next", '
    '<https://api.github.com/repos/o/r/issues?page=5>; rel="last"'
)


def test_parses_next_and_last():
    links = parse_link_header(SAMPLE_LINK)
    assert links["next"] == "https://api.github.com/repos/o/r/issues?page=2"
    assert links["last"] == "https://api.github.com/repos/o/r/issues?page=5"


def test_empty_header_returns_empty_dict():
    assert parse_link_header(None) == {}
    assert parse_link_header("") == {}


def test_single_rel():
    header = '<https://api.github.com/repos/o/r/issues?page=1>; rel="first"'
    assert parse_link_header(header) == {"first": "https://api.github.com/repos/o/r/issues?page=1"}
