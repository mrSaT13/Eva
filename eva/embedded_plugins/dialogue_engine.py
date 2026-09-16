"""
Движок выполнения диалоговых навыков Eva.

Реализует пошаговые сценарии с блоками, переменными и интентами.
"""

import json
import os
import tempfile
import threading
import time
import logging
from typing import Any, Optional

_logger = logging.getLogger('eva_skills')


def _sessions_file() -> str:
    # Уважаем EVA_HOME, иначе сессии падают в ~/eva в обход конфига
    base = os.environ.get('EVA_HOME', os.path.expanduser('~/eva'))
    return os.path.join(base, 'dialogue_sessions.json')


_SESSIONS_FILE = os.path.expanduser('~/eva/dialogue_sessions.json')


class DialogueSession:
    def __init__(self, skill_id: str, user_id: str = 'default'):
        self.skill_id = skill_id
        self.user_id = user_id
        self.current_block: str = 'start'
        self.variables: dict[str, Any] = {}
        self.finished = False

    def to_dict(self) -> dict:
        return {
            'skill_id': self.skill_id,
            'user_id': self.user_id,
            'current_block': self.current_block,
            'variables': self.variables,
            'finished': self.finished,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'DialogueSession':
        s = cls(data['skill_id'], data.get('user_id', 'default'))
        s.current_block = data.get('current_block', 'start')
        s.variables = data.get('variables', {})
        s.finished = data.get('finished', False)
        return s


class DialogueEngine:
    def __init__(self):
        self._sessions: dict[str, DialogueSession] = {}
        self._lock = threading.Lock()
        self._sessions_file = _sessions_file()
        self._load_sessions()

    def _load_sessions(self):
        try:
            if os.path.exists(self._sessions_file):
                with open(self._sessions_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for key, sdata in data.items():
                    self._sessions[key] = DialogueSession.from_dict(sdata)
        except Exception:
            _logger.exception("Не удалось загрузить сессии диалогов из %s", self._sessions_file)

    def _save_sessions(self):
        try:
            path = self._sessions_file
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with self._lock:
                snapshot = {k: v.to_dict() for k, v in self._sessions.items()}
            fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix='.tmp')
            try:
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    json.dump(snapshot, f, ensure_ascii=False, indent=2)
                os.replace(tmp, path)
            except BaseException:
                try:
                    os.remove(tmp)
                except OSError:
                    pass
                raise
        except Exception as e:
            _logger.error("Ошибка сохранения сессий: %s", e)

    def _session_key(self, skill_id: str, user_id: str) -> str:
        return f"{skill_id}:{user_id}"

    def get_session(self, skill_id: str, user_id: str = 'default') -> Optional[DialogueSession]:
        key = self._session_key(skill_id, user_id)
        with self._lock:
            return self._sessions.get(key)

    def create_session(self, skill_id: str, user_id: str = 'default') -> DialogueSession:
        key = self._session_key(skill_id, user_id)
        session = DialogueSession(skill_id, user_id)
        with self._lock:
            self._sessions[key] = session
        self._save_sessions()
        return session

    def process_step(self, skill: dict, session: DialogueSession, user_input: str = '') -> dict:
        dialogue = skill.get('dialogue', {})
        blocks = {b['id']: b for b in dialogue.get('steps', [])}
        exit_phrases = dialogue.get('exit_phrases', ['хватит', 'стоп', 'пока', 'выйти'])
        block_id = session.current_block
        block = blocks.get(block_id)

        if not block or session.finished:
            session.finished = True
            self._save_sessions()
            return {'text': 'Сценарий завершён.', 'end_session': True}

        lower = user_input.lower().strip()
        if lower in exit_phrases:
            session.finished = True
            self._save_sessions()
            return {'text': 'Хорошо! Если захочешь — обращайся.', 'end_session': True}

        block_type = block.get('type', 'text')
        result = {}

        if block_type in ('text', 'intro'):
            result = self._handle_text(block, session, user_input)
        elif block_type == 'loop':
            result = self._handle_loop(block, session, user_input)
        elif block_type == 'finale':
            result = self._handle_finale(block, session, user_input)
        else:
            result = self._handle_text(block, session, user_input)

        self._save_sessions()
        return result

    def _handle_text(self, block: dict, session: DialogueSession, user_input: str) -> dict:
        import random
        text = block.get('text', '')
        if isinstance(text, list):
            text = random.choice(text)
        text = self._substitute(text, session.variables)

        question = block.get('question', '')
        if question:
            question = self._substitute(question, session.variables)

        if question and not user_input:
            return {'text': f"{text}\n\n{question}", 'question': question}

        if question and user_input:
            save_to = block.get('save_to', 'user_answer')
            session.variables[save_to] = user_input

        next_block = block.get('next', '')
        if next_block:
            session.current_block = next_block

        return {
            'text': text,
            'end_session': block.get('end_session', False),
            'sound': block.get('sound', ''),
        }

    def _handle_loop(self, block: dict, session: DialogueSession, user_input: str) -> dict:
        import random
        save_to = block.get('save_to', 'user_answer')
        if user_input:
            session.variables[save_to] = user_input

        counter_var = block.get('counter_var', '$loop_count')
        count = session.variables.get(counter_var, 0) + 1
        session.variables[counter_var] = count

        template = block.get('template', '{user_answer}')
        text = self._substitute(template, session.variables)

        exit_condition = block.get('exit_condition', '')
        if exit_condition and self._evaluate_condition(exit_condition, session.variables):
            next_block = block.get('next', '')
            session.current_block = next_block
        else:
            next_block = block.get('self_loop', block.get('id', ''))
            session.current_block = next_block

        return {'text': text, 'end_session': block.get('end_session', False)}

    def _handle_finale(self, block: dict, session: DialogueSession, user_input: str) -> dict:
        import random
        text = block.get('text', 'Сценарий завершён.')
        if isinstance(text, list):
            text = random.choice(text)
        text = self._substitute(text, session.variables)
        session.finished = True
        return {
            'text': text,
            'end_session': block.get('end_session', True),
            'sound': block.get('sound', ''),
        }

    def _substitute(self, text: str, variables: dict) -> str:
        result = text
        for key, value in variables.items():
            result = result.replace('{' + key + '}', str(value))
        return result

    def _evaluate_condition(self, condition: str, variables: dict) -> bool:
        if not condition:
            return False
        try:
            expr = condition
            for key, value in variables.items():
                if isinstance(value, (int, float)):
                    expr = expr.replace(key, str(value))
                elif isinstance(value, str) and value.isdigit():
                    expr = expr.replace(key, value)
            return bool(eval(expr, {"__builtins__": {}}, {}))
        except Exception:
            return False


_engine: Optional[DialogueEngine] = None
_engine_lock = threading.Lock()


def get_engine() -> DialogueEngine:
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = DialogueEngine()
    return _engine
