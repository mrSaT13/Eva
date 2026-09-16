"""
Загружает модель для движка распознания речи Vosk.

В настройках указывается публичный URL, по которому расположен архив с моделью.
Если файл не был загружен ранее, то он будет загружен при запуске приложения или при изменении конфигурации плагина.
"""

import os
import tempfile
import zipfile
from functools import cache, lru_cache
from hashlib import md5
from logging import getLogger
from os.path import basename, dirname, isdir, isfile, join
from shutil import rmtree, move
from typing import Optional, Callable, Any, TypedDict
from urllib.parse import urlparse
from urllib.request import urlretrieve

from eva.plugin_loader.file_patterns import pick_random_file, first_substitution

name = 'vosk_model_loader'
version = '1.0.0'

_logger = getLogger(name)


class _Config(TypedDict):
    model_origin_url: str
    model_search_paths: list[str]
    model_direct_paths: list[str]
    model_storage_path: str
    model_cache_size: int


config: _Config = {
    "model_origin_url": "https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip",
    "model_search_paths": [
        "{eva_home}/vosk/models/{file_name}",
    ],
    "model_direct_paths": [
        "{eva_home}/vosk/models/vosk-model-small-ru-0.22",
        "{eva_path}/../resources/vosk-models/c611af587fcbdacc16bc7a1c6148916c-vosk-model-small-ru-0.22/vosk-model-small-ru-0.22",
        "{eva_path}/../resources/vosk-models/dist/model",
    ],
    "model_storage_path": "{eva_home}/vosk/models/{file_name}",
    "model_cache_size": 1,
}


def _download_model() -> str:
    raw_url: str = config['model_origin_url']
    parsed_url = urlparse(raw_url)
    file_basename = f'{md5(raw_url.encode("utf-8")).hexdigest()}-{basename(parsed_url.path)}'
    try:
        return pick_random_file(config['model_search_paths'], override_vars=dict(file_name=file_basename))
    except FileNotFoundError:
        _logger.info(
            f"Файл модели '{file_basename}' не найден. Пытаюсь скачать.")

    target_path = first_substitution(
        config['model_storage_path'], override_vars=dict(file_name=file_basename))
    os.makedirs(dirname(target_path), exist_ok=True)

    urlretrieve(raw_url, target_path)

    _logger.info(f"Файл модели загружен в {target_path}")

    return target_path


_model_path: Optional[str] = None
_all_model_paths: list[str] = []


def _is_valid_model(path: str) -> bool:
    if not isdir(path):
        return False
    if isfile(join(path, 'conf', 'model.conf')):
        return True
    if isfile(join(path, 'am-onnx', 'encoder.onnx')) or isfile(join(path, 'am-onnx', 'encoder.int8.onnx')):
        return True
    if isfile(join(path, 'lang', 'bpe.model')):
        return True
    return False


def receive_config(*_args, **_kwargs):
    global _model_path, _all_model_paths

    _all_model_paths = []
    for direct_path_pattern in config.get('model_direct_paths', []):
        try:
            path = first_substitution(direct_path_pattern)
            if _is_valid_model(path):
                _all_model_paths.append(path)
                if _model_path is None:
                    _model_path = path
                    _logger.info("Найдена извлечённая модель: %s", path)
        except (ValueError, FileNotFoundError):
            pass

    if _model_path is None:
        _model_path = _download_model()


def get_vosk_model_local_path(*_args, **_kwargs) -> Optional[str]:
    return _model_path


def _get_extraction_path_for_archive(archive_path: str) -> str:
    return archive_path + '.extracted'


def _find_model(zip_info: list[zipfile.ZipInfo]) -> Optional[zipfile.ZipInfo]:
    for entry in zip_info:
        def has_sub_path(p: str) -> bool:
            return any(it.filename == (entry.filename + p) for it in zip_info)

        if entry.is_dir() and (
            (has_sub_path('am/final.mdl') and
             has_sub_path('graph/phones/word_boundary.int') and
             has_sub_path('conf/model.conf')) or
            (has_sub_path('am-onnx/encoder.onnx')) or
            (has_sub_path('lang/bpe.model'))
        ):
            return entry

    return None


def get_extracted_vosk_model_path(*args, **kwargs) -> Optional[str]:
    archive_path = get_vosk_model_local_path(*args, **kwargs)

    if archive_path is None:
        return None

    extracted_path = _get_extraction_path_for_archive(archive_path)

    if isdir(extracted_path):
        if os.stat(extracted_path).st_mtime >= os.stat(archive_path).st_mtime:
            _logger.debug("Похоже, архив %s уже извлечён в %s",
                          archive_path, extracted_path)
            return extracted_path
        else:
            try:
                rmtree(extracted_path)
            except FileNotFoundError:
                pass

    if not isfile(archive_path) or os.path.getsize(archive_path) == 0:
        _logger.warning("Архив модели не найден или повреждён: %s", archive_path)
        return None

    try:
        with zipfile.ZipFile(archive_path, 'r') as zip_file:
            model_entry = _find_model(zip_file.filelist)

            if model_entry is None:
                _logger.error(
                    "Не удалось найти модель в архиве %s", archive_path)
                return None

            with tempfile.TemporaryDirectory() as temp_dir:
                for entry in zip_file.filelist:
                    if entry.filename.startswith(model_entry.filename):
                        zip_file.extract(entry, temp_dir)

                move(join(temp_dir, model_entry.filename), extracted_path)

        return extracted_path
    except Exception:
        try:
            rmtree(extracted_path)
        except FileNotFoundError:
            pass
        raise


@cache
def _get_model_loader() -> Callable[[str], Optional[Any]]:
    cache_size: Optional[int] = config['model_cache_size']

    @lru_cache(maxsize=cache_size)
    def _load_vosk_model(path: str):
        if isfile(join(path, 'am-onnx', 'encoder.int8.onnx')) or isfile(join(path, 'am-onnx', 'encoder.onnx')):
            return _load_sherpa_model(path)

        try:
            from vosk import Model
        except ImportError:
            _logger.error("Пакет vosk не установлен")
            return None

        try:
            model = Model(path)
        except Exception:
            _logger.exception("Ошибка при загрузке модели vosk из %s", path)
            return None

        return model

    return _load_vosk_model


class _SherpaModel:
    def __init__(self, recognizer):
        self._recognizer = recognizer

    def CreateRecognizer(self, sample_rate: int):
        return _SherpaRecognizer(self._recognizer, sample_rate)


class _SherpaRecognizer:
    def __init__(self, recognizer, sample_rate: int):
        import sherpa_onnx
        self._stream = recognizer.create_stream()
        self._recognizer = recognizer

    def AcceptWaveform(self, samples) -> bool:
        import numpy as np
        import struct
        if isinstance(samples, bytes):
            audio = np.frombuffer(samples, dtype=np.int16).astype(np.float32) / 32768.0
        else:
            audio = samples
        self._stream.accept_waveform(self._recognizer.config.model_config.sample_rate, audio)
        self._recognizer.decode_stream(self._stream)
        return self._stream.is_ready()

    def Result(self) -> str:
        import json
        result = self._stream.result
        return json.dumps({"text": result.text.strip()})

    def PartialResult(self) -> str:
        import json
        result = self._stream.result
        return json.dumps({"partial": result.text.strip()})

    def Reset(self):
        self._stream = self._recognizer.create_stream()

    def FinalResult(self) -> str:
        return self.Result()


def _load_sherpa_model(path: str):
    try:
        import sherpa_onnx
    except ImportError:
        _logger.error("Пакет sherpa-onnx не установлен")
        return None

    try:
        encoder = join(path, 'am-onnx', 'encoder.int8.onnx')
        decoder = join(path, 'am-onnx', 'decoder.int8.onnx')
        joiner = join(path, 'am-onnx', 'joiner.int8.onnx')
        tokens = join(path, 'lang', 'tokens.txt')

        if not isfile(encoder):
            encoder = join(path, 'am-onnx', 'encoder.onnx')
        if not isfile(decoder):
            decoder = join(path, 'am-onnx', 'decoder.onnx')
        if not isfile(joiner):
            joiner = join(path, 'am-onnx', 'joiner.onnx')

        if not (isfile(encoder) and isfile(decoder) and isfile(joiner) and isfile(tokens)):
            _logger.warning("Не найдены все файлы ONNX модели в %s", path)
            return None

        recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
            encoder=encoder,
            decoder=decoder,
            joiner=joiner,
            tokens=tokens,
            num_threads=2,
            sample_rate=16000,
            enable_endpoint_detection=True,
            rule1_min_trailing_silence=2.4,
            rule2_min_trailing_silence=1.2,
            rule3_min_utterance_length=20.0,
        )
        _logger.info("Загружена ONNX модель через sherpa-onnx: %s", path)
        return _SherpaModel(recognizer)
    except Exception:
        _logger.warning("Sherpa-onnx не поддерживает модель из %s, пропускаю", path)
        return None


def get_vosk_model(nxt, prev, *args, **kwargs):
    if prev is None:
        for model_path in _all_model_paths:
            model = _get_model_loader()(model_path)
            if model is not None:
                prev = model
                break

    return nxt(
        prev,
        *args, **kwargs,
    )
