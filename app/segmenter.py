import argparse
import re
from functools import lru_cache

from app.model import boundary_probs_for_string, load_bilstm


PUNCTUATION = set(",.;:!?…()[]{}\"'—–-")
PREFIXES = ("ищу", "куплю", "сдаю", "сдам", "продам", "продаю", "сниму", "отдам")
SHORT_WORDS = {"в", "к", "с", "и", "у", "о", "а", "я", "на", "по", "от", "до", "за"}
COMMON_WORDS = {
    "айфон",
    "iphone",
    "про",
    "дом",
    "квартиру",
    "квартира",
    "москве",
    "подмосковье",
    "диван",
    "доставка",
    "недорого",
    "даром",
    "кошку",
    "телевизор",
    "ноутбук",
    "грузчиков",
    "переезда",
    "метро",
    "мебелью",
    "техникой",
    "samsung",
    "philips",
    "hp",
}


class SpaceRestorer:
    def __init__(self, threshold: float = 0.6) -> None:
        self.threshold = threshold
        self.model, self.char2id, self.device = load_bilstm()

    def restore(self, text: str) -> str:
        if not text:
            return ""

        chunks = self._split_by_punctuation(text)
        restored = []
        for chunk, is_punctuation in chunks:
            if is_punctuation:
                restored.append(chunk)
            else:
                restored.append(self._restore_chunk(chunk))

        return self._postprocess(self._join_tokens(restored))

    def _restore_chunk(self, chunk: str) -> str:
        if len(chunk) <= 1:
            return chunk

        probs = boundary_probs_for_string(chunk, self.model, self.char2id, self.device)
        cut_positions = set()

        for index, probability in enumerate(probs, start=1):
            if probability >= self.threshold or self._hard_boundary(chunk[index - 1], chunk[index]):
                cut_positions.add(index)

        cut_positions.update(self._known_word_boundaries(chunk))
        cut_positions.difference_update(self._protected_inner_boundaries(chunk))

        parts = []
        start = 0
        for end in sorted(cut_positions):
            if end > start:
                parts.append(chunk[start:end])
            start = end
        if start < len(chunk):
            parts.append(chunk[start:])

        return " ".join(part for part in parts if part)

    def _known_word_boundaries(self, chunk: str) -> set[int]:
        lowered = chunk.lower().replace("ё", "е")
        boundaries = set()

        for prefix in PREFIXES:
            if lowered.startswith(prefix) and len(chunk) > len(prefix):
                boundaries.add(len(prefix))

        for word in COMMON_WORDS:
            start = 0
            while True:
                index = lowered.find(word, start)
                if index == -1:
                    break
                end = index + len(word)
                if index > 0:
                    boundaries.add(index)
                if end < len(chunk):
                    boundaries.add(end)
                start = index + 1

        return boundaries

    def _protected_inner_boundaries(self, chunk: str) -> set[int]:
        lowered = chunk.lower().replace("ё", "е")
        protected = set()

        for word in set(PREFIXES) | COMMON_WORDS:
            start = 0
            while True:
                index = lowered.find(word, start)
                if index == -1:
                    break
                for boundary in range(index + 1, index + len(word)):
                    protected.add(boundary)
                start = index + 1

        return protected

    @staticmethod
    def _split_by_punctuation(text: str) -> list[tuple[str, bool]]:
        parts = []
        cursor = 0
        while cursor < len(text):
            char = text[cursor]
            if char in PUNCTUATION:
                parts.append((char, True))
                cursor += 1
                continue

            end = cursor + 1
            while end < len(text) and text[end] not in PUNCTUATION:
                end += 1
            parts.append((text[cursor:end], False))
            cursor = end
        return parts

    @staticmethod
    def _hard_boundary(left: str, right: str) -> bool:
        if left.isdigit() != right.isdigit():
            return True
        if left.isascii() != right.isascii() and not left.isdigit() and not right.isdigit():
            return True
        if left.islower() and right.isupper():
            return True
        return False

    @staticmethod
    def _join_tokens(tokens: list[str]) -> str:
        text = ""
        for token in tokens:
            if token in PUNCTUATION:
                text = text.rstrip() + token + " "
            else:
                text += token + " "
        return text.strip()

    @staticmethod
    def _postprocess(text: str) -> str:
        text = re.sub(r"\s+", " ", text).strip()
        text = re.sub(r"\b([A-Za-zА-Яа-яёЁ]+)\s+(\d+)\s+([A-Za-zА-Яа-яёЁ]+)\b", r"\1 \2 \3", text)
        return text


@lru_cache(maxsize=1)
def get_restorer() -> SpaceRestorer:
    return SpaceRestorer()


def restore_text(text: str) -> str:
    return get_restorer().restore(text)


def main() -> None:
    parser = argparse.ArgumentParser(description="Restore spaces in a compressed query.")
    parser.add_argument("text", help="Input query without spaces.")
    args = parser.parse_args()
    print(restore_text(args.text))


if __name__ == "__main__":
    main()
