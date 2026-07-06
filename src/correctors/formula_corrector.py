import re


class FormulaCorrector:
    """校正 OCR 输出的 LaTeX 公式"""

    COMMON_ERRORS = {
        "\n": "",
        "  ": " ",
    }

    async def correct(self, markdown: str, llm_callback=None) -> str:
        result = self._fix_common_errors(markdown)
        result = self._fix_delimiters(result)
        if llm_callback:
            result = await self._llm_fix(result, llm_callback)
        return result

    def _fix_common_errors(self, text: str) -> str:
        for wrong, right in self.COMMON_ERRORS.items():
            text = text.replace(wrong, right)
        return text

    def _fix_delimiters(self, text: str) -> str:
        text = re.sub(r"\$\$(.+?)\$\$", r"$$\1$$", text)
        text = re.sub(r"(?<!\$)\$(.+?)\$(?!\$)", r"$\1$", text)
        return text

    async def _llm_fix(self, markdown: str, llm_callback) -> str:
        prompt = (
            "You are a LaTeX formula restoration expert. "
            "The following document contains mathematical formulas that may have OCR errors. "
            "Fix all LaTeX formulas and ensure they are valid. "
            f"Keep all non-formula content unchanged.\n\n{markdown}"
        )
        return await llm_callback(prompt)