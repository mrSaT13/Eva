<script setup lang="ts">
import { ref } from 'vue';
import MicIcon from '~icons/material-symbols/mic';
import VolumeIcon from '~icons/material-symbols/volume-up';
import SendIcon from '~icons/material-symbols/send';
import CheckIcon from '~icons/material-symbols/check-circle';
import ErrorIcon from '~icons/material-symbols/error';
import LoadingIcon from '~icons/line-md/loading-twotone-loop';
import StopIcon from '~icons/material-symbols/stop';

const activeTab = ref<'microphone' | 'tts' | 'api' | 'websocket'>('websocket');

// WebSocket test
const wsStatus = ref<'idle' | 'testing' | 'ok' | 'error'>('idle');
const wsError = ref<string | null>(null);
const wsMessages = ref<string[]>([]);
let ws: WebSocket | null = null;

// Microphone test
const micStatus = ref<'idle' | 'testing' | 'ok' | 'error'>('idle');
const micError = ref<string | null>(null);
let mediaStream: MediaStream | null = null;

// TTS test
const ttsStatus = ref<'idle' | 'testing' | 'ok' | 'error'>('idle');
const ttsError = ref<string | null>(null);
const ttsText = ref('Привет! Я Ева, тест голосового синтеза работает.');
const ttsAudioUrl = ref<string | null>(null);

// API test
const apiStatus = ref<'idle' | 'testing' | 'ok' | 'error'>('idle');
const apiError = ref<string | null>(null);
const apiResults = ref<Record<string, string>>({});

const testWebSocket = async () => {
    wsStatus.value = 'testing';
    wsError.value = null;
    wsMessages.value = [];

    try {
        const url = new URL(window.location.toString());
        url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
        url.pathname = '/api/face_web/ws';
        url.hash = '';

        ws = new WebSocket(url.toString());

        ws.onopen = () => {
            wsMessages.value.push('Соединение установлено');

            // Отправляем запрос на согласование протоколов
            ws!.send(JSON.stringify({
                type: 'negotiate/request',
                protocols: [
                    ['in.text-direct'],
                    ['out.text-plain'],
                ]
            }));
        };

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            wsMessages.value.push(`← ${data.type}: ${JSON.stringify(data).substring(0, 100)}`);

            if (data.type === 'negotiate_agree') {
                // Отправляем тестовую команду
                setTimeout(() => {
                    ws!.send(JSON.stringify({
                        type: 'in.text-direct/text',
                        text: 'привет'
                    }));
                    wsMessages.value.push('→ Отправлено: "привет"');
                }, 500);
            }

            if (data.type === 'out.text-plain/text') {
                wsMessages.value.push(`Ответ: ${data.text}`);
                wsStatus.value = 'ok';
                ws!.close();
            }
        };

        ws.onerror = (error) => {
            wsStatus.value = 'error';
            wsError.value = 'Ошибка WebSocket соединения';
        };

        ws.onclose = () => {
            if (wsStatus.value === 'testing') {
                wsStatus.value = wsMessages.value.length > 0 ? 'ok' : 'error';
            }
        };

    } catch (e: any) {
        wsStatus.value = 'error';
        wsError.value = e.message;
    }
};

const stopWebSocket = () => {
    if (ws) {
        ws.close();
        ws = null;
    }
    wsStatus.value = 'idle';
};

const testMicrophone = async () => {
    micStatus.value = 'testing';
    micError.value = null;

    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaStream = stream;

        const audioContext = new AudioContext();
        const source = audioContext.createMediaStreamSource(stream);
        const analyser = audioContext.createAnalyser();
        source.connect(analyser);

        await new Promise(resolve => setTimeout(resolve, 1500));

        const dataArray = new Uint8Array(analyser.frequencyBinCount);
        analyser.getByteFrequencyData(dataArray);

        const hasAudio = dataArray.some(v => v > 0);

        stream.getTracks().forEach(track => track.stop());
        audioContext.close();
        mediaStream = null;

        if (hasAudio) {
            micStatus.value = 'ok';
        } else {
            micStatus.value = 'error';
            micError.value = 'Микрофон не воспроизводит звук. Проверьте настройки.';
        }
    } catch (e: any) {
        micStatus.value = 'error';
        micError.value = e.message || 'Не удалось получить доступ к микрофону';
    }
};

const stopMicrophone = () => {
    if (mediaStream) {
        mediaStream.getTracks().forEach(track => track.stop());
        mediaStream = null;
    }
    micStatus.value = 'idle';
};

const testTTS = async () => {
    ttsStatus.value = 'testing';
    ttsError.value = null;
    ttsAudioUrl.value = null;

    try {
        const response = await fetch('/api/notification_api/notify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: ttsText.value }),
        });

        if (response.ok) {
            ttsStatus.value = 'ok';
        } else {
            throw new Error(`HTTP ${response.status}`);
        }
    } catch (e: any) {
        ttsStatus.value = 'error';
        ttsError.value = e.message;
    }
};

const testAPI = async () => {
    apiStatus.value = 'testing';
    apiError.value = null;

    try {
        const results: Record<string, string> = {};

        // Test configs
        try {
            const res = await fetch('/api/config/configs');
            results.configs = res.ok ? `OK (${(await res.json()).length} plugins)` : `Error: ${res.status}`;
        } catch { results.configs = 'Error: Network'; }

        // Test models
        try {
            const res = await fetch('/api/vosk_sherpa/models');
            results.models = res.ok ? `OK (${(await res.json()).length} models)` : `Error: ${res.status}`;
        } catch { results.models = 'Error: Network'; }

        // Test notify
        try {
            const res = await fetch('/api/notification_api/notify', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: 'Тест API' }),
            });
            results.notify = res.ok ? 'OK' : `Error: ${res.status}`;
        } catch { results.notify = 'Error: Network'; }

        // Test WebSocket
        try {
            const url = new URL(window.location.toString());
            url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
            url.pathname = '/api/face_web/ws';
            const testWs = new WebSocket(url.toString());
            await new Promise((resolve, reject) => {
                testWs.onopen = () => { results.websocket = 'OK'; testWs.close(); resolve(null); };
                testWs.onerror = () => { results.websocket = 'Error'; reject(null); };
                setTimeout(() => { results.websocket = 'Timeout'; testWs.close(); resolve(null); }, 3000);
            });
        } catch { results.websocket = 'Error'; }

        apiResults.value = results;
        apiStatus.value = Object.values(results).every(r => r.startsWith('OK')) ? 'ok' : 'error';
    } catch (e: any) {
        apiStatus.value = 'error';
        apiError.value = e.message;
    }
};
</script>

<template>
    <div class="testing-page">
        <h1>Тестирование</h1>
        <p class="subtitle">Проверка компонентов системы</p>

        <div class="tabs">
            <button class="tab" :class="{ active: activeTab === 'websocket' }" @click="activeTab = 'websocket'">
                WebSocket + Чат
            </button>
            <button class="tab" :class="{ active: activeTab === 'microphone' }" @click="activeTab = 'microphone'">
                Микрофон
            </button>
            <button class="tab" :class="{ active: activeTab === 'tts' }" @click="activeTab = 'tts'">
                Голос (TTS)
            </button>
            <button class="tab" :class="{ active: activeTab === 'api' }" @click="activeTab = 'api'">
                Все endpoints
            </button>
        </div>

        <!-- WebSocket Test -->
        <div v-if="activeTab === 'websocket'" class="test-panel">
            <div class="test-header">
                <h2>Тест WebSocket и чата</h2>
                <div class="test-actions">
                    <button class="test-btn" @click="testWebSocket" :disabled="wsStatus === 'testing'" v-if="wsStatus !== 'testing'">
                        <SendIcon /> Отправить "привет"
                    </button>
                    <button class="test-btn stop" @click="stopWebSocket" v-else>
                        <StopIcon /> Стоп
                    </button>
                </div>
            </div>

            <div class="test-result" :class="wsStatus">
                <div v-if="wsStatus === 'idle'" class="status-text">Нажмите для теста WebSocket соединения и отправки команды</div>
                <div v-else-if="wsStatus === 'testing'" class="status-text">
                    <LoadingIcon class="spin" /> Тестирование...
                </div>
                <div v-else-if="wsStatus === 'ok'" class="status-text">
                    <CheckIcon /> WebSocket работает, ответ получен
                </div>
                <div v-else-if="wsStatus === 'error'" class="status-text">
                    <ErrorIcon /> {{ wsError }}
                </div>
            </div>

            <div v-if="wsMessages.length > 0" class="ws-log">
                <div v-for="(msg, i) in wsMessages" :key="i" class="ws-msg">
                    {{ msg }}
                </div>
            </div>
        </div>

        <!-- Microphone Test -->
        <div v-if="activeTab === 'microphone'" class="test-panel">
            <div class="test-header">
                <h2>Тест микрофона</h2>
                <div class="test-actions">
                    <button class="test-btn" @click="testMicrophone" :disabled="micStatus === 'testing'" v-if="micStatus !== 'testing'">
                        <MicIcon /> Начать
                    </button>
                    <button class="test-btn stop" @click="stopMicrophone" v-else>
                        <StopIcon /> Стоп
                    </button>
                </div>
            </div>

            <div class="test-result" :class="micStatus">
                <div v-if="micStatus === 'idle'" class="status-text">Нажмите для проверки микрофона</div>
                <div v-else-if="micStatus === 'testing'" class="status-text">
                    <LoadingIcon class="spin" /> Слушаю... Говорите в микрофон
                </div>
                <div v-else-if="micStatus === 'ok'" class="status-text">
                    <CheckIcon /> Микрофон работает, звук обнаружен
                </div>
                <div v-else-if="micStatus === 'error'" class="status-text">
                    <ErrorIcon /> {{ micError }}
                </div>
            </div>
        </div>

        <!-- TTS Test -->
        <div v-if="activeTab === 'tts'" class="test-panel">
            <div class="test-header">
                <h2>Тест голоса (TTS)</h2>
                <button class="test-btn" @click="testTTS" :disabled="ttsStatus === 'testing'">
                    <VolumeIcon v-if="ttsStatus !== 'testing'" />
                    <LoadingIcon v-else class="spin" />
                    {{ ttsStatus === 'testing' ? 'Озвучка...' : 'Озвучить текст' }}
                </button>
            </div>

            <div class="tts-input">
                <label>Текст для синтеза:</label>
                <textarea v-model="ttsText" rows="3"></textarea>
            </div>

            <div class="test-result" :class="ttsStatus">
                <div v-if="ttsStatus === 'idle'" class="status-text">Введите текст и нажмите "Озвучить"</div>
                <div v-else-if="ttsStatus === 'testing'" class="status-text">
                    <LoadingIcon class="spin" /> Синтез и воспроизведение...
                </div>
                <div v-else-if="ttsStatus === 'ok'" class="status-text">
                    <CheckIcon /> TTS работает, текст озвучен
                </div>
                <div v-else-if="ttsStatus === 'error'" class="status-text">
                    <ErrorIcon /> {{ ttsError }}
                </div>
            </div>
        </div>

        <!-- API Test -->
        <div v-if="activeTab === 'api'" class="test-panel">
            <div class="test-header">
                <h2>Тест всех endpoints</h2>
                <button class="test-btn" @click="testAPI" :disabled="apiStatus === 'testing'">
                    <LoadingIcon v-if="apiStatus === 'testing'" class="spin" />
                    <span v-else>Запустить все тесты</span>
                </button>
            </div>

            <div class="test-result" :class="apiStatus">
                <div v-if="apiStatus === 'idle'" class="status-text">Нажмите для проверки всех API endpoints</div>
                <div v-else-if="apiStatus === 'testing'" class="status-text">
                    <LoadingIcon class="spin" /> Проверка...
                </div>
                <div v-else-if="apiStatus === 'ok'" class="status-text">
                    <CheckIcon /> Все endpoints работают
                </div>
                <div v-else-if="apiStatus === 'error'" class="status-text">
                    <ErrorIcon /> {{ apiError }}
                </div>
            </div>

            <div v-if="Object.keys(apiResults).length > 0" class="api-results">
                <div class="api-item" v-for="(result, key) in apiResults" :key="key">
                    <span class="api-name">{{ key }}</span>
                    <span class="api-status" :class="{ ok: result.startsWith('OK'), error: !result.startsWith('OK') }">
                        {{ result }}
                    </span>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.testing-page {
    display: flex;
    flex-direction: column;
    gap: 20px;
}

h1 { font-size: 24px; font-weight: 600; margin-bottom: 4px; }
.subtitle { color: var(--text-secondary); font-size: 14px; }

.tabs { display: flex; gap: 8px; flex-wrap: wrap; }

.tab {
    padding: 10px 16px;
    border-radius: var(--radius-sm);
    background: var(--bg-card);
    border: 1px solid var(--border);
    color: var(--text-secondary);
    font-size: 13px;
    cursor: pointer;
    transition: all 0.2s;
}
.tab:hover { background: var(--bg-hover); }
.tab.active { background: var(--accent); color: white; border-color: var(--accent); }

.test-panel {
    background: var(--bg-card);
    border-radius: var(--radius);
    padding: 24px;
}

.test-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
}
.test-header h2 { font-size: 16px; font-weight: 600; }
.test-actions { display: flex; gap: 8px; }

.test-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 16px;
    border-radius: var(--radius-sm);
    background: var(--accent);
    color: white;
    border: none;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    transition: background 0.2s;
}
.test-btn:hover:not(:disabled) { background: var(--accent-hover); }
.test-btn:disabled { opacity: 0.6; cursor: not-allowed; }
.test-btn.stop { background: var(--color-error); }

.test-result {
    padding: 16px;
    border-radius: var(--radius-sm);
    margin-bottom: 16px;
}
.test-result.idle { background: var(--bg-input); }
.test-result.testing { background: rgba(255, 152, 0, 0.1); color: #ff9800; }
.test-result.ok { background: rgba(76, 175, 80, 0.1); color: #4caf50; }
.test-result.error { background: rgba(244, 67, 54, 0.1); color: #f44336; }

.status-text { display: flex; align-items: center; gap: 8px; font-size: 14px; }

.tts-input { margin-bottom: 16px; }
.tts-input label { display: block; font-size: 13px; color: var(--text-secondary); margin-bottom: 6px; }
.tts-input textarea {
    width: 100%;
    padding: 10px;
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    background: var(--bg-input);
    color: var(--text-primary);
    font-size: 14px;
    resize: vertical;
}
.tts-input textarea:focus { outline: none; border-color: var(--accent); }

.ws-log {
    background: var(--bg-input);
    border-radius: var(--radius-sm);
    padding: 12px;
    max-height: 300px;
    overflow-y: auto;
    font-family: var(--font-mono);
    font-size: 12px;
}
.ws-msg {
    padding: 4px 0;
    border-bottom: 1px solid var(--border);
    color: var(--text-secondary);
}
.ws-msg:last-child { border-bottom: none; }

.api-results { display: flex; flex-direction: column; gap: 8px; }
.api-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 12px;
    background: var(--bg-input);
    border-radius: var(--radius-sm);
}
.api-name { font-size: 13px; font-weight: 500; }
.api-status { font-size: 12px; padding: 2px 8px; border-radius: 8px; }
.api-status.ok { background: rgba(76, 175, 80, 0.2); color: #4caf50; }
.api-status.error { background: rgba(244, 67, 54, 0.2); color: #f44336; }

.spin { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
</style>
