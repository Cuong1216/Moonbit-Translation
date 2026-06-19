import os
import json
import logging
import asyncio
from google import genai
from google.genai import types
from typing import Dict, List, Tuple

# Thiết lập logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GlossaryBuilder")

class GlossaryBuilder:
    """
    Dịch vụ tự động xây dựng bảng thuật ngữ (Glossary) bằng cách đối chiếu
    văn bản gốc (source_text) và văn bản dịch (translated_text) cũ thông qua Gemini API.
    """

    def chunk_texts(self, source_text: str, translated_text: str, lines_per_chunk: int = 40) -> List[Tuple[str, str]]:
        """
        Cắt 2 chuỗi văn bản dài thành các đoạn tương ứng nhau theo số lượng dòng văn bản.
        Đảm bảo số lượng đoạn cắt của 2 chuỗi là bằng nhau để đối chiếu song song.
        """
        # Chia thành các dòng văn bản phi rỗng
        src_lines = [line.strip() for line in source_text.split('\n') if line.strip()]
        tgt_lines = [line.strip() for line in translated_text.split('\n') if line.strip()]

        if not src_lines or not tgt_lines:
            return []

        # Tính toán số lượng đoạn cắt tương đối
        # Ưu tiên chia theo chunk_size, nhưng đảm bảo tối thiểu có 1 đoạn
        num_chunks = max(1, min(len(src_lines), len(tgt_lines)) // lines_per_chunk)

        src_step = len(src_lines) / num_chunks
        tgt_step = len(tgt_lines) / num_chunks

        chunks = []
        for i in range(num_chunks):
            # Tính toán chỉ số bắt đầu và kết thúc cho đoạn i
            src_start = int(i * src_step)
            src_end = int((i + 1) * src_step) if i < num_chunks - 1 else len(src_lines)

            tgt_start = int(i * tgt_step)
            tgt_end = int((i + 1) * tgt_step) if i < num_chunks - 1 else len(tgt_lines)

            src_chunk = "\n".join(src_lines[src_start:src_end])
            tgt_chunk = "\n".join(tgt_lines[tgt_start:tgt_end])
            
            chunks.append((src_chunk, tgt_chunk))

        logger.info(f"Đã cắt văn bản thành {len(chunks)} đoạn đối chiếu.")
        return chunks

    async def extract_terms(self, source_chunk: str, translated_chunk: str, api_key: str) -> Dict[str, str]:
        """
        Gọi Gemini API trong chế độ JSON để trích xuất các cặp thuật ngữ từ một cặp đoạn văn bản đối chiếu.
        """
        if not api_key:
            raise ValueError("Cần cung cấp Gemini API Key để thực hiện trích xuất thuật ngữ.")
            
        client = genai.Client(api_key=api_key)

        system_instruction = (
            "Bạn là chuyên gia ngôn ngữ học. Đối chiếu bản gốc và bản dịch. "
            "Tìm các danh từ riêng, tên nhân vật, địa danh, chiêu thức, vật phẩm. "
            "Trả về đúng định dạng JSON phẳng: {\"từ_gốc_1\": \"từ_dịch_1\", \"từ_gốc_2\": \"từ_dịch_2\"}. "
            "Không giải thích thêm."
        )

        user_prompt = (
            f"Hãy đối chiếu các đoạn văn sau và trích xuất danh từ/thuật ngữ:\n\n"
            f"--- BẢN GỐC (SOURCE) ---\n{source_chunk}\n\n"
            f"--- BẢN DỊCH (TRANSLATION) ---\n{translated_chunk}\n"
        )

        try:
            # Import helper để phân tích và chọn model khả dụng tránh lỗi 404
            from utils import resolve_model_name
            resolved_model = await asyncio.to_thread(resolve_model_name, "gemini-1.5-flash", api_key)
            
            # Sử dụng model đã giải quyết thích hợp
            response = await client.aio.models.generate_content(
                model=resolved_model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json"
                )
            )

            # Phân tích cú pháp JSON kết quả
            if response.text:
                terms = json.loads(response.text)
                if isinstance(terms, dict):
                    # Làm sạch khoảng trắng của các khóa và giá trị
                    return {str(k).strip(): str(v).strip() for k, v in terms.items() if k and v}
            
            return {}

        except json.JSONDecodeError as je:
            logger.warning(f"Lỗi giải mã JSON từ Gemini API phản hồi: {je}. Nội dung nhận được: {response.text if 'response' in locals() else ''}")
            return {}
        except Exception as e:
            logger.error(f"Lỗi xảy ra khi gọi Gemini API để trích xuất thuật ngữ: {e}")
            return {}

    async def build_glossary(self, source_text: str, translated_text: str, api_key: str, lines_per_chunk: int = 40) -> Dict[str, str]:
        """
        Lặp qua toàn bộ văn bản gốc và dịch:
        1. Chia nhỏ văn bản thành các đoạn tương ứng.
        2. Gọi API trích xuất thuật ngữ cho từng đoạn.
        3. Tổng hợp kết quả: thống kê tần suất xuất hiện và giải quyết xung đột khi một từ gốc có nhiều từ dịch khác nhau.
        4. Loại bỏ các kết quả sai lệch và trả về bảng Glossary thống nhất.
        """
        chunks = self.chunk_texts(source_text, translated_text, lines_per_chunk)
        
        # Thống kê tần suất: term_frequencies = { source_term: { target_term: frequency_count } }
        term_frequencies: Dict[str, Dict[str, int]] = {}

        for idx, (src_chunk, tgt_chunk) in enumerate(chunks):
            logger.info(f"Đang phân tích đoạn {idx + 1}/{len(chunks)}...")
            
            # Trích xuất cặp từ từ đoạn hiện tại
            extracted = await self.extract_terms(src_chunk, tgt_chunk, api_key)
            
            # Gộp và đếm tần suất
            for src, tgt in extracted.items():
                # Chuẩn hóa để tránh trùng lặp do viết hoa/thường (tùy chỉnh nếu cần giữ nguyên chữ hoa chữ thường)
                # Ở đây chúng ta giữ nguyên định dạng chữ viết gốc nhưng group theo chuỗi gốc chuẩn hóa
                src_key = src.strip()
                tgt_val = tgt.strip()

                if not src_key or not tgt_val:
                    continue

                if src_key not in term_frequencies:
                    term_frequencies[src_key] = {}
                
                term_frequencies[src_key][tgt_val] = term_frequencies[src_key].get(tgt_val, 0) + 1

        # Tổng hợp Glossary cuối cùng
        final_glossary: Dict[str, str] = {}
        
        for src_term, translations in term_frequencies.items():
            # Chọn dịch nghĩa có tần suất xuất hiện cao nhất
            # Ví dụ: "Xiao Yan" -> {"Tiêu Viêm": 5, "Tiêu viêm": 1} => chọn "Tiêu Viêm"
            best_translation = max(translations, key=translations.get)
            best_freq = translations[best_translation]
            
            # Loại bỏ các cặp từ sai lệch hoặc nhiễu:
            # - Từ dịch trùng lặp hoàn toàn với từ gốc (không phải dịch nghĩa thực sự, trừ khi là tên riêng giữ nguyên)
            # - Tần suất quá thấp hoặc không đủ tin cậy nếu có sự tranh chấp mạnh (ví dụ: freq của từ đúng rất thấp)
            total_occurrences = sum(translations.values())
            
            # Nếu có sự tranh chấp dịch thuật (từ gốc có nhiều dịch nghĩa),
            # tỉ lệ đồng thuận của nghĩa tốt nhất phải chiếm ưu thế (ví dụ: > 50% tổng số lần xuất hiện)
            if len(translations) > 1:
                agreement_ratio = best_freq / total_occurrences
                if agreement_ratio < 0.5:
                    logger.warning(f"Từ '{src_term}' bị tranh chấp dịch nghĩa: {translations}. Bỏ qua hoặc chọn nghĩa tốt nhất với độ tin cậy thấp.")
            
            # Bỏ qua nếu từ gốc và từ dịch giống hệt nhau mà không có ý nghĩa thực tế
            if src_term.lower() == best_translation.lower() and len(src_term) <= 3:
                # Nếu từ rất ngắn giống hệt nhau thì thường là từ nhiễu (ví dụ: "the" -> "the")
                continue

            final_glossary[src_term] = best_translation

        logger.info(f"Quá trình xây dựng Glossary hoàn tất. Thu thập được {len(final_glossary)} thuật ngữ.")
        return final_glossary

# Khởi tạo instance mặc định
glossary_builder = GlossaryBuilder()
