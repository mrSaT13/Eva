<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import CheckIcon from '~icons/material-symbols/check-circle';
import ErrorIcon from '~icons/material-symbols/error';
import LoadingIcon from '~icons/line-md/loading-twotone-loop';
import SaveIcon from '~icons/material-symbols/save';
import HomeIcon from '~icons/material-symbols/home';
import BotIcon from '~icons/material-symbols/psychology';
import ChatIcon from '~icons/material-symbols/chat';
import RssIcon from '~icons/material-symbols/rss-feed';
import MusicIcon from '~icons/material-symbols/music-note';
import WeatherIcon from '~icons/material-symbols/cloud';
import WikiIcon from '~icons/material-symbols/menu-book';
import AddIcon from '~icons/material-symbols/add-circle';
import CloseIcon from '~icons/material-symbols/close';
import PlugIcon from '~icons/material-symbols/extension';

const showModal = ref(false);

const availableIntegrations = [
    { id: 'ha', name: 'Home Assistant', desc: 'Управление умным домом', icon: HomeIcon, category: 'smart-home' },
    { id: 'mqtt', name: 'MQTT', desc: 'Брокер сообщений IoT', icon: PlugIcon, category: 'smart-home' },
    { id: 'zigbee', name: 'Zigbee', desc: 'Zigbee2MQTT устройства', icon: PlugIcon, category: 'smart-home' },
    { id: 'yandex', name: 'Яндекс Станция', desc: 'Интеграция с Яндексом', icon: BotIcon, category: 'smart-home' },
    { id: 'google_home', name: 'Google Home', desc: 'Google Assistant', icon: BotIcon, category: 'smart-home' },
    { id: 'ikea', name: 'IKEA Trådfri', desc: 'Умное освещение IKEA', icon: HomeIcon, category: 'smart-home' },
    { id: 'philips', name: 'Philips Hue', desc: 'Умное освещение Hue', icon: HomeIcon, category: 'smart-home' },
    { id: 'tuya', name: 'Tuya', desc: 'Умные устройства Tuya', icon: PlugIcon, category: 'smart-home' },
    { id: 'xiaomi', name: 'Xiaomi Mi Home', desc: 'Умные устройства Xiaomi', icon: PlugIcon, category: 'smart-home' },
    { id: 'freshrss', name: 'FreshRSS', desc: 'Читалка RSS лент', icon: RssIcon, category: 'news' },
    { id: 'rss', name: 'RSS Ленты', desc: 'Новости и подкасты', icon: RssIcon, category: 'news' },
    { id: 'navidrome', name: 'Navidrome', desc: 'Музыкальный сервер (Subsonic API)', icon: MusicIcon, category: 'media' },
    { id: 'spotify', name: 'Spotify', desc: 'Музыкальный стриминг', icon: MusicIcon, category: 'media' },
    { id: 'weather', name: 'Погода', desc: 'Прогноз погоды (wttr.in)', icon: WeatherIcon, category: 'utilities' },
    { id: 'wiki', name: 'Википедия', desc: 'Поиск статей', icon: WikiIcon, category: 'utilities' },
    { id: 'lmstudio', name: 'LM Studio', desc: 'Локальный LLM сервер', icon: BotIcon, category: 'ai' },
    { id: 'ollama', name: 'Ollama', desc: 'Локальный LLM сервер', icon: BotIcon, category: 'ai' },
    { id: 'openai', name: 'OpenAI', desc: 'GPT модели', icon: BotIcon, category: 'ai' },
    { id: 'telegram', name: 'Telegram', desc: 'Telegram бот', icon: ChatIcon, category: 'messaging' },
    { id: 'discord', name: 'Discord', desc: 'Discord бот', icon: ChatIcon, category: 'messaging' },
];

const activeIntegrations = ref<Set<string>>(new Set());

const availableToAdd = computed(() => {
    return availableIntegrations.filter(i => !activeIntegrations.value.has(i.id));
});

const categories = computed(() => {
    const cats: Record<string, typeof availableIntegrations> = {};
    for (const item of availableToAdd.value) {
        if (!cats[item.category]) cats[item.category] = [];
        cats[item.category].push(item);
    }
    return cats;
});

const categoryNames: Record<string, string> = {
    'smart-home': 'Умный дом',
    'news': 'Новости',
    'media': 'Медиа',
    'utilities': 'Утилиты',
    'ai': 'ИИ',
    'messaging': 'Сообщения',
};

const haUrl = ref('');
const haToken = ref('');
const haStatus = ref<'idle' | 'testing' | 'ok' | 'error'>('idle');
const haMessage = ref('');
const saved = ref(false);

const freshrssUrl = ref('');
const freshrssUser = ref('');
const freshrssToken = ref('');
const freshrssSaved = ref(false);

const navidromeUrl = ref('');
const navidromeUser = ref('');
const navidromePassword = ref('');
const navidromeSaved = ref(false);

const rssFeeds = ref<string[]>([]);
const newRssFeed = ref('');

const weatherCity = ref('Moscow');
const weatherSaved = ref(false);

const loadHAConfig = async () => {
    try {
        const r = await fetch('/api/automations/ha_status');
        if (r.ok) {
            const data = await r.json();
            if (data.connected) { haStatus.value = 'ok'; haMessage.value = data.message || 'Подключено'; }
            else { haStatus.value = 'error'; haMessage.value = data.error || 'Не настроено'; }
        }
    } catch {}
};

const saveHAConfig = async () => {
    try {
        await fetch('/api/config/configs/automations', {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ha_url: haUrl.value, ha_token: haToken.value }),
        });
        saved.value = true;
        setTimeout(() => saved.value = false, 2000);
    } catch {}
};

const testHA = async () => {
    haStatus.value = 'testing';
    try {
        await fetch('/api/config/configs/automations', {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ha_url: haUrl.value, ha_token: haToken.value }),
        });
        const r = await fetch('/api/automations/ha_status');
        if (r.ok) {
            const data = await r.json();
            haStatus.value = data.connected ? 'ok' : 'error';
            haMessage.value = data.connected ? (data.message || 'Подключено') : (data.error || 'Ошибка');
        }
    } catch { haStatus.value = 'error'; haMessage.value = 'Ошибка сети'; }
};

const saveFreshRSS = async () => {
    try {
        await fetch('/api/config/configs/integrations', {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ freshrss_url: freshrssUrl.value, freshrss_user: freshrssUser.value, freshrss_token: freshrssToken.value }),
        });
        freshrssSaved.value = true;
        setTimeout(() => freshrssSaved.value = false, 2000);
    } catch {}
};

const saveNavidrome = async () => {
    try {
        await fetch('/api/config/configs/integrations', {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ navidrome_url: navidromeUrl.value, navidrome_user: navidromeUser.value, navidrome_password: navidromePassword.value }),
        });
        navidromeSaved.value = true;
        setTimeout(() => navidromeSaved.value = false, 2000);
    } catch {}
};

const loadRSSFeeds = async () => {
    try {
        const r = await fetch('/api/integrations/rss/feeds');
        if (r.ok) rssFeeds.value = await r.json();
    } catch {}
};

const addRssFeed = async () => {
    if (!newRssFeed.value.trim()) return;
    try {
        await fetch('/api/integrations/rss/feeds', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: newRssFeed.value.trim() }),
        });
        newRssFeed.value = '';
        await loadRSSFeeds();
    } catch {}
};

const removeRssFeed = async (url: string) => {
    try {
        await fetch(`/api/integrations/rss/feeds?url=${encodeURIComponent(url)}`, { method: 'DELETE' });
        await loadRSSFeeds();
    } catch {}
};

const saveWeather = async () => {
    try {
        await fetch('/api/config/configs/integrations', {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ weather_city: weatherCity.value }),
        });
        weatherSaved.value = true;
        setTimeout(() => weatherSaved.value = false, 2000);
    } catch {}
};

const isIntegrationActive = (id: string) => activeIntegrations.value.has(id);

const isIntegrationConfigured = (id: string) => {
    switch (id) {
        case 'ha': return !!(haUrl.value && haToken.value);
        case 'freshrss': return !!freshrssUrl.value;
        case 'navidrome': return !!navidromeUrl.value;
        case 'weather': return !!weatherCity.value;
        case 'rss': return rssFeeds.value.length > 0;
        default: return false;
    }
};

const addIntegration = (id: string) => {
    activeIntegrations.value.add(id);
    showModal.value = false;
};

const removeIntegration = (id: string) => {
    activeIntegrations.value.delete(id);
};

const loadAllConfigs = async () => {
    try {
        const r = await fetch('/api/config/configs');
        if (r.ok) {
            const data = await r.json();
            for (const item of data) {
                const cfg = item.config || {};
                if (item.scope === 'automations' && cfg.ha_url && cfg.ha_token) {
                    activeIntegrations.value.add('ha');
                }
                if (item.scope === 'integrations') {
                    if (cfg.freshrss_url) activeIntegrations.value.add('freshrss');
                    if (cfg.navidrome_url) activeIntegrations.value.add('navidrome');
                    if (cfg.weather_city) activeIntegrations.value.add('weather');
                    if (cfg.rss_feeds && cfg.rss_feeds.length > 0) activeIntegrations.value.add('rss');
                }
                if (item.scope === 'llm_settings' && (cfg.type === 'lmstudio' || cfg.base_url)) {
                    activeIntegrations.value.add('lmstudio');
                }
                if (item.scope === 'face_telegram' && cfg.token) {
                    activeIntegrations.value.add('telegram');
                }
            }
        }
    } catch {}
};

onMounted(() => {
    loadAllConfigs();
    loadHAConfig();
    loadRSSFeeds();
});
</script>

<template>
    <div class="int-settings">
        <div class="header-row">
            <div>
                <h2>Интеграции</h2>
                <p class="subtitle">Подключение внешних сервисов</p>
            </div>
            <button class="add-btn" @click="showModal = true">
                <AddIcon /> Добавить
            </button>
        </div>

        <div v-if="isIntegrationActive('ha')" class="section-card">
            <div class="section-header">
                <div class="icon-box"><HomeIcon /></div>
                <div class="header-text"><h3>Home Assistant</h3><p>Управление умным домом</p></div>
                <span class="status-badge" :class="isIntegrationConfigured('ha') ? 'configured' : 'not-configured'">
                    {{ isIntegrationConfigured('ha') ? 'Настроена' : 'Не настроена' }}
                </span>
                <button class="remove-int-btn" @click="removeIntegration('ha')" title="Удалить">×</button>
            </div>
            <div class="fields">
                <div class="field">
                    <label>URL сервера</label>
                    <input v-model="haUrl" type="text" class="input" placeholder="http://192.168.1.100:8123" />
                </div>
                <div class="field">
                    <label>Токен доступа</label>
                    <input v-model="haToken" type="password" class="input" placeholder="eyJ0eXAiOiJKV1QiLCJhbGci..." />
                </div>
            </div>
            <div class="field-actions">
                <button class="test-btn" @click="testHA" :disabled="haStatus === 'testing'">
                    <LoadingIcon v-if="haStatus === 'testing'" class="spin" />
                    Проверить
                </button>
                <button class="save-btn" @click="saveHAConfig">
                    <CheckIcon v-if="saved" /><SaveIcon v-else />
                    {{ saved ? 'Сохранено' : 'Сохранить' }}
                </button>
            </div>
            <div v-if="haStatus !== 'idle'" class="status-bar" :class="haStatus">
                <component :is="haStatus === 'ok' ? CheckIcon : ErrorIcon" />
                {{ haMessage }}
            </div>
            <div class="hint">
                <p>Для получения токена: Профиль -> Долгосрочные токены -> Создать</p>
            </div>
        </div>

        <div v-if="isIntegrationActive('freshrss')" class="section-card">
            <div class="section-header">
                <div class="icon-box"><RssIcon /></div>
                <div class="header-text"><h3>FreshRSS</h3><p>Читалка RSS лент</p></div>
                <span class="status-badge" :class="isIntegrationConfigured('freshrss') ? 'configured' : 'not-configured'">
                    {{ isIntegrationConfigured('freshrss') ? 'Настроена' : 'Не настроена' }}
                </span>
                <button class="remove-int-btn" @click="removeIntegration('freshrss')" title="Удалить">×</button>
            </div>
            <div class="fields">
                <div class="field">
                    <label>URL сервера</label>
                    <input v-model="freshrssUrl" type="text" class="input" placeholder="http://localhost:8080" />
                </div>
                <div class="field">
                    <label>Пользователь</label>
                    <input v-model="freshrssUser" type="text" class="input" placeholder="admin" />
                </div>
                <div class="field">
                    <label>Токен API</label>
                    <input v-model="freshrssToken" type="password" class="input" placeholder="API токен FreshRSS" />
                </div>
            </div>
            <div class="field-actions">
                <button class="save-btn" @click="saveFreshRSS">
                    <CheckIcon v-if="freshrssSaved" /><SaveIcon v-else />
                    {{ freshrssSaved ? 'Сохранено' : 'Сохранить' }}
                </button>
            </div>
        </div>

        <div v-if="isIntegrationActive('rss')" class="section-card">
            <div class="section-header">
                <div class="icon-box"><RssIcon /></div>
                <div class="header-text"><h3>RSS Ленты</h3><p>Новости и подкасты</p></div>
                <button class="remove-int-btn" @click="removeIntegration('rss')" title="Удалить">×</button>
            </div>
            <div class="fields">
                <div v-for="feed in rssFeeds" :key="feed" class="feed-item">
                    <span class="feed-url">{{ feed }}</span>
                    <button class="remove-btn" @click="removeRssFeed(feed)">Удалить</button>
                </div>
                <div class="field" style="display:flex;gap:8px">
                    <input v-model="newRssFeed" type="text" class="input" placeholder="https://example.com/rss.xml" style="flex:1" />
                    <button class="save-btn" @click="addRssFeed">Добавить</button>
                </div>
            </div>
        </div>

        <div v-if="isIntegrationActive('navidrome')" class="section-card">
            <div class="section-header">
                <div class="icon-box"><MusicIcon /></div>
                <div class="header-text"><h3>Navidrome</h3><p>Музыкальный сервер (Subsonic API)</p></div>
                <span class="status-badge" :class="isIntegrationConfigured('navidrome') ? 'configured' : 'not-configured'">
                    {{ isIntegrationConfigured('navidrome') ? 'Настроена' : 'Не настроена' }}
                </span>
                <button class="remove-int-btn" @click="removeIntegration('navidrome')" title="Удалить">×</button>
            </div>
            <div class="fields">
                <div class="field">
                    <label>URL сервера</label>
                    <input v-model="navidromeUrl" type="text" class="input" placeholder="http://localhost:4533" />
                </div>
                <div class="field">
                    <label>Пользователь</label>
                    <input v-model="navidromeUser" type="text" class="input" placeholder="admin" />
                </div>
                <div class="field">
                    <label>Пароль</label>
                    <input v-model="navidromePassword" type="password" class="input" placeholder="Пароль" />
                </div>
            </div>
            <div class="field-actions">
                <button class="save-btn" @click="saveNavidrome">
                    <CheckIcon v-if="navidromeSaved" /><SaveIcon v-else />
                    {{ navidromeSaved ? 'Сохранено' : 'Сохранить' }}
                </button>
            </div>
        </div>

        <div v-if="isIntegrationActive('weather')" class="section-card">
            <div class="section-header">
                <div class="icon-box"><WeatherIcon /></div>
                <div class="header-text"><h3>Погода</h3><p>Прогноз погоды (wttr.in)</p></div>
                <button class="remove-int-btn" @click="removeIntegration('weather')" title="Удалить">×</button>
            </div>
            <div class="fields">
                <div class="field">
                    <label>Город по умолчанию</label>
                    <input v-model="weatherCity" type="text" class="input" placeholder="Moscow" />
                </div>
            </div>
            <div class="field-actions">
                <button class="save-btn" @click="saveWeather">
                    <CheckIcon v-if="weatherSaved" /><SaveIcon v-else />
                    {{ weatherSaved ? 'Сохранено' : 'Сохранить' }}
                </button>
            </div>
            <div class="hint">
                <p>Голосовая команда: "погода" или "погода в Москве"</p>
            </div>
        </div>

        <div v-if="isIntegrationActive('wiki')" class="section-card">
            <div class="section-header">
                <div class="icon-box"><WikiIcon /></div>
                <div class="header-text"><h3>Википедия</h3><p>Поиск статей</p></div>
                <button class="remove-int-btn" @click="removeIntegration('wiki')" title="Удалить">×</button>
            </div>
            <div class="hint">
                <p>Голосовая команда: "вики Python" или "википедия квантовая физика"</p>
            </div>
        </div>

        <div v-if="isIntegrationActive('lmstudio')" class="section-card">
            <div class="section-header">
                <div class="icon-box"><BotIcon /></div>
                <div class="header-text"><h3>LM Studio</h3><p>Локальный LLM сервер</p></div>
                <button class="remove-int-btn" @click="removeIntegration('lmstudio')" title="Удалить">×</button>
            </div>
            <div class="hint"><p>Настройте в настройках LLM (вкладка "LLM")</p></div>
        </div>

        <div v-if="isIntegrationActive('telegram')" class="section-card">
            <div class="section-header">
                <div class="icon-box"><ChatIcon /></div>
                <div class="header-text"><h3>Telegram</h3><p>Telegram бот</p></div>
                <button class="remove-int-btn" @click="removeIntegration('telegram')" title="Удалить">×</button>
            </div>
            <div class="hint"><p>Настройте токен в config/face_telegram.yaml</p></div>
        </div>

        <div v-if="activeIntegrations.size === 0" class="empty-state">
            <PlugIcon class="empty-icon" />
            <p>Нет активных интеграций</p>
            <button class="add-btn" @click="showModal = true">
                <AddIcon /> Добавить интеграцию
            </button>
        </div>
    </div>

    <Teleport to="body">
        <div v-if="showModal" class="modal-overlay" @click.self="showModal = false">
            <div class="modal">
                <div class="modal-header">
                    <h3>Добавить интеграцию</h3>
                    <button class="close-btn" @click="showModal = false"><CloseIcon /></button>
                </div>
                <div class="modal-body">
                    <div v-if="availableToAdd.length === 0" class="modal-empty">Все интеграции уже добавлены</div>
                    <div v-for="(items, cat) in categories" :key="cat" class="modal-category">
                        <h4>{{ categoryNames[cat as string] || cat }}</h4>
                        <div class="modal-grid">
                            <div
                                v-for="item in items"
                                :key="item.id"
                                class="modal-card"
                                @click="addIntegration(item.id)"
                            >
                                <div class="modal-card-icon">
                                    <component :is="item.icon" />
                                </div>
                                <div class="modal-card-info">
                                    <span class="modal-card-name">{{ item.name }}</span>
                                    <span class="modal-card-desc">{{ item.desc }}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </Teleport>
</template>

<style scoped>
.int-settings h2 { font-size: 20px; font-weight: 600; margin-bottom: 4px; }
.subtitle { color: var(--text-secondary); font-size: 13px; }

.header-row { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }

.add-btn { display: flex; align-items: center; gap: 6px; padding: 10px 20px; border-radius: var(--radius-sm); font-size: 14px; cursor: pointer; border: none; background: var(--accent); color: white; font-weight: 500; }
.add-btn:hover { background: var(--accent-hover); }

.section-card { background: var(--bg-card); border-radius: var(--radius); padding: 20px; margin-bottom: 16px; }
.section-header { display: flex; gap: 12px; align-items: center; margin-bottom: 16px; }
.section-header h3 { font-size: 16px; font-weight: 600; margin-bottom: 2px; }
.section-header p { font-size: 12px; color: var(--text-secondary); }
.header-text { flex: 1; }

.remove-int-btn { width: 28px; height: 28px; border-radius: 50%; border: 1px solid var(--border); background: var(--bg-input); color: var(--text-secondary); font-size: 18px; cursor: pointer; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.remove-int-btn:hover { background: rgba(244,67,54,0.1); color: #f44336; border-color: #f44336; }

.status-badge {
    padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 500; flex-shrink: 0;
}
.status-badge.configured { background: rgba(76,175,80,0.15); color: #4caf50; }
.status-badge.not-configured { background: rgba(255,152,0,0.15); color: #ff9800; }

.icon-box { width: 44px; height: 44px; border-radius: 10px; background: var(--accent-dim); color: var(--accent); display: flex; align-items: center; justify-content: center; font-size: 22px; flex-shrink: 0; }

.fields { display: flex; flex-direction: column; gap: 12px; margin-bottom: 12px; }
.field label { display: block; font-size: 12px; color: var(--text-secondary); margin-bottom: 4px; }

.input { width: 100%; padding: 10px 12px; border: 1px solid var(--border); border-radius: var(--radius-sm); background: var(--bg-input); color: var(--text-primary); font-size: 14px; }
.input:focus { outline: none; border-color: var(--accent); }

.field-actions { display: flex; gap: 8px; margin-bottom: 12px; }
.test-btn, .save-btn { display: flex; align-items: center; gap: 6px; padding: 8px 16px; border-radius: var(--radius-sm); font-size: 13px; cursor: pointer; border: none; }
.test-btn { background: var(--bg-input); border: 1px solid var(--border); color: var(--text-secondary); }
.save-btn { background: var(--accent); color: white; }
.test-btn:hover:not(:disabled) { background: var(--bg-hover); }
.save-btn:hover { background: var(--accent-hover); }

.status-bar { display: flex; align-items: center; gap: 6px; padding: 8px 12px; border-radius: var(--radius-sm); font-size: 12px; }
.status-bar.ok { background: rgba(76,175,80,0.1); color: #4caf50; }
.status-bar.error { background: rgba(244,67,54,0.1); color: #f44336; }

.hint { font-size: 11px; color: var(--text-muted); }
.hint p { margin-bottom: 2px; }
.spin { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

.feed-item { display: flex; align-items: center; justify-content: space-between; padding: 8px 12px; background: var(--bg-input); border-radius: var(--radius-sm); }
.feed-url { font-size: 12px; color: var(--text-primary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; margin-right: 8px; }
.remove-btn { font-size: 11px; color: #f44336; background: none; border: none; cursor: pointer; }
.remove-btn:hover { text-decoration: underline; }

.empty-state { display: flex; flex-direction: column; align-items: center; gap: 12px; padding: 40px 20px; color: var(--text-muted); }
.empty-icon { font-size: 48px; opacity: 0.3; }

.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); backdrop-filter: blur(4px); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal { background: var(--bg-secondary); border-radius: var(--radius); width: 90%; max-width: 500px; max-height: 80vh; overflow-y: auto; border: 1px solid var(--border); }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; border-bottom: 1px solid var(--border); }
.modal-header h3 { font-size: 16px; font-weight: 600; }
.close-btn { width: 32px; height: 32px; border-radius: 50%; border: none; background: var(--bg-input); color: var(--text-secondary); cursor: pointer; display: flex; align-items: center; justify-content: center; }
.close-btn:hover { background: var(--bg-hover); }
.modal-body { padding: 16px 20px; }
.modal-category { margin-bottom: 16px; }
.modal-category h4 { font-size: 12px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }
.modal-grid { display: flex; flex-direction: column; gap: 8px; }
.modal-card { display: flex; align-items: center; gap: 12px; padding: 12px; border-radius: var(--radius-sm); border: 1px solid var(--border); cursor: pointer; transition: all 0.2s; }
.modal-card:hover { background: var(--bg-hover); border-color: var(--accent); }
.modal-card.active { background: var(--accent-dim); border-color: var(--accent); opacity: 0.6; cursor: default; }
.modal-card-icon { width: 36px; height: 36px; border-radius: 8px; background: var(--accent-dim); color: var(--accent); display: flex; align-items: center; justify-content: center; font-size: 18px; flex-shrink: 0; }
.modal-card-info { flex: 1; }
.modal-card-name { display: block; font-size: 14px; font-weight: 500; }
.modal-card-desc { display: block; font-size: 11px; color: var(--text-secondary); }
.modal-card-check { color: var(--accent); font-size: 18px; flex-shrink: 0; }
</style>
