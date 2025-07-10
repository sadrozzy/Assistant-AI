import re
from typing import Dict, Any, Optional

DATE_PATTERN = (
    r'\b('
    r'\d{1,2}[./]\d{1,2}'  # 21.04, 21/04
    r'|сегодня|сёдня|сёд|сев'
    r'|завтра|завтр|зав'
    r'|послезавтра|посл|поз|позав'
    r'|понедельник|пн'
    r'|вторник|вт'
    r'|среда|ср'
    r'|четверг|чт'
    r'|пятница|пт'
    r'|суббота|сб'
    r'|воскресенье|вс'
    r'|monday|mon'
    r'|tuesday|tue'
    r'|wednesday|wed'
    r'|thursday|thu'
    r'|friday|fri'
    r'|saturday|sat'
    r'|sunday|sun'
    r'|today'
    r'|tomorrow'
    r'|aftertomorrow'
    r')\b'
)

PATTERN = re.compile(
    r'(?P<reminder>!\d+\s*[мчдmhd])|'
    r'(?P<duration>\d+\s*[чмhm])|'
    r'(?P<date>' + DATE_PATTERN + r')|'
    r'(?P<time>\b\d{1,2}[:\-]\d{2}\b)',
    re.IGNORECASE
)

def parse_task_text(text: str) -> Dict[str, Optional[int]]:
    """
    Парсит текст задачи и извлекает:
    - дату (21.04, 21/04, сегодня, завтра, послезавтра, дни недели, сокращения)
    - время (14:00, 14-00)
    - длительность (1ч, 30м) -> int минут
    - напоминание (!15м, !1ч, !1д) -> int минут
    Возвращает словарь с найденными параметрами и очищенным текстом задачи.
    """
    result = {
        'date': None,
        'time': None,
        'duration': None,  # int минут
        'reminder': None,  # int минут (будет использоваться как remind_at)
        'clean_text': text,
    }
    clean_text = text

    # --- Напоминание ---
    reminder_pattern = r'!(\d+)\s*(м|ч|д|m|h|d)'
    match = re.search(reminder_pattern, clean_text, re.IGNORECASE)
    if match:
        value, unit = int(match.group(1)), match.group(2).lower()
        if unit in ['м', 'm']:
            minutes = value
        elif unit in ['ч', 'h']:
            minutes = value * 60
        elif unit in ['д', 'd']:
            minutes = value * 1440
        else:
            minutes = None
        result['reminder'] = minutes
        clean_text = clean_text.replace(match.group(0), '').strip()

    # --- Длительность ---
    duration_pattern = r'(\d+)\s*(ч|м|h|m)'
    match = re.search(duration_pattern, clean_text, re.IGNORECASE)
    if match:
        value, unit = int(match.group(1)), match.group(2).lower()
        if unit in ['м', 'm']:
            minutes = value
        elif unit in ['ч', 'h']:
            minutes = value * 60
        else:
            minutes = None
        result['duration'] = minutes
        clean_text = clean_text.replace(match.group(0), '').strip()

    # --- Время ---
    time_pattern = r'\b\d{1,2}[:\-]\d{2}\b'
    match = re.search(time_pattern, clean_text)
    if match:
        result['time'] = match.group(0)
        clean_text = clean_text.replace(match.group(0), '').strip()

    # --- Дата ---
    date_pattern = DATE_PATTERN
    match = re.search(date_pattern, clean_text, re.IGNORECASE)
    if match:
        result['date'] = match.group(0)
        clean_text = clean_text.replace(match.group(0), '').strip()

    result['clean_text'] = re.sub(r'\s+', ' ', clean_text).strip()
    return result 