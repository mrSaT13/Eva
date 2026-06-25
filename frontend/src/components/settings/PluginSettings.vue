<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import CheckIcon from '~icons/material-symbols/check-circle';
import ErrorIcon from '~icons/material-symbols/error';
import LoadingIcon from '~icons/line-md/loading-twotone-loop';
import SaveIcon from '~icons/material-symbols/save';
import CloseIcon from '~icons/material-symbols/close';
import TimerIcon from '~icons/material-symbols/timer';
import CloudIcon from '~icons/material-symbols/cloud';
import PlugIcon from '~icons/material-symbols/extension';
import SystemIcon from '~icons/material-symbols/settings';
import InfoIcon from '~icons/material-symbols/info-outline';
import UploadIcon from '~icons/material-symbols/upload';
import HomeIcon from '~icons/material-symbols/home';
import ChatIcon from '~icons/material-symbols/chat';
import MusicIcon from '~icons/material-symbols/music-note';
import RssIcon from '~icons/material-symbols/rss-feed';
import BotIcon from '~icons/material-symbols/psychology';
import MicIcon from '~icons/material-symbols/mic';
import SpeakerIcon from '~icons/material-symbols/volume-up';
import LanguageIcon from '~icons/material-symbols/language';
import KeyIcon from '~icons/material-symbols/key';
import WebIcon from '~icons/material-symbols/language';
import TtsIcon from '~icons/material-symbols/record-voice-over';

interface Plugin {
    scope: string;
    config: any;
    comment?: string;
    enabled?: boolean;
}

const plugins = ref<Plugin[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);
const activeTab = ref<'connected' | 'system'>('connected');

const pluginMeta: Record<string, { name: string; icon: any; desc: string }> = {
    'plugin_timer': { name: 'Таймер', icon: TimerIcon, desc: 'Голосовые таймеры с оповещениями. Скажите "таймер на 5 минут".' },
    'integrations': { name: 'Интеграции', icon: PlugIcon, desc: 'FreshRSS, RSS ленты, Navidrome, погода, Википедия.' },
    'rooms': { name: 'Комнаты', icon: HomeIcon, desc: 'Управление устройствами по комнатам из Home Assistant.' },
    'voice_commands': { name: 'Голосовые команды', icon: ChatIcon, desc: 'Привязка голосовых команд к автоматизациям и макросы с переменными.' },
    'voice_profiles': { name: 'Голосовые профили', icon: SpeakerIcon, desc: 'Выбор голоса и настройки озвучки ответов.' },
    'automations': { name: 'Автоматизации', icon: SystemIcon, desc: 'Сценарии автоматизации: триггеры по времени, состоянию, команде.' },
    'ha_images': { name: 'Камеры HA', icon: CloudIcon, desc: 'Просмотр камер Home Assistant в чате.' },
    'greetings': { name: 'Приветствия', icon: ChatIcon, desc: 'Приветствия, благодарности, прощания и знакомство.' },
    'command_aliases': { name: 'Алиасы команд', icon: KeyIcon, desc: 'Создание коротких команд-заменителей.' },
    'plugin_date': { name: 'Дата', icon: SystemIcon, desc: 'Текущая дата. Скажите "какая дата".' },
    'skill_time': { name: 'Время', icon: TimerIcon, desc: 'Текущее время. Скажите "сколько времени".' },
    'plugin_random': { name: 'Случайное число', icon: SystemIcon, desc: 'Подброс монетки, бросок кубика.' },
    'brain': { name: 'Мозг', icon: BotIcon, desc: 'Ядро диалога и обработка команд.' },
    'vosk_model_loader': { name: 'VOSK модель', icon: MicIcon, desc: 'Загрузка модели распознавания речи.' },
    'vosk_sherpa': { name: 'Sherpa ONNX', icon: MicIcon, desc: 'ONNX модели для распознавания речи.' },
    'tts_cache': { name: 'Кеш TTS', icon: SpeakerIcon, desc: 'Кеширование озвучки для ускорения.' },
    'plugin_tts_edge': { name: 'Edge TTS', icon: SpeakerIcon, desc: 'Озвучка Microsoft Edge (бесплатно, качественно).' },
    'plugin_tts_openai': { name: 'OpenAI TTS', icon: SpeakerIcon, desc: 'Озвучка OpenAI (требует API ключ).' },
    'plugin_tts_pyttsx': { name: 'pyttsx3 TTS', icon: SpeakerIcon, desc: 'Локальная озвучка через pyttsx3.' },
    'plugin_out_tts_serverside': { name: 'Серверный TTS', icon: SpeakerIcon, desc: 'Озвучка на стороне сервера для веб-клиента.' },
    'llm_fallback_context': { name: 'LLM Fallback', icon: BotIcon, desc: 'Обработка неизвестных команд через ИИ.' },
    'llm_ollama': { name: 'Ollama LLM', icon: BotIcon, desc: 'Локальный ИИ через Ollama.' },
    'llm_openai': { name: 'OpenAI LLM', icon: BotIcon, desc: 'ИИ через OpenAI API.' },
    'llm_lmstudio': { name: 'LM Studio', icon: BotIcon, desc: 'Локальный ИИ через LM Studio.' },
    'ai_skill_timer': { name: 'AI Таймер', icon: TimerIcon, desc: 'ИИ-инструмент для установки таймеров.' },
    'ai_skill_datetime': { name: 'AI Дата/Время', icon: TimerIcon, desc: 'ИИ-инструмент для получения даты и времени.' },
    'ai_skill_weather': { name: 'AI Погода', icon: CloudIcon, desc: 'ИИ-инструмент для получения погоды.' },
    'web_authentication': { name: 'Веб-авторизация', icon: KeyIcon, desc: 'Авторизация в веб-интерфейсе.' },
    'web_face_frontend': { name: 'Веб-интерфейс', icon: WebIcon, desc: 'Фронтенд веб-интерфейса.' },
    'face_web_server': { name: 'Веб-сервер', icon: WebIcon, desc: 'HTTP сервер для веб-интерфейса.' },
    'telegram_auth': { name: 'Telegram Auth', icon: ChatIcon, desc: 'Авторизация Telegram бота.' },
    'face_telegram': { name: 'Telegram бот', icon: ChatIcon, desc: 'Интерфейс Telegram бота.' },
    'telegram_input_audio': { name: 'Telegram аудио ввод', icon: MicIcon, desc: 'Голосовые сообщения из Telegram.' },
    'telegram_output_audio': { name: 'Telegram аудио вывод', icon: SpeakerIcon, desc: 'Озвучка ответов в Telegram.' },
    'telegram_io_plaintext': { name: 'Telegram текст', icon: ChatIcon, desc: 'Текстовые сообщения в Telegram.' },
    'local_input_sounddevice_vosk': { name: 'Локальный микрофон', icon: MicIcon, desc: 'Захват звука с микрофона через VOSK.' },
    'local_output_sounddevice': { name: 'Локальный динамик', icon: SpeakerIcon, desc: 'Воспроизведение звука через динамик.' },
    'translation_provider_libretranslate': { name: 'Переводчик', icon: LanguageIcon, desc: 'Перевод текста через LibreTranslate.' },
    'skill_translate': { name: 'Команда перевода', icon: LanguageIcon, desc: 'Голосовая команда "переведи ...".' },
    'plugin_language': { name: 'Язык', icon: LanguageIcon, desc: 'Определение языка сообщений.' },
    'plugin_global_mute_group': { name: 'Глобальная тишина', icon: SpeakerIcon, desc: 'Приостановка всех выходов.' },
    'plugin_audio_converter_ffmpeg': { name: 'Конвертер FFmpeg', icon: SystemIcon, desc: 'Конвертация аудио через FFmpeg.' },
    'plugin_audio_converter_soundfile': { name: 'Конвертер SoundFile', icon: SystemIcon, desc: 'Конвертация аудио через SoundFile.' },
    'remote_text_protocols': { name: 'Удалённые протоколы', icon: WebIcon, desc: 'Протоколы для удалённых текстовых клиентов.' },
    'original_plugin_loader': { name: 'Загрузчик плагинов', icon: PlugIcon, desc: 'Загрузка legacy-плагинов VACore.' },
    'logging': { name: 'Логирование', icon: SystemIcon, desc: 'Настройки логов приложения.' },
    'config': { name: 'Конфигурация', icon: SystemIcon, desc: 'Система конфигурации плагинов.' },
    'face_console': { name: 'Консоль', icon: SystemIcon, desc: 'Консольный интерфейс ввода/вывода.' },
    'ai_skill_timer': { name: 'AI Таймер', icon: TimerIcon, desc: 'ИИ-инструмент для таймеров.' },
    'ai_skill_datetime': { name: 'AI Дата/Время', icon: TimerIcon, desc: 'ИИ-инструмент для даты/времени.' },
    'ai_skill_weather': { name: 'AI Погода', icon: CloudIcon, desc: 'ИИ-инструмент для погоды.' },
};

const systemScopes = new Set([
    'brain', 'vosk_model_loader', 'vosk_sherpa', 'tts_cache',
    'plugin_tts_edge', 'plugin_tts_openai', 'plugin_tts_pyttsx',
    'plugin_out_tts_serverside', 'plugin_global_mute_group',
    'plugin_language', 'logging', 'config', 'face_console',
    'plugin_audio_converter_ffmpeg', 'plugin_audio_converter_soundfile',
    'remote_text_protocols', 'original_plugin_loader',
    'llm_fallback_context', 'llm_ollama', 'llm_openai', 'llm_lmstudio',
    'ai_skill_timer', 'ai_skill_datetime', 'ai_skill_weather',
    'web_authentication', 'web_face_frontend', 'face_web_server',
    'telegram_auth', 'face_telegram', 'telegram_input_audio',
    'telegram_output_audio', 'telegram_io_plaintext',
    'local_input_sounddevice_vosk', 'local_output_sounddevice',
    'translation_provider_libretranslate', 'skill_translate',
]);

const connectedPlugins = computed(() =>
    plugins.value.filter(p => !systemScopes.has(p.scope))
);
const systemPlugins = computed(() =>
    plugins.value.filter(p => systemScopes.has(p.scope))
);
const displayPlugins = computed(() =>
    activeTab.value === 'connected' ? connectedPlugins.value : systemPlugins.value
);

const showTimerSettings = ref(false);
const timerConfig = ref({ notify_sound: true, notify_text: 'Таймер сработал! Прошло {time}', notify_services: false, notify_services_list: [] as string[] });
const timerSaving = ref(false);

const showWeatherSettings = ref(false);
const weatherConfig = ref({ weather_city: 'Moscow' });
const weatherSaving = ref(false);

const showPluginConfig = ref(false);
const selectedPlugin = ref<Plugin | null>(null);
const editConfigText = ref('');
const configSaving = ref(false);

const showInfo = ref(false);
const infoPlugin = ref<Plugin | null>(null);

const showUpload = ref(false);
const uploadFile = ref<File | null>(null);
const uploadStatus = ref('');
const userPlugins = ref<any[]>([]);
const showUserPluginSettings = ref(false);
const editingUserPlugin = ref<any>(null);
const editConfigValues = ref<Record<string, string>>({});
const editSaving = ref(false);

const timerServices = [
    { id: 'ha', name: 'Home Assistant', icon: HomeIcon, desc: 'Уведомление через HA' },
    { id: 'telegram', name: 'Telegram', icon: ChatIcon, desc: 'Отправка в Telegram' },
    { id: 'freshrss', name: 'FreshRSS', icon: RssIcon, desc: 'Уведомление FreshRSS' },
    { id: 'navidrome', name: 'Navidrome', icon: MusicIcon, desc: 'Уведомление Navidrome' },
];

const fetchPlugins = async () => {
    try {
        const res = await fetch('/api/config/configs');
        if (res.ok) plugins.value = await res.json();
    } catch (e: any) { error.value = e.message; }
    finally { loading.value = false; }
};

const fetchUserPlugins = async () => {
    try {
        const res = await fetch('/api/discover_plugins/plugins/user');
        if (res.ok) userPlugins.value = await res.json();
    } catch {}
};

const togglePlugin = async (plugin: Plugin) => {
    try {
        await fetch(`/api/config/configs/${plugin.scope}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled: !plugin.enabled }),
        });
        plugin.enabled = !plugin.enabled;
    } catch (e: any) { error.value = e.message; }
};

const openTimerSettings = async () => {
    try {
        const r = await fetch('/api/timer/config');
        if (r.ok) {
            const data = await r.json();
            timerConfig.value = { ...timerConfig.value, ...data };
            if (!Array.isArray(timerConfig.value.notify_services_list)) timerConfig.value.notify_services_list = [];
        }
    } catch {}
    showTimerSettings.value = true;
};

const saveTimerSettings = async () => {
    timerSaving.value = true;
    try {
        await fetch('/api/timer/config', {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(timerConfig.value),
        });
        setTimeout(() => { timerSaving.value = false; showTimerSettings.value = false; }, 800);
    } catch { timerSaving.value = false; }
};

const openWeatherSettings = async () => {
    const p = plugins.value.find(p => p.scope === 'integrations');
    if (p?.config?.weather_city) weatherConfig.value.weather_city = p.config.weather_city;
    showWeatherSettings.value = true;
};

const saveWeatherSettings = async () => {
    weatherSaving.value = true;
    try {
        await fetch('/api/config/configs/integrations', {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ weather_city: weatherConfig.value.weather_city }),
        });
        setTimeout(() => { weatherSaving.value = false; showWeatherSettings.value = false; }, 800);
    } catch { weatherSaving.value = false; }
};

const openPluginConfig = (plugin: Plugin) => {
    selectedPlugin.value = plugin;
    editConfigText.value = JSON.stringify(plugin.config, null, 2);
    showPluginConfig.value = true;
};

const savePluginConfig = async () => {
    if (!selectedPlugin.value) return;
    configSaving.value = true;
    try {
        const parsed = JSON.parse(editConfigText.value);
        await fetch(`/api/config/configs/${selectedPlugin.value.scope}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(parsed),
        });
        selectedPlugin.value.config = parsed;
        setTimeout(() => { configSaving.value = false; showPluginConfig.value = false; }, 800);
    } catch (e: any) { error.value = 'Ошибка JSON: ' + e.message; configSaving.value = false; }
};

const toggleService = (serviceId: string) => {
    const list = timerConfig.value.notify_services_list;
    const idx = list.indexOf(serviceId);
    if (idx >= 0) list.splice(idx, 1);
    else list.push(serviceId);
};

const openInfo = (plugin: Plugin) => {
    infoPlugin.value = plugin;
    showInfo.value = true;
};

const handleUpload = async () => {
    if (!uploadFile.value) return;
    uploadStatus.value = 'Загрузка и установка зависимостей...';
    const formData = new FormData();
    formData.append('file', uploadFile.value);
    try {
        const r = await fetch('/api/discover_plugins/plugins/upload', { method: 'POST', body: formData });
        const data = await r.json();
        if (data.status === 'ok') {
            let msg = `Загружено: ${data.filename}`;
            if (data.installed && data.installed.length > 0) {
                msg += `. Установлены: ${data.installed.join(', ')}`;
            }
            if (data.missing && data.missing.length > 0 && data.installed?.length !== data.missing.length) {
                const failed = data.missing.filter((m: string) => !data.installed?.includes(m));
                if (failed.length) msg += `. Не удалось: ${failed.join(', ')}`;
            }
            msg += '. Перезапустите для применения.';
            uploadStatus.value = msg;
            uploadFile.value = null;
            await fetchUserPlugins();
            setTimeout(() => { showUpload.value = false; uploadStatus.value = ''; }, 5000);
        } else {
            uploadStatus.value = 'Ошибка: ' + (data.error || 'неизвестная');
        }
    } catch {
        uploadStatus.value = 'Ошибка сети';
    }
};

const openUserPluginSettings = (plugin: any) => {
    editingUserPlugin.value = plugin;
    editConfigValues.value = {};
    for (const field of plugin.config_fields || []) {
        editConfigValues.value[field.key] = field.value;
    }
    showUserPluginSettings.value = true;
};

const saveUserPluginConfig = async () => {
    if (!editingUserPlugin.value) return;
    editSaving.value = true;
    try {
        const r = await fetch(`/api/discover_plugins/plugins/user/${editingUserPlugin.value.filename}`);
        const data = await r.json();
        let source = data.source || '';
        for (const [key, val] of Object.entries(editConfigValues.value)) {
            const regex = new RegExp(`(['"]${key}['"]\\s*:\\s*)(True|False|['"])(.+?)\\2`, 'm');
            const regexBool = new RegExp(`(['"]${key}['"]\\s*:\\s*)(True|False)`, 'm');
            if (val === 'True' || val === 'False') {
                source = source.replace(regexBool, `$1${val}`);
            } else {
                source = source.replace(regex, `$1$2${val}$2`);
            }
        }
        await fetch(`/api/discover_plugins/plugins/user/${editingUserPlugin.value.filename}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ source }),
        });
        await fetchUserPlugins();
        setTimeout(() => { editSaving.value = false; showUserPluginSettings.value = false; }, 800);
    } catch { editSaving.value = false; }
};

const deleteUserPlugin = async (filename: string) => {
    if (!confirm('Удалить плагин?')) return;
    try {
        await fetch(`/api/discover_plugins/plugins/user/${filename}`, { method: 'DELETE' });
        await fetchUserPlugins();
    } catch {}
};

const getMeta = (scope: string) => pluginMeta[scope] || { name: scope, icon: PlugIcon, desc: 'Плагин без описания' };

onMounted(() => {
    fetchPlugins();
    fetchUserPlugins();
});
</script>

<template>
    <div class="plugin-settings">
        <div class="header-row">
            <div>
                <h2>Плагины</h2>
                <p class="subtitle">Управление плагинами и настройками</p>
            </div>
            <button class="upload-btn" @click="showUpload = true">
                <UploadIcon /> Загрузить плагин
            </button>
        </div>

        <div class="tabs">
            <button class="tab" :class="{ active: activeTab === 'connected' }" @click="activeTab = 'connected'">
                <PlugIcon /> Подключённые
            </button>
            <button class="tab" :class="{ active: activeTab === 'system' }" @click="activeTab = 'system'">
                <SystemIcon /> Системные
            </button>
        </div>

        <div v-if="loading" class="loading"><LoadingIcon class="spin" /></div>
        <div v-else-if="error" class="error"><ErrorIcon /> {{ error }}</div>

        <div v-else class="plugins-grid">
            <div v-for="plugin in displayPlugins" :key="plugin.scope" class="plugin-tile" :class="{ disabled: plugin.enabled === false }">
                <div class="tile-header">
                    <div class="tile-icon">
                        <component :is="getMeta(plugin.scope).icon" />
                    </div>
                    <label class="toggle">
                        <input type="checkbox" :checked="plugin.enabled !== false" @change="togglePlugin(plugin)" />
                        <span class="toggle-slider"></span>
                    </label>
                </div>
                <div class="tile-name">{{ getMeta(plugin.scope).name }}</div>
                <div class="tile-desc">{{ getMeta(plugin.scope).desc }}</div>
                <div class="tile-actions">
                    <button v-if="plugin.scope === 'plugin_timer'" class="action-btn" @click="openTimerSettings">
                        <TimerIcon /> Настройки
                    </button>
                    <button v-if="plugin.scope === 'integrations'" class="action-btn" @click="openWeatherSettings">
                        <CloudIcon /> Погода
                    </button>
                    <button class="icon-btn" @click="openInfo(plugin)" title="Информация">
                        <InfoIcon />
                    </button>
                    <button class="icon-btn" @click="openPluginConfig(plugin)" title="JSON конфигурация">
                        ⚙️
                    </button>
                </div>
            </div>
        </div>

        <div v-if="activeTab === 'connected' && userPlugins.length > 0" class="user-plugins-section">
            <h3>Загруженные плагины</h3>
            <p class="section-hint">Плагины из папки plugins. Изменения вступят в силу после перезапуска.</p>
            <div class="plugins-grid">
                <div v-for="p in userPlugins" :key="p.filename" class="plugin-tile user-plugin">
                    <div class="tile-header">
                        <div class="tile-icon user-icon"><PlugIcon /></div>
                    </div>
                    <div class="tile-name">{{ p.display_name }}</div>
                    <div v-if="p.version" class="tile-version">v{{ p.version }}</div>
                    <div class="tile-desc">{{ p.description || p.filename }}</div>
                    <div v-if="p.commands && p.commands.length" class="tile-commands">
                        <span v-for="cmd in p.commands.slice(0, 5)" :key="cmd" class="cmd-tag">{{ cmd }}</span>
                        <span v-if="p.commands.length > 5" class="cmd-more">+{{ p.commands.length - 5 }}</span>
                    </div>
                    <div class="tile-meta">{{ p.modified }} · {{ Math.round(p.size / 1024) }} KB</div>
                    <div class="tile-actions">
                        <button v-if="p.config_fields && p.config_fields.length" class="action-btn" @click="openUserPluginSettings(p)">
                            <SettingsIcon /> Настройки
                        </button>
                        <button class="icon-btn" @click="openInfo(p)" title="Информация">
                            <InfoIcon />
                        </button>
                        <button class="icon-btn danger" @click="deleteUserPlugin(p.filename)" title="Удалить">🗑️</button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <Teleport to="body">
        <!-- Timer Settings -->
        <div v-if="showTimerSettings" class="modal-overlay" @click.self="showTimerSettings = false">
            <div class="modal">
                <div class="modal-header">
                    <h3><TimerIcon /> Настройки таймера</h3>
                    <button class="close-btn" @click="showTimerSettings = false"><CloseIcon /></button>
                </div>
                <div class="modal-body">
                    <div class="setting-row">
                        <label class="toggle-row">
                            <span>Звуковое оповещение</span>
                            <label class="toggle"><input type="checkbox" v-model="timerConfig.notify_sound" /><span class="toggle-slider"></span></label>
                        </label>
                    </div>
                    <div class="setting-row">
                        <label>Текст оповещения</label>
                        <input v-model="timerConfig.notify_text" type="text" class="input" />
                        <p class="hint">Переменная: {time} — время таймера</p>
                    </div>
                    <div class="setting-row">
                        <label class="toggle-row">
                            <span>Отправлять уведомления</span>
                            <label class="toggle"><input type="checkbox" v-model="timerConfig.notify_services" /><span class="toggle-slider"></span></label>
                        </label>
                    </div>
                    <div v-if="timerConfig.notify_services" class="services-section">
                        <p class="section-label">Выберите сервисы:</p>
                        <div v-for="svc in timerServices" :key="svc.id" class="service-item" @click="toggleService(svc.id)">
                            <label class="checkbox-row">
                                <input type="checkbox" :checked="timerConfig.notify_services_list.includes(svc.id)" @click.stop />
                                <span class="svc-icon-wrap"><component :is="svc.icon" /></span>
                                <span class="svc-info">
                                    <span class="svc-name">{{ svc.name }}</span>
                                    <span class="svc-desc">{{ svc.desc }}</span>
                                </span>
                            </label>
                        </div>
                    </div>
                    <div class="modal-actions">
                        <button class="cancel-btn" @click="showTimerSettings = false">Отмена</button>
                        <button class="save-btn" @click="saveTimerSettings"><CheckIcon v-if="timerSaving" /> {{ timerSaving ? '✓' : 'Сохранить' }}</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Weather Settings -->
        <div v-if="showWeatherSettings" class="modal-overlay" @click.self="showWeatherSettings = false">
            <div class="modal">
                <div class="modal-header">
                    <h3><CloudIcon /> Настройки погоды</h3>
                    <button class="close-btn" @click="showWeatherSettings = false"><CloseIcon /></button>
                </div>
                <div class="modal-body">
                    <div class="setting-row">
                        <label>Город по умолчанию</label>
                        <input v-model="weatherConfig.weather_city" type="text" class="input" placeholder="Moscow" />
                    </div>
                    <p class="hint">Голос: "погода" или "погода в Москве"</p>
                    <div class="modal-actions">
                        <button class="cancel-btn" @click="showWeatherSettings = false">Отмена</button>
                        <button class="save-btn" @click="saveWeatherSettings"><CheckIcon v-if="weatherSaving" /> {{ weatherSaving ? '✓' : 'Сохранить' }}</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Info Modal -->
        <div v-if="showInfo && infoPlugin" class="modal-overlay" @click.self="showInfo = false">
            <div class="modal">
                <div class="modal-header">
                    <h3><InfoIcon /> {{ getMeta(infoPlugin.scope).name }}</h3>
                    <button class="close-btn" @click="showInfo = false"><CloseIcon /></button>
                </div>
                <div class="modal-body">
                    <p class="info-desc">{{ getMeta(infoPlugin.scope).desc }}</p>
                    <div class="info-row"><span class="info-label">Scope:</span> <code>{{ infoPlugin.scope }}</code></div>
                    <div class="info-row"><span class="info-label">Статус:</span> {{ infoPlugin.enabled !== false ? '✅ Включён' : '❌ Выключен' }}</div>
                    <div v-if="infoPlugin.comment" class="info-row"><span class="info-label">Описание:</span> {{ infoPlugin.comment }}</div>
                    <div class="modal-actions">
                        <button class="cancel-btn" @click="showInfo = false">Закрыть</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Plugin Config -->
        <div v-if="showPluginConfig" class="modal-overlay" @click.self="showPluginConfig = false">
            <div class="modal">
                <div class="modal-header">
                    <h3>⚙️ {{ selectedPlugin?.scope }}</h3>
                    <button class="close-btn" @click="showPluginConfig = false"><CloseIcon /></button>
                </div>
                <div class="modal-body">
                    <textarea v-model="editConfigText" class="config-textarea" rows="14"></textarea>
                    <p class="hint">JSON конфигурация. Изменяйте осторожно.</p>
                    <div class="modal-actions">
                        <button class="cancel-btn" @click="showPluginConfig = false">Отмена</button>
                        <button class="save-btn" @click="savePluginConfig"><SaveIcon /> {{ configSaving ? '✓' : 'Сохранить' }}</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Upload Plugin -->
        <div v-if="showUpload" class="modal-overlay" @click.self="showUpload = false">
            <div class="modal">
                <div class="modal-header">
                    <h3><UploadIcon /> Загрузить плагин</h3>
                    <button class="close-btn" @click="showUpload = false"><CloseIcon /></button>
                </div>
                <div class="modal-body">
                    <p class="info-desc">Загрузите Python-файл плагина (.py). Зависимости установятся автоматически.</p>
                    <div class="upload-area">
                        <input type="file" accept=".py" @change="(e: any) => uploadFile = e.target.files[0]" class="file-input" />
                        <p v-if="uploadFile" class="file-name">{{ uploadFile.name }}</p>
                        <p v-else class="file-hint">Нажмите или перетащите файл .py</p>
                    </div>
                    <p v-if="uploadStatus" class="upload-status" :class="{ ok: uploadStatus.includes('Загружено') }">{{ uploadStatus }}</p>
                    <div class="modal-actions">
                        <button class="cancel-btn" @click="showUpload = false">Отмена</button>
                        <button class="save-btn" @click="handleUpload" :disabled="!uploadFile"><UploadIcon /> Загрузить</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Edit User Plugin Settings -->
        <div v-if="showUserPluginSettings && editingUserPlugin" class="modal-overlay" @click.self="showUserPluginSettings = false">
            <div class="modal">
                <div class="modal-header">
                    <h3><SettingsIcon /> {{ editingUserPlugin.display_name }}</h3>
                    <button class="close-btn" @click="showUserPluginSettings = false"><CloseIcon /></button>
                </div>
                <div class="modal-body">
                    <p class="info-desc">{{ editingUserPlugin.description || 'Настройки плагина' }}</p>
                    <div v-if="editingUserPlugin.commands && editingUserPlugin.commands.length" class="plugin-commands-section">
                        <p class="section-label">Команды:</p>
                        <div class="commands-list">
                            <span v-for="cmd in editingUserPlugin.commands" :key="cmd" class="cmd-tag">"{{ cmd }}"</span>
                        </div>
                    </div>
                    <div v-if="editingUserPlugin.config_fields && editingUserPlugin.config_fields.length" class="config-section">
                        <p class="section-label">Настройки:</p>
                        <div v-for="field in editingUserPlugin.config_fields" :key="field.key" class="config-field">
                            <label v-if="field.type === 'bool'" class="toggle-row">
                                <span>{{ field.label }}</span>
                                <label class="toggle">
                                    <input type="checkbox" :checked="editConfigValues[field.key] === 'True'" @change="editConfigValues[field.key] = ($event.target as HTMLInputElement).checked ? 'True' : 'False'" />
                                    <span class="toggle-slider"></span>
                                </label>
                            </label>
                            <template v-else>
                                <label>{{ field.label }}</label>
                                <input v-model="editConfigValues[field.key]" :type="field.type === 'number' ? 'number' : 'text'" class="input" />
                            </template>
                        </div>
                    </div>
                    <div v-else class="no-config">
                        <p>Этот плагин не имеет настраиваемых параметров.</p>
                    </div>
                    <div class="modal-actions">
                        <button class="cancel-btn" @click="showUserPluginSettings = false">Отмена</button>
                        <button v-if="editingUserPlugin.config_fields && editingUserPlugin.config_fields.length" class="save-btn" @click="saveUserPluginConfig"><SaveIcon /> {{ editSaving ? '✓' : 'Сохранить' }}</button>
                    </div>
                </div>
            </div>
        </div>
    </Teleport>
</template>

<style scoped>
.plugin-settings h2 { font-size: 20px; font-weight: 600; margin-bottom: 4px; }
.subtitle { color: var(--text-secondary); font-size: 13px; }
.header-row { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; }
.upload-btn { display: flex; align-items: center; gap: 6px; padding: 8px 16px; border-radius: var(--radius-sm); border: 1px dashed var(--accent); background: transparent; color: var(--accent); font-size: 13px; cursor: pointer; }
.upload-btn:hover { background: var(--accent-dim); }

.tabs { display: flex; gap: 4px; margin-bottom: 20px; background: var(--bg-input); border-radius: var(--radius); padding: 4px; }
.tab { flex: 1; display: flex; align-items: center; justify-content: center; gap: 6px; padding: 10px 16px; border-radius: var(--radius-sm); border: none; background: transparent; color: var(--text-secondary); font-size: 13px; font-weight: 500; cursor: pointer; transition: all 0.2s; }
.tab.active { background: var(--accent); color: white; }
.tab:hover:not(.active) { background: var(--bg-hover); }

.loading { display: flex; justify-content: center; padding: 40px; }
.spin { font-size: 32px; color: var(--accent); animation: spin 1s linear infinite; }
.error { display: flex; align-items: center; gap: 8px; color: #f44336; padding: 20px; }

.plugins-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 12px; }
.plugin-tile { background: var(--bg-card); border-radius: var(--radius); padding: 16px; display: flex; flex-direction: column; gap: 6px; border: 1px solid var(--border); transition: all 0.2s; }
.plugin-tile:hover { border-color: var(--accent); }
.plugin-tile.disabled { opacity: 0.5; }

.tile-header { display: flex; justify-content: space-between; align-items: center; }
.tile-icon { width: 40px; height: 40px; border-radius: 10px; background: var(--accent-dim); color: var(--accent); display: flex; align-items: center; justify-content: center; font-size: 20px; }
.tile-name { font-size: 13px; font-weight: 600; }
.tile-desc { font-size: 11px; color: var(--text-muted); line-height: 1.4; flex: 1; }
.tile-actions { display: flex; gap: 4px; margin-top: 4px; }
.action-btn { display: flex; align-items: center; gap: 4px; padding: 4px 10px; border-radius: var(--radius-sm); border: 1px solid var(--border); background: var(--bg-input); color: var(--text-secondary); font-size: 11px; cursor: pointer; }
.action-btn:hover { border-color: var(--accent); color: var(--accent); }
.icon-btn { width: 28px; height: 28px; border-radius: 50%; border: 1px solid var(--border); background: var(--bg-input); cursor: pointer; font-size: 14px; display: flex; align-items: center; justify-content: center; color: var(--text-secondary); }
.icon-btn:hover { border-color: var(--accent); color: var(--accent); }

.toggle { position: relative; width: 40px; height: 22px; flex-shrink: 0; }
.toggle input { opacity: 0; width: 0; height: 0; }
.toggle-slider { position: absolute; cursor: pointer; inset: 0; background: var(--bg-input); border-radius: 11px; transition: background 0.3s; }
.toggle-slider::before { content: ''; position: absolute; height: 16px; width: 16px; left: 3px; bottom: 3px; background: var(--text-primary); border-radius: 50%; transition: transform 0.3s; }
.toggle input:checked + .toggle-slider { background: var(--accent); }
.toggle input:checked + .toggle-slider::before { transform: translateX(18px); }

.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); backdrop-filter: blur(4px); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal { background: var(--bg-secondary); border-radius: var(--radius); width: 90%; max-width: 460px; border: 1px solid var(--border); }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; border-bottom: 1px solid var(--border); }
.modal-header h3 { font-size: 16px; font-weight: 600; display: flex; align-items: center; gap: 8px; }
.close-btn { width: 32px; height: 32px; border-radius: 50%; border: none; background: var(--bg-input); color: var(--text-secondary); cursor: pointer; display: flex; align-items: center; justify-content: center; }
.close-btn:hover { background: var(--bg-hover); }
.modal-body { padding: 20px; }

.setting-row { margin-bottom: 16px; }
.setting-row label { display: block; font-size: 13px; font-weight: 500; margin-bottom: 6px; }
.toggle-row { display: flex; justify-content: space-between; align-items: center; cursor: pointer; }
.input { width: 100%; padding: 10px 12px; border: 1px solid var(--border); border-radius: var(--radius-sm); background: var(--bg-input); color: var(--text-primary); font-size: 14px; }
.input:focus { outline: none; border-color: var(--accent); }
.hint { font-size: 11px; color: var(--text-muted); margin-top: 4px; }

.services-section { margin: 12px 0; }
.section-label { font-size: 12px; color: var(--text-muted); margin-bottom: 8px; }
.service-item { padding: 10px 12px; border-radius: var(--radius-sm); cursor: pointer; border: 1px solid var(--border); margin-bottom: 6px; }
.service-item:hover { border-color: var(--accent); background: var(--accent-dim); }
.checkbox-row { display: flex; align-items: center; gap: 10px; cursor: pointer; }
.checkbox-row input { accent-color: var(--accent); width: 16px; height: 16px; }
.svc-icon-wrap { color: var(--accent); display: flex; align-items: center; }
.svc-info { display: flex; flex-direction: column; }
.svc-name { font-size: 13px; font-weight: 500; }
.svc-desc { font-size: 11px; color: var(--text-muted); }

.info-desc { font-size: 14px; color: var(--text-primary); margin-bottom: 16px; line-height: 1.5; }
.info-row { font-size: 13px; margin-bottom: 8px; color: var(--text-secondary); }
.info-label { font-weight: 500; color: var(--text-primary); }
.info-row code { background: var(--bg-input); padding: 2px 6px; border-radius: 4px; font-size: 12px; }

.config-textarea { width: 100%; padding: 12px; border: 1px solid var(--border); border-radius: var(--radius-sm); background: var(--bg-input); color: var(--text-primary); font-family: 'Consolas', monospace; font-size: 12px; resize: vertical; line-height: 1.5; }
.config-textarea:focus { outline: none; border-color: var(--accent); }

.upload-area { border: 2px dashed var(--border); border-radius: var(--radius-sm); padding: 24px; text-align: center; margin: 16px 0; cursor: pointer; position: relative; }
.upload-area:hover { border-color: var(--accent); }
.file-input { position: absolute; inset: 0; opacity: 0; cursor: pointer; }
.file-name { font-size: 13px; color: var(--accent); font-weight: 500; }
.file-hint { font-size: 13px; color: var(--text-muted); }
.upload-status { font-size: 12px; margin-top: 8px; color: var(--text-secondary); }
.upload-status.ok { color: #4caf50; }

.user-plugins-section { margin-top: 24px; padding-top: 20px; border-top: 1px solid var(--border); }
.user-plugins-section h3 { font-size: 14px; font-weight: 600; margin-bottom: 4px; }
.section-hint { font-size: 11px; color: var(--text-muted); margin-bottom: 12px; }
.user-plugin { border-style: dashed; }
.user-icon { background: rgba(76,175,80,0.1); color: #4caf50; }
.tile-version { font-size: 11px; color: var(--accent); font-weight: 500; }
.tile-commands { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 4px; }
.cmd-tag { padding: 2px 8px; background: var(--accent-dim); color: var(--accent); border-radius: 10px; font-size: 10px; font-weight: 500; }
.cmd-more { padding: 2px 6px; color: var(--text-muted); font-size: 10px; }
.tile-meta { font-size: 11px; color: var(--text-muted); margin-top: 4px; }
.icon-btn.danger { color: #f44336; }
.icon-btn.danger:hover { background: rgba(244,67,54,0.1); }
.modal-wide { max-width: 700px; }
.plugin-commands-section { margin-bottom: 16px; }
.section-label { font-size: 12px; color: var(--text-muted); margin-bottom: 8px; }
.commands-list { display: flex; flex-wrap: wrap; gap: 6px; }
.config-section { margin-top: 12px; }
.config-field { margin-bottom: 12px; }
.config-field label { display: block; font-size: 12px; color: var(--text-secondary); margin-bottom: 4px; }
.no-config { padding: 16px; text-align: center; color: var(--text-muted); font-size: 13px; }

.modal-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 20px; }
.cancel-btn, .save-btn { display: flex; align-items: center; gap: 4px; padding: 8px 16px; border-radius: var(--radius-sm); font-size: 13px; cursor: pointer; border: none; }
.cancel-btn { background: var(--bg-input); border: 1px solid var(--border); color: var(--text-secondary); }
.save-btn { background: var(--accent); color: white; }
.cancel-btn:hover { background: var(--bg-hover); }
.save-btn:hover { background: var(--accent-hover); }

@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
</style>
