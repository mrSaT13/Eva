"""
Плагин для загрузки и использования VOSK моделей через sherpa-onnx.
"""

import os
import zipfile
import tempfile
from hashlib import md5
from logging import getLogger
from os.path import basename, dirname, isdir, isfile, join
from shutil import rmtree, move
from typing import Optional, Any
from urllib.parse import urlparse
from urllib.request import urlretrieve

from eva.plugin_loader.file_patterns import first_substitution
from eva.plugin_loader.magic_plugin import MagicPlugin

_logger = getLogger('vosk_sherpa')


class VoskSherpaPlugin(MagicPlugin):
    name = 'vosk_sherpa'
    version = '1.0.0'

    config: dict[str, Any] = {
        "models": {
            "vosk-small-ru-0.22": {
                "name": "VOSK Small Russian 0.22",
                "description": "Маленькая модель для русского языка (~50MB)",
                "url": "https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip",
                "size_mb": 50,
                "language": "ru",
            },
            "vosk-ru-0.54": {
                "name": "VOSK Russian 0.54",
                "description": "Новая модель VOSK 0.54 для русского (~200MB)",
                "url": "https://alphacephei.com/vosk/models/vosk-model-ru-0.54.zip",
                "size_mb": 200,
                "language": "ru",
            },
        },
        "model_storage_path": "{eva_home}/vosk/models/{file_name}",
    }

    _download_progress: dict[str, dict[str, Any]] = {}

    def register_fastapi_endpoints(self, router, *_args, **_kwargs):
        from fastapi import APIRouter, HTTPException
        from pydantic import BaseModel

        r: APIRouter = router
        plugin = self

        class DownloadRequest(BaseModel):
            model_id: str

        @r.get('/models')
        async def list_models():
            result = []
            for model_id, info in plugin.config['models'].items():
                path = plugin.get_model_path(model_id)
                progress = plugin._download_progress.get(model_id, {})
                result.append({
                    "id": model_id,
                    "name": info['name'],
                    "description": info['description'],
                    "size_mb": info['size_mb'],
                    "language": info['language'],
                    "installed": path is not None,
                    "path": path,
                    "progress": progress,
                })
            return result

        @r.post('/models/download')
        async def download_model_endpoint(req: DownloadRequest):
            if req.model_id not in plugin.config['models']:
                raise HTTPException(404, f"Модель {req.model_id} не найдена")
            path = plugin.get_model_path(req.model_id)
            if path:
                return {"status": "already_installed", "path": path}
            import asyncio
            loop = asyncio.get_event_loop()
            loop.run_in_executor(None, plugin.download_model, req.model_id)
            return {"status": "downloading"}

        @r.get('/models/progress')
        async def get_progress():
            return plugin._download_progress.copy()

    def get_model_path(self, model_id: str) -> Optional[str]:
        """Возвращает путь к модели или None если не найдена."""
        if model_id not in self.config['models']:
            return None
        model_info = self.config['models'][model_id]
        file_basename = f'{md5(model_info["url"].encode("utf-8")).hexdigest()}-{basename(urlparse(model_info["url"]).path)}'
        
        search_paths = [
            '{eva_home}/vosk/models/{file_name}',
            '{eva_home}/vosk/models/vosk-model-small-ru-0.22',
            '{eva_home}/vosk/models/vosk-model-ru-0.54',
            '{eva_home}/vosk/models/vosk-model-small-en-us-0.15',
            '{eva_path}/../resources/vosk-models/c611af587fcbdacc16bc7a1c6148916c-vosk-model-small-ru-0.22/vosk-model-small-ru-0.22',
        ]
        
        for search_path in search_paths:
            try:
                path = first_substitution(search_path, override_vars=dict(file_name=file_basename))
                if isdir(path):
                    return path
                if isfile(path):
                    return path
                zip_path = path if path.endswith('.zip') else path + '.zip'
                if isfile(zip_path):
                    return zip_path
            except (ValueError, FileNotFoundError):
                pass
        
        return None

    def download_model(self, model_id: str) -> Optional[str]:
        if model_id not in self.config['models']:
            return None
        model_info = self.config['models'][model_id]
        url = model_info['url']
        file_basename = f'{md5(url.encode("utf-8")).hexdigest()}-{basename(urlparse(url).path)}'
        
        # Проверяем, не скачана ли уже модель
        existing = self.get_model_path(model_id)
        if existing:
            _logger.info("Модель %s уже загружена: %s", model_id, existing)
            return existing
        
        zip_path = first_substitution(self.config['model_storage_path'], override_vars=dict(file_name=file_basename))
        
        # Проверяем, не скачан ли zip
        if isfile(zip_path) and os.path.getsize(zip_path) > 0:
            _logger.info("Zip файл модели %s уже существует: %s", model_id, zip_path)
            self._download_progress[model_id] = {"status": "ready", "progress": 100}
            return zip_path
        
        self._download_progress[model_id] = {"status": "downloading", "progress": 0}
        try:
            os.makedirs(dirname(zip_path), exist_ok=True)
            def _hook(block, block_size, total):
                if total > 0:
                    self._download_progress[model_id]["progress"] = min(block * block_size / total * 100, 100)
            urlretrieve(url, zip_path, reporthook=_hook)
            self._download_progress[model_id] = {"status": "ready", "progress": 100}
            _logger.info("Модель %s скачана в %s", model_id, zip_path)
            return zip_path
        except Exception as e:
            self._download_progress[model_id] = {"status": "error", "error": str(e)}
            _logger.exception("Ошибка скачивания модели %s", model_id)
            return None
