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


_TIME_WORDS = {
    'секунд': 1, 'сек': 1, 'с': 1,
    'минут': 60, 'мин': 60, 'м': 60,
    'час': 3600, 'ч': 3600,
}

_HA_ON = ('включи', 'включить', 'открой', 'открыть', 'запусти', 'запустить')
_HA_OFF = ('выключи', 'выключить', 'закрой', 'закрыть', 'останови', 'остановить')

# Русское слово -> домен HA и дружелюбное имя для подбора entity_id
_HA_DOMAINS = (
    (('свет', 'ламп', 'люстр', 'подсветк'), 'light'),
    (('розетк', 'выключател', 'реле'), 'switch'),
    (('телевизор', 'тв'), 'media_player'),
    (('кондиционер', 'климат'), 'climate'),
    (('штор', 'жалюзи'), 'cover'),
    (('пылесос',), 'vacuum'),
    (('вентилятор',), 'fan'),
)


def _uid() -> str:
    return str(uuid.uuid4())[:8]


def _slug_intent(request: str) -> str:
    import re
    words = re.findall(r'[a-zA-Zа-яА-ЯёЁ0-9]+', request.lower())[:4]
    slug = '.'.join(words) if words else 'custom'
    return f"Custom.{slug}"


def _parse_timer(request: str):
    """Возвращает секунды, если в запросе просьба про таймер/напоминание."""
    import re
    low = request.lower()
    if not any(w in low for w in ('таймер', 'напомни', 'напоминание', 'через', 'будильник')):
        return None
    m = re.search(r'(\d+)\s*(секунд\w*|сек|минут\w*|мин|час\w*|ч)\b', low)
    if not m:
        return None
    amount, unit = int(m.group(1)), m.group(2)
    for key, mult in _TIME_WORDS.items():
        if unit.startswith(key):
            return amount * mult
    return None


def _parse_ha_action(request: str, entities: list[str]):
    """Возвращает (service, entity_id), если запрос похож на управление устройством."""
    low = request.lower()
    turn_on = any(w in low for w in _HA_ON)
    turn_off = any(w in low for w in _HA_OFF)
    if not turn_on and not turn_off:
        return None
    for keywords, domain in _HA_DOMAINS:
        if any(k in low for k in keywords):
            entity_id = _match_entity(low, keywords, entities, domain)
            service = f"{domain}.turn_{'on' if turn_on else 'off'}"
            return service, entity_id
    return None


def _match_entity(low: str, keywords: tuple, entities: list[str], domain: str):
    """Лучшее совпадение entity_id: сначала по словам запроса, потом первый entity домена."""
    import re
    words = [w for w in re.findall(r'[а-яёa-z0-9]+', low) if len(w) > 3]
    domain_ents = [e for e in entities if e.startswith(domain + '.')]
    pool = domain_ents or entities
    for w in words:
        for e in pool:
            if w in e.lower():
                return e
    return pool[0] if pool else None


def _collect_ha_entities(pm) -> list[str]:
    """Entity_id из HA для подбора устройств."""
    entities: list[str] = []
    try:
        ha_url = ha_token = None
        for plugin_name in ('voice_commands', 'automations', 'integrations'):
            p = pm.get_plugin_by_name(plugin_name) if hasattr(pm, 'get_plugin_by_name') else None
            if p is not None:
                cfg = getattr(p, 'config', {}) or {}
                if cfg.get('ha_url'):
                    ha_url, ha_token = cfg['ha_url'], cfg.get('ha_token')
                    break
        if ha_url and ha_token:
            import httpx
            resp = httpx.get(f"{ha_url}/api/states",
                             headers={"Authorization": f"Bearer {ha_token}"}, timeout=10)
            if resp.status_code == 200:
                entities = [s.get('entity_id', '') for s in resp.json() if s.get('entity_id')]
    except Exception as e:
        _logger.warning("Не удалось получить entity HA: %s", e)
    return entities


def _store_skill(pm, skill: dict) -> str:
    """Сохраняет навык через плагин eva_skills (или напрямую в skills.json как fallback)."""
    get_plugin = getattr(pm, 'get_plugin_by_name', None)
    plugin = get_plugin('eva_skills') if callable(get_plugin) else None
    if plugin is not None:
        try:
            skills = plugin.config.setdefault('skills', [])
            skills.append(skill)
            plugin._save_skills()
            return 'plugin'
        except Exception as e:
            _logger.warning("Сохранение через плагин не удалось: %s", e)
    import os
    skills_path = os.path.join(
        os.environ.get('EVA_HOME', os.path.expanduser('~/eva')), 'skills.json')
    skills = []
    try:
        with open(skills_path, 'r', encoding='utf-8') as f:
            skills = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    skills.append(skill)
    os.makedirs(os.path.dirname(skills_path) or '.', exist_ok=True)
    with open(skills_path, 'w', encoding='utf-8') as f:
        json.dump(skills, f, ensure_ascii=False, indent=2)
    return 'file'


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

            # Синхронный запрос: без asyncio.run в пуле (висло при живом event loop)
            resp = httpx.get(
                f"{ha_url}/api/states",
                headers={"Authorization": f"Bearer {ha_token}"},
                timeout=10,
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

    entities = _collect_ha_entities(pm)
    actions: list[dict] = []
    phrases = [request.lower()]
    notes: list[str] = []

    seconds = _parse_timer(request)
    ha_action = _parse_ha_action(request, entities)

    if seconds:
        actions.append({"type": "timer", "config": {"seconds": seconds}})
        actions.append({"type": "text",
                        "config": {"text": f"Таймер на {seconds} секунд запущен"}})
        phrases.append(f"таймер {request.lower()}")
    elif ha_action:
        service, entity_id = ha_action
        if entity_id:
            actions.append({"type": "ha_service",
                            "config": {"service": service, "entity_id": entity_id}})
            what = 'включено' if service.endswith('.turn_on') else 'выключено'
            actions.append({"type": "text",
                            "config": {"text": f"{entity_id}: {what}"}})
        else:
            actions.append({"type": "text", "config": {
                "text": "Подходящее устройство в Home Assistant не найдено. "
                        "Проверьте подключение HA и названия устройств."}})
            notes.append("entity не найден — создан навык-заглушка с подсказкой")
    else:
        actions.append({"type": "text", "config": {"text": f"Выполняю: {request}"}})
        notes.append("намерение не распознано как таймер/HA — создан текстовый навык, "
                     "дополните actions вручную")

    skill = {
        "id": _uid(),
        "intent": _slug_intent(request),
        "name": request[:50],
        "description": request,
        "enabled": True,
        "matchMode": "contains",
        "category": "custom",
        "phrases": phrases,
        "slots": [],
        "actions": actions,
        "reactions": [
            {"text": f"Готово: {request}", "tts": f"Выполнила: {request}"}
        ],
        "session": {"enabled": False, "ttl": 60},
    }

    try:
        via = _store_skill(pm, skill)
        _logger.info("Навык создан: %s (id=%s, via=%s)", skill['name'], skill['id'], via)
        detail = ''
        if ha_action and ha_action[1]:
            detail = f" Действие: {ha_action[0]} -> {ha_action[1]}."
        elif seconds:
            detail = f" Действие: таймер {seconds} сек."
        if notes:
            detail += ' Замечание: ' + '; '.join(notes)
        return (f"Навык '{skill['name']}' создан с id {skill['id']}.{detail} "
                f"Перезапустите приложение для активации.")
    except Exception as e:
        _logger.error("Ошибка сохранения навыка: %s", e)
        return f"Ошибка создания навыка: {e}"
