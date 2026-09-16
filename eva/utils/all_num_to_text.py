# MIT License
# Janvarev Vladislav
#
# library for translate all digits in text to pronounce

import re
from logging import getLogger

_logger = getLogger('all_num_to_text')

try:
    from lingua_franca.format import pronounce_number  # type: ignore
except ImportError:
    pronounce_number = None  # type: ignore
    _logger.warning(
        "lingua-franca не установлен, числа озвучиваются встроенным num_to_text_ru")


def _fallback_pronounce(num: float) -> str:
    from eva.utils.num_to_text_ru import num2text
    if float(num).is_integer():
        return str(num2text(int(num)))
    int_part, _, frac_part = str(num).partition('.')
    int_words = str(num2text(int(int_part))) if int_part not in ('', '-') else ''
    prefix = 'минус ' if str(num).startswith('-') else ''
    digits = ' '.join(str(num2text(int(d))) for d in frac_part if d.isdigit())
    return f"{prefix}{int_words} точка {digits}".strip()


def _say_number(num: float) -> str:
    if pronounce_number is not None:
        try:
            return str(pronounce_number(num))
        except Exception:
            _logger.debug("lingua-franca не смогла произнести %s, использую фолбэк", num)
    return _fallback_pronounce(num)


def load_language(lang: str):
    import lingua_franca  # type: ignore
    lingua_franca.load_language(lang)


def convert_one_num_float(match_obj):
    if match_obj.group() is not None:
        text = str(match_obj.group())
        return _say_number(float(match_obj.group()))
    return ''


def convert_diapazon(match_obj):
    if match_obj.group() is not None:
        text = str(match_obj.group())
        text = text.replace("-", " тире ")
        return all_num_to_text(text)


def all_num_to_text(text: str) -> str:
    text = re.sub(r'[\d]*[.][\d]+-[\d]*[.][\d]+', convert_diapazon, text)
    text = re.sub(r'-[\d]*[.][\d]+', convert_one_num_float, text)
    text = re.sub(r'[\d]*[.][\d]+', convert_one_num_float, text)
    text = re.sub(r'[\d]-[\d]+', convert_diapazon, text)
    text = re.sub(r'-[\d]+', convert_one_num_float, text)
    text = re.sub(r'[\d]+', convert_one_num_float, text)
    text = text.replace("%", " процентов")
    return text
