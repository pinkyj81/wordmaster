import pytest
from WordMaster.app import app, WordsRow


class FakeWord:
    def __init__(self, id, word, meaning):
        self.id = id
        self.word = word
        self.meaning = meaning


class FakeQuery:
    def __init__(self, items):
        self._items = items

    def filter_by(self, **kwargs):
        # ignore kwargs in smoke test
        return self

    def all(self):
        return self._items


def test_get_words_returns_json(monkeypatch):
    """Smoke test: `/get_words/<text_id>` should return a JSON list of words.

    This test monkeypatches `WordsRow.query` so it doesn't require a real DB.
    Run with: `pytest WordMaster/tests/test_get_words.py`
    """
    fake_items = [
        FakeWord("1", "apple", "사과"),
        FakeWord("2", "book", "책"),
    ]

    fake_query = FakeQuery(fake_items)
    # Replace the query object on the model with our fake query
    # Use an application context so Flask-SQLAlchemy's query descriptor works safely
    with app.app_context():
        monkeypatch.setattr(WordsRow, "query", fake_query)
        client = app.test_client()
        resp = client.get("/get_words/ANYTEXTID")

    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    assert data[0]["word"] == "apple"
    assert data[0]["meaning"] == "사과"
    assert data[1]["id"] == "2"
