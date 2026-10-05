import json
import pytest
from enterprise_ai_patterns.fine_tuning.dataset import ChatExample, ChatTurn, write_jsonl


def test_chat_example_requires_target_assistant_turn(tmp_path):
    bad = ChatExample((ChatTurn("user", "hello"),))
    with pytest.raises(ValueError):
        bad.validate()

    good = ChatExample((
        ChatTurn("system", "classify"),
        ChatTurn("user", "text"),
        ChatTurn("assistant", '{"label":"x"}'),
    ))
    path = tmp_path / "examples.jsonl"
    write_jsonl([good], path)
    record = json.loads(path.read_text().strip())
    assert record["messages"][-1]["role"] == "assistant"
