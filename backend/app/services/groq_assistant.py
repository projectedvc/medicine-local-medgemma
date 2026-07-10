import httpx

from app.core.config import settings


SYSTEM_PROMPTS = {
    "ru": (
        "Ты MedAI, ассистент медицинского отдела. Помогай врачу структурировать работу, объяснять "
        "рентгенологические термины, готовить нейтральные формулировки, планы наблюдения и CRM-задачи. "
        "Не выдавай себя за врача, не ставь окончательный диагноз и не назначай лечение. Если ситуация "
        "может быть неотложной, прямо рекомендуй срочную очную оценку. Отвечай по-русски, кратко и по делу."
    ),
    "kk": (
        "Сен MedAI медициналық бөлім ассистентісің. Дәрігерге жұмысты құрылымдауға, радиология "
        "терминдерін түсіндіруге, бейтарап қорытынды мәтіндерін және CRM міндеттерін дайындауға көмектес. "
        "Соңғы диагноз қойма және ем тағайындама. Шұғыл жағдай белгісі болса, жедел дәрігерлік бағалауды ұсын."
    ),
    "en": (
        "You are MedAI, an assistant for a clinical imaging team. Help clinicians structure work, explain "
        "radiology terms, draft neutral wording, follow-up plans, and CRM tasks. Do not claim to be a doctor, "
        "make a final diagnosis, or prescribe treatment. Flag potentially urgent situations for immediate "
        "in-person assessment. Be concise and practical."
    ),
}


async def ask_medai(
    messages: list[dict[str, str]],
    *,
    lang: str = "ru",
    study_context: str | None = None,
) -> str:
    if not settings.groq_api_key:
        raise RuntimeError("MedAI помощник не настроен: добавьте GROQ_API_KEY в backend/.env")

    system_content = SYSTEM_PROMPTS.get(lang, SYSTEM_PROMPTS["ru"])
    if study_context:
        system_content += f"\n\nКонтекст выбранного исследования:\n{study_context}"

    payload = {
        "model": settings.groq_model,
        "messages": [{"role": "system", "content": system_content}, *messages[-20:]],
        "temperature": 0.35,
        "max_completion_tokens": 1024,
        "top_p": 0.9,
        "stream": False,
    }
    headers = {"Authorization": f"Bearer {settings.groq_api_key}", "Content-Type": "application/json"}
    timeout = httpx.Timeout(settings.groq_timeout_seconds)

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
        )
    if response.status_code >= 400:
        raise RuntimeError("MedAI временно недоступен. Проверьте конфигурацию помощника и повторите запрос.")

    data = response.json()
    content = data.get("choices", [{}])[0].get("message", {}).get("content")
    if not content:
        raise RuntimeError("MedAI не вернул ответ. Повторите запрос.")
    return str(content).strip()
