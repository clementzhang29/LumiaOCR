import re


class OrderingCorrector:
    async def correct(self, markdown: str, llm_callback=None) -> str:
        if llm_callback:
            return await self._llm_fix(markdown, llm_callback)
        return self._rule_fix(markdown)

    def _rule_fix(self, markdown: str) -> str:
        lines = markdown.split("\n")
        cleaned = [l for l in lines if not self._is_header_footer(l)]
        return "\n".join(cleaned)

    def _is_header_footer(self, line: str) -> bool:
        line = line.strip()
        if re.match(r"^[-—]*\s*\d+\s*[-—]*$", line):
            return True
        if re.match(r"^[Pp]age\s+\d+\s+of\s+\d+$", line):
            return True
        return False

    async def _llm_fix(self, markdown: str, llm_callback) -> str:
        prompt = (
            "You are a document layout restoration expert. "
            "The following OCR output may have incorrect paragraph ordering, "
            "page breaks in the middle of paragraphs, or headers/footers mixed in. "
            "Restore the correct reading order. "
            f"Remove page headers, footers, and page numbers.\n\n{markdown}"
        )
        return await llm_callback(prompt)