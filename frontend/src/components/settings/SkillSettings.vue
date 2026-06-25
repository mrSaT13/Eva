<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import AddIcon from '~icons/material-symbols/add';
import DeleteIcon from '~icons/material-symbols/delete';
import EditIcon from '~icons/material-symbols/edit';
import CloseIcon from '~icons/material-symbols/close';
import SaveIcon from '~icons/material-symbols/save';
import CheckIcon from '~icons/material-symbols/check';
import PlayIcon from '~icons/material-symbols/play-arrow';
import HttpIcon from '~icons/material-symbols/cloud';
import PluginIcon from '~icons/material-symbols/extension';
import HomeIcon from '~icons/material-symbols/home';
import TimerIcon from '~icons/material-symbols/timer';
import BotIcon from '~icons/material-symbols/psychology';
import TextIcon from '~icons/material-symbols/chat';
import MacroIcon from '~icons/material-symbols/account-tree';
import StarIcon from '~icons/material-symbols/star';
import SearchIcon from '~icons/material-symbols/search';
import CodeIcon from '~icons/material-symbols/code';
import ConsoleIcon from '~icons/material-symbols/terminal';
import VolumeIcon from '~icons/material-symbols/volume-up';
import GeoIcon from '~icons/material-symbols/location-on';
import NumberIcon from '~icons/material-symbols/numbers';
import BoolIcon from '~icons/material-symbols/toggle-on';
import ListIcon from '~icons/material-symbols/list';
import StringIcon from '~icons/material-symbols/abc';
import DateIcon from '~icons/material-symbols/event';

/* =========================================================
   ТИПЫ
   ========================================================= */

type ActionType = 'http' | 'plugin' | 'ha_service' | 'timer' | 'llm' | 'text' | 'macro';

/** Типы слотов */
type SlotType = 'string' | 'number' | 'date' | 'geo' | 'list' | 'bool';

interface SkillSlot {
    id: string;
    name: string;            // имя переменной, используется в {name}
    type: SlotType;
    required: boolean;
    /** Примеры фраз, обучающие извлечению */
    examples: string[];
    /** Возможные значения для list */
    values?: string[];
    /** Значение по умолчанию */
    defaultValue?: string;
}

interface SkillAction {
    id: string;
    type: ActionType;
    config: Record<string, any>;
}

interface SkillReaction {
    id: string;
    text: string;            // текст для UI/чата
    tts?: string;            // что произнести (с эмоциями/паузами)
    sound?: string;          // звук после ответа
}

interface Skill {
    id: string;
    /** Полное имя интента в стиле "Home.TurnOnLight" / "Weather.Get" */
    intent: string;
    name: string;
    description: string;
    enabled: boolean;
    /** Голосовые фразы со слотами {name} */
    phrases: string[];
    matchMode: 'exact' | 'regex' | 'contains';
    /** Типизированные слоты для извлечения параметров */
    slots: SkillSlot[];
    /** Цепочка действий */
    actions: SkillAction[];
    /** Реакции (одна из них выбирается по ситуации) */
    reactions: SkillReaction[];
    /** Сессионность — можно уточнять в несколько шагов */
    session: {
        enabled: boolean;
        ttl: number;     // секунды, сколько держать сессию
    };
    category: 'utility' | 'home' | 'web' | 'time' | 'fun' | 'custom' | 'auto';
    type?: 'simple' | 'dialogue';
    dialogue?: {
        steps: any[];
        exit_phrases: string[];
        variables: Record<string, any>;
    };
    createdAt: number;
}

/* =========================================================
   УТИЛИТЫ
   ========================================================= */

const STORAGE_KEY = 'eva-skills-v2';
const newId = () => Math.random().toString(36).slice(2, 11);

const defaultActionConfig = (type: ActionType): Record<string, any> => {
    switch (type) {
        case 'http':       return { method: 'POST', url: '', headers: '{}', body: '{"text": "{phrase}"}' };
        case 'plugin':     return { plugin: 'plugin_global_mute_group', function: 'set_mute', args: 'true' };
        case 'ha_service': return { entity_id: '', service: 'light.turn_on', data: '{}' };
        case 'timer':      return { seconds: 300, message: 'Таймер сработал!' };
        case 'llm':        return { prompt: '{phrase}', system: 'Ты — голосовой ассистент. Кратко ответь на запрос.' };
        case 'text':       return { text: 'Готово' };
        case 'macro':      return { skills: [] as string[] };
    }
};

const actionTypeMeta: Record<ActionType, { name: string; icon: any; desc: string; color: string }> = {
    http:       { name: 'HTTP-запрос',     icon: HttpIcon,   desc: 'Вызов любого API/вебхука',                 color: '#2196f3' },
    plugin:     { name: 'Плагин/функция',  icon: PluginIcon, desc: 'Вызов функции подключённого плагина',      color: '#7c4dff' },
    ha_service: { name: 'Home Assistant',  icon: HomeIcon,   desc: 'Сервис HA: свет, шторы, климат, медиа',     color: '#03a9f4' },
    timer:      { name: 'Таймер/время',    icon: TimerIcon,  desc: 'Установить таймер, напоминание, расписание', color: '#ff9800' },
    llm:        { name: 'ИИ (LLM)',        icon: BotIcon,    desc: 'Передать запрос языковой модели',           color: '#e91e63' },
    text:       { name: 'Текстовый ответ', icon: TextIcon,   desc: 'Просто произнести фразу',                   color: '#4caf50' },
    macro:      { name: 'Макрос',          icon: MacroIcon,  desc: 'Последовательность из других навыков',      color: '#9c27b0' },
};

const categoryMeta: Record<string, { name: string; icon: any; color: string }> = {
    utility: { name: 'Утилиты',       icon: StarIcon,   color: '#4caf50' },
    home:    { name: 'Умный дом',     icon: HomeIcon,   color: '#03a9f4' },
    web:     { name: 'Веб/интеграции', icon: HttpIcon,   color: '#2196f3' },
    time:    { name: 'Время',         icon: TimerIcon,  color: '#ff9800' },
    fun:     { name: 'Развлечения',   icon: TextIcon,   color: '#e91e63' },
    custom:  { name: 'Свои',          icon: StarIcon,   color: '#9e9e9e' },
    auto:    { name: 'Авто',          icon: BotIcon,    color: '#7c4dff' },
};

const getCategoryMeta = (cat: string) => categoryMeta[cat] || { name: cat, icon: StarIcon, color: '#9e9e9e' };

const slotTypeMeta: Record<SlotType, { name: string; icon: any; color: string; example: string; desc: string }> = {
    string: { name: 'Строка',    icon: StringIcon, color: '#7c4dff', example: 'Москва, кухня, Вася',     desc: 'Любой текст' },
    number: { name: 'Число',     icon: NumberIcon, color: '#2196f3', example: '5, 25, 100.5',            desc: 'Целое или дробное' },
    date:   { name: 'Дата',      icon: DateIcon,   color: '#ff9800', example: 'завтра, 25.12, через час', desc: 'Дата и время' },
    geo:    { name: 'Геолокация', icon: GeoIcon,    color: '#03a9f4', example: 'Москва, ул. Ленина 5',    desc: 'Город, адрес, координаты' },
    list:   { name: 'Список',    icon: ListIcon,   color: '#9c27b0', example: 'свет / шторы / климат',    desc: 'Одно из заданных значений' },
    bool:   { name: 'Да/Нет',    icon: BoolIcon,   color: '#4caf50', example: 'да, нет, включи, выключи', desc: 'Булево значение' },
};

/** Извлекает имена слотов из строки фразы */
const extractSlotNames = (phrase: string): string[] => {
    const re = /\{(\w+)\}/g;
    const set = new Set<string>();
    let m;
    while ((m = re.exec(phrase))) set.add(m[1]);
    return Array.from(set);
};

/** Парсит фразу пользователя и возвращает пары {slot_name: value} */
const parsePhraseToSlots = (
    phrase: string,
    template: string,
    slots: SkillSlot[]
): Record<string, string> => {
    const result: Record<string, string> = {};
    // Заменяем {slot} на wildcards в regex
    const reText = template.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/\\\{\w+\\\}/g, '(.+?)');
    const re = new RegExp(`^${reText}$`, 'i');
    const m = phrase.match(re);
    if (!m) {
        // Если не совпало целиком — пробуем contains
        const parts = template.split(/(\{\w+\})/g);
        let cursor = 0;
        for (let i = 0; i < parts.length; i++) {
            const p = parts[i];
            if (p.startsWith('{')) {
                const name = p.slice(1, -1);
                result[name] = '...';
            } else {
                cursor += p.length;
            }
        }
        return result;
    }
    const names = extractSlotNames(template);
    names.forEach((name, i) => {
        result[name] = (m[i + 1] || '').trim();
    });
    // Применяем значения по умолчанию
    for (const s of slots) {
        if (!result[s.name] && s.defaultValue !== undefined) result[s.name] = s.defaultValue;
        // Валидация list — приводим к ближайшему
        if (s.type === 'list' && result[s.name] && s.values?.length) {
            const lower = result[s.name].toLowerCase();
            const found = s.values.find(v => v.toLowerCase() === lower || lower.includes(v.toLowerCase()));
            if (found) result[s.name] = found;
        }
        // Валидация number
        if (s.type === 'number' && result[s.name]) {
            const cleaned = result[s.name].replace(/[^\d.,]/g, '').replace(',', '.');
            const n = parseFloat(cleaned);
            if (!isNaN(n)) result[s.name] = String(n);
        }
        // Валидация bool
        if (s.type === 'bool' && result[s.name]) {
            const yes = ['да', 'включи', 'включить', 'yes', 'on', 'true'];
            const no  = ['нет', 'выключи', 'выключить', 'off', 'false'];
            const l = result[s.name].toLowerCase();
            if (yes.some(w => l.includes(w))) result[s.name] = 'true';
            else if (no.some(w => l.includes(w))) result[s.name] = 'false';
        }
    }
    return result;
};

const resolveTemplate = (tmpl: string, slots: Record<string, string>, extra: Record<string, string> = {}): string => {
    let out = tmpl;
    for (const [k, v] of Object.entries({ ...slots, ...extra })) {
        out = out.replaceAll(`{${k}}`, v || `{${k}}`);
    }
    return out;
};

/** Подсветка слотов в строке */
const highlightPhrase = (phrase: string, slots: SkillSlot[]) => {
    const parts = phrase.split(/(\{\w+\})/g);
    return parts.map((p, i) => {
        if (p.startsWith('{') && p.endsWith('}')) {
            const name = p.slice(1, -1);
            const slot = slots.find(s => s.name === name);
            const color = slot ? slotTypeMeta[slot.type].color : '#9e9e9e';
            return { type: 'slot', name, color, key: i };
        }
        return { type: 'text', text: p, key: i };
    });
};

/* =========================================================
   ШАБЛОНЫ
   ========================================================= */

const templates: Omit<Skill, 'id' | 'createdAt'>[] = [
    {
        intent: 'Home.TurnOnLight',
        name: 'Включи свет',
        description: 'Включает свет в указанной комнате через Home Assistant',
        enabled: true,
        phrases: ['включи свет', 'включи свет в {room}'],
        matchMode: 'contains',
        slots: [
            { id: newId(), name: 'room', type: 'list', required: false, examples: ['кухня', 'спальня', 'зал'],
              values: ['кухня', 'спальня', 'зал', 'ванная', 'детская'], defaultValue: 'зал' },
        ],
        actions: [{
            id: newId(), type: 'ha_service',
            config: { entity_id: 'light.{room}', service: 'light.turn_on', data: '{}' }
        }],
        reactions: [{ id: newId(), text: 'Включаю свет в {room}', tts: 'Включаю свет в {room}!' }],
        session: { enabled: false, ttl: 60 },
        category: 'home',
    },
    {
        intent: 'Weather.Get',
        name: 'Погода в городе',
        description: 'Голосовой запрос погоды через wttr.in + краткое резюме от LLM',
        enabled: true,
        phrases: ['погода', 'погода в {city}', 'какая погода в {city}'],
        matchMode: 'contains',
        slots: [
            { id: newId(), name: 'city', type: 'geo', required: true, examples: ['Москва', 'Санкт-Петербург', 'Казань'] },
        ],
        actions: [
            { id: newId(), type: 'http', config: { method: 'GET', url: 'https://wttr.in/{city}?format=j1&lang=ru', headers: '{}', body: '' } },
            { id: newId(), type: 'llm', config: {
                prompt: 'Сделай краткий прогноз погоды на сегодня из этих данных: {last_response}. Ответь на русском в 2-3 предложениях.',
                system: 'Ты — лаконичный метеоролог.' } },
        ],
        reactions: [{ id: newId(), text: '{last_response}' }],
        session: { enabled: false, ttl: 60 },
        category: 'web',
    },
    {
        intent: 'Timer.Set',
        name: 'Таймер на N минут',
        description: 'Устанавливает таймер на заданное количество минут',
        enabled: true,
        phrases: ['таймер на {minutes} минут', 'поставь таймер на {minutes}', 'засеки {minutes} минут'],
        matchMode: 'regex',
        slots: [
            { id: newId(), name: 'minutes', type: 'number', required: true, examples: ['5', '10', '25'] },
        ],
        actions: [{
            id: newId(), type: 'timer',
            config: { seconds: '{minutes} * 60', message: 'Таймер на {minutes} минут сработал!' }
        }],
        reactions: [{ id: newId(), text: 'Поставила таймер на {minutes} минут', tts: 'Поставила таймер на {minutes} минут.' }],
        session: { enabled: true, ttl: 300 },
        category: 'time',
    },
    {
        intent: 'Telegram.Send',
        name: 'Отправить в Телеграм',
        description: 'Отправляет сообщение в Telegram через бот-API',
        enabled: true,
        phrases: ['отправь в телеграм {text}', 'напиши в тг {text}'],
        matchMode: 'contains',
        slots: [
            { id: newId(), name: 'text', type: 'string', required: true, examples: ['привет', 'я ушёл с работы'] },
        ],
        actions: [{
            id: newId(), type: 'http', config: {
                method: 'POST',
                url: 'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',
                headers: '{"Content-Type": "application/json"}',
                body: '{"chat_id": "{CHAT_ID}", "text": "{text}"}'
            }
        }],
        reactions: [{ id: newId(), text: 'Отправила в Telegram: «{text}»' }],
        session: { enabled: false, ttl: 60 },
        category: 'web',
    },
    {
        intent: 'LLM.Ask',
        name: 'Спросить у ИИ',
        description: 'Отправляет любой вопрос в LLM и озвучивает ответ',
        enabled: true,
        phrases: ['спроси у ии {query}', 'что такое {query}'],
        matchMode: 'contains',
        slots: [
            { id: newId(), name: 'query', type: 'string', required: true, examples: ['что такое LLM', 'когда основан Python'] },
        ],
        actions: [{
            id: newId(), type: 'llm',
            config: { prompt: '{query}', system: 'Ты — умный голосовой помощник. Кратко ответь на вопрос.' }
        }],
        reactions: [{ id: newId(), text: '{last_response}' }],
        session: { enabled: false, ttl: 60 },
        category: 'utility',
    },
];

/* =========================================================
   СОСТОЯНИЕ
   ========================================================= */

const skills = ref<Skill[]>([]);
const searchQuery = ref('');
const activeCategory = ref<Skill['category'] | 'all'>('all');
const showForm = ref(false);
const editingId = ref<string | null>(null);
const showTemplates = ref(false);
const newPhrase = ref('');
const newSlotName = ref('');
const newSlotType = ref<SlotType>('string');

const form = ref<Skill>({
    id: '',
    intent: '',
    name: '',
    description: '',
    enabled: true,
    phrases: [],
    matchMode: 'contains',
    slots: [],
    actions: [],
    reactions: [{ id: newId(), text: 'Готово' }],
    session: { enabled: false, ttl: 60 },
    category: 'custom',
    type: 'simple',
    dialogue: { steps: [], exit_phrases: ['хватит', 'стоп', 'пока'], variables: {} },
    createdAt: 0,
});

/* Ева Консоль — состояние тестера */
const testConsole = ref({
    query: '',
    mode: 'server' as 'local' | 'server',  // по умолчанию — реальный сервер
    resolvedIntent: null as Skill | null,
    resolvedSlots: {} as Record<string, string>,
    reaction: '',
    actionsPlan: [] as { name: string; color: string }[],
    sessionKept: false,
    serverStatus: 'idle' as 'idle' | 'sending' | 'ok' | 'error' | 'no_match',
    serverMessage: '',
});

/* Авто-создание навыков через LLM */
const autoCreateMode = ref(false);
const autoCreateRequest = ref('');
const autoCreateStatus = ref<'idle' | 'loading' | 'ok' | 'error'>('idle');
const autoCreateMessage = ref('');

const autoCreateSkill = async () => {
    if (!autoCreateRequest.value.trim()) return;
    autoCreateStatus.value = 'loading';
    autoCreateMessage.value = '';
    try {
        const res = await fetch('/api/eva_skills/auto_create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ request: autoCreateRequest.value }),
        });
        const data = await res.json();
        if (data.status === 'ok') {
            autoCreateStatus.value = 'ok';
            autoCreateMessage.value = data.message || 'Навык создан!';
            autoCreateRequest.value = '';
            await loadSkills();
        } else {
            autoCreateStatus.value = 'error';
            autoCreateMessage.value = data.message || 'Ошибка';
        }
    } catch (e: any) {
        autoCreateStatus.value = 'error';
        autoCreateMessage.value = e.message;
    }
};

/* =========================================================
   ЗАГРУЗКА / СОХРАНЕНИЕ
   ========================================================= */

const loadSkills = async () => {
    try {
        const r = await fetch('/api/eva_skills/list');
        if (r.ok) {
            const data = await r.json();
            if (Array.isArray(data) && data.length) {
                skills.value = data;
                return;
            }
        }
    } catch {}
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (raw) skills.value = JSON.parse(raw);
    } catch {}
};

const persistSkills = async () => {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(skills.value)); } catch {}
    try {
        await fetch('/api/eva_skills/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ skills: skills.value }),
        });
    } catch {}
};

watch(skills, persistSkills, { deep: true });

/* =========================================================
   ФИЛЬТРАЦИЯ И СТАТИСТИКА
   ========================================================= */

const filteredSkills = computed(() => {
    let list = skills.value;
    if (activeCategory.value !== 'all') {
        list = list.filter(s => s.category === activeCategory.value);
    }
    if (searchQuery.value.trim()) {
        const q = searchQuery.value.toLowerCase();
        list = list.filter(s =>
            s.intent.toLowerCase().includes(q) ||
            s.name.toLowerCase().includes(q) ||
            s.description.toLowerCase().includes(q) ||
            s.phrases.some(p => p.toLowerCase().includes(q))
        );
    }
    return list;
});

const stats = computed(() => ({
    total: skills.value.length,
    enabled: skills.value.filter(s => s.enabled).length,
    intents: new Set(skills.value.map(s => s.intent.split('.')[0])).size,
    slots: skills.value.reduce((acc, s) => acc + s.slots.length, 0),
}));

/* =========================================================
   CRUD
   ========================================================= */

const resetForm = () => {
    form.value = {
        id: newId(),
        intent: '',
        name: '',
        description: '',
        enabled: true,
        phrases: [],
        matchMode: 'contains',
        slots: [],
        actions: [{ id: newId(), type: 'text', config: defaultActionConfig('text') }],
        reactions: [{ id: newId(), text: 'Готово' }],
        session: { enabled: false, ttl: 60 },
        category: 'custom',
        type: 'simple',
        dialogue: { steps: [], exit_phrases: ['хватит', 'стоп', 'пока'], variables: {} },
        createdAt: Date.now(),
    };
    editingId.value = null;
    newPhrase.value = '';
    newSlotName.value = '';
};

const dialogueExitPhrases = ref('хватит, стоп, пока');

const addDialogueStep = () => {
    if (!form.value.dialogue) {
        form.value.dialogue = { steps: [], exit_phrases: [], variables: {} };
    }
    const stepNum = (form.value.dialogue.steps?.length || 0) + 1;
    form.value.dialogue.steps.push({
        id: `step_${stepNum}`,
        type: stepNum === 1 ? 'intro' : 'text',
        text: '',
        question: '',
        template: '',
        next: '',
        save_to: 'user_answer',
        counter_var: '$loop_count',
        exit_condition: '',
        self_loop: '',
    });
};

const removeStep = (idx: number) => {
    form.value.dialogue?.steps?.splice(idx, 1);
};

const addPhrase = () => {
    const p = newPhrase.value.trim();
    if (!p) return;
    if (!form.value.phrases.includes(p)) form.value.phrases.push(p);
    newPhrase.value = '';
    // Авто-добавление слотов из фразы
    const names = extractSlotNames(p);
    for (const n of names) {
        if (!form.value.slots.find(s => s.name === n)) {
            form.value.slots.push({ id: newId(), name: n, type: 'string', required: false, examples: [] });
        }
    }
};

const removePhrase = (idx: number) => form.value.phrases.splice(idx, 1);

const addSlot = () => {
    const name = newSlotName.value.trim().replace(/\s+/g, '_').toLowerCase();
    if (!name) return;
    if (form.value.slots.find(s => s.name === name)) return;
    form.value.slots.push({ id: newId(), name, type: newSlotType.value, required: false, examples: [] });
    newSlotName.value = '';
};

const removeSlot = (id: string) => {
    form.value.slots = form.value.slots.filter(s => s.id !== id);
};

const addAction = (type: ActionType) => {
    form.value.actions.push({ id: newId(), type, config: defaultActionConfig(type) });
};
const removeAction = (idx: number) => form.value.actions.splice(idx, 1);
const moveAction = (idx: number, dir: -1 | 1) => {
    const newIdx = idx + dir;
    if (newIdx < 0 || newIdx >= form.value.actions.length) return;
    const [item] = form.value.actions.splice(idx, 1);
    form.value.actions.splice(newIdx, 0, item);
};

const addReaction = () => {
    form.value.reactions.push({ id: newId(), text: 'Готово' });
};
const removeReaction = (id: string) => {
    form.value.reactions = form.value.reactions.filter(r => r.id !== id);
};

const saveForm = () => {
    if (!form.value.intent || !form.value.name || form.value.phrases.length === 0) {
        alert('Заполни интент, название и добавь хотя бы одну фразу');
        return;
    }
    if (editingId.value) {
        const idx = skills.value.findIndex(s => s.id === editingId.value);
        if (idx >= 0) skills.value[idx] = { ...form.value };
    } else {
        skills.value.unshift({ ...form.value, id: newId(), createdAt: Date.now() });
    }
    showForm.value = false;
    resetForm();
};

const editSkill = (skill: Skill) => {
    form.value = JSON.parse(JSON.stringify(skill));
    editingId.value = skill.id;
    showForm.value = true;
};

const deleteSkill = (id: string) => {
    if (!confirm('Удалить навык?')) return;
    skills.value = skills.value.filter(s => s.id !== id);
};

const toggleSkill = (skill: Skill) => { skill.enabled = !skill.enabled; };

const importTemplate = (tmpl: typeof templates[0]) => {
    const skill: Skill = {
        ...tmpl,
        id: newId(),
        createdAt: Date.now(),
        slots: tmpl.slots.map(s => ({ ...s, id: newId() })),
        actions: tmpl.actions.map(a => ({ ...a, id: newId() })),
        reactions: tmpl.reactions.map(r => ({ ...r, id: newId() })),
    };
    skills.value.unshift(skill);
    showTemplates.value = false;
};

/* =========================================================
   ALICE CONSOLE — тестирование
   ========================================================= */

const runTest = async () => {
    const q = testConsole.value.query.trim();
    if (!q) return;

    if (testConsole.value.mode === 'server') {
        await runTestOnServer(q);
        return;
    }

    // Локальный режим — имитация (как раньше)
    let matched: Skill | null = null;
    let matchedTemplate = '';
    let slots: Record<string, string> = {};

    for (const s of skills.value) {
        if (!s.enabled) continue;
        for (const p of s.phrases) {
            const names = extractSlotNames(p);
            if (names.length === 0) {
                if (q.toLowerCase().includes(p.toLowerCase())) {
                    matched = s; matchedTemplate = p; slots = {}; break;
                }
            } else {
                const parsed = parsePhraseToSlots(q, p, s.slots);
                if (Object.keys(parsed).length > 0 && q.toLowerCase().includes(p.toLowerCase().replace(/\{\w+\}/g, '').trim().split(/\s+/)[0] || '')) {
                    matched = s; matchedTemplate = p; slots = parsed; break;
                }
            }
        }
        if (matched) break;
    }

    testConsole.value.resolvedIntent = matched;
    testConsole.value.resolvedSlots = slots;

    if (matched) {
        const reaction = matched.reactions[0]?.text || matched.actions[matched.actions.length - 1]?.config.text || 'Готово';
        testConsole.value.reaction = resolveTemplate(reaction, slots);
        testConsole.value.actionsPlan = matched.actions.map(a => ({
            name: actionTypeMeta[a.type].name,
            color: actionTypeMeta[a.type].color,
        }));
        testConsole.value.sessionKept = matched.session.enabled;
        testConsole.value.serverStatus = 'ok';
        testConsole.value.serverMessage = 'Сопоставлено локально';
    } else {
        testConsole.value.reaction = '🤷 Не удалось сопоставить фразу ни с одним интентом';
        testConsole.value.actionsPlan = [];
        testConsole.value.sessionKept = false;
        testConsole.value.serverStatus = 'no_match';
        testConsole.value.serverMessage = 'Нет совпадений';
    }
};

/** Реальный тест через серверный API — настоящий matcher + выполнение */
const runTestOnServer = async (text: string) => {
    testConsole.value.serverStatus = 'sending';
    testConsole.value.serverMessage = 'Отправляю на сервер...';
    try {
        const r = await fetch('/api/eva_skills/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text }),
        });
        if (!r.ok) {
            testConsole.value.serverStatus = 'error';
            testConsole.value.serverMessage = `HTTP ${r.status}`;
            return;
        }
        const data = await r.json();
        if (!data.matched) {
            testConsole.value.resolvedIntent = null;
            testConsole.value.resolvedSlots = {};
            testConsole.value.reaction = '🤷 На сервере нет подходящего навыка';
            testConsole.value.actionsPlan = [];
            testConsole.value.sessionKept = false;
            testConsole.value.serverStatus = 'no_match';
            testConsole.value.serverMessage = 'Сервер не нашёл навык';
            return;
        }
        const skill = skills.value.find(s => s.id === data.skill_id) || null;
        testConsole.value.resolvedIntent = skill;
        testConsole.value.resolvedSlots = data.slots || {};
        testConsole.value.reaction = data.response || data.last_action_result || 'Готово';
        testConsole.value.actionsPlan = skill ? skill.actions.map(a => ({
            name: actionTypeMeta[a.type].name,
            color: actionTypeMeta[a.type].color,
        })) : [];
        testConsole.value.sessionKept = skill?.session?.enabled || false;
        testConsole.value.serverStatus = 'ok';
        testConsole.value.serverMessage = `Сервер выполнил за ${new Date().toLocaleTimeString()}`;
    } catch (e) {
        testConsole.value.serverStatus = 'error';
        testConsole.value.serverMessage = `Сервер недоступен: ${e}`;
        // Фоллбэк на локальный режим
        testConsole.value.mode = 'local';
        runTest();
    }
};

const clearConsole = () => {
    testConsole.value = {
        query: '', mode: 'server',
        resolvedIntent: null, resolvedSlots: {},
        reaction: '', actionsPlan: [], sessionKept: false,
        serverStatus: 'idle', serverMessage: '',
    };
};

/* =========================================================
   ВНЕШНИЕ ДАННЫЕ
   ========================================================= */

const availablePlugins = ref<{ name: string; display_name: string }[]>([]);
const availableHAEntities = ref<{ entity_id: string; name: string; domain: string; state: string; unit: string }[]>([]);
const availableHAServices = ref<{ full: string; name: string; domain: string; service: string; target: boolean }[]>([]);

const fetchPlugins = async () => {
    try {
        const r = await fetch('/api/config/configs');
        if (r.ok) {
            const data = await r.json();
            availablePlugins.value = (data || []).map((p: any) => ({
                name: p.scope, display_name: p.comment || p.scope,
            }));
        }
    } catch {}
};

const haEntityFilter = ref('');
const haEntityDomain = ref('');
const haEntityDomains = ref<string[]>([]);

const fetchHAEntities = async (domain: string = '', filter: string = '') => {
    try {
        const params = new URLSearchParams();
        if (domain) params.set('domain', domain);
        if (filter) params.set('filter', filter);
        params.set('limit', '500');
        const r = await fetch(`/api/eva_skills/ha/entities?${params}`);
        if (r.ok) {
            const data = await r.json();
            availableHAEntities.value = (data.entities || []).map((e: any) => ({
                entity_id: e.entity_id,
                name: e.friendly_name || e.entity_id,
                domain: e.domain,
                state: e.state,
                unit: e.unit,
            }));
            if (data.domains) haEntityDomains.value = data.domains;
        }
    } catch {}
};

const fetchHAServices = async (domain: string = '') => {
    try {
        const params = domain ? `?domain=${domain}` : '';
        const r = await fetch(`/api/eva_skills/ha/services${params}`);
        if (r.ok) {
            const data = await r.json();
            availableHAServices.value = data.services || [];
        }
    } catch {}
};

loadSkills();
fetchPlugins();
fetchHAEntities();
fetchHAServices();
</script>

<template>
    <div class="skill-settings">
        <!-- Заголовок и статистика -->
        <div class="header">
            <div>
                <h2>Конструктор навыков <span class="alice-badge">Eva</span></h2>
                <p class="subtitle">Создавай интенты со слотами, действиями и реакциями</p>
            </div>
            <div class="header-actions">
                <button class="ghost-btn" @click="showTemplates = true">
                    <StarIcon /> Шаблоны
                </button>
                <button class="ghost-btn" @click="autoCreateMode = !autoCreateMode" :class="{ active: autoCreateMode }">
                    <BotIcon /> Авто-создание
                </button>
                <button class="primary-btn" @click="showForm = true; resetForm()">
                    <AddIcon /> Создать навык
                </button>
            </div>
        </div>

        <!-- Карточки со статистикой -->
        <div class="stats-row">
            <div class="stat-card">
                <div class="stat-value">{{ stats.total }}</div>
                <div class="stat-label">Навыков</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ stats.intents }}</div>
                <div class="stat-label">Категорий</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ stats.slots }}</div>
                <div class="stat-label">Слотов</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ stats.enabled }}</div>
                <div class="stat-label">Активных</div>
            </div>
        </div>

        <!-- Авто-создание навыков -->
        <div v-if="autoCreateMode" class="auto-create-panel">
            <h3><BotIcon /> Авто-создание навыков</h3>
            <p class="hint">Опиши что должен делать навык — Eva создаст его автоматически</p>
            <div class="auto-create-row">
                <input v-model="autoCreateRequest" type="text" class="input"
                    placeholder="Например: навык для включения музыки на Яндекс.Станции"
                    @keydown.enter="autoCreateSkill" />
                <button class="primary-btn" @click="autoCreateSkill" :disabled="autoCreateStatus === 'loading'">
                    {{ autoCreateStatus === 'loading' ? 'Создаю...' : 'Создать' }}
                </button>
            </div>
            <div v-if="autoCreateStatus === 'ok'" class="auto-create-result ok">{{ autoCreateMessage }}</div>
            <div v-if="autoCreateStatus === 'error'" class="auto-create-result error">{{ autoCreateMessage }}</div>
        </div>

        <!-- Основной layout: список + Ева Консоль -->
        <div class="main-layout">
            <div class="left-col">
                <!-- Поиск и фильтры -->
                <div class="toolbar">
                    <div class="search-input">
                        <SearchIcon />
                        <input v-model="searchQuery" placeholder="Поиск по навыкам, интентам..." />
                    </div>
                    <div class="categories">
                        <button
                            class="cat-btn"
                            :class="{ active: activeCategory === 'all' }"
                            @click="activeCategory = 'all'"
                        >Все</button>
                        <button
                            v-for="(meta, key) in categoryMeta"
                            :key="key"
                            class="cat-btn"
                            :class="{ active: activeCategory === key }"
                            :style="activeCategory === key ? { background: meta.color, borderColor: meta.color, color: 'white' } : {}"
                            @click="activeCategory = key as any"
                        >
                            <component :is="meta.icon" />
                            {{ meta.name }}
                        </button>
                    </div>
                </div>

                <!-- Список навыков -->
                <div v-if="filteredSkills.length === 0" class="empty-state">
                    <StarIcon class="empty-icon" />
                    <h3>Нет навыков</h3>
                    <p>Нажми "Создать навык" или возьми готовый шаблон</p>
                    <button class="primary-btn" @click="showTemplates = true">
                        <StarIcon /> Открыть ��аблоны
                    </button>
                </div>

                <div v-else class="skills-list">
                    <div
                        v-for="skill in filteredSkills"
                        :key="skill.id"
                        class="skill-card"
                        :class="{ disabled: !skill.enabled }"
                    >
                        <div class="skill-main">
                            <div class="skill-head">
                                <div class="skill-title-row">
                                    <span class="intent-badge">
                                        <CodeIcon /> {{ skill.intent }}
                                    </span>
                                    <span class="category-badge" :style="{ background: getCategoryMeta(skill.category).color + '22', color: getCategoryMeta(skill.category).color }">
                                        <component :is="getCategoryMeta(skill.category).icon" />
                                        {{ getCategoryMeta(skill.category).name }}
                                    </span>
                                    <span v-if="skill.session.enabled" class="session-badge" title="Сессионный навык">
                                        🔗 Сессия {{ skill.session.ttl }}с
                                    </span>
                                </div>
                                <h3>{{ skill.name }}</h3>
                                <p v-if="skill.description" class="skill-desc">{{ skill.description }}</p>
                            </div>

                            <div class="skill-phrases">
                                <div class="section-label">Фразы:</div>
                                <div class="phrases-list">
                                    <span v-for="p in skill.phrases" :key="p" class="phrase-tag">
                                        <template v-for="part in highlightPhrase(p, skill.slots)" :key="part.key">
                                            <span v-if="part.type === 'slot'" class="slot-inline" :style="{ background: part.color + '22', color: part.color, borderColor: part.color }">{{ part.name }}</span>
                                            <span v-else>{{ part.text }}</span>
                                        </template>
                                    </span>
                                </div>
                            </div>

                            <div v-if="skill.slots.length" class="skill-slots-preview">
                                <div class="section-label">Слоты:</div>
                                <div class="slots-list">
                                    <span
                                        v-for="s in skill.slots"
                                        :key="s.id"
                                        class="slot-chip"
                                        :style="{ borderColor: slotTypeMeta[s.type].color, color: slotTypeMeta[s.type].color }"
                                    >
                                        <component :is="slotTypeMeta[s.type].icon" />
                                        {{ s.name }}<span v-if="s.required">*</span>
                                    </span>
                                </div>
                            </div>

                            <div class="skill-actions-preview">
                                <div class="section-label">Действия:</div>
                                <div class="actions-flow">
                                    <template v-for="(a, idx) in skill.actions" :key="a.id">
                                        <div class="action-chip" :style="{ borderColor: actionTypeMeta[a.type].color }">
                                            <component :is="actionTypeMeta[a.type].icon" :style="{ color: actionTypeMeta[a.type].color }" />
                                            <span>{{ actionTypeMeta[a.type].name }}</span>
                                        </div>
                                        <span v-if="idx < skill.actions.length - 1" class="arrow">→</span>
                                    </template>
                                </div>
                            </div>

                            <div v-if="skill.reactions.length" class="skill-response">
                                💬 <em>"{{ skill.reactions[0].text }}"</em>
                                <span v-if="skill.reactions.length > 1" class="more-reactions">+{{ skill.reactions.length - 1 }}</span>
                            </div>
                        </div>

                        <div class="skill-side">
                            <label class="switch" :title="skill.enabled ? 'Выключить' : 'Включить'">
                                <input type="checkbox" :checked="skill.enabled" @change="toggleSkill(skill)" />
                                <span class="slider"></span>
                            </label>
                            <button class="icon-btn" @click="editSkill(skill)" title="Редактировать">
                                <EditIcon />
                            </button>
                            <button class="icon-btn danger" @click="deleteSkill(skill.id)" title="Удалить">
                                <DeleteIcon />
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- ALICE CONSOLE -->
            <aside class="alice-console">
                <div class="console-header">
                    <ConsoleIcon />
                    <h3>Ева Консоль</h3>
                    <button class="icon-btn xs" @click="clearConsole" title="Очистить"><CloseIcon /></button>
                </div>

                <div class="console-body">
                    <div class="console-input">
                        <label>Запрос пользователя:</label>
                        <textarea
                            v-model="testConsole.query"
                            @keydown.ctrl.enter="runTest"
                            class="input mono"
                            rows="2"
                            placeholder='Например: "включи свет в спальне"'
                        ></textarea>

                        <div class="mode-switch">
                            <label class="radio inline">
                                <input type="radio" v-model="testConsole.mode" value="server" />
                                <span>🌐 На сервере Eva</span>
                            </label>
                            <label class="radio inline">
                                <input type="radio" v-model="testConsole.mode" value="local" />
                                <span>💻 Локальный матчер</span>
                            </label>
                        </div>

                        <button class="primary-btn sm" @click="runTest" :disabled="testConsole.serverStatus === 'sending'">
                            <PlayIcon v-if="testConsole.serverStatus !== 'sending'" />
                            <span v-else class="spin-dot"></span>
                            {{ testConsole.serverStatus === 'sending' ? 'Выполняю...' : 'Тестировать (Ctrl+Enter)' }}
                        </button>

                        <div v-if="testConsole.serverStatus !== 'idle'" class="server-status" :class="testConsole.serverStatus">
                            <span v-if="testConsole.serverStatus === 'sending'">⏳</span>
                            <span v-else-if="testConsole.serverStatus === 'ok'">✅</span>
                            <span v-else-if="testConsole.serverStatus === 'no_match'">🤷</span>
                            <span v-else-if="testConsole.serverStatus === 'error'">⚠️</span>
                            {{ testConsole.serverMessage }}
                        </div>
                    </div>

                    <div v-if="testConsole.resolvedIntent || testConsole.query" class="console-output">
                        <div class="console-section">
                            <div class="console-label">🎯 Intent:</div>
                            <div v-if="testConsole.resolvedIntent" class="intent-found">
                                <span class="intent-badge">
                                    <CodeIcon /> {{ testConsole.resolvedIntent.intent }}
                                </span>
                                <span class="muted">{{ testConsole.resolvedIntent.name }}</span>
                            </div>
                            <div v-else class="not-found">— не сопоставлен —</div>
                        </div>

                        <div v-if="Object.keys(testConsole.resolvedSlots).length" class="console-section">
                            <div class="console-label">📦 Slots (извлечено):</div>
                            <div class="slots-extracted">
                                <div
                                    v-for="(v, k) in testConsole.resolvedSlots"
                                    :key="k"
                                    class="slot-extracted"
                                >
                                    <span class="slot-name">{{ k }}:</span>
                                    <span class="slot-value">{{ v }}</span>
                                </div>
                            </div>
                        </div>

                        <div v-if="testConsole.actionsPlan.length" class="console-section">
                            <div class="console-label">⚙️ План действий:</div>
                            <div class="console-flow">
                                <template v-for="(a, i) in testConsole.actionsPlan" :key="i">
                                    <div class="action-chip" :style="{ borderColor: a.color }">
                                        <span :style="{ color: a.color }">●</span> {{ a.name }}
                                    </div>
                                    <span v-if="i < testConsole.actionsPlan.length - 1" class="arrow">→</span>
                                </template>
                            </div>
                        </div>

                        <div class="console-section">
                            <div class="console-label">💬 Реакция:</div>
                            <div class="reaction-block">
                                <template v-if="testConsole.reaction">
                                    <div class="reaction-text">{{ testConsole.reaction }}</div>
                                    <div v-if="testConsole.sessionKept" class="session-info">🔗 Сессия сохранена</div>
                                </template>
                                <div v-else class="muted">Введите запрос и нажмите Тестировать</div>
                            </div>
                        </div>
                    </div>
                </div>
            </aside>
        </div>

        <!-- Модалка шаблонов -->
        <Teleport to="body">
            <div v-if="showTemplates" class="modal-overlay" @click.self="showTemplates = false">
                <div class="modal modal-wide">
                    <div class="modal-header">
                        <h3><StarIcon /> Готовые шаблоны</h3>
                        <button class="close-btn" @click="showTemplates = false"><CloseIcon /></button>
                    </div>
                    <div class="modal-body">
                        <div class="templates-grid">
                            <div
                                v-for="(tmpl, i) in templates"
                                :key="i"
                                class="template-card"
                                @click="importTemplate(tmpl)"
                            >
                                <span class="intent-badge small">
                                    <CodeIcon /> {{ tmpl.intent }}
                                </span>
                                <h4>{{ tmpl.name }}</h4>
                                <p>{{ tmpl.description }}</p>
                                <div class="template-phrases">
                                    <span v-for="p in tmpl.phrases.slice(0, 2)" :key="p" class="phrase-tag sm">{{ p }}</span>
                                </div>
                                <div class="template-slots" v-if="tmpl.slots.length">
                                    <span
                                        v-for="s in tmpl.slots"
                                        :key="s.id"
                                        class="slot-chip sm"
                                        :style="{ borderColor: slotTypeMeta[s.type].color, color: slotTypeMeta[s.type].color }"
                                    >
                                        <component :is="slotTypeMeta[s.type].icon" /> {{ s.name }}
                                    </span>
                                </div>
                                <div class="template-actions">
                                    <span
                                        v-for="a in tmpl.actions"
                                        :key="a.id"
                                        class="action-chip sm"
                                        :style="{ borderColor: actionTypeMeta[a.type].color }"
                                    >
                                        <component :is="actionTypeMeta[a.type].icon" :style="{ color: actionTypeMeta[a.type].color }" />
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </Teleport>

        <!-- Модалка конструктора -->
        <Teleport to="body">
            <div v-if="showForm" class="modal-overlay" @click.self="showForm = false">
                <div class="modal modal-xl">
                    <div class="modal-header">
                        <h3>
                            <AddIcon v-if="!editingId" />
                            <EditIcon v-else />
                            {{ editingId ? 'Редактировать навык' : 'Новый навык' }}
                        </h3>
                        <button class="close-btn" @click="showForm = false"><CloseIcon /></button>
                    </div>

                    <div class="modal-body">
                        <!-- Шаг 1: Интент и базовая информация -->
                        <div class="wizard-section">
                            <div class="wizard-step">
                                <span class="step-num">1</span>
                                <span class="step-title">Интент и базовая информация</span>
                            </div>
                            <div class="form-row">
                                <div class="field" style="flex: 1">
                                    <label>Intent (Категория.Действие)</label>
                                    <input
                                        v-model="form.intent"
                                        class="input mono"
                                        placeholder="Home.TurnOnLight"
                                    />
                                    <p class="hint">Используй точечную нотацию: <code>Категория.Действие</code></p>
                                </div>
                                <div class="field" style="flex: 1">
                                    <label>Тип навыка</label>
                                    <select v-model="form.type" class="input">
                                        <option value="simple">Простой (фраза → действие)</option>
                                        <option value="dialogue">Диалоговый (многошаговый сценарий)</option>
                                    </select>
                                </div>
                                <div class="field" style="flex: 1">
                                    <label>Категория</label>
                                    <select v-model="form.category" class="input">
                                        <option v-for="(meta, key) in categoryMeta" :key="key" :value="key">
                                            {{ meta.name }}
                                        </option>
                                    </select>
                                </div>
                            </div>
                            <div class="field">
                                <label>Название</label>
                                <input v-model="form.name" class="input" placeholder="Например: Включи свет" />
                            </div>
                            <div class="field">
                                <label>Описание</label>
                                <input v-model="form.description" class="input" placeholder="Что делает навык" />
                            </div>
                        </div>

                        <!-- Шаг 2: Фразы -->
                        <div class="wizard-section">
                            <div class="wizard-step">
                                <span class="step-num">2</span>
                                <span class="step-title">Голосовые фразы</span>
                            </div>
                            <div class="field">
                                <label>Режим распознавания</label>
                                <div class="radio-group">
                                    <label class="radio">
                                        <input type="radio" v-model="form.matchMode" value="contains" />
                                        <span>Фраза содержится (рекомендуется)</span>
                                    </label>
                                    <label class="radio">
                                        <input type="radio" v-model="form.matchMode" value="exact" />
                                        <span>Точное совпадение</span>
                                    </label>
                                    <label class="radio">
                                        <input type="radio" v-model="form.matchMode" value="regex" />
                                        <span>Регулярное выражение</span>
                                    </label>
                                </div>
                            </div>
                            <div class="field">
                                <label>Фразы</label>
                                <div class="phrase-input">
                                    <input
                                        v-model="newPhrase"
                                        @keydown.enter="addPhrase"
                                        class="input"
                                        placeholder='Например: "включи свет в {room}"'
                                    />
                                    <button class="primary-btn sm" @click="addPhrase"><AddIcon /> Добавить</button>
                                </div>
                                <p class="hint">
                                    Используй <code>{имя_слота}</code> для переменных — они будут извлечены и подставлены в действия и ответы.
                                    Слоты автоматически добавятся при добавлении фразы.
                                </p>
                                <div class="phrases-list">
                                    <span v-for="(p, idx) in form.phrases" :key="idx" class="phrase-tag">
                                        <template v-for="part in highlightPhrase(p, form.slots)" :key="part.key">
                                            <span v-if="part.type === 'slot'" class="slot-inline" :style="{ background: part.color + '22', color: part.color, borderColor: part.color }">{{ part.name }}</span>
                                            <span v-else>{{ part.text }}</span>
                                        </template>
                                        <button class="phrase-remove" @click="removePhrase(idx)"><CloseIcon /></button>
                                    </span>
                                    <span v-if="form.phrases.length === 0" class="empty-hint">Добавь хотя бы одну фразу</span>
                                </div>
                            </div>
                        </div>

                        <!-- Шаг 3: Слоты (типизированные) -->
                        <div class="wizard-section">
                            <div class="wizard-step">
                                <span class="step-num">3</span>
                                <span class="step-title">Слоты (типизированные параметры)</span>
                            </div>
                            <p class="hint">Слоты позволяют извлекать структурированные данные из фразы (число, дата, город, локация и т.п.)</p>

                            <div class="phrase-input">
                                <input
                                    v-model="newSlotName"
                                    @keydown.enter="addSlot"
                                    class="input"
                                    placeholder="имя_слота (например: room)"
                                />
                                <select v-model="newSlotType" class="input" style="max-width: 180px">
                                    <option v-for="(meta, t) in slotTypeMeta" :key="t" :value="t">{{ meta.name }}</option>
                                </select>
                                <button class="primary-btn sm" @click="addSlot"><AddIcon /> Добавить слот</button>
                            </div>

                            <div v-if="form.slots.length" class="slots-grid">
                                <div
                                    v-for="slot in form.slots"
                                    :key="slot.id"
                                    class="slot-card"
                                    :style="{ borderLeftColor: slotTypeMeta[slot.type].color }"
                                >
                                    <div class="slot-head">
                                        <div class="slot-name-block">
                                            <component :is="slotTypeMeta[slot.type].icon" :style="{ color: slotTypeMeta[slot.type].color }" />
                                            <input v-model="slot.name" class="input mono sm" />
                                        </div>
                                        <select v-model="slot.type" class="input sm">
                                            <option v-for="(meta, t) in slotTypeMeta" :key="t" :value="t">{{ meta.name }}</option>
                                        </select>
                                        <label class="checkbox">
                                            <input type="checkbox" v-model="slot.required" />
                                            <span>обяз.</span>
                                        </label>
                                        <button class="icon-btn xs danger" @click="removeSlot(slot.id)"><DeleteIcon /></button>
                                    </div>
                                    <div class="slot-body">
                                        <div class="slot-meta">{{ slotTypeMeta[slot.type].desc }} — примеры: <code>{{ slotTypeMeta[slot.type].example }}</code></div>

                                        <div v-if="slot.type === 'list'" class="field">
                                            <label>Допустимые значения (через запятую)</label>
                                            <input
                                                v-model="slot.values"
                                                class="input sm"
                                                placeholder="кухня, спальня, зал"
                                                @input="slot.values = ($event.target as HTMLInputElement).value.split(',').map(s => s.trim()).filter(Boolean)"
                                            />
                                        </div>

                                        <div class="field">
                                            <label>Значение по умолчанию</label>
                                            <input v-model="slot.defaultValue" class="input sm" placeholder="опционально" />
                                        </div>

                                        <div class="field">
                                            <label>Примеры (для обучения, через запятую)</label>
                                            <input
                                                :value="slot.examples.join(', ')"
                                                @input="slot.examples = ($event.target as HTMLInputElement).value.split(',').map(s => s.trim()).filter(Boolean)"
                                                class="input sm"
                                                :placeholder="slotTypeMeta[slot.type].example"
                                            />
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div v-else class="empty-hint center">Слотов пока нет — добавь фразу с {переменной}</div>
                        </div>

                        <!-- Шаг 4: Действия -->
                        <div class="wizard-section">
                            <div class="wizard-step">
                                <span class="step-num">4</span>
                                <span class="step-title">Действия (что выполнить)</span>
                            </div>
                            <div class="actions-list">
                                <div v-for="(action, idx) in form.actions" :key="action.id" class="action-block">
                                    <div class="action-header">
                                        <div class="action-num">{{ idx + 1 }}</div>
                                        <select v-model="action.type" class="input action-type" @change="action.config = defaultActionConfig(action.type)">
                                            <option v-for="(meta, t) in actionTypeMeta" :key="t" :value="t">{{ meta.name }}</option>
                                        </select>
                                        <div class="action-controls">
                                            <button class="icon-btn xs" @click="moveAction(idx, -1)" :disabled="idx === 0">↑</button>
                                            <button class="icon-btn xs" @click="moveAction(idx, 1)" :disabled="idx === form.actions.length - 1">↓</button>
                                            <button class="icon-btn xs danger" @click="removeAction(idx)"><DeleteIcon /></button>
                                        </div>
                                    </div>
                                    <p class="action-desc">{{ actionTypeMeta[action.type].desc }}</p>

                                    <!-- HTTP -->
                                    <template v-if="action.type === 'http'">
                                        <div class="form-row">
                                            <div class="field" style="flex: 0 0 100px">
                                                <label>Метод</label>
                                                <select v-model="action.config.method" class="input">
                                                    <option>GET</option><option>POST</option>
                                                    <option>PUT</option><option>DELETE</option>
                                                </select>
                                            </div>
                                            <div class="field" style="flex: 1">
                                                <label>URL (можно {слот})</label>
                                                <input v-model="action.config.url" class="input" placeholder="https://api.example.com/..." />
                                            </div>
                                        </div>
                                        <div class="field">
                                            <label>Заголовки (JSON)</label>
                                            <input v-model="action.config.headers" class="input mono" placeholder='{"Authorization": "Bearer ..."}' />
                                        </div>
                                        <div class="field" v-if="action.config.method !== 'GET'">
                                            <label>Тело запроса (JSON)</label>
                                            <textarea v-model="action.config.body" class="input mono" rows="3" placeholder='{"text": "{slot}"}'></textarea>
                                        </div>
                                    </template>

                                    <!-- Плагин -->
                                    <template v-if="action.type === 'plugin'">
                                        <div class="form-row">
                                            <div class="field" style="flex: 1">
                                                <label>Плагин</label>
                                                <select v-model="action.config.plugin" class="input">
                                                    <option v-for="p in availablePlugins" :key="p.name" :value="p.name">{{ p.display_name }}</option>
                                                </select>
                                            </div>
                                            <div class="field" style="flex: 1">
                                                <label>Функция</label>
                                                <input v-model="action.config.function" class="input" placeholder="например: set_mute" />
                                            </div>
                                        </div>
                                        <div class="field">
                                            <label>Аргументы (через запятую)</label>
                                            <input v-model="action.config.args" class="input" placeholder="true, {slot}" />
                                        </div>
                                    </template>

                                    <!-- HA -->
                                    <template v-if="action.type === 'ha_service'">
                                        <div class="field">
                                            <label>Домен</label>
                                            <select v-model="haEntityDomain" class="input" @change="fetchHAEntities(haEntityDomain, haEntityFilter)">
                                                <option value="">Все домены</option>
                                                <option v-for="d in haEntityDomains" :key="d" :value="d">{{ d }}</option>
                                            </select>
                                        </div>
                                        <div class="field">
                                            <label>Поиск устройства</label>
                                            <input v-model="haEntityFilter" class="input" placeholder="Фильтр по имени или ID..."
                                                @input="fetchHAEntities(haEntityDomain, haEntityFilter)" />
                                        </div>
                                        <div class="field">
                                            <label>Устройство ({{ availableHAEntities.length }} шт.)</label>
                                            <select v-model="action.config.entity_id" class="input">
                                                <option value="">— выбери —</option>
                                                <option v-for="d in availableHAEntities" :key="d.entity_id" :value="d.entity_id">
                                                    {{ d.name }} ({{ d.state }}{{ d.unit }})
                                                </option>
                                            </select>
                                        </div>
                                        <div class="field">
                                            <label>Сервис</label>
                                            <select v-model="action.config.service" class="input"
                                                @focus="fetchHAServices(action.config.entity_id?.split('.')[0] || '')">
                                                <option value="">— выбери —</option>
                                                <option v-for="s in availableHAServices" :key="s.full" :value="s.full">
                                                    {{ s.name || s.full }}
                                                </option>
                                            </select>
                                        </div>
                                    </template>

                                    <!-- Таймер -->
                                    <template v-if="action.type === 'timer'">
                                        <div class="field">
                                            <label>Длительность (секунд, можно {слот})</label>
                                            <input v-model="action.config.seconds" class="input" placeholder="300 или {minutes} * 60" />
                                        </div>
                                        <div class="field">
                                            <label>Сообщение при срабатывании</label>
                                            <input v-model="action.config.message" class="input" placeholder="Таймер сработал!" />
                                        </div>
                                    </template>

                                    <!-- LLM -->
                                    <template v-if="action.type === 'llm'">
                                        <div class="field">
                                            <label>Системный промпт</label>
                                            <textarea v-model="action.config.system" class="input" rows="2"></textarea>
                                        </div>
                                        <div class="field">
                                            <label>Промпт (можно <code>{слот}</code>)</label>
                                            <textarea v-model="action.config.prompt" class="input" rows="2"></textarea>
                                        </div>
                                    </template>

                                    <!-- Текст -->
                                    <template v-if="action.type === 'text'">
                                        <div class="field">
                                            <label>Текст ответа</label>
                                            <input v-model="action.config.text" class="input" placeholder="Что сказать ассистенту" />
                                        </div>
                                    </template>

                                    <!-- Macro -->
                                    <template v-if="action.type === 'macro'">
                                        <div class="field">
                                            <label>Вложенные навыки (id через запятую)</label>
                                            <input v-model="action.config.skills" class="input" placeholder="id_навыка_1, id_навыка_2" />
                                        </div>
                                    </template>
                                </div>
                            </div>
                            <div class="add-action-row">
                                <span class="add-label">+ Добавить действие:</span>
                                <button
                                    v-for="(meta, t) in actionTypeMeta"
                                    :key="t"
                                    class="add-action-btn"
                                    :style="{ borderColor: meta.color, color: meta.color }"
                                    @click="addAction(t)"
                                >
                                    <component :is="meta.icon" /> {{ meta.name }}
                                </button>
                            </div>
                        </div>

                        <!-- Шаг 5: Реакции -->
                        <div class="wizard-section">
                            <div class="wizard-step">
                                <span class="step-num">5</span>
                                <span class="step-title">Реакции (что ответит ассистент)</span>
                            </div>
                            <p class="hint">Можно задать несколько реакций — ассистент выберет подходящую по ситуации</p>

                            <div class="reactions-list">
                                <div
                                    v-for="(r, idx) in form.reactions"
                                    :key="r.id"
                                    class="reaction-row"
                                >
                                    <div class="reaction-num">{{ idx + 1 }}</div>
                                    <div class="reaction-fields">
                                        <div class="field">
                                            <label><TextIcon /> Текст (можно <code>{слот}</code>, <code>{last_response}</code>)</label>
                                            <input v-model="r.text" class="input" placeholder="Готово!" />
                                        </div>
                                        <div class="form-row">
                                            <div class="field" style="flex: 1">
                                                <label><VolumeIcon /> TTS (озвучка)</label>
                                                <input v-model="r.tts" class="input" placeholder="Текст для озвучки с паузами/эмоциями" />
                                            </div>
                                            <div class="field" style="flex: 0 0 200px">
                                                <label>🔊 Звук</label>
                                                <input v-model="r.sound" class="input" placeholder="ding.mp3" />
                                            </div>
                                        </div>
                                    </div>
                                    <button class="icon-btn danger" @click="removeReaction(r.id)"><DeleteIcon /></button>
                                </div>
                            </div>
                            <button class="ghost-btn sm" @click="addReaction"><AddIcon /> Добавить реакцию</button>
                        </div>

                        <!-- Шаг 6: Сессия -->
                        <div class="wizard-section">
                            <div class="wizard-step">
                                <span class="step-num">6</span>
                                <span class="step-title">Сессия (контекст между вызовами)</span>
                            </div>
                            <div class="form-row">
                                <label class="checkbox big">
                                    <input type="checkbox" v-model="form.session.enabled" />
                                    <span>Включить сессию — ассистент будет помнить контекст для уточнений</span>
                                </label>
                            </div>
                            <div v-if="form.session.enabled" class="field">
                                <label>TTL сессии (секунд)</label>
                                <input v-model.number="form.session.ttl" type="number" class="input" />
                                <p class="hint">Сколько секунд хранить контекст после последнего вызова</p>
                            </div>
                        </div>

                        <!-- Шаг 7: Сценарий диалога (только для dialogue типа) -->
                        <div v-if="form.type === 'dialogue'" class="wizard-section">
                            <div class="wizard-step">
                                <span class="step-num">7</span>
                                <span class="step-title">Сценарий диалога</span>
                            </div>
                            <div class="field">
                                <label>Фразы выхода</label>
                                <input v-model="dialogueExitPhrases" class="input" placeholder="хватит, стоп, пока" />
                                <p class="hint">Через запятую — эти фразы завершают диалог</p>
                            </div>
                            <div class="field">
                                <label>Шаги сценария ({{ form.dialogue?.steps?.length || 0 }})</label>
                            </div>
                            <div v-for="(step, idx) in form.dialogue?.steps || []" :key="idx" class="dialogue-step">
                                <div class="step-header">
                                    <span class="step-badge">{{ idx + 1 }}</span>
                                    <select v-model="step.type" class="input" style="width: 150px">
                                        <option value="intro">Приветствие</option>
                                        <option value="text">Текст</option>
                                        <option value="loop">Цикл</option>
                                        <option value="finale">Финал</option>
                                    </select>
                                    <button class="icon-btn-sm" @click="removeStep(idx)">✕</button>
                                </div>
                                <div class="field">
                                    <label>Текст</label>
                                    <textarea v-model="step.text" class="input" rows="2" placeholder="Что говорит Eva"></textarea>
                                </div>
                                <div v-if="step.type !== 'finale'" class="field">
                                    <label>Вопрос пользователю</label>
                                    <input v-model="step.question" class="input" placeholder="Кого позвал дед?" />
                                </div>
                                <div v-if="step.type === 'loop'" class="field">
                                    <label>Шаблон ответа</label>
                                    <input v-model="step.template" class="input" placeholder="Позвал {prev_character} {user_answer}" />
                                </div>
                                <div v-if="step.type !== 'finale'" class="field">
                                    <label>Следующий шаг</label>
                                    <select v-model="step.next" class="input">
                                        <option v-for="(s, i) in form.dialogue?.steps || []" :key="i" :value="s.id || `step_${i}`">
                                            {{ s.id || `Шаг ${i+1}` }}
                                        </option>
                                    </select>
                                </div>
                            </div>
                            <button class="ghost-btn" @click="addDialogueStep">
                                <AddIcon /> Добавить шаг
                            </button>
                        </div>
                    </div>

                    <div class="modal-footer">
                        <button class="ghost-btn" @click="showForm = false">Отмена</button>
                        <button class="primary-btn" @click="saveForm">
                            <CheckIcon /> Сохранить навык
                        </button>
                    </div>
                </div>
            </div>
        </Teleport>
    </div>
</template>

<style scoped>
.skill-settings { display: flex; flex-direction: column; gap: 16px; }
.skill-settings h2 { font-size: 22px; font-weight: 600; margin-bottom: 4px; display: flex; align-items: center; gap: 10px; }
.subtitle { color: var(--text-secondary); font-size: 13px; }
.header { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; flex-wrap: wrap; }
.header-actions { display: flex; gap: 8px; }

.alice-badge {
    font-size: 10px; padding: 2px 8px; background: var(--accent);
    color: white; border-radius: 8px; font-weight: 600; letter-spacing: 0.5px;
}

.auto-create-panel {
    background: var(--bg-card); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 20px; margin-bottom: 20px;
}
.auto-create-panel h3 { font-size: 16px; font-weight: 600; margin-bottom: 8px; display: flex; align-items: center; gap: 8px; }
.auto-create-panel .hint { font-size: 12px; color: var(--text-muted); margin-bottom: 12px; }
.auto-create-row { display: flex; gap: 8px; }
.auto-create-row .input { flex: 1; }
.auto-create-result { margin-top: 12px; padding: 10px 14px; border-radius: var(--radius-sm); font-size: 13px; }
.auto-create-result.ok { background: rgba(76,175,80,0.1); color: #4caf50; }
.auto-create-result.error { background: rgba(244,67,54,0.1); color: #f44336; }
.ghost-btn.active { background: var(--accent); color: white; }

.primary-btn {
    display: flex; align-items: center; gap: 6px;
    padding: 10px 16px; border-radius: var(--radius-sm);
    background: var(--accent); color: white; border: none;
    font-size: 13px; font-weight: 500; cursor: pointer; transition: background 0.2s, transform 0.2s;
}
.primary-btn:hover:not(:disabled) { background: var(--accent-hover); transform: translateY(-1px); }
.primary-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.primary-btn.sm { padding: 6px 12px; font-size: 12px; }

.ghost-btn {
    display: flex; align-items: center; gap: 6px;
    padding: 10px 16px; border-radius: var(--radius-sm);
    background: transparent; color: var(--text-secondary);
    border: 1px solid var(--border); font-size: 13px; cursor: pointer;
}
.ghost-btn:hover { background: var(--bg-hover); color: var(--text-primary); }
.ghost-btn.sm { padding: 6px 12px; font-size: 12px; }

.stats-row {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 10px;
}
.stat-card {
    background: var(--bg-card); padding: 16px; border-radius: var(--radius);
    text-align: center; border: 1px solid var(--border);
}
.stat-value { font-size: 28px; font-weight: 700; color: var(--accent); }
.stat-label { font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-top: 4px; }

/* MAIN LAYOUT */
.main-layout { display: grid; grid-template-columns: 1fr 380px; gap: 16px; align-items: start; }
.left-col { display: flex; flex-direction: column; gap: 16px; min-width: 0; }

.toolbar { display: flex; flex-direction: column; gap: 12px; }
.search-input {
    display: flex; align-items: center; gap: 8px;
    background: var(--bg-card); padding: 10px 14px;
    border-radius: var(--radius-sm); border: 1px solid var(--border);
}
.search-input input { flex: 1; background: none; border: none; color: var(--text-primary); font-size: 14px; outline: none; }
.categories { display: flex; gap: 6px; flex-wrap: wrap; }
.cat-btn {
    display: flex; align-items: center; gap: 4px;
    padding: 6px 12px; border-radius: 16px;
    background: var(--bg-card); border: 1px solid var(--border);
    color: var(--text-secondary); font-size: 12px; cursor: pointer; transition: all 0.2s;
}
.cat-btn:hover { background: var(--bg-hover); }

.skills-list { display: flex; flex-direction: column; gap: 12px; }
.skill-card {
    background: var(--bg-card); border-radius: var(--radius);
    padding: 16px; display: flex; gap: 16px;
    border: 1px solid var(--border); transition: all 0.2s;
}
.skill-card:hover { border-color: var(--accent); }
.skill-card.disabled { opacity: 0.5; }

.skill-main { flex: 1; min-width: 0; }
.skill-head { margin-bottom: 12px; }
.skill-title-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 6px; }
.skill-title-row h3 { font-size: 16px; font-weight: 600; }
.skill-desc { font-size: 13px; color: var(--text-secondary); margin-top: 4px; }

.intent-badge {
    display: inline-flex; align-items: center; gap: 4px;
    padding: 3px 8px; background: var(--bg-input);
    border: 1px solid var(--border); border-radius: 8px;
    font-family: var(--font-mono); font-size: 11px; color: var(--accent);
}
.intent-badge.small { font-size: 10px; padding: 2px 6px; }

.session-badge {
    display: inline-flex; align-items: center; gap: 4px;
    padding: 3px 8px; background: rgba(76, 175, 80, 0.15);
    color: #4caf50; border-radius: 8px; font-size: 11px;
}

.section-label { font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; }

.phrases-list { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px; }
.phrase-tag {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 4px 10px; background: var(--bg-input);
    color: var(--text-primary); border-radius: 12px; font-size: 12px;
}
.phrase-tag.sm { font-size: 11px; padding: 2px 6px; }
.slot-inline {
    display: inline-block; padding: 0 6px; border: 1px solid;
    border-radius: 4px; font-family: var(--font-mono); font-size: 11px;
    font-weight: 600;
}
.phrase-remove { background: none; border: none; color: var(--text-muted); cursor: pointer; padding: 0; display: flex; }
.phrase-remove:hover { color: var(--color-error); }
.empty-hint { font-size: 12px; color: var(--text-muted); font-style: italic; }
.empty-hint.center { text-align: center; padding: 20px; }

.slots-list { display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 12px; }
.slot-chip {
    display: inline-flex; align-items: center; gap: 4px;
    padding: 2px 8px; background: var(--bg-input);
    border: 1px solid; border-radius: 10px; font-size: 11px;
    font-family: var(--font-mono);
}
.slot-chip.sm { font-size: 10px; padding: 1px 5px; }

.actions-flow {
    display: flex; flex-wrap: wrap; align-items: center; gap: 6px; margin-bottom: 12px;
}
.action-chip {
    display: inline-flex; align-items: center; gap: 4px;
    padding: 4px 10px; background: var(--bg-input);
    border: 1px solid; border-radius: 12px; font-size: 12px; color: var(--text-primary);
}
.action-chip.sm { padding: 2px 6px; }
.arrow { color: var(--text-muted); font-size: 14px; }

.skill-response {
    font-size: 13px; color: var(--text-secondary);
    padding: 8px 12px; background: var(--bg-input);
    border-radius: var(--radius-sm); border-left: 3px solid var(--accent);
    display: flex; align-items: center; justify-content: space-between; gap: 8px;
}
.more-reactions {
    font-size: 11px; padding: 2px 6px; background: var(--accent-dim);
    color: var(--accent); border-radius: 8px;
}

.skill-side {
    display: flex; flex-direction: column; gap: 4px; align-items: center; flex-shrink: 0;
}
.switch { position: relative; width: 36px; height: 20px; display: inline-block; cursor: pointer; }
.switch input { opacity: 0; width: 0; height: 0; }
.switch .slider {
    position: absolute; cursor: pointer; inset: 0;
    background: var(--bg-input); border-radius: 10px; transition: background 0.3s;
}
.switch .slider::before {
    content: ''; position: absolute; height: 14px; width: 14px;
    left: 3px; bottom: 3px; background: white; border-radius: 50%;
    transition: transform 0.3s;
}
.switch input:checked + .slider { background: var(--accent); }
.switch input:checked + .slider::before { transform: translateX(16px); }

.icon-btn {
    display: flex; align-items: center; justify-content: center;
    width: 32px; height: 32px; border-radius: 50%;
    background: none; border: 1px solid var(--border);
    color: var(--text-secondary); cursor: pointer; transition: all 0.2s;
}
.icon-btn:hover { background: var(--bg-hover); color: var(--accent); }
.icon-btn.xs { width: 24px; height: 24px; font-size: 12px; }
.icon-btn.danger:hover { color: var(--color-error); }

.empty-state {
    display: flex; flex-direction: column; align-items: center; gap: 12px;
    padding: 60px 20px; color: var(--text-muted); text-align: center;
}
.empty-icon { font-size: 64px; opacity: 0.3; }
.empty-state h3 { font-size: 18px; color: var(--text-primary); }

/* ALICE CONSOLE */
.alice-console {
    background: var(--bg-card); border: 1px solid var(--border);
    border-radius: var(--radius); position: sticky; top: 80px;
    max-height: calc(100vh - 100px); display: flex; flex-direction: column;
}
.console-header {
    display: flex; align-items: center; gap: 8px;
    padding: 14px 16px; border-bottom: 1px solid var(--border);
    background: var(--bg-input); border-radius: var(--radius) var(--radius) 0 0;
}
.console-header h3 { font-size: 14px; font-weight: 600; flex: 1; }
.console-body { padding: 14px 16px; overflow-y: auto; display: flex; flex-direction: column; gap: 14px; }

.console-input { display: flex; flex-direction: column; gap: 8px; }
.console-input label { font-size: 11px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; }
.console-input textarea { resize: vertical; min-height: 60px; }

.console-output { display: flex; flex-direction: column; gap: 14px; padding-top: 10px; border-top: 1px dashed var(--border); }
.console-section { display: flex; flex-direction: column; gap: 6px; }
.console-label { font-size: 11px; color: var(--text-muted); font-weight: 600; }

.intent-found { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.not-found { font-size: 13px; color: var(--color-error); font-style: italic; }
.muted { font-size: 12px; color: var(--text-muted); font-style: italic; }

.slots-extracted { display: flex; flex-direction: column; gap: 4px; background: var(--bg-input); padding: 8px; border-radius: var(--radius-sm); }
.slot-extracted { display: flex; gap: 8px; font-size: 12px; }
.slot-name { color: var(--accent); font-family: var(--font-mono); font-weight: 600; }
.slot-value { color: var(--text-primary); }

.console-flow { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }
.reaction-block {
    background: var(--bg-input); padding: 10px 12px; border-radius: var(--radius-sm);
    border-left: 3px solid var(--accent);
}
.reaction-text { font-size: 13px; color: var(--text-primary); line-height: 1.4; }
.session-info { font-size: 11px; color: #4caf50; margin-top: 6px; }

/* MODALS */
.modal-overlay {
    position: fixed; inset: 0; background: rgba(0,0,0,0.6);
    backdrop-filter: blur(4px); display: flex; align-items: center;
    justify-content: center; z-index: 1000; padding: 16px;
}
.modal {
    background: var(--bg-secondary); border-radius: var(--radius);
    width: 100%; max-width: 500px; max-height: 90vh;
    display: flex; flex-direction: column; border: 1px solid var(--border);
}
.modal-wide { max-width: 800px; }
.modal-xl { max-width: 760px; }
.modal-header {
    display: flex; justify-content: space-between; align-items: center;
    padding: 16px 20px; border-bottom: 1px solid var(--border);
}
.modal-header h3 { font-size: 16px; font-weight: 600; display: flex; align-items: center; gap: 8px; }
.close-btn {
    width: 32px; height: 32px; border-radius: 50%; border: none;
    background: var(--bg-input); color: var(--text-secondary);
    cursor: pointer; display: flex; align-items: center; justify-content: center;
}
.close-btn:hover { background: var(--bg-hover); }
.modal-body { padding: 20px; overflow-y: auto; }
.modal-footer {
    padding: 16px 20px; border-top: 1px solid var(--border);
    display: flex; gap: 8px; justify-content: flex-end;
}

.templates-grid {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    gap: 12px;
}
.template-card {
    background: var(--bg-card); padding: 14px; border-radius: var(--radius-sm);
    border: 1px solid var(--border); cursor: pointer; transition: all 0.2s;
    display: flex; flex-direction: column; gap: 8px;
}
.template-card:hover { border-color: var(--accent); transform: translateY(-2px); }
.template-card h4 { font-size: 14px; font-weight: 600; }
.template-card p { font-size: 12px; color: var(--text-secondary); line-height: 1.4; }
.template-phrases { display: flex; flex-wrap: wrap; gap: 4px; }
.template-slots { display: flex; flex-wrap: wrap; gap: 4px; }
.template-actions { display: flex; gap: 4px; margin-top: auto; }

/* WIZARD */
.wizard-section {
    background: var(--bg-card); padding: 16px;
    border-radius: var(--radius); margin-bottom: 16px;
}
.wizard-step {
    display: flex; align-items: center; gap: 10px;
    margin-bottom: 12px; padding-bottom: 12px;
    border-bottom: 1px solid var(--border);
}
.step-num {
    width: 24px; height: 24px; border-radius: 50%;
    background: var(--accent); color: white;
    display: flex; align-items: center; justify-content: center;
    font-size: 12px; font-weight: 700;
}
.step-title { font-size: 14px; font-weight: 600; }

.form-row { display: flex; gap: 12px; margin-bottom: 12px; }
.field { margin-bottom: 12px; flex: 1; }
.field label { display: flex; align-items: center; gap: 4px; font-size: 12px; color: var(--text-secondary); margin-bottom: 4px; }
.input {
    width: 100%; padding: 10px 12px;
    border: 1px solid var(--border); border-radius: var(--radius-sm);
    background: var(--bg-input); color: var(--text-primary); font-size: 14px;
}
.input:focus { outline: none; border-color: var(--accent); }
.input.mono { font-family: var(--font-mono); font-size: 12px; }
.input.sm { padding: 6px 10px; font-size: 12px; }
.input.action-type { font-weight: 500; }

.radio-group { display: flex; flex-direction: column; gap: 6px; }
.radio { display: flex; align-items: center; gap: 8px; cursor: pointer; font-size: 13px; }
.radio input { accent-color: var(--accent); }
.radio.inline { font-size: 12px; gap: 4px; }

.mode-switch {
    display: flex; gap: 12px; flex-wrap: wrap;
    padding: 8px 10px; background: var(--bg-input);
    border-radius: var(--radius-sm);
}

.server-status {
    font-size: 12px; padding: 8px 10px; border-radius: var(--radius-sm);
    display: flex; align-items: center; gap: 6px;
}
.server-status.ok       { background: rgba(76, 175, 80, 0.15); color: #4caf50; }
.server-status.error    { background: rgba(244, 67, 54, 0.15); color: #f44336; }
.server-status.no_match { background: rgba(255, 152, 0, 0.15); color: #ff9800; }
.server-status.sending  { background: var(--bg-hover); color: var(--accent); }

.checkbox { display: flex; align-items: center; gap: 6px; cursor: pointer; font-size: 13px; }
.checkbox input { accent-color: var(--accent); }
.checkbox.big { font-size: 13px; padding: 6px 0; }

.hint { font-size: 11px; color: var(--text-muted); margin-top: 4px; }
.hint code { background: var(--bg-input); padding: 1px 4px; border-radius: 3px; font-size: 11px; }

.phrase-input { display: flex; gap: 6px; align-items: center; }
.phrase-input .input { flex: 1; }

.slots-grid { display: flex; flex-direction: column; gap: 8px; margin-top: 10px; }
.slot-card {
    background: var(--bg-input); border-left: 3px solid;
    border-radius: var(--radius-sm); padding: 10px;
    display: flex; flex-direction: column; gap: 8px;
}
.slot-head { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.slot-name-block { display: flex; align-items: center; gap: 6px; flex: 1; min-width: 120px; }
.slot-name-block .input { width: auto; flex: 1; }
.slot-body { display: flex; flex-direction: column; gap: 6px; padding-left: 8px; border-left: 1px dashed var(--border); }
.slot-meta { font-size: 11px; color: var(--text-muted); }
.slot-meta code { background: var(--bg-card); padding: 1px 4px; border-radius: 3px; }

.actions-list { display: flex; flex-direction: column; gap: 12px; }
.action-block {
    background: var(--bg-input); border-radius: var(--radius-sm);
    padding: 12px; border-left: 3px solid var(--accent);
}
.action-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.action-num {
    width: 22px; height: 22px; border-radius: 50%;
    background: var(--accent); color: white;
    display: flex; align-items: center; justify-content: center;
    font-size: 11px; font-weight: 700; flex-shrink: 0;
}
.action-controls { display: flex; gap: 4px; margin-left: auto; }
.action-desc { font-size: 12px; color: var(--text-muted); margin-bottom: 10px; font-style: italic; }

.reactions-list { display: flex; flex-direction: column; gap: 10px; margin-bottom: 12px; }
.reaction-row {
    display: flex; gap: 10px; align-items: flex-start;
    background: var(--bg-input); padding: 10px; border-radius: var(--radius-sm);
    border-left: 3px solid var(--accent);
}
.reaction-num {
    width: 22px; height: 22px; border-radius: 50%;
    background: var(--accent); color: white;
    display: flex; align-items: center; justify-content: center;
    font-size: 11px; font-weight: 700; flex-shrink: 0;
}
.reaction-fields { flex: 1; display: flex; flex-direction: column; gap: 8px; }

.add-action-row {
    display: flex; flex-wrap: wrap; gap: 6px; align-items: center;
    margin-top: 12px; padding: 10px; background: var(--bg-input);
    border-radius: var(--radius-sm);
}
.add-label { font-size: 12px; color: var(--text-secondary); margin-right: 4px; }
.add-action-btn {
    display: inline-flex; align-items: center; gap: 4px;
    padding: 5px 10px; border-radius: 14px;
    background: var(--bg-card); border: 1px dashed;
    font-size: 11px; cursor: pointer; transition: all 0.2s;
}
.add-action-btn:hover { background: var(--bg-hover); }

@keyframes spin { from { transform: rotate(0); } to { transform: rotate(360deg); } }

@media (max-width: 1100px) {
    .main-layout { grid-template-columns: 1fr; }
    .alice-console { position: static; max-height: 500px; }
}

@media (max-width: 640px) {
    .header { flex-direction: column; }
    .header-actions { width: 100%; }
    .form-row { flex-direction: column; }
    .skill-card { flex-direction: column; }
    .skill-side { flex-direction: row; justify-content: flex-end; }
}
</style>
