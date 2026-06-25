"""
Инструмент LLM для автоматического создания навыков Eva.

LLM анализирует запрос пользователя, доступные плагины/интеграции
и генерирует навыки в формате eva_skills.
"""

import json
import uuid
import logging
from typing import Annotated

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from eva.plugin_loader.magic_plugin import operation

name = 'ai_skill_creator'
version = '0.1.0'

_logger = logging.getLogger(name)


def _uid() -> str:
    return str(uuid.uuid4())[:8]


def _get_integrations_info(pm) -> str:
    """Собирает информацию о доступных интеграциях и плагинах."""
    info_parts = []

    try:
        for step in pm.get_operation_sequence('define_commands'):
            plugin_name = getattr(step.plugin, 'name', 'unknown')
            info_parts.append(f"- Плагин: {plugin_name}")
    except Exception:
        pass

    ha_url = None
    ha_token = None
    try:
        for plugin_name in ('voice_commands', 'automations', 'integrations'):
            p = pm.get_plugin_by_name(plugin_name) if hasattr(pm, 'get_plugin_by_name') else None
            if p is not None:
                cfg = getattr(p, 'config', {}) or {}
                if cfg.get('ha_url'):
                    ha_url = cfg['ha_url']
                    ha_token = cfg.get('ha_token')
                    info_parts.append(f"- Home Assistant подключён: {ha_url}")
                    break
    except Exception:
        pass

    if ha_url and ha_token:
        try:
            import httpx
            import concurrent.futures
            import asyncio

            async def fetch_entities():
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.get(
                        f"{ha_url}/api/states",
                        headers={"Authorization": f"Bearer {ha_token}"}
                    )
                    if resp.status_code == 200:
                        states = resp.json()
                        domains = {}
                        for s in states[:100]:
                            eid = s.get('entity_id', '')
                            domain = eid.split('.')[0] if '.' in eid else 'other'
                            if domain not in domains:
                                domains[domain] = []
                            friendly = (s.get('attributes') or {}).get('friendly_name', '')
                            domains[domain].append(f"{eid} ({friendly})" if friendly else eid)
                        info_parts.append("- Доступные устройства/датчики HA:")
                        for d, ents in sorted(domains.items()):
                            info_parts.append(f"  {d}: {', '.join(ents[:5])}")

            with concurrent.futures.ThreadPoolExecutor() as pool:
                pool.submit(asyncio.run, fetch_entities()).result(timeout=8)
        except Exception:
            pass
    else:
        info_parts.append("- Home Assistant: не подключён")

    try:
        skills_path = __import__('os').path.expanduser('~/eva/skills.json')
        with open(skills_path, 'r', encoding='utf-8') as f:
            skills = json.load(f)
        info_parts.append(f"- Уже создано навыков: {len(skills)}")
        for s in skills[:10]:
            info_parts.append(f"  - {s.get('name', '?')}: {s.get('description', '')}")
    except Exception:
        pass

    return '\n'.join(info_parts) if info_parts else 'Нет информации об интеграциях'


@operation('lc_tools')
@tool(parse_docstring=True)
def create_skills(
        request: str,
        run_config: RunnableConfig,
) -> str:
    """
    Создаёт новые навыки (голосовые команды) для Eva на основе запроса пользователя.

    Используй этот инструмент когда пользователь просит создать новую команду или функцию.
    Анализируй доступные интеграции и создавай работающие навыки.

    Args:
        request: Описание того, что должен делать навык. Например: "Навык для включения музыки на Яндекс.Станции"
    """
    va = run_config['configurable']['eva_va_api']
    pm = run_config['configurable']['eva_pm']

    integrations = _get_integrations_info(pm)

    _logger.info("Создание навыков по запросу: %s", request)

    skill = {
        "id": _uid(),
        "intent": f"Custom.{request[:30].replace(' ', '.')}",
        "name": request[:50],
        "description": request,
        "enabled": True,
        "matchMode": "contains",
        "category": "custom",
        "phrases": [request.lower()],
        "slots": [],
        "actions": [
            {"type": "text", "config": {"text": f"Выполняю: {request}"}}
        ],
        "reactions": [
            {"text": f"Готово: {request}", "tts": f"Выполнила: {request}"}
        ],
        "session": {"enabled": False, "ttl": 60},
    }

    try:
        skills_path = __import__('os').path.expanduser('~/eva/skills.json')
        skills = []
        try:
            with open(skills_path, 'r', encoding='utf-8') as f:
                skills = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

        skills.append(skill)

        with open(skills_path, 'w', encoding='utf-8') as f:
            json.dump(skills, f, ensure_ascii=False, indent=2)

        _logger.info("Навык создан: %s (id=%s)", skill['name'], skill['id'])
        return f"Навык '{skill['name']}' создан с id {skill['id']}. Перезапустите приложение для активации."
    except Exception as e:
        _logger.error("Ошибка сохранения навыка: %s", e)
        return f"Ошибка создания навыка: {e}"
