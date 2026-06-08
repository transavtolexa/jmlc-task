import json
from pathlib import Path
from typing import Optional

import torch
from torch import nn


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WEIGHTS_PATH = PROJECT_ROOT / "models" / "bilstm_ru_stream_no_oscar.pth"
DEFAULT_CHAR2ID_PATH = PROJECT_ROOT / "models" / "char2id_stream_no_oscar.json"
MAX_LEN = 128


class CharBoundaryTagger(nn.Module):
    def __init__(self, vocab_size: int, emb_dim: int, hidden: int) -> None:
        super().__init__()
        self.emb = nn.Embedding(vocab_size, emb_dim, padding_idx=0)
        self.rnn = nn.LSTM(emb_dim, hidden, batch_first=True, bidirectional=True)
        self.out = nn.Linear(hidden * 2, 1)

    def forward(self, x: torch.Tensor, lengths: torch.Tensor) -> torch.Tensor:
        emb = self.emb(x)
        packed = nn.utils.rnn.pack_padded_sequence(
            emb,
            lengths.cpu(),
            batch_first=True,
            enforce_sorted=False,
        )
        h, _ = self.rnn(packed)
        h, _ = nn.utils.rnn.pad_packed_sequence(h, batch_first=True)
        logits = self.out(h).squeeze(-1)
        return logits[:, :-1]


def load_bilstm(
    weights_path: Path = DEFAULT_WEIGHTS_PATH,
    char2id_path: Path = DEFAULT_CHAR2ID_PATH,
    device: Optional[str] = None,
) -> tuple[CharBoundaryTagger, dict[str, int], str]:
    device = device or ("cuda" if torch.cuda.is_available() else "cpu")

    with char2id_path.open("r", encoding="utf-8") as file:
        char2id = json.load(file)

    state_dict = torch.load(weights_path, map_location="cpu")
    emb_dim = state_dict["emb.weight"].shape[1]
    hidden = state_dict["out.weight"].shape[1] // 2

    model = CharBoundaryTagger(len(char2id), emb_dim=emb_dim, hidden=hidden)
    model.load_state_dict(state_dict, strict=True)
    model.to(device)
    model.eval()
    return model, char2id, device


@torch.no_grad()
def boundary_probs_for_string(
    text: str,
    model: CharBoundaryTagger,
    char2id: dict[str, int],
    device: str,
) -> list[float]:
    normalized = text.lower().replace("ё", "е")
    if len(normalized) <= 1:
        return []

    def one_pass(chunk: str) -> list[float]:
        x = torch.tensor(
            [[char2id.get(char, 1) for char in chunk]],
            dtype=torch.long,
            device=device,
        )
        lengths = torch.tensor([x.size(1)], dtype=torch.long, device=device)
        logits = model(x, lengths)
        return torch.sigmoid(logits).squeeze(0).tolist()

    if len(normalized) <= MAX_LEN:
        return one_pass(normalized)

    window = MAX_LEN
    step = MAX_LEN - 16
    sums = [0.0] * (len(normalized) - 1)
    counts = [0] * (len(normalized) - 1)

    start = 0
    while start < len(normalized):
        end = min(len(normalized), start + window)
        probs = one_pass(normalized[start:end])
        for offset, probability in enumerate(probs):
            index = start + offset
            if index < len(sums):
                sums[index] += probability
                counts[index] += 1
        if end == len(normalized):
            break
        start += step

    return [sums[index] / max(1, counts[index]) for index in range(len(sums))]
