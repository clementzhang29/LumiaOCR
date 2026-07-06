import re


class TableCorrector:
    async def correct(self, markdown: str, llm_callback=None) -> str:
        if llm_callback:
            return await self._llm_fix(markdown, llm_callback)
        return self._rule_fix(markdown)

    def _rule_fix(self, markdown: str) -> str:
        lines = markdown.split("\n")
        fixed = []
        in_table = False
        for i, line in enumerate(lines):
            if "|" in line and line.strip().startswith("|"):
                if not in_table:
                    in_table = True
                if i + 1 < len(lines) and re.match(r"^[\s\|:\-\+]+$", lines[i + 1]) is None:
                    if re.search(r"[-]{3,}", line) is None:
                        pass
            else:
                in_table = False
            fixed.append(line)
        return "\n".join(fixed)

    async def _llm_fix(self, markdown: str, llm_callback) -> str:
        prompt = (
            "You are a document table restoration expert. "
            "The following OCR output contains tables that may be broken or misaligned. "
            "Restore all tables to correct Markdown table format. "
            f"Keep all non-table content unchanged.\n\n{markdown}"
        )
        return await llm_callback(prompt)