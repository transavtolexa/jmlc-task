from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.schemas import RestoreRequest, RestoreResponse
from app.segmenter import restore_text


app = FastAPI(
    title="Avito Query Space Restoration",
    description="Restore spaces in compressed Russian classified-search queries.",
    version="0.1.0",
)


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return """
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Space Restoration</title>
  <style>
    body {
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f6f7f9;
      color: #20242c;
    }
    main {
      max-width: 720px;
      margin: 72px auto;
      padding: 0 20px;
    }
    h1 {
      margin: 0 0 8px;
      font-size: 32px;
      line-height: 1.15;
    }
    p {
      margin: 0 0 28px;
      color: #667085;
      font-size: 16px;
    }
    .panel {
      background: white;
      border: 1px solid #e4e7ec;
      border-radius: 8px;
      padding: 20px;
      box-shadow: 0 10px 28px rgba(16, 24, 40, 0.06);
    }
    label {
      display: block;
      margin-bottom: 8px;
      font-weight: 600;
    }
    input {
      box-sizing: border-box;
      width: 100%;
      height: 48px;
      padding: 0 14px;
      border: 1px solid #cfd4dc;
      border-radius: 8px;
      font-size: 17px;
    }
    button {
      width: 100%;
      height: 46px;
      margin-top: 14px;
      border: 0;
      border-radius: 8px;
      background: #00a046;
      color: white;
      font-size: 16px;
      font-weight: 700;
      cursor: pointer;
    }
    button:disabled {
      opacity: 0.65;
      cursor: wait;
    }
    .result {
      margin-top: 18px;
      padding: 16px;
      min-height: 24px;
      border-radius: 8px;
      background: #f2f4f7;
      font-size: 20px;
      line-height: 1.4;
      word-break: break-word;
    }
    .error {
      color: #b42318;
    }
  </style>
</head>
<body>
  <main>
    <h1>Восстановление пробелов</h1>
    <p>Введите строку без пробелов и получите нормализованный вариант.</p>

    <section class="panel">
      <label for="text">Текст</label>
      <input id="text" value="куплюайфон14про" autocomplete="off">
      <button id="submit" type="button">Восстановить</button>
      <div id="result" class="result"></div>
    </section>
  </main>

  <script>
    const input = document.getElementById("text");
    const button = document.getElementById("submit");
    const result = document.getElementById("result");

    async function restore() {
      const text = input.value.trim();
      if (!text) {
        result.textContent = "";
        return;
      }

      button.disabled = true;
      result.classList.remove("error");
      result.textContent = "Обработка...";

      try {
        const response = await fetch("/restore", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({text})
        });
        const data = await response.json();
        result.textContent = data.restored;
      } catch (error) {
        result.classList.add("error");
        result.textContent = "Не удалось обработать запрос";
      } finally {
        button.disabled = false;
      }
    }

    button.addEventListener("click", restore);
    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        restore();
      }
    });
  </script>
</body>
</html>
"""


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/restore", response_model=RestoreResponse)
def restore(request: RestoreRequest) -> RestoreResponse:
    return RestoreResponse(text=request.text, restored=restore_text(request.text))
