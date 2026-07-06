import re


class MarkdownCleaner:
    """
    Normalize OCR Markdown into a predictable, readable document profile.

    Markdown cannot preserve PDF fonts or exact line spacing like a layout file,
    so this cleaner focuses on stable semantic layout: headings, paragraphs,
    tables, formulas, lists, blank lines, and noisy OCR spacing.
    """

    def clean(self, markdown: str) -> str:
        text = markdown or ""
        text = self._normalize_line_breaks(text)
        text = self._remove_control_chars(text)
        text = self._normalize_whitespace(text)
        text = self._fix_heading_spacing(text)
        text = self._normalize_heading_blocks(text)
        text = self._protect_markdown_blocks(text)
        text = self._merge_wrapped_paragraph_lines(text)
        text = self._fix_list_spacing(text)
        text = self._normalize_table_spacing(text)
        text = self._normalize_formula_spacing(text)
        text = self._fix_code_blocks(text)
        text = self._remove_excessive_blank_lines(text)
        return text.strip() + "\n"

    def profile(self) -> dict:
        return {
            "format": "semantic_markdown",
            "blank_lines": "single blank line between blocks",
            "headings": "normalized ATX headings with spaces",
            "paragraphs": "wrapped OCR lines merged into readable paragraphs",
            "tables": "pipe tables normalized with cell padding",
            "formulas": "display formulas isolated as blocks; inline formulas tightened",
            "limitations": "PDF font family, exact glyph size, and pixel-level line spacing are not preserved in Markdown",
        }

    def _normalize_line_breaks(self, text: str) -> str:
        return text.replace("\r\n", "\n").replace("\r", "\n")

    def _remove_control_chars(self, text: str) -> str:
        return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)

    def _normalize_whitespace(self, text: str) -> str:
        lines = []
        for line in text.split("\n"):
            line = line.replace("\t", "    ").rstrip()
            if not line.startswith("    ") and not line.startswith("|"):
                line = line.lstrip()
                line = re.sub(r"[ ]{3,}", "  ", line)
            lines.append(line)
        return "\n".join(lines)

    def _fix_heading_spacing(self, text: str) -> str:
        text = re.sub(r"(?m)^(#{1,6})(?!\s)", r"\1 ", text)
        text = re.sub(r"(?m)^<b>([^<\n]{3,80})</b>\s*$", r"## \1", text)
        text = re.sub(r"(?m)^\*\*([^*\n]{3,80})\*\*\s*$", r"## \1", text)
        return text

    def _normalize_heading_blocks(self, text: str) -> str:
        lines = text.split("\n")
        output = []
        for line in lines:
            if re.match(r"^#{1,6}\s", line.strip()):
                if output and output[-1].strip():
                    output.append("")
                output.append(line.strip())
                output.append("")
            else:
                output.append(line)
        return "\n".join(output).strip()

    def _protect_markdown_blocks(self, text: str) -> str:
        text = re.sub(r"(?m)([^\n])\n(```)", r"\1\n\n\2", text)
        text = re.sub(r"(?m)(```)\n([^\n])", r"\1\n\n\2", text)
        return text

    def _merge_wrapped_paragraph_lines(self, text: str) -> str:
        lines = text.split("\n")
        merged = []

        for line in lines:
            stripped = line.strip()
            if not merged or not stripped or not merged[-1].strip():
                merged.append(line)
                continue

            prev = merged[-1].rstrip()
            prev_stripped = prev.strip()
            structural = (
                prev_stripped.startswith(("#", "-", "*", ">", "|", "```"))
                or stripped.startswith(("#", "-", "*", ">", "|", "```"))
                or re.match(r"^\d+[.)]\s", stripped)
                or re.search(r"[。！？；：.!?:;]$", prev_stripped)
            )

            if structural:
                merged.append(line)
            else:
                merged[-1] = f"{prev} {stripped}"

        return "\n".join(merged)

    def _fix_list_spacing(self, text: str) -> str:
        text = re.sub(r"\n{3,}(?=[\-*+]\s|\d+[.)]\s)", "\n\n", text)
        text = re.sub(r"(?m)^([\-*+])(?=\S)", r"\1 ", text)
        text = re.sub(r"(?m)^(\d+[.)])(?=\S)", r"\1 ", text)
        return text

    def _normalize_table_spacing(self, text: str) -> str:
        lines = text.split("\n")
        output = []
        in_table = False

        for line in lines:
            is_table = line.strip().startswith("|") and line.strip().endswith("|")
            if is_table:
                cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
                normalized = "| " + " | ".join(cells) + " |"
                if not in_table and output and output[-1].strip():
                    output.append("")
                output.append(normalized)
                in_table = True
            else:
                if in_table and line.strip():
                    output.append("")
                output.append(line)
                in_table = False

        return "\n".join(output)

    def _normalize_formula_spacing(self, text: str) -> str:
        text = re.sub(r"\n{0,2}(\$\$[\s\S]*?\$\$)\n{0,2}", r"\n\n\1\n\n", text)
        text = re.sub(r"\$\s+([^$\n]+?)\s+\$", r"$\1$", text)
        text = re.sub(r"(?m)^ +$", "", text)
        return text

    def _remove_excessive_blank_lines(self, text: str) -> str:
        return re.sub(r"\n{3,}", "\n\n", text)

    def _fix_code_blocks(self, text: str) -> str:
        return re.sub(r"(?<!`)```(?!`)", "```", text)
