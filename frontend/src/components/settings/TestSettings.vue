<script setup lang="ts">
import { ref } from 'vue';
import CheckIcon from '~icons/material-symbols/check-circle';
import ErrorIcon from '~icons/material-symbols/error';
import LoadingIcon from '~icons/line-md/loading-twotone-loop';
import SendIcon from '~icons/material-symbols/send';
import MicIcon from '~icons/material-symbols/mic';
import VolumeIcon from '~icons/material-symbols/volume-up';
import StopIcon from '~icons/material-symbols/stop';

const activeTest = ref<'llm' | 'websocket' | 'microphone' | 'tts'>('llm');

// LLM Test
const llmStatus = ref<'idle' | 'testing' | 'ok' | 'error'>('idle');
const llmError = ref<string | null>(null);
const llmResponse = ref<string | null>(null);
const llmInput = ref('Привет! Кратко ответь кто ты.');

const testLLM = async () => {
    llmStatus.value = 'testing';
    llmError.value = null;
    llmResponse.value = null;

    try {
        const wsUrl = new URL(window.location.href);
        wsUrl.protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        wsUrl.pathname = '/api/face_web/ws';
        wsUrl.hash = '';
        wsUrl.search = '';

        const ws = new WebSocket(wsUrl.toString());

        ws.onopen = () => {
            ws.send(JSON.stringify({
                type: 'negotiate/request',
                protocols: [['in.text-direct'], ['out.text-plain']]
            }));
        };

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);

            if (data.type === 'negotiate_agree') {
                setTimeout(() => {
                    ws.send(JSON.stringify({
                        type: 'in.text-direct/text',
                        text: llmInput.value
                    }));
                }, 300);
            }

            if (data.type === 'out.text-plain/text') {
                llmResponse.value = data.text;
                llmStatus.value = 'ok';
                ws.close();
            }
        };

        ws.onerror = () => {
            llmStatus.value = 'error';
            llmError.value = 'Ошибка WebSocket';
        };

        setTimeout(() => {
            if (llmStatus.value === 'testing') {
                llmStatus.value = 'error';
                llmError.value = 'Таймаут (10 сек)';
                ws.close();
            }
        }, 10000);

    } catch (e: any) {
        llmStatus.value = 'error';
        llmError.value = e.message;
    }
};

// WebSocket Test
const wsStatus = ref<'idle' | 'testing' | 'ok' | 'error'>('idle');
const wsMessages = ref<string[]>([]);

const testWebSocket = async () => {
    wsStatus.value = 'testing';
    wsMessages.value = [];

    try {
        const wsUrl = new URL(window.location.href);
        wsUrl.protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        wsUrl.pathname = '/api/face_web/ws';
        wsUrl.hash = '';
        wsUrl.search = '';

        const ws = new WebSocket(wsUrl.toString());

        ws.onopen = () => {
            wsMessages.value.push('✓ Соединение установлено');
            ws.send(JSON.stringify({
                type: 'negotiate/request',
                protocols: [['in.text-direct'], ['out.text-plain']]
            }));
        };

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            wsMessages.value.push(`← ${data.type}`);

            if (data.type === 'negotiate_agree') {
                wsMessages.value.push('✓ Протоколы согласованы');
                setTimeout(() => {
                    ws.send(JSON.stringify({ type: 'in.text-direct/text', text: 'привет' }));
                    wsMessages.value.push('→ Отправлено: "привет"');
                }, 300);
            }

            if (data.type === 'out.text-plain/text') {
                wsMessages.value.push(`✓ Ответ: ${data.text}`);
                wsStatus.value = 'ok';
                ws.close();
            }
        };

        ws.onerror = () => {
            wsStatus.value = 'error';
            wsMessages.value.push('✗ Ошибка WebSocket');
        };

        setTimeout(() => {
            if (wsStatus.value === 'testing') {
                wsStatus.value = wsMessages.value.length > 1 ? 'ok' : 'error';
                ws.close();
            }
        }, 5000);

    } catch (e: any) {
        wsStatus.value = 'error';
    }
};

// Microphone Test
const micStatus = ref<'idle' | 'testing' | 'ok' | 'error'>('idle');
let mediaStream: MediaStream | null = null;

const testMicrophone = async () => {
    micStatus.value = 'testing';
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaStream = stream;
        const ctx = new AudioContext();
        const src = ctx.createMediaStreamSource(stream);
        const analyser = ctx.createAnalyser();
        src.connect(analyser);
        await new Promise(r => setTimeout(r, 1500));
        const data = new Uint8Array(analyser.frequencyBinCount);
        analyser.getByteFrequencyData(data);
        stream.getTracks().forEach(t => t.stop());
        ctx.close();
        mediaStream = null;
        micStatus.value = data.some(v => v > 0) ? 'ok' : 'error';
    } catch (e: any) {
        micStatus.value = 'error';
    }
};

// TTS Test
const ttsStatus = ref<'idle' | 'testing' | 'ok' | 'error'>('idle');
const ttsText = ref('Привет! Я Ева.');

const testTTS = async () => {
    ttsStatus.value = 'testing';
    try {
        const res = await fetch('/api/notification_api/notify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: ttsText.value }),
        });
        ttsStatus.value = res.ok ? 'ok' : 'error';
    } catch {
        ttsStatus.value = 'error';
    }
};
</script>

<template>
    <div class="test-settings">
        <h2>Тестирование</h2>
        <p class="subtitle">Проверка компонентов системы</p>

        <div class="test-tabs">
            <button class="test-tab" :class="{ active: activeTest === 'llm' }" @click="activeTest = 'llm'">🤖 LLM</button>
            <button class="test-tab" :class="{ active: activeTest === 'websocket' }" @click="activeTest = 'websocket'">🔌 WebSocket</button>
            <button class="test-tab" :class="{ active: activeTest === 'microphone' }" @click="activeTest = 'microphone'">🎤 Микрофон</button>
            <button class="test-tab" :class="{ active: activeTest === 'tts' }" @click="activeTest = 'tts'">🔊 TTS</button>
        </div>

        <!-- LLM Test -->
        <div v-if="activeTest === 'llm'" class="test-panel">
            <h3>Тест подключения к LLM</h3>
            <p class="test-desc">Проверяет работу языковой модели (LM Studio / Ollama / OpenAI)</p>

            <div class="llm-input">
                <input v-model="llmInput" placeholder="Введите запрос..." class="form-input" />
                <button class="test-btn" @click="testLLM" :disabled="llmStatus === 'testing'">
                    <LoadingIcon v-if="llmStatus === 'testing'" class="spin" />
                    <SendIcon v-else />
                    Отправить
                </button>
            </div>

            <div class="test-result" :class="llmStatus">
                <div v-if="llmStatus === 'idle'" class="status-text">Введите запрос и нажмите "Отправить"</div>
                <div v-else-if="llmStatus === 'testing'" class="status-text"><LoadingIcon class="spin" /> Обработка...</div>
                <div v-else-if="llmStatus === 'ok'" class="status-text"><CheckIcon /> {{ llmResponse }}</div>
                <div v-else-if="llmStatus === 'error'" class="status-text"><ErrorIcon /> {{ llmError }}</div>
            </div>
        </div>

        <!-- WebSocket Test -->
        <div v-if="activeTest === 'websocket'" class="test-panel">
            <h3>Тест WebSocket</h3>
            <button class="test-btn" @click="testWebSocket" :disabled="wsStatus === 'testing'">
                <LoadingIcon v-if="wsStatus === 'testing'" class="spin" />
                Запустить тест
            </button>

            <div v-if="wsMessages.length > 0" class="ws-log">
                <div v-for="(msg, i) in wsMessages" :key="i">{{ msg }}</div>
            </div>
        </div>

        <!-- Microphone Test -->
        <div v-if="activeTest === 'microphone'" class="test-panel">
            <h3>Тест микрофона</h3>
            <button class="test-btn" @click="testMicrophone" :disabled="micStatus === 'testing'">
                <MicIcon v-if="micStatus !== 'testing'" />
                <LoadingIcon v-else class="spin" />
                {{ micStatus === 'testing' ? 'Слушаю...' : 'Проверить микрофон' }}
            </button>
            <div v-if="micStatus === 'ok'" class="test-result ok"><CheckIcon /> Микрофон работает</div>
            <div v-if="micStatus === 'error'" class="test-result error"><ErrorIcon /> Микрофон не работает</div>
        </div>

        <!-- TTS Test -->
        <div v-if="activeTest === 'tts'" class="test-panel">
            <h3>Тест голоса (TTS)</h3>
            <div class="llm-input">
                <input v-model="ttsText" placeholder="Текст для озвучки..." class="form-input" />
                <button class="test-btn" @click="testTTS" :disabled="ttsStatus === 'testing'">
                    <VolumeIcon v-if="ttsStatus !== 'testing'" />
                    <LoadingIcon v-else class="spin" />
                    Озвучить
                </button>
            </div>
            <div v-if="ttsStatus === 'ok'" class="test-result ok"><CheckIcon /> Текст озвучен</div>
            <div v-if="ttsStatus === 'error'" class="test-result error"><ErrorIcon /> Ошибка TTS</div>
        </div>
    </div>
</template>

<style scoped>
.test-settings h2 { font-size: 20px; font-weight: 600; margin-bottom: 4px; }
.subtitle { color: var(--text-secondary); font-size: 13px; margin-bottom: 20px; }

.test-tabs { display: flex; gap: 8px; margin-bottom: 20px; flex-wrap: wrap; }

.test-tab {
    padding: 8px 16px;
    border-radius: var(--radius-sm);
    background: var(--bg-card);
    border: 1px solid var(--border);
    color: var(--text-secondary);
    font-size: 13px;
    cursor: pointer;
    transition: all 0.2s;
}

.test-tab:hover { background: var(--bg-hover); }
.test-tab.active { background: var(--accent); color: white; border-color: var(--accent); }

.test-panel {
    padding: 20px;
    background: var(--bg-card);
    border-radius: var(--radius);
}

.test-panel h3 { font-size: 16px; font-weight: 600; margin-bottom: 4px; }
.test-desc { font-size: 12px; color: var(--text-muted); margin-bottom: 16px; }

.llm-input { display: flex; gap: 8px; margin-bottom: 16px; }

.form-input {
    flex: 1;
    padding: 10px 12px;
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    background: var(--bg-input);
    color: var(--text-primary);
    font-size: 14px;
}

.form-input:focus { outline: none; border-color: var(--accent); }

.test-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 10px 16px;
    border-radius: var(--radius-sm);
    background: var(--accent);
    color: white;
    border: none;
    font-size: 13px;
    cursor: pointer;
    transition: background 0.2s;
}

.test-btn:hover:not(:disabled) { background: var(--accent-hover); }
.test-btn:disabled { opacity: 0.6; }

.test-result {
    padding: 16px;
    border-radius: var(--radius-sm);
    margin-top: 12px;
}

.test-result.idle { background: var(--bg-input); }
.test-result.testing { background: rgba(255, 152, 0, 0.1); color: #ff9800; }
.test-result.ok { background: rgba(76, 175, 80, 0.1); color: #4caf50; }
.test-result.error { background: rgba(244, 67, 54, 0.1); color: #f44336; }

.status-text { display: flex; align-items: center; gap: 8px; font-size: 14px; }

.ws-log {
    margin-top: 12px;
    padding: 12px;
    background: var(--bg-input);
    border-radius: var(--radius-sm);
    font-family: var(--font-mono);
    font-size: 12px;
}

.ws-log div { padding: 4px 0; border-bottom: 1px solid var(--border); }
.ws-log div:last-child { border-bottom: none; }

.spin { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
</style>
