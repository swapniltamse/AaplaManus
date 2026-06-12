from app.router import classify, FAST_LOCAL, SMART_LOCAL, CODE_EXPERT


def test_short_simple_prompt_routes_to_fast_local():
    result = classify("What is 2 + 2?")
    assert result.model_key == FAST_LOCAL
    assert result.needs_browser is False
    assert result.needs_code is False


def test_research_prompt_routes_to_smart_local():
    result = classify("Research the latest AI regulations in financial services")
    assert result.model_key == SMART_LOCAL
    assert result.needs_browser is True


def test_code_prompt_routes_to_code_expert():
    result = classify("Write a Python script to parse CSV files")
    assert result.model_key == CODE_EXPERT
    assert result.needs_code is True


def test_file_prompt_routes_to_smart_local():
    result = classify("Summarize this document and extract the key points")
    assert result.model_key == SMART_LOCAL
    assert result.needs_file is True


def test_long_prompt_flags_complex():
    long_prompt = "research " + "detail " * 85
    result = classify(long_prompt)
    assert result.is_complex is True


def test_browser_plus_code_flags_complex():
    result = classify("Search the web and write a Python script comparing the results")
    assert result.is_complex is True
    assert result.needs_code is True
    assert result.needs_browser is True


def test_model_name_is_non_empty():
    result = classify("hello")
    assert result.model_name
