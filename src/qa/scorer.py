import re


class QualityScorer:
    def __init__(self):
        self.weights = {
            "text_coverage": 0.25,
            "table_integrity": 0.20,
            "formula_validity": 0.20,
            "ordering_coherence": 0.20,
            "format_cleanliness": 0.15,
        }

    async def score(self, markdown: str, source_pdf: str = None) -> dict:
        scores = {
            "text_coverage": self._score_text_coverage(markdown),
            "table_integrity": self._score_table_integrity(markdown),
            "formula_validity": self._score_formula_validity(markdown),
            "ordering_coherence": self._score_ordering_coherence(markdown),
            "format_cleanliness": self._score_format_cleanliness(markdown),
        }
        total = sum(scores[k] * self.weights[k] for k in scores)
        return {"scores": scores, "total": round(total, 3), "passed": total >= 0.85}

    def _score_text_coverage(self, text: str) -> float:
        if not text.strip():
            return 0.0
        total_chars = len(text.strip())
        if total_chars < 100:
            return 0.3
        return min(1.0, total_chars / 5000)

    def _score_table_integrity(self, text: str) -> float:
        tables = re.findall(r"\|.*\|", text)
        if not tables:
            return 0.7
        ok = sum(1 for t in tables if t.count("|") >= 2)
        return ok / len(tables)

    def _score_formula_validity(self, text: str) -> float:
        formulas = re.findall(r"\$\$.*?\$\$|\$.*?\$", text)
        if not formulas:
            return 0.8
        ok = sum(1 for f in formulas if f.count("$") % 2 == 0)
        return ok / len(formulas)

    def _score_ordering_coherence(self, text: str) -> float:
        paragraphs = [p for p in text.split("\n\n") if len(p.strip()) > 20]
        if len(paragraphs) < 2:
            return 0.7
        return min(1.0, len(paragraphs) / max(len(text) / 200, 1))

    def _score_format_cleanliness(self, text: str) -> float:
        issues = 0
        if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", text):
            issues += 1
        if re.search(r" {3,}", text):
            issues += 1
        if re.search(r"\n{3,}", text):
            issues += 1
        if re.search(r"(?m)^#{1,6}\S", text):
            issues += 1
        if re.search(r"(?m)^\|[^ ].*[^ ]\|$", text):
            issues += 1
        return max(0.0, 1.0 - issues * 0.1)
