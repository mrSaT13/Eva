<script setup lang="ts">
import { ref, watch, onMounted } from 'vue';
import CheckIcon from '~icons/material-symbols/check-circle';
import ErrorIcon from '~icons/material-symbols/error';
import LoadingIcon from '~icons/line-md/loading-twotone-loop';
import SaveIcon from '~icons/material-symbols/save';

type LlmType = 'lmstudio' | 'ollama' | 'openai';

interface LlmSettings {
    url: string;
    model: string;
    apiKey: string;
    temperature: number;
}

const defaults: Record<LlmType, LlmSettings> = {
    lmstudio: { url: 'http://127.0.0.1:1234/v1', model: 'local-model', apiKey: 'lm-studio', temperature: 0.7 },
    ollama:   { url: 'http://127.0.0.1:11434',    model: 'llama3',     apiKey: '',         temperature: 0.8 },
    openai:   { url: 'https://api.openai.com/v1',  model: 'gpt-4o-mini', apiKey: '',        temperature: 0.7 },
};

const STORAGE_KEY = 'eva_llm_settings';

const loadAll = (): Record<LlmType, LlmSettings> => {
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (raw) return { ...defaults, ...JSON.parse(raw) };
    } catch {}
    return { ...defaults };
};

const saveAll = (all: Record<LlmType, LlmSettings>) => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(all));
};

const allSettings = ref<Record<LlmType, LlmSettings>>(loadAll());
const llmType = ref<LlmType>('lmstudio');
const systemPrompt = ref('Ты - умный голосовой помощник Eva. Отвечай кратко и на том языке, на котором задан вопрос.');

const llmUrl = ref(allSettings.value.lmstudio.url);
const llmModel = ref(allSettings.value.lmstudio.model);
const llmApiKey = ref(allSettings.value.lmstudio.apiKey);
const llmTemperature = ref(allSettings.value.lmstudio.temperature);

const testStatus = ref<'idle' | 'testing' | 'ok' | 'error'>('idle');
const testError = ref<string | null>(null);
const testResponse = ref<string | null>(null);
const testInput = ref('Привет! Кратко ответь кто ты.');
const saved = ref(false);

const applyType = (type: LlmType) => {
    const s = allSettings.value[type];
    llmUrl.value = s.url;
    llmModel.value = s.model;
    llmApiKey.value = s.apiKey;
    llmTemperature.value = s.temperature;
};

const syncToAll = () => {
    allSettings.value[llmType.value] = {
        url: llmUrl.value,
        model: llmModel.value,
        apiKey: llmApiKey.value,
        temperature: llmTemperature.value,
    };
};

watch(llmType, (newType, oldType) => {
    if (oldType) {
        allSettings.value[oldType] = {
            url: llmUrl.value,
            model: llmModel.value,
            apiKey: llmApiKey.value,
            temperature: llmTemperature.value,
        };
    }
    applyType(newType);
});

const loadConfig = async () => {
    try {
        const res = await fetch('/api/config/configs/llm_fallback_context');
        if (res.ok) {
            const data = await res.json();
            if (data.config?.llm_settings) {
                const t = data.config.llm_settings.type || 'lmstudio';
                if (t in defaults) llmType.value = t as LlmType;
                allSettings.value[t] = {
                    url: data.config.llm_settings.base_url || defaults[t as LlmType].url,
                    model: data.config.llm_settings.model || defaults[t as LlmType].model,
                    apiKey: data.config.llm_settings.api_key || defaults[t as LlmType].apiKey,
                    temperature: data.config.llm_settings.temperature ?? defaults[t as LlmType].temperature,
                };
                applyType(llmType.value);
            }
            if (data.config?.system_prompt) {
                systemPrompt.value = data.config.system_prompt;
            }
        }
    } catch {}
};

const saveConfig = async () => {
    syncToAll();
    saveAll(allSettings.value);
    try {
        await fetch('/api/config/configs/llm_fallback_context', {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                llm_settings: {
                    type: llmType.value,
                    base_url: llmUrl.value,
                    model: llmModel.value,
                    api_key: llmApiKey.value,
                    temperature: llmTemperature.value,
                },
                system_prompt: systemPrompt.value,
            }),
        });
        saved.value = true;
        setTimeout(() => saved.value = false, 2000);
    } catch {}
};

const testLLM = async () => {
    testStatus.value = 'testing';
    testError.value = null;
    testResponse.value = null;

    try {
        const wsUrl = new URL(window.location.href);
        wsUrl.protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        wsUrl.pathname = '/api/face_web/ws';
        wsUrl.hash = '';
        wsUrl.search = '';

        const ws = new WebSocket(wsUrl.toString());

        ws.onopen = () => {
            ws.send(JSON.stringify({ type: 'negotiate/request', protocols: [['in.text-direct'], ['out.text-plain']] }));
        };

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'negotiate/agree') {
                setTimeout(() => {
                    ws.send(JSON.stringify({ type: 'in.text-direct/text', text: testInput.value }));
                }, 300);
            }
            if (data.type === 'out.text-plain/text') {
                testResponse.value = data.text;
                testStatus.value = 'ok';
                ws.close();
            }
        };

        ws.onerror = () => { testStatus.value = 'error'; testError.value = 'Ошибка WebSocket'; };

        setTimeout(() => {
            if (testStatus.value === 'testing') { testStatus.value = 'error'; testError.value = 'Таймаут'; ws.close(); }
        }, 15000);
    } catch (e: any) { testStatus.value = 'error'; testError.value = e.message; }
};

onMounted(loadConfig);
</script>

<template>
    <div class="llm-settings">
        <h2>Настройки LLM</h2>
        <p class="subtitle">Конфигурация языковой модели</p>

        <div class="section">
            <h3>Тип LLM</h3>
            <div class="type-selector">
                <button class="type-btn" :class="{ active: llmType === 'lmstudio' }" @click="llmType = 'lmstudio'">
                    🤖 LM Studio
                </button>
                <button class="type-btn" :class="{ active: llmType === 'ollama' }" @click="llmType = 'ollama'">
                    🦙 Ollama
                </button>
                <button class="type-btn" :class="{ active: llmType === 'openai' }" @click="llmType = 'openai'">
                    💬 OpenAI
                </button>
            </div>
        </div>

        <div class="section">
            <h3>Подключение</h3>
            <div class="fields">
                <div class="field">
                    <label>URL сервера</label>
                    <input v-model="llmUrl" type="text" class="input" :placeholder="llmType === 'lmstudio' ? 'http://127.0.0.1:1234/v1' : llmType === 'ollama' ? 'http://127.0.0.1:11434' : 'https://api.openai.com/v1'" />
                </div>
                <div class="field">
                    <label>Модель</label>
                    <input v-model="llmModel" type="text" class="input" :placeholder="llmType === 'lmstudio' ? 'local-model' : llmType === 'ollama' ? 'llama3' : 'gpt-4o-mini'" />
                </div>
                <div class="field" v-if="llmType === 'openai'">
                    <label>API ключ</label>
                    <input v-model="llmApiKey" type="password" class="input" placeholder="sk-..." />
                </div>
                <div class="field">
                    <label>Температура: {{ llmTemperature }}</label>
                    <input v-model.number="llmTemperature" type="range" min="0" max="1" step="0.1" class="range" />
                </div>
            </div>
        </div>

        <div class="section">
            <h3>Системный промпт</h3>
            <textarea v-model="systemPrompt" class="textarea" rows="4"></textarea>
        </div>

        <button class="save-btn" @click="saveConfig">
            <CheckIcon v-if="saved" /><SaveIcon v-else />
            {{ saved ? 'Сохранено!' : 'Сохранить настройки' }}
        </button>

        <div class="section test-section">
            <h3>Тест подключения</h3>
            <div class="test-row">
                <input v-model="testInput" type="text" class="input" placeholder="Тестовый запрос..." />
                <button class="test-btn" @click="testLLM" :disabled="testStatus === 'testing'">
                    <LoadingIcon v-if="testStatus === 'testing'" class="spin" />
                    Тест
                </button>
            </div>
            <div v-if="testStatus === 'ok'" class="test-result ok"><CheckIcon /> {{ testResponse }}</div>
            <div v-if="testStatus === 'error'" class="test-result error"><ErrorIcon /> {{ testError }}</div>
        </div>

        <div class="info-box">
            <p><strong>LM Studio:</strong> Запустите LM Studio → загрузите модель → запустите сервер (вкладка "Local Server")</p>
            <p><strong>Ollama:</strong> Установите Ollama → запустите `ollama serve` → скачайте модель</p>
            <p><strong>OpenAI:</strong> Получите API ключ на platform.openai.com</p>
        </div>
    </div>
</template>

<style scoped>
.llm-settings h2 { font-size: 20px; font-weight: 600; margin-bottom: 4px; }
.subtitle { color: var(--text-secondary); font-size: 13px; margin-bottom: 20px; }

.section { margin-bottom: 24px; }
.section h3 { font-size: 14px; font-weight: 600; margin-bottom: 12px; color: var(--accent); }

.type-selector { display: flex; gap: 8px; flex-wrap: wrap; }
.type-btn {
    padding: 10px 16px; border-radius: var(--radius-sm);
    background: var(--bg-card); border: 1px solid var(--border);
    color: var(--text-secondary); font-size: 13px; cursor: pointer;
}
.type-btn:hover { background: var(--bg-hover); }
.type-btn.active { background: var(--accent); color: white; border-color: var(--accent); }

.fields { display: flex; flex-direction: column; gap: 12px; }
.field label { display: block; font-size: 12px; color: var(--text-secondary); margin-bottom: 4px; }

.input {
    width: 100%; padding: 10px 12px;
    border: 1px solid var(--border); border-radius: var(--radius-sm);
    background: var(--bg-input); color: var(--text-primary); font-size: 14px;
}
.input:focus { outline: none; border-color: var(--accent); }

.textarea {
    width: 100%; padding: 10px 12px;
    border: 1px solid var(--border); border-radius: var(--radius-sm);
    background: var(--bg-input); color: var(--text-primary); font-size: 13px;
    resize: vertical; font-family: var(--font-mono);
}
.textarea:focus { outline: none; border-color: var(--accent); }

.range { width: 100%; accent-color: var(--accent); }

.save-btn {
    display: flex; align-items: center; gap: 6px;
    padding: 10px 20px; border-radius: var(--radius-sm);
    background: var(--accent); color: white; border: none;
    font-size: 14px; cursor: pointer; margin-bottom: 24px;
}
.save-btn:hover { background: var(--accent-hover); }

.test-section { padding: 20px; background: var(--bg-card); border-radius: var(--radius); }
.test-row { display: flex; gap: 8px; margin-bottom: 12px; }
.test-row .input { flex: 1; }

.test-btn {
    padding: 10px 20px; border-radius: var(--radius-sm);
    background: var(--accent); color: white; border: none; font-size: 13px; cursor: pointer;
}
.test-btn:hover:not(:disabled) { background: var(--accent-hover); }
.test-btn:disabled { opacity: 0.6; }

.test-result { padding: 12px; border-radius: var(--radius-sm); font-size: 13px; }
.test-result.ok { background: rgba(76,175,80,0.1); color: #4caf50; display: flex; align-items: center; gap: 6px; }
.test-result.error { background: rgba(244,67,54,0.1); color: #f44336; display: flex; align-items: center; gap: 6px; }

.info-box { padding: 16px; background: var(--bg-card); border-radius: var(--radius-sm); font-size: 12px; color: var(--text-muted); }
.info-box p { margin-bottom: 4px; }

.spin { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
</style>
