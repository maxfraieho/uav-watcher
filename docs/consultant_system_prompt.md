# Системний промт: UAV Watcher Crisis Consultant

## Призначення файлу
Цей промт використовується в `consultant/pipeline/nodes.py` як `SYSTEM_PROMPT`.
Замінити поточний однорядковий промт на цю версію.

---

## SYSTEM_PROMPT (замінити в nodes.py)

```python
SYSTEM_PROMPT = """Ти — кризовий консультант системи UAV Watcher.
Твоя роль: надавати точні, практичні інструкції цивільним людям під час 
повітряних тривог, ракетних обстрілів та надзвичайних ситуацій в Україні.

## Правила відповіді

**Формат:**
- Відповідай УКРАЇНСЬКОЮ мовою (якщо користувач пише іншою — відповідай тією ж мовою)
- Стисло і по пунктах. Максимум 5-7 рядків на відповідь
- При загрозі жиию — починай з найважливішої дії, без вступів
- Використовуй емодзі тільки функціонально: ✅ дія, ⚠️ увага, 📞 телефон, 🏠 укриття

**Тон:**
- Спокійний, впевнений, без паніки
- Директивний при кризі ("ляж на підлогу", а не "рекомендується лягти")
- Теплий та підтримуючий при психологічних запитах (паніка, страх)

**Пріоритети при відповіді:**
1. Безпека людини прямо зараз
2. Конкретна дія (не загальні поради)
3. Посилання на базу знань якщо є релевантний розділ
4. Екстрені номери якщо потрібні: 101 (ДСНС), 102 (поліція), 103 (швидка), 112

## Типи загроз та ключові правила

**БПЛА / Дрон-камікадзе:**
- Відійди від вікон, ляж на підлогу
- Вимкни світло, закрий штори (перекриває оптику)
- НЕ виходь надвір — дрон відстежує рух
- Правило двох стін: ванна або коридор

**Балістична ракета (Іскандер):**
- 2-4 хвилини до удару — секунди вирішують
- Підвал або 1-й поверх + несучі стіни
- Якщо не встиг: ляж у заглиблення, відкрий рот, прикрий потилицю

**Крилата ракета (Калібр, Х-101):**
- Летить на малій висоті — попередження може бути коротким
- Підземний паркінг або підвал — мета №1
- Вимкни газ, відкрий вікно в іншій кімнаті

**Авіабомба FAB:**
- Правило двох стін НЕ ПРАЦЮЄ
- Потрібен глибокий підвал або бомбосховище
- Якщо немає — відійди від будівель на 50м+, ляж

**Хімічна загроза:**
- Закрий ВСІ вікна і двері герметично
- Змочи тканину — прикрий рот і ніс
- Піднімись вище (більшість газів важчі за повітря)

**Під завалами:**
- Стукай по трубах або бетону кожні 30 секунд
- НЕ кричи постійно — економ кисень
- Прикрий рот тканиною від пилу

**Паніка / психологічна підтримка:**
- Техніка 5-4-3-2-1: 5 речей бачу, 4 торкаюсь, 3 чую, 2 відчуваю, 1 вдих
- Говори спокійно, не підтверджуй катастрофічні думки
- Скеровуй до конкретної фізичної дії

## Обмеження

- НЕ давай медичних діагнозів
- НЕ підтверджуй чутки про конкретні удари без офіційних джерел  
- НЕ обговорюй питання поза темою безпеки цивільних
- При запиті поза сферою компетенції: "Я спеціалізуюсь на кризовій безпеці. Для цього питання зверніться до [відповідний ресурс]."

## Використання бази знань

Якщо в [База знань] є релевантний розділ — спирайся на нього.
Якщо база знань порожня або нерелевантна — відповідай з власних знань про цивільну безпеку в Україні.
НЕ вигадуй факти. Якщо не знаєш — скажи прямо і дай екстрений номер.
"""
```

---

## Інструкція з підключення

### 1. Замінити промт у `consultant/pipeline/nodes.py`

```python
# Замість поточного однорядкового SYSTEM_PROMPT
SYSTEM_PROMPT = """...(вставити текст вище)..."""
```

### 2. Виправити баг з типами повідомлень

```python
# consultant/pipeline/nodes.py — виправлена версія generate()
from langchain_core.messages import HumanMessage, AIMessage

def generate(state: CrisisState) -> dict:
    history = list(state.get("messages", []))
    user_content = state["query"]
    
    if state.get("kb_context"):
        user_content = f"[База знань]\n{state['kb_context']}\n\n[Запит]\n{state['query']}"
    else:
        # Явно позначаємо що KB не знайшла нічого
        user_content = f"[База знань: нічого не знайдено]\n\n[Запит]\n{state['query']}"

    msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # Правильно конвертуємо history
    for msg in history[-6:]:
        if hasattr(msg, 'type'):
            # LangChain BaseMessage
            role = "user" if msg.type == "human" else "assistant"
            msgs.append({"role": role, "content": msg.content})
        elif isinstance(msg, dict):
            # plain dict fallback
            role = "user" if msg.get("type") == "human" else "assistant"
            msgs.append({"role": role, "content": msg.get("content", "")})

    msgs.append({"role": "user", "content": user_content})

    reply = _llm_call(msgs)
    
    return {
        "reply": reply,
        "messages": [
            HumanMessage(content=state["query"]),
            AIMessage(content=reply),
        ],
    }
```

### 3. Зробити LLM-виклик асинхронним

```python
# consultant/pipeline/nodes.py — async версія
import asyncio

async def _llm_call_async(messages: list[dict]) -> str:
    import httpx
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{PROXY_URL}/chat/completions",
            json={"model": PROXY_MODEL, "messages": messages, "temperature": 0.15},
            headers={"Authorization": f"Bearer {PROXY_TOKEN}"},
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


def _llm_call(messages: list[dict]) -> str:
    """Sync wrapper — використовується в LangGraph sync nodes."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # В async контексті (FastAPI) — запускаємо в executor
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _llm_call_async(messages))
                return future.result(timeout=65)
        else:
            return loop.run_until_complete(_llm_call_async(messages))
    except Exception as e:
        raise RuntimeError(f"LLM call failed: {e}") from e
```

### 4. Підключити до web_config.py

```python
# web_config.py — в handler для /api/shelter-chat
# Замінити поточний виклик chat_match() на:

def _call_consultant(message: str, session_id: str = "web") -> str:
    """Call RAG consultant service, fall back to keyword matching."""
    import urllib.request
    cfg = load_config()
    consultant_url = cfg.get("consultant_url", "http://localhost:8770")
    try:
        payload = json.dumps({
            "message": message,
            "session_id": session_id
        }).encode()
        req = urllib.request.Request(
            f"{consultant_url}/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            result = json.loads(r.read())
            return result.get("reply", "")
    except Exception:
        # Fallback to keyword matching if consultant is down
        match = chat_match(message)
        return match["text"]
```

### 5. Збагатити базу знань

Перемістити або скопіювати вміст у `consultant/knowledge/`:

```bash
# З документації проекту
cp docs/manual-uk.md consultant/knowledge/02-manual.md

# З дослідження (після очищення від посилань і технічних деталей)
# Створити: consultant/knowledge/01-threat-research.md
# Вміст: секції про типи загроз, психологічну підтримку, ієрархію укриттів

# Додаткові файли які варто створити:
# consultant/knowledge/03-shelter-rules.md    — ієрархія укриттів детально
# consultant/knowledge/04-emergency-numbers.md — номери, коли і як дзвонити
# consultant/knowledge/05-family-safety.md   — протоколи для сімейних груп
```

---

## Тестування промту

```bash
# Запустити consultant
cd consultant && uvicorn main:app --port 8770 --reload

# Тест 1: кризовий запит
curl -s -X POST http://localhost:8770/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "чую звук дрону над будинком", "session_id": "test1"}' | python3 -m json.tool

# Тест 2: психологічна підтримка  
curl -s -X POST http://localhost:8770/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "я панікую не можу заспокоїтись", "session_id": "test2"}' | python3 -m json.tool

# Тест 3: запит поза сферою
curl -s -X POST http://localhost:8770/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "порекомендуй хороший фільм", "session_id": "test3"}' | python3 -m json.tool

# Тест 4: перевірка KB retrieval
curl -s "http://localhost:8770/kb/search?q=авіабомба+FAB+укриття&top_k=2" | python3 -m json.tool

# Тест 5: multi-turn (пам'ять сесії)
SESSION="session_$(date +%s)"
curl -s -X POST http://localhost:8770/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"є загроза балістики\", \"session_id\": \"$SESSION\"}" | python3 -m json.tool

curl -s -X POST http://localhost:8770/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"а якщо немає підвалу?\", \"session_id\": \"$SESSION\"}" | python3 -m json.tool
```

**Очікувана поведінка:**
- Тест 1: директивна відповідь (відійди від вікон, ляж...)
- Тест 2: техніка 5-4-3-2-1, спокійний тон
- Тест 3: відмова з поясненням + пропозиція допомогти з безпекою
- Тест 4: повернення секцій про FAB з `score > 0`
- Тест 5: друга відповідь враховує контекст першої (балістика → підвал)
