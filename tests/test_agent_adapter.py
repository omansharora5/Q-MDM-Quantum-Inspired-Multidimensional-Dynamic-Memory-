from examples.agent_tool_loop import run_agent


class MemoryStub:
    def connect(self, *args):
        pass

    def recall(self, query, **kwargs):
        assert kwargs["dataset"] == "personal-assistant"
        return {"handles":[{"id":"m-1","version":2}]}

    def expand(self, memory_id, version):
        assert (memory_id,version) == ("m-1",2)
        return {"payload":{"dataset":"personal-assistant","source":{"text":"Use the coach."}}}


def test_model_adapter_opens_observed_evidence_and_rejects_arbitrary_tools():
    turns = iter([
        {"tool_calls":[{"id":"bad","name":"shell","arguments":{}}]},
        {"tool_calls":[{"id":"read","name":"memory_expand","arguments":{"memory_id":"m-1","version":2}}]},
        {"content":"Use the coach [m-1@v2]."},
    ])

    def next_turn(messages, tools):
        assert {tool["name"] for tool in tools} == {"memory_recall","memory_expand"}
        if messages[-1].get("tool_call_id") == "bad":
            assert messages[-1]["result"] == {"error":"Unknown tool"}
        return next(turns)

    result = run_agent(next_turn,"What is the plan?",MemoryStub(),dataset="personal-assistant")
    assert result["opened"] == ["m-1@v2"] and "coach" in result["answer"]
