import os
import sys
from importlib.util import spec_from_file_location, module_from_spec
from inspect import isclass
from logging import getLogger
from os.path import isfile, basename, splitext
from types import ModuleType
from typing import Optional, TypedDict, Iterable

from eva.plugin_loader.abc import PluginManager, Plugin, OperationStep
from eva.plugin_loader.errors import PluginExcludedException
from eva.plugin_loader.file_patterns import match_files, substitute_patterns
from eva.plugin_loader.magic_plugin import MagicPlugin, after, step_name, operation, MagicModulePlugin
from eva.plugin_loader.run_operation import call_until_first_result, call_all


class PluginDiscoveryPlugin(MagicPlugin):
    name = 'discover_plugins'
    version = '1.0.2'

    _logger = getLogger(name)

    class _Config(TypedDict):
        pluginPaths: list[str]
        appendPythonPath: list[str]
        excludePlugins: list[str]

    config: _Config = {
        'pluginPaths': [
            "{eva_path}/embedded_plugins/plugin_*.py",
            "{python_path}/irene_plugin_*/plugin_*.py",
            "{eva_home}/plugins/plugin_*.py",
            "{eva_home}/plugins/*/plugin_*.py",
        ],
        'appendPythonPath': [
            "{eva_home}/plugins",
            "{eva_home}/deps",
        ],
        "excludePlugins": []
    }

    config_comment = """
    Настройки поиска и загрузки пользовательских плагинов.

    Доступные параметры:
    - `pluginPaths`       - шаблоны путей файлов плагинов
    - `appendPythonPath`  - шаблоны путей папок, которые будут добавлены в PYTHONPATH.
                            Если зависимости плагинов ставятся в папку, не находящуюся в PYTHONPATH, то путь к этой
                            папке нужно указать здесь.
    - `excludePlugins`    - список плагинов, которые загружать не нужно. См. далее.
    
    ## Отключение плагинов

    Для отключения плагина, в excludePlugins можно указать:

    - имя файла плагина, с расширением (например, plugin_tts_cache.py) или без (например, plugin_tts_cache).
      При возможности, стоит использовать этот способ т.к. в этом случае файл плагина не будет импортирован, что ускорит
      загрузку всего приложения.
    - имя плагина, как указано в его переменной name (например, tts_cache)
    - имя плагина с версией (например, tts_cache@0.2.0).
      Такой вариант можно использовать чтобы отключить стандартную версию плагина, положив свою версию в одну из папок,
      указанных в pluginPaths.
    """

    def __init__(self) -> None:
        super().__init__()
        self._plugins: list[Plugin] = []
        self._excluded: set[str] = set()

    def receive_config(self, config, *_args, **_kwargs):
        self._excluded = set(config['excludePlugins'])

    def get_operation_steps(self, op_name: str) -> Iterable[OperationStep]:
        for plugin in self._plugins:
            yield from plugin.get_operation_steps(op_name)

        yield from super().get_operation_steps(op_name)

    @after('config')
    def bootstrap(self, pm: PluginManager, *_args, **_kwargs):
        sys.path.extend(substitute_patterns(self.config['appendPythonPath']))

        plugin_discover_op = list(
            pm.get_operation_sequence('discover_plugins_at_path'))
        plugin_discovered_op = list(
            pm.get_operation_sequence('plugin_discovered'))

        for plugin_path in match_files(self.config['pluginPaths']):
            try:
                plugins: Optional[Iterable[Plugin]] = call_until_first_result(
                    plugin_discover_op, pm, plugin_path)
            except PluginExcludedException:
                self._logger.info(
                    "Плагин из файла %s отключён",
                    plugin_path,
                )
                continue
            except ImportError as e:
                self._logger.warning(
                    "Плагин %s не загружен: не установлена зависимость %s. "
                    "Установите: pip install %s",
                    plugin_path, str(e), str(e).split("'")[-2] if "'" in str(e) else str(e)
                )
                continue
            except Exception as e:
                self._logger.warning(
                    "Плагин %s не загружен: %s",
                    plugin_path, e
                )
                continue

            if plugins is None:
                self._logger.warning(
                    "Не удалось загрузить плагин из %s",
                    plugin_path
                )
                continue

            for plugin in plugins:
                if plugin.name in self._excluded or str(plugin) in self._excluded:
                    continue

                self._logger.debug(
                    "Найден плагин %s в файле %s",
                    plugin, plugin_path
                )

                self._plugins.append(plugin)
                call_all(plugin_discovered_op, pm, plugin)

    @step_name('discover_python_module')
    def discover_plugins_at_path(self, pm: PluginManager, path: str, *_args, **_kwargs):
        if not isfile(path):
            return

        if not path.endswith('.py'):
            return

        file_basename = basename(path)

        if file_basename in self._excluded:
            raise PluginExcludedException()

        module_name = splitext(file_basename)[0]

        if module_name in self._excluded:
            raise PluginExcludedException()

        spec = spec_from_file_location(
            module_name,
            path,
        )

        if spec is None or spec.loader is None:
            self._logger.warning(
                "Не удалось загрузить модуль плагина %s - не удалось создать спецификацию модуля",
                path
            )
            return

        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        return call_until_first_result(pm.get_operation_sequence('discover_plugins_in_module'), pm, module)

    @step_name('discover_explicit_plugins')
    def discover_plugins_in_module(self, pm: PluginManager, module: ModuleType, *_args, **_kwargs):
        found = []
        excluded = 0
        attrs = getattr(module, '__all__', dir(module))

        for attr in attrs:
            value = getattr(module, attr, None)

            if isinstance(value, Plugin):
                found.append(value)
            elif isclass(value) and \
                    issubclass(value, Plugin) and \
                    getattr(value, '__module__', module.__name__) == module.__name__:
                if getattr(value, 'name', None) in self._excluded:
                    excluded = excluded + 1
                    continue

                found.append(value())

        if len(found) > 0:
            return found

        if excluded > 0:
            raise PluginExcludedException()

    @operation('discover_plugins_in_module')
    @step_name('discover_magic_plugin_module')
    @after('discover_explicit_plugins')
    def discover_magic_plugin_module(self, _pm: PluginManager, module: ModuleType, *_args, **_kwargs):
        name = getattr(module, 'name', None)

        if not isinstance(name, str):
            return None

        version = getattr(module, 'version', None)

        if not isinstance(version, str):
            return None

        return MagicModulePlugin(module),

    def register_fastapi_endpoints(self, router, *_args, **_kwargs) -> None:
        from fastapi import APIRouter, UploadFile, HTTPException
        from pydantic import BaseModel, Field

        r: APIRouter = router

        def _safe_plugin_path(plugins_dir: str, filename: str) -> str:
            # Защита от path traversal: только basename, только plugin_*.py
            import os
            base = os.path.basename(filename or '')
            if not base.endswith('.py'):
                base += '.py'
            if not base.startswith('plugin_'):
                raise HTTPException(status_code=400, detail="Имя файла должно начинаться с plugin_ и заканчиваться .py")
            if '/' in filename or '\\' in filename or '..' in filename:
                raise HTTPException(status_code=400, detail="Недопустимое имя файла")
            full = os.path.abspath(os.path.join(plugins_dir, base))
            if os.path.commonpath([full, os.path.abspath(plugins_dir)]) != os.path.abspath(plugins_dir):
                raise HTTPException(status_code=400, detail="Недопустимый путь")
            return full

        def _parse_plugin_meta(source: str) -> dict:
            import re
            import ast
            meta = {}
            m = re.search(r"^name\s*=\s*['\"](.+?)['\"]", source, re.MULTILINE)
            if m:
                meta['name'] = m.group(1)
            m = re.search(r"^version\s*=\s*['\"](.+?)['\"]", source, re.MULTILINE)
            if m:
                meta['version'] = m.group(1)
            doc_match = re.search(r'^"""(.+?)"""', source, re.DOTALL)
            if not doc_match:
                doc_match = re.search(r"^'''(.+?)'''", source, re.DOTALL)
            if doc_match:
                meta['description'] = doc_match.group(1).strip()[:300]
            else:
                meta['description'] = ''
            commands = []
            cmd_block = re.search(r'define_commands\s*=\s*\{(.+?)\}', source, re.DOTALL)
            if cmd_block:
                for line in cmd_block.group(1).splitlines():
                    km = re.match(r'\s*["\'](.+?)["\']', line)
                    if km:
                        keys = [k.strip() for k in km.group(1).split('|') if k.strip()]
                        commands.extend(keys)
            meta['commands'] = commands[:30]
            config_fields = []
            config_block = re.search(r'config\s*=\s*\{(.+?)\n\}', source, re.DOTALL)
            if config_block:
                try:
                    raw = '{' + config_block.group(1) + '}'
                    raw = re.sub(r'#.*$', '', raw, flags=re.MULTILINE)
                    raw = raw.replace('None', '"None"')
                    parsed = ast.literal_eval(raw)

                    ru_labels = {
                        'enabled': 'Включён', 'music_folder': 'Папка с музыкой',
                        'ha_url': 'URL Home Assistant', 'ha_token': 'Токен HA',
                        'ha_entity_id': 'Устройство HA', 'min_similarity': 'Мин. схожесть',
                        'min_score': 'Мин. оценка', 'min_score_diff': 'Мин. разница оценок',
                        'use_intro_phrases': 'Фразы-интро', 'notify_ha_errors': 'Уведомления об ошибках',
                        'wiki_plugin_name': 'Плагин Wiki', 'max_artists_in_stats': 'Макс. артистов в статистике',
                        'min_artist_score': 'Мин. оценка артиста', 'min_track_score': 'Мин. оценка трека',
                        'auto_rescan_interval_minutes': 'Авто-пересканирование (мин)',
                        'auto_scan_enabled': 'Авто-сканирование', 'auto_scan_interval_hours': 'Интервал сканирования (час)',
                        'ma_ip': 'IP Music Assistant', 'ma_port': 'Порт Music Assistant',
                        'ma_token': 'Токен Music Assistant',
                        'enable_confirmation_flow': 'Подтверждение действий',
                        'enable_learning_cache': 'Кэш обучения',
                        'model_storage_path': 'Путь хранения моделей',
                        'model_origin_url': 'URL модели', 'model_cache_size': 'Размер кэша',
                        'wavPath': 'Путь к звуку', 'wavRepeatTimes': 'Повторений звука',
                        'notify_sound': 'Звуковое оповещение', 'notify_text': 'Текст оповещения',
                        'notify_services': 'Уведомления в сервисы',
                        'poll_interval': 'Интервал опроса (сек)',
                        'weather_city': 'Город для погоды', 'cache_ttl': 'Время кэша (сек)',
                        'rss_feeds': 'RSS ленты',
                        'freshrss_url': 'URL FreshRSS', 'freshrss_user': 'Пользователь FreshRSS',
                        'freshrss_token': 'Токен FreshRSS',
                        'navidrome_url': 'URL Navidrome', 'navidrome_user': 'Пользователь Navidrome',
                        'navidrome_password': 'Пароль Navidrome',
                    }
                    for key, val in parsed.items():
                        if isinstance(val, (dict, list)):
                            continue
                        config_fields.append({
                            "key": key,
                            "label": ru_labels.get(key.lower(), key),
                            "value": str(val),
                            "type": "bool" if isinstance(val, bool) else "number" if isinstance(val, (int, float)) else "text"
                        })
                except Exception:
                    pass
            meta['config_fields'] = config_fields
            return meta

        class PluginModel(BaseModel):
            name: str = Field(
                title="Имя плагина",
            )
            version: str = Field(
                title="Версия плагина",
            )
            docs: Optional[str] = Field(
                title="Документация плагина",
                description="Извлекается из docstring'а класса или модуля плагина",
            )

        @r.get(
            '/plugins',
            response_model=list[PluginModel],
            name="Получение списка всех пользовательских плагинов",
        )
        def list_all_user_plugins():
            """
            Возвращает список всех плагинов с их краткими описаниями.
            """
            return [
                PluginModel(
                    name=plugin.name,
                    version=plugin.version,
                    docs=getattr(plugin, '__doc__', None)
                ) for plugin in self._plugins
            ]

        @r.post('/plugins/upload')
        async def upload_plugin(file: UploadFile):
            import os
            import sys
            from eva.plugin_loader.file_patterns import first_substitution
            try:
                plugins_dir = first_substitution('{eva_home}/plugins')
                os.makedirs(plugins_dir, exist_ok=True)
                content = await file.read()
                if len(content) > 512 * 1024:
                    return {"status": "error", "error": "Файл слишком большой (лимит 512KB)"}
                content_str = content.decode('utf-8', errors='replace')
                target = _safe_plugin_path(plugins_dir, file.filename or 'plugin.py')
                filename = os.path.basename(target)
                with open(target, 'wb') as f:
                    f.write(content)

                missing = []
                for line in content_str.splitlines():
                    line = line.strip()
                    if line.startswith('import ') or line.startswith('from '):
                        parts = line.split()
                        if 'import' in parts:
                            idx = parts.index('import')
                            mod = parts[idx + 1].split('.')[0].split(',')[0]
                            if mod not in ('os', 'sys', 'json', 'time', 're', 'asyncio', 'logging',
                                           'datetime', 'typing', 'collections', 'functools', 'hashlib',
                                           'urllib', 'pathlib', 'io', 'math', 'random', 'uuid', 'abc',
                                           'dataclasses', 'enum', 'traceback', 'inspect', 'textwrap',
                                           'string', 'struct', 'base64', 'copy', 'itertools', 'operator',
                                           'contextlib', 'shutil', 'tempfile', 'threading', 'socket',
                                           'ctypes', 'array', 'wave', 'struct', 'codecs'):
                                try:
                                    __import__(mod)
                                except ImportError:
                                    missing.append(mod)

                installed = []
                # Авто-установка pip-пакетов из загруженного кода отключена (RCE-вектор).
                # Только сообщаем о недостающих модулях — ставит их администратор вручную.
                if missing:
                    self._logger.warning("Загружен плагин %s, отсутствуют модули: %s", filename, missing)

                return {"status": "ok", "filename": filename, "path": target, "missing": missing, "installed": installed,
                        "note": "Авто-установка зависимостей отключена. Установите недостающие пакеты вручную и перезапустите."}
            except Exception as e:
                return {"status": "error", "error": str(e)}

        @r.get('/plugins/user')
        async def list_user_plugins():
            import os
            import re
            from eva.plugin_loader.file_patterns import first_substitution
            plugins_dir = first_substitution('{eva_home}/plugins')
            result = []
            if os.path.isdir(plugins_dir):
                for f in sorted(os.listdir(plugins_dir)):
                    if f.endswith('.py') and f.startswith('plugin_'):
                        full = os.path.join(plugins_dir, f)
                        size = os.path.getsize(full)
                        mtime = os.path.getmtime(full)
                        import datetime
                        dt = datetime.datetime.fromtimestamp(mtime).strftime('%d.%m.%Y %H:%M')
                        try:
                            with open(full, 'r', encoding='utf-8', errors='replace') as fh:
                                source = fh.read()
                            meta = _parse_plugin_meta(source)
                        except Exception:
                            source = ''
                            meta = {}
                        result.append({
                            "filename": f,
                            "display_name": meta.get('name', f[7:-3] if f.startswith('plugin_') else f[:-3]),
                            "version": meta.get('version', ''),
                            "description": meta.get('description', ''),
                            "commands": meta.get('commands', []),
                            "config_fields": meta.get('config_fields', []),
                            "size": size,
                            "modified": dt,
                            "path": full,
                        })
            return result

        @r.get('/plugins/user/{filename}')
        async def get_user_plugin(filename: str):
            import os
            from eva.plugin_loader.file_patterns import first_substitution
            plugins_dir = first_substitution('{eva_home}/plugins')
            full = _safe_plugin_path(plugins_dir, filename)
            if not os.path.isfile(full):
                return {"error": "File not found"}
            with open(full, 'r', encoding='utf-8', errors='replace') as f:
                return {"filename": os.path.basename(full), "source": f.read()}

        @r.put('/plugins/user/{filename}')
        async def update_user_plugin(filename: str, body: dict):
            import os
            from eva.plugin_loader.file_patterns import first_substitution
            plugins_dir = first_substitution('{eva_home}/plugins')
            full = _safe_plugin_path(plugins_dir, filename)
            if not os.path.isfile(full):
                return {"error": "File not found"}
            source = body.get('source', '')
            if len(source) > 512 * 1024:
                return {"error": "Файл слишком большой (лимит 512KB)"}
            with open(full, 'w', encoding='utf-8') as f:
                f.write(source)
            return {"status": "ok", "message": "Plugin updated. Restart to apply."}

        @r.delete('/plugins/user/{filename}')
        async def delete_user_plugin(filename: str):
            import os
            from eva.plugin_loader.file_patterns import first_substitution
            plugins_dir = first_substitution('{eva_home}/plugins')
            full = _safe_plugin_path(plugins_dir, filename)
            if os.path.isfile(full):
                os.remove(full)
            return {"status": "ok"}
