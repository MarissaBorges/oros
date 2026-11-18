from backend.context import extract_trace_context


def test_extract_python_trace_context() -> None:
    trace = 'Traceback (most recent call last):\n  File "/home/borges/dev/oros/backend/views.py", line 42'
    context = extract_trace_context(trace)
    assert context["has_trace"] is True
    assert context["locations"][0]["line"] == 42
    assert "views.py" in context["locations"][0]["file"]
