import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from services.translator import novel_translator

@patch("google.genai.Client")
@pytest.mark.asyncio
async def test_translate_chunk_success(mock_client_class):
    # Setup mock for models.list
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    dummy_model = MagicMock()
    dummy_model.name = "models/gemini-1.5-flash"
    mock_client.models.list.return_value = [dummy_model]

    # Setup mock for Client generate_content (async)
    mock_response = MagicMock()
    mock_response.text = "Đây là bản dịch tiếng Việt."
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    # Run translate_chunk
    result = await novel_translator.translate_chunk(
        chunk="This is a English text.",
        glossary_dict={},
        api_key="fake-key",
        model_name="gemini-1.5-flash",
        source_lang="Tiếng Anh",
        target_lang="Tiếng Việt"
    )

    # Assertions
    assert result == "Đây là bản dịch tiếng Việt."
    mock_client_class.assert_any_call(api_key="fake-key")
    
    # Check that system instruction contains correct source and target language
    kwargs = mock_client.aio.models.generate_content.call_args[1]
    config = kwargs.get("config")
    system_instruction = config.system_instruction
    assert "Tiếng Anh" in system_instruction
    assert "Tiếng Việt" in system_instruction

@patch("google.genai.Client")
@pytest.mark.asyncio
async def test_translate_chunk_with_glossary(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    dummy_model = MagicMock()
    dummy_model.name = "models/gemini-1.5-flash"
    mock_client.models.list.return_value = [dummy_model]

    mock_response = MagicMock()
    mock_response.text = "Tiêu Viêm tu luyện Luyện Khí."
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    glossary = {"Xiao Yan": "Tiêu Viêm", "Qi Refining": "Luyện Khí"}
    result = await novel_translator.translate_chunk(
        chunk="Xiao Yan practices Qi Refining.",
        glossary_dict=glossary,
        api_key="fake-key",
        source_lang="English",
        target_lang="Vietnamese"
    )

    assert result == "Tiêu Viêm tu luyện Luyện Khí."
    kwargs = mock_client.aio.models.generate_content.call_args[1]
    config = kwargs.get("config")
    system_instruction = config.system_instruction
    assert "- Xiao Yan -> Tiêu Viêm" in system_instruction
    assert "- Qi Refining -> Luyện Khí" in system_instruction

@patch("asyncio.sleep")
@patch("google.genai.Client")
@pytest.mark.asyncio
async def test_translate_chunk_retry_on_failure(mock_client_class, mock_sleep):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    dummy_model = MagicMock()
    dummy_model.name = "models/gemini-1.5-flash"
    mock_client.models.list.return_value = [dummy_model]

    mock_response = MagicMock()
    mock_response.text = "Bản dịch sau khi thử lại."
    
    # First call throws error, second call succeeds
    mock_client.aio.models.generate_content = AsyncMock(side_effect=[Exception("Temporary error"), mock_response])

    result = await novel_translator.translate_chunk(
        chunk="Hello",
        glossary_dict={},
        api_key="fake-key"
    )

    assert result == "Bản dịch sau khi thử lại."
    assert mock_client.aio.models.generate_content.call_count == 2
    mock_sleep.assert_called_once_with(5)

@patch("google.genai.Client")
@pytest.mark.asyncio
async def test_translate_full_novel(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    dummy_model = MagicMock()
    dummy_model.name = "models/gemini-1.5-flash"
    mock_client.models.list.return_value = [dummy_model]

    mock_response_1 = MagicMock()
    mock_response_1.text = "Đoạn một được dịch."
    mock_response_2 = MagicMock()
    mock_response_2.text = "Đoạn hai được dịch."
    mock_client.aio.models.generate_content = AsyncMock(side_effect=[mock_response_1, mock_response_2])

    text = "Chunk one.\nChunk two."
    
    result = await novel_translator.translate_full_novel(
        text=text,
        glossary_dict={},
        api_key="fake-key",
        max_chars=15,
        source_lang="Trung Quốc",
        target_lang="Tiếng Việt"
    )

    assert result == "Đoạn một được dịch.\n\nĐoạn hai được dịch."
    assert mock_client.aio.models.generate_content.call_count == 2

@patch("services.translator.AsyncAnthropic")
@pytest.mark.asyncio
async def test_claude_translator_success(mock_anthropic_class):
    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client
    
    mock_message = MagicMock()
    mock_text_content = MagicMock()
    mock_text_content.text = "Bản dịch từ Claude"
    mock_message.content = [mock_text_content]
    mock_client.messages.create = AsyncMock(return_value=mock_message)
    
    result = await novel_translator.translate_chunk(
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

@patch("services.translator.AsyncOpenAI")
@pytest.mark.asyncio
async def test_openrouter_translator_success(mock_openai_class):
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client
    
    mock_completion = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "Bản dịch từ OpenRouter"
    mock_completion.choices = [mock_choice]
    mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
    
    result = await novel_translator.translate_chunk(
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

@pytest.mark.asyncio
async def test_translate_full_novel_concurrency():
    # Test that translate_full_novel correctly tags indices,
    # uses a semaphore to limit concurrency, and sorts results back in order.
    async def mock_translate_chunk(chunk, glossary_dict, api_key, **kwargs):
        if "one" in chunk:
            await asyncio.sleep(0.05)
            return "Dịch Một"
        elif "two" in chunk:
            await asyncio.sleep(0.01)
            return "Dịch Hai"
        return "Dịch Khác"

    with patch.object(novel_translator, 'translate_chunk', side_effect=mock_translate_chunk):
        result = await novel_translator.translate_full_novel(
            text="Chunk one.\nChunk two.",
            glossary_dict={},
            api_key="fake-key",
            max_chars=15,
            concurrency_limit=2
        )
        # Even though Chunk two finishes first (0.01s vs 0.05s), the final result
        # must be ordered correctly as Chunk one first, then Chunk two.
        assert result == "Dịch Một\n\nDịch Hai"

@patch("services.translator.AsyncOpenAI")
@pytest.mark.asyncio
async def test_openrouter_translator_agentic_success(mock_openai_class):
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client
    
    # Mocking completion responses for two calls
    mock_response_raw = MagicMock()
    mock_choice_raw = MagicMock()
    mock_choice_raw.message.content = "Bản dịch thô sơ"
    mock_response_raw.choices = [mock_choice_raw]
    
    mock_response_edited = MagicMock()
    mock_choice_edited = MagicMock()
    mock_choice_edited.message.content = "Bản dịch đã được biên tập mượt mà"
    mock_response_edited.choices = [mock_choice_edited]
    
    mock_client.chat.completions.create = AsyncMock(side_effect=[mock_response_raw, mock_response_edited])
    
    result = await novel_translator.translate_chunk(
        chunk="Raw Chinese text",
        glossary_dict={},
        api_key="fake-openrouter-key",
        provider="openrouter",
        use_agentic=True
    )
    
    assert result == "Bản dịch đã được biên tập mượt mà"
    assert mock_client.chat.completions.create.call_count == 2
    
    # Verify first call args
    call_args_list = mock_client.chat.completions.create.call_args_list
    first_call_kwargs = call_args_list[0][1]
    assert first_call_kwargs["model"] == "google/gemini-2.5-flash"
    assert first_call_kwargs["messages"][0]["content"] == "Dịch sát nghĩa đen đoạn văn sau sang Tiếng Việt. Ngữ cảnh từ các đoạn trước: Không có. Hãy tham chiếu cách xưng hô và bối cảnh này để dịch đoạn tiếp theo cho đồng nhất. Nếu không có ngữ cảnh, hãy dịch bình thường."
    assert first_call_kwargs["messages"][1]["content"] == "Raw Chinese text"
    
    # Verify second call args
    second_call_kwargs = call_args_list[1][1]
    assert second_call_kwargs["model"] == "meta-llama/llama-3-8b-instruct:free"
    assert second_call_kwargs["messages"][0]["content"] == "Biên tập lại bản dịch thô sau cho văn phong thuần Việt, giữ nguyên ý nghĩa gốc, sửa lỗi ngữ pháp. Ngữ cảnh từ các đoạn trước: Không có. Hãy tham chiếu cách xưng hô và bối cảnh này để dịch đoạn tiếp theo cho đồng nhất. Nếu không có ngữ cảnh, hãy dịch bình thường."
    assert second_call_kwargs["messages"][1]["content"] == "Bản dịch thô sơ"

@patch("asyncio.sleep")
@patch("services.translator.AsyncOpenAI")
@pytest.mark.asyncio
async def test_openrouter_translator_backoff_retry(mock_openai_class, mock_sleep):
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client
    
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "Bản dịch thành công"
    mock_response.choices = [mock_choice]
    
    from unittest.mock import call
    # Fail first two calls, succeed third call
    mock_client.chat.completions.create = AsyncMock(side_effect=[
        Exception("Rate limit 429"), 
        Exception("Rate limit 429"), 
        mock_response
    ])
    
    result = await novel_translator.translate_chunk(
        chunk="Hello",
        glossary_dict={},
        api_key="fake-key",
        provider="openrouter",
        use_agentic=False
    )
    
    assert result == "Bản dịch thành công"
    assert mock_client.chat.completions.create.call_count == 3
    mock_sleep.assert_has_calls([call(5), call(10)])


@pytest.mark.asyncio
async def test_translate_full_novel_sliding_window():
    # We want to test that each chunk is translated sequentially and receives the previous translations as context.
    calls = []
    async def mock_translate_chunk(chunk, glossary_dict, api_key, previous_context="", **kwargs):
        calls.append((chunk, previous_context))
        return f"Translated {chunk}"

    with patch.object(novel_translator, 'translate_chunk', side_effect=mock_translate_chunk):
        result = await novel_translator.translate_full_novel(
            text="Chunk 1\nChunk 2\nChunk 3\nChunk 4\nChunk 5",
            glossary_dict={},
            api_key="fake-key",
            max_chars=10,  # Ensure it splits into individual chunks
        )
        
        # Verify result is concatenated correctly
        expected_result = "Translated Chunk 1\n\nTranslated Chunk 2\n\nTranslated Chunk 3\n\nTranslated Chunk 4\n\nTranslated Chunk 5"
        assert result == expected_result
        
        # Verify sequential calls and sliding window context (max 3 chunks)
        # Call 1: "Chunk 1", previous_context=""
        # Call 2: "Chunk 2", previous_context="Translated Chunk 1"
        # Call 3: "Chunk 3", previous_context="Translated Chunk 1\n\nTranslated Chunk 2"
        # Call 4: "Chunk 4", previous_context="Translated Chunk 1\n\nTranslated Chunk 2\n\nTranslated Chunk 3"
        # Call 5: "Chunk 5", previous_context="Translated Chunk 2\n\nTranslated Chunk 3\n\nTranslated Chunk 4" (Chunk 1 popped out)
        assert len(calls) == 5
        assert calls[0] == ("Chunk 1", "")
        assert calls[1] == ("Chunk 2", "Translated Chunk 1")
        assert calls[2] == ("Chunk 3", "Translated Chunk 1\n\nTranslated Chunk 2")
        assert calls[3] == ("Chunk 4", "Translated Chunk 1\n\nTranslated Chunk 2\n\nTranslated Chunk 3")
        assert calls[4] == ("Chunk 5", "Translated Chunk 2\n\nTranslated Chunk 3\n\nTranslated Chunk 4")


@patch("google.genai.Client")
@pytest.mark.asyncio
async def test_gemini_translator_with_context(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    dummy_model = MagicMock()
    dummy_model.name = "models/gemini-1.5-flash"
    mock_client.models.list.return_value = [dummy_model]

    mock_response = MagicMock()
    mock_response.text = "Bản dịch tiếng Việt."
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    result = await novel_translator.translate_chunk(
        chunk="Hello",
        glossary_dict={},
        api_key="fake-key",
        previous_context="Previously translated paragraph."
    )

    assert result == "Bản dịch tiếng Việt."
    kwargs = mock_client.aio.models.generate_content.call_args[1]
    config = kwargs.get("config")
    system_instruction = config.system_instruction
    assert "Ngữ cảnh từ các đoạn trước: Previously translated paragraph." in system_instruction


@patch("services.translator.httpx.AsyncClient")
@pytest.mark.asyncio
async def test_ollama_translator_success(mock_async_client_class):
    mock_client = MagicMock()
    mock_async_client_class.return_value = mock_client
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"response": "Đây là bản dịch từ Ollama."}
    mock_response.raise_for_status = MagicMock()
    
    mock_client.post = AsyncMock(return_value=mock_response)

    result = await novel_translator.translate_chunk(
        chunk="Hello Ollama",
        glossary_dict={},
        api_key="ollama",
        model_name="llama3",
        source_lang="Tiếng Anh",
        target_lang="Tiếng Việt",
        provider="ollama",
        use_cache=False
    )

    assert result == "Đây là bản dịch từ Ollama."
    mock_client.post.assert_called_once()
    kwargs = mock_client.post.call_args[1]
    
    json_data = kwargs.get("json", {})
    assert json_data["model"] == "llama3"
    assert json_data["prompt"] == "Hello Ollama"
    assert json_data["stream"] is False
    assert "Tiếng Anh" in json_data["system"]
    assert "Tiếng Việt" in json_data["system"]


def test_translator_factory_ollama():
    from services.translator import TranslatorFactory, LocalTranslator
    translator = TranslatorFactory.get_translator("ollama")
    assert isinstance(translator, LocalTranslator)

