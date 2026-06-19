import os
import re
import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any
import google.generativeai as genai
import google.api_core.exceptions
from anthropic import Anthropic
from openai import OpenAI

# Thiết lập logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NovelTranslator")


class BaseTranslator(ABC):
    """
    Interface/Abstract Class đại diện cho chiến lược dịch thuật.
    """
    def translate_chunk(self, chunk: str, context: Dict[str, Any]) -> str:
        import hashlib
        from database import SessionLocal, TranslationMemory
        from sqlalchemy.exc import IntegrityError

        # 1. Chuẩn hóa đoạn văn
        clean_chunk = chunk.strip()
        if not clean_chunk:
            return ""

        # 2. Xác định cấu hình bypass cache (ví dụ: dùng API key fake trong unit tests)
        api_key = context.get("api_key", "")
        is_fake_key = isinstance(api_key, str) and api_key.startswith("fake-")
        use_cache = context.get("use_cache", True) and not is_fake_key

        source_hash = hashlib.sha256(clean_chunk.encode("utf-8")).hexdigest()

        if use_cache:
            db = SessionLocal()
            try:
                record = db.query(TranslationMemory).filter(TranslationMemory.source_hash == source_hash).first()
                if record:
                    logger.info(f"Translation Memory HIT for hash: {source_hash}")
                    return record.target_text
            except Exception as e:
                logger.error(f"Lỗi truy vấn Translation Memory: {e}")
            finally:
                db.close()

        # 3. Cache Miss hoặc Bypass: Gọi API dịch thực tế
        translated_text = self._translate_chunk_api(chunk, context)

        # 4. Ghi lại kết quả dịch mới vào Translation Memory
        if use_cache and translated_text and translated_text.strip():
            db = SessionLocal()
            try:
                # Tránh chèn bản ghi rỗng hoặc gây crash nếu có xung đột trùng lặp
                new_record = TranslationMemory(
                    source_hash=source_hash,
                    source_text=clean_chunk,
                    target_text=translated_text.strip()
                )
                db.add(new_record)
                db.commit()
                logger.info(f"Translation Memory SAVED for hash: {source_hash}")
            except IntegrityError:
                db.rollback()
            except Exception as e:
                db.rollback()
                logger.error(f"Lỗi ghi Translation Memory: {e}")
            finally:
                db.close()

        return translated_text

    @abstractmethod
    def _translate_chunk_api(self, chunk: str, context: Dict[str, Any]) -> str:
        pass


class GeminiTranslator(BaseTranslator):
    def _translate_chunk_api(self, chunk: str, context: Dict[str, Any]) -> str:
        api_key = context.get("api_key")
        model_name = context.get("model", "gemini-1.5-flash")
        glossary_dict = context.get("glossary", {})
        source_lang = context.get("source_lang", "Trung Quốc")
        target_lang = context.get("target_lang", "Tiếng Việt")

        if not api_key:
            raise ValueError("Cần cung cấp Gemini API Key để dịch thuật.")
            
        genai.configure(api_key=api_key)

        glossary_str = "\n".join([f"- {src} -> {tgt}" for src, tgt in glossary_dict.items()]) if glossary_dict else "Không có"

        system_prompt = (
            f"Bạn là một dịch giả chuyên nghiệp. Hãy dịch văn bản sau từ {source_lang} sang {target_lang}. "
            f"Bắt buộc tuân thủ bảng thuật ngữ sau:\n{glossary_str}\n\n"
            "Giữ nguyên định dạng xuống dòng và không giải thích hay thêm bớt nội dung ngoài bản dịch."
        )

        max_retries = 3
        retry_delay = 5

        for attempt in range(1, max_retries + 2):
            try:
                from utils import resolve_model_name
                resolved_model = resolve_model_name(model_name, api_key)
                
                model = genai.GenerativeModel(
                    model_name=resolved_model,
                    system_instruction=system_prompt
                )
                
                response = model.generate_content(chunk)

                if response.text:
                    return response.text
                
                raise ValueError("API trả về phản hồi rỗng.")

            except (google.api_core.exceptions.ResourceExhausted, 
                    google.api_core.exceptions.ServiceUnavailable, 
                    Exception) as e:
                
                if attempt > max_retries:
                    logger.error(f"Đã thử lại {max_retries} lần nhưng vẫn thất bại khi dịch đoạn này. Lỗi: {e}")
                    raise e
                
                logger.warning(
                    f"Gặp lỗi khi gọi Gemini API (Lần thử {attempt}/{max_retries + 1}): {e}. "
                    f"Đang chờ {retry_delay} giây trước khi thử lại..."
                )
                time.sleep(retry_delay)

        return ""


class ClaudeTranslator(BaseTranslator):
    def _translate_chunk_api(self, chunk: str, context: Dict[str, Any]) -> str:
        api_key = context.get("api_key")
        model_name = context.get("model", "claude-3-haiku-20240307")
        glossary_dict = context.get("glossary", {})
        source_lang = context.get("source_lang", "Trung Quốc")
        target_lang = context.get("target_lang", "Tiếng Việt")

        if not api_key:
            raise ValueError("Cần cung cấp Claude API Key để dịch thuật.")

        glossary_str = "\n".join([f"- {src} -> {tgt}" for src, tgt in glossary_dict.items()]) if glossary_dict else "Không có"

        system_prompt = (
            f"Bạn là một dịch giả chuyên nghiệp. Hãy dịch văn bản sau từ {source_lang} sang {target_lang}. "
            f"Bắt buộc tuân thủ bảng thuật ngữ sau:\n{glossary_str}\n\n"
            "Giữ nguyên định dạng xuống dòng và không giải thích hay thêm bớt nội dung ngoài bản dịch."
        )

        max_retries = 3
        retry_delay = 5

        for attempt in range(1, max_retries + 2):
            try:
                client = Anthropic(api_key=api_key)
                message = client.messages.create(
                    model=model_name,
                    max_tokens=4000,
                    system=system_prompt,
                    messages=[{"role": "user", "content": chunk}]
                )
                if message.content and len(message.content) > 0:
                    text_content = message.content[0].text
                    if text_content:
                        return text_content
                raise ValueError("Anthropic API trả về phản hồi rỗng.")
            except Exception as e:
                if attempt > max_retries:
                    logger.error(f"Đã thử lại {max_retries} lần nhưng vẫn thất bại khi dịch đoạn này bằng Claude. Lỗi: {e}")
                    raise e
                logger.warning(
                    f"Gặp lỗi khi gọi Anthropic API (Lần thử {attempt}/{max_retries + 1}): {e}. "
                    f"Đang chờ {retry_delay} giây trước khi thử lại..."
                )
                time.sleep(retry_delay)

        return ""


class OpenRouterTranslator(BaseTranslator):
    def _translate_chunk_api(self, chunk: str, context: Dict[str, Any]) -> str:
        api_key = context.get("api_key")
        model_name = context.get("model", "deepseek/deepseek-chat")
        glossary_dict = context.get("glossary", {})
        source_lang = context.get("source_lang", "Trung Quốc")
        target_lang = context.get("target_lang", "Tiếng Việt")

        if not api_key:
            raise ValueError("Cần cung cấp OpenRouter API Key để dịch thuật.")

        glossary_str = "\n".join([f"- {src} -> {tgt}" for src, tgt in glossary_dict.items()]) if glossary_dict else "Không có"

        system_prompt = (
            f"Bạn là một dịch giả chuyên nghiệp. Hãy dịch văn bản sau từ {source_lang} sang {target_lang}. "
            f"Bắt buộc tuân thủ bảng thuật ngữ sau:\n{glossary_str}\n\n"
            "Giữ nguyên định dạng xuống dòng và không giải thích hay thêm bớt nội dung ngoài bản dịch."
        )

        max_retries = 3
        retry_delay = 5

        for attempt in range(1, max_retries + 2):
            try:
                client = OpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=api_key
                )
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": chunk}
                    ]
                )
                if response.choices and len(response.choices) > 0:
                    text_content = response.choices[0].message.content
                    if text_content:
                        return text_content
                raise ValueError("OpenRouter API trả về phản hồi rỗng.")
            except Exception as e:
                if attempt > max_retries:
                    logger.error(f"Đã thử lại {max_retries} lần nhưng vẫn thất bại khi dịch đoạn này bằng OpenRouter. Lỗi: {e}")
                    raise e
                logger.warning(
                    f"Gặp lỗi khi gọi OpenRouter API (Lần thử {attempt}/{max_retries + 1}): {e}. "
                    f"Đang chờ {retry_delay} giây trước khi thử lại..."
                )
                time.sleep(retry_delay)

        return ""


class TranslatorFactory:
    """
    Factory để khởi tạo đúng lớp Translator dựa trên provider.
    """
    @staticmethod
    def get_translator(provider: str) -> BaseTranslator:
        provider_clean = provider.strip().lower()
        if provider_clean == "gemini":
            return GeminiTranslator()
        elif provider_clean == "claude":
            return ClaudeTranslator()
        elif provider_clean == "openrouter":
            return OpenRouterTranslator()
        else:
            raise ValueError(f"Nhà cung cấp AI không được hỗ trợ: {provider}")


class NovelTranslator:
    """
    Dịch vụ dịch thuật tiểu thuyết sử dụng thiết kế Strategy Pattern thông qua TranslatorFactory.
    Hỗ trợ chia nhỏ văn bản thông minh và tự động thử lại khi gặp lỗi.
    """

    def smart_chunking(self, text: str, max_chars: int = 3000) -> List[str]:
        if not text:
            return []
            
        if len(text) <= max_chars:
            return [text]

        chunks = []
        paragraphs = text.split('\n')
        current_chunk = []
        current_len = 0

        for para in paragraphs:
            added_len = len(para) + (1 if current_chunk else 0)
            
            if current_len + added_len <= max_chars:
                current_chunk.append(para)
                current_len += added_len
            else:
                if len(para) > max_chars:
                    if current_chunk:
                        chunks.append("\n".join(current_chunk))
                        current_chunk = []
                        current_len = 0
                    
                    sentences = re.split(r'(?<=[.!?])\s+', para)
                    
                    for sentence in sentences:
                        sentence = sentence.strip()
                        if not sentence:
                            continue
                        
                        sent_len = len(sentence) + (1 if current_chunk else 0)
                        
                        if current_len + sent_len <= max_chars:
                            current_chunk.append(sentence)
                            current_len += sent_len
                        else:
                            if current_chunk:
                                chunks.append(" ".join(current_chunk))
                            current_chunk = [sentence]
                            current_len = len(sentence)
                else:
                    if current_chunk:
                        chunks.append("\n".join(current_chunk))
                    current_chunk = [para]
                    current_len = len(para)

        if current_chunk:
            chunks.append("\n".join(current_chunk))

        logger.info(f"Đã chia văn bản thành {len(chunks)} đoạn dịch thông minh.")
        return chunks

    def translate_chunk(self, chunk: str, glossary_dict: Dict[str, str], api_key: str, model_name: str = "gemini-1.5-flash", source_lang: str = "Trung Quốc", target_lang: str = "Tiếng Việt", provider: str = "gemini") -> str:
        """
        Dịch một đoạn sử dụng provider tương ứng.
        """
        translator = TranslatorFactory.get_translator(provider)
        context = {
            "api_key": api_key,
            "model": model_name,
            "glossary": glossary_dict,
            "source_lang": source_lang,
            "target_lang": target_lang
        }
        return translator.translate_chunk(chunk, context)

    def translate_full_novel(self, text: str, glossary_dict: Dict[str, str], api_key: str, model_name: str = "gemini-1.5-flash", max_chars: int = 3000, source_lang: str = "Trung Quốc", target_lang: str = "Tiếng Việt", provider: str = "gemini") -> str:
        chunks = self.smart_chunking(text, max_chars)
        translated_chunks = []

        for idx, chunk in enumerate(chunks):
            logger.info(f"Đang dịch đoạn {idx + 1}/{len(chunks)}...")
            translated_chunk = self.translate_chunk(
                chunk=chunk,
                glossary_dict=glossary_dict,
                api_key=api_key,
                model_name=model_name,
                source_lang=source_lang,
                target_lang=target_lang,
                provider=provider
            )
            translated_chunks.append(translated_chunk)

        return "\n\n".join(translated_chunks)


# Khởi tạo một instance mặc định để sử dụng nhanh
novel_translator = NovelTranslator()
