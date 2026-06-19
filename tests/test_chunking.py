import pytest
from services.translator import novel_translator

def test_smart_chunking_short_text():
    text = "Hello world. This is a simple test."
    chunks = novel_translator.smart_chunking(text, max_chars=100)
    assert chunks == [text]

def test_smart_chunking_split_by_paragraph():
    paragraph_1 = "This is the first paragraph. " * 5
    paragraph_2 = "This is the second paragraph. " * 5
    text = f"{paragraph_1}\n{paragraph_2}"
    
    # Set max_chars to fit paragraph_1 but not the combined text
    chunks = novel_translator.smart_chunking(text, max_chars=200)
    assert len(chunks) == 2
    assert chunks[0] == paragraph_1
    assert chunks[1] == paragraph_2

def test_smart_chunking_split_by_sentence_inside_long_paragraph():
    sentence_1 = "Sentence number one. " * 5
    sentence_2 = "Sentence number two. " * 5
    text = sentence_1 + sentence_2
    
    # Since it's a single paragraph but length > max_chars (150), it must split by sentence.
    chunks = novel_translator.smart_chunking(text, max_chars=150)
    assert len(chunks) == 2
    for chunk in chunks:
        assert len(chunk) <= 150
        assert chunk[-1] in [".", "!", "?"]

def test_smart_chunking_empty_text():
    assert novel_translator.smart_chunking("") == []
    assert novel_translator.smart_chunking(None) == []
