import pytest
from unittest.mock import MagicMock, patch
from services.translator import novel_translator

@patch("google.generativeai.GenerativeModel")
@patch("google.generativeai.list_models")
@patch("google.generativeai.configure")
def test_translate_chunk_success(mock_configure, mock_list_models, mock_generative_model):
    # Setup mock for list_models
    dummy_model = MagicMock()
    dummy_model.name = "models/gemini-1.5-flash"
    mock_list_models.return_value = [dummy_model]

    # Setup mock for GenerativeModel instance
    mock_model_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Đây là bản dịch tiếng Việt."
    mock_model_instance.generate_content.return_value = mock_response
    mock_generative_model.return_value = mock_model_instance

    # Run translate_chunk
    result = novel_translator.translate_chunk(
        chunk="This is a English text.",
        glossary_dict={},
        api_key="fake-key",
        model_name="gemini-1.5-flash",
        source_lang="Tiếng Anh",
        target_lang="Tiếng Việt"
    )

    # Assertions
    assert result == "Đây là bản dịch tiếng Việt."
    mock_configure.assert_any_call(api_key="fake-key")
    mock_generative_model.assert_called_once()
    
    # Check that system instruction contains correct source and target language
    kwargs = mock_generative_model.call_args[1]
    system_instruction = kwargs.get("system_instruction", "")
    assert "Tiếng Anh" in system_instruction
    assert "Tiếng Việt" in system_instruction

@patch("google.generativeai.GenerativeModel")
@patch("google.generativeai.list_models")
def test_translate_chunk_with_glossary(mock_list_models, mock_generative_model):
    dummy_model = MagicMock()
    dummy_model.name = "models/gemini-1.5-flash"
    mock_list_models.return_value = [dummy_model]

    mock_model_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Tiêu Viêm tu luyện Luyện Khí."
    mock_model_instance.generate_content.return_value = mock_response
    mock_generative_model.return_value = mock_model_instance

    glossary = {"Xiao Yan": "Tiêu Viêm", "Qi Refining": "Luyện Khí"}
    result = novel_translator.translate_chunk(
        chunk="Xiao Yan practices Qi Refining.",
        glossary_dict=glossary,
        api_key="fake-key",
        source_lang="English",
        target_lang="Vietnamese"
    )

    assert result == "Tiêu Viêm tu luyện Luyện Khí."
    kwargs = mock_generative_model.call_args[1]
    system_instruction = kwargs.get("system_instruction", "")
    assert "- Xiao Yan -> Tiêu Viêm" in system_instruction
    assert "- Qi Refining -> Luyện Khí" in system_instruction

@patch("time.sleep")
@patch("google.generativeai.GenerativeModel")
@patch("google.generativeai.list_models")
def test_translate_chunk_retry_on_failure(mock_list_models, mock_generative_model, mock_sleep):
    dummy_model = MagicMock()
    dummy_model.name = "models/gemini-1.5-flash"
    mock_list_models.return_value = [dummy_model]

    mock_model_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Bản dịch sau khi thử lại."
    
    # First call throws error, second call succeeds
    mock_model_instance.generate_content.side_effect = [Exception("Temporary error"), mock_response]
    mock_generative_model.return_value = mock_model_instance

    result = novel_translator.translate_chunk(
        chunk="Hello",
        glossary_dict={},
        api_key="fake-key"
    )

    assert result == "Bản dịch sau khi thử lại."
    assert mock_model_instance.generate_content.call_count == 2
    mock_sleep.assert_called_once_with(5)

@patch("google.generativeai.GenerativeModel")
@patch("google.generativeai.list_models")
def test_translate_full_novel(mock_list_models, mock_generative_model):
    dummy_model = MagicMock()
    dummy_model.name = "models/gemini-1.5-flash"
    mock_list_models.return_value = [dummy_model]

    mock_model_instance = MagicMock()
    mock_response_1 = MagicMock()
    mock_response_1.text = "Đoạn một được dịch."
    mock_response_2 = MagicMock()
    mock_response_2.text = "Đoạn hai được dịch."
    mock_model_instance.generate_content.side_effect = [mock_response_1, mock_response_2]
    mock_generative_model.return_value = mock_model_instance

    text = "Chunk one.\nChunk two."
    
    result = novel_translator.translate_full_novel(
        text=text,
        glossary_dict={},
        api_key="fake-key",
        max_chars=15,
        source_lang="Trung Quốc",
        target_lang="Tiếng Việt"
    )

    assert result == "Đoạn một được dịch.\n\nĐoạn hai được dịch."
    assert mock_model_instance.generate_content.call_count == 2

@patch("services.translator.Anthropic")
def test_claude_translator_success(mock_anthropic_class):
    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client
    
    mock_message = MagicMock()
    mock_text_content = MagicMock()
    mock_text_content.text = "Bản dịch từ Claude"
    mock_message.content = [mock_text_content]
    mock_client.messages.create.return_value = mock_message
    
    result = novel_translator.translate_chunk(
        chunk="Hello",
        glossary_dict={},
        api_key="fake-claude-key",
        model_name="claude-3-haiku-20240307",
        source_lang="Tiếng Anh",
        target_lang="Tiếng Việt",
        provider="claude"
    )
    
    assert result == "Bản dịch từ Claude"
    mock_anthropic_class.assert_called_once_with(api_key="fake-claude-key")
    mock_client.messages.create.assert_called_once()
    kwargs = mock_client.messages.create.call_args[1]
    assert kwargs["model"] == "claude-3-haiku-20240307"
    assert "Tiếng Anh" in kwargs["system"]

@patch("services.translator.OpenAI")
def test_openrouter_translator_success(mock_openai_class):
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client
    
    mock_completion = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "Bản dịch từ OpenRouter"
    mock_completion.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_completion
    
    result = novel_translator.translate_chunk(
        chunk="Hello",
        glossary_dict={},
        api_key="fake-openrouter-key",
        model_name="deepseek/deepseek-chat",
        source_lang="Tiếng Anh",
        target_lang="Tiếng Việt",
        provider="openrouter"
    )
    
    assert result == "Bản dịch từ OpenRouter"
    mock_openai_class.assert_called_once_with(
        base_url="https://openrouter.ai/api/v1",
        api_key="fake-openrouter-key"
    )
    mock_client.chat.completions.create.assert_called_once()
    kwargs = mock_client.chat.completions.create.call_args[1]
    assert kwargs["model"] == "deepseek/deepseek-chat"
    system_msg = kwargs["messages"][0]["content"]
    assert "Tiếng Anh" in system_msg
