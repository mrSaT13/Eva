<script setup lang="ts">
import { inject, ref, computed } from 'vue';
import Message from './Message.vue';
import TimerWidget from './TimerWidget.vue';
import TemperatureWidget from './TemperatureWidget.vue';
import { eventBusKey } from '../eventBus';
import { useActor } from '@xstate/vue';
import type { ActorRef } from 'xstate';

import SendIcon from '~icons/material-symbols/send'
import CameraIcon from '~icons/material-symbols/camera'
import NoMessagesIcon from '~icons/mdi/message-processing-outline'

const inputValue = ref('');
const eventBus = inject(eventBusKey);
const showCameras = ref(false);
const cameras = ref<any[]>([]);
const loadingCameras = ref(false);

const loadCameras = async () => {
    loadingCameras.value = true;
    try {
        const res = await fetch('/api/ha_images/cameras');
        if (res.ok) cameras.value = await res.json();
    } catch {}
    loadingCameras.value = false;
    showCameras.value = !showCameras.value;
};

const sendCameraSnapshot = async (entityId: string) => {
    eventBus?.send('IN_TEXT_COMMAND', `Покажи камеру ${entityId}`);
    showCameras.value = false;
};

const historySm = useActor<ActorRef<any, any>>(inject('messageHistoryMachine') as any);

const showTempWidget = ref(false);
const tempEntityId = ref('');

const checkTemperatureQuery = (text: string) => {
    const lower = text.toLowerCase();
    if (lower.includes('температур') || lower.includes('тепл') || lower.includes('холодн')) {
        const match = text.match(/(sensor\.\w+)/);
        if (match) {
            tempEntityId.value = match[1];
            showTempWidget.value = true;
            setTimeout(() => { showTempWidget.value = false; }, 10000);
        }
    }
};

const sendCommand = () => {
    const command = inputValue.value;
    inputValue.value = '';
    if (command.trim() == '') return;
    checkTemperatureQuery(command);
    eventBus?.send('IN_TEXT_COMMAND', command);
};
</script>

<template>
    <div class="dialog-page">
        <TimerWidget />
        <TemperatureWidget :entityId="tempEntityId" :visible="showTempWidget" />
        <div class="messages-feed" ref="feed">
            <template v-for="message in historySm.state.value.context.messages" :key="message.id">
                <Message :message="message" />
            </template>
            <div v-if="historySm.state.value.context.messages.length === 0" class="empty-state">
                <div class="empty-icon">
                    <NoMessagesIcon />
                </div>
                <h3>Eva</h3>
                <p>Начните диалог с голосовым ассистентом</p>
                <p class="hint">Скажите "Ева" или напишите сообщение</p>
            </div>
            <div v-if="historySm.state.value.context.thinking" class="message message-out thinking-bubble">
                <div class="message-bubble thinking">
                    <span class="dot"></span><span class="dot"></span><span class="dot"></span>
                </div>
            </div>
        </div>

        <div v-if="showCameras" class="cameras-panel">
            <div class="cameras-header">
                <span>Камеры Home Assistant</span>
                <button @click="showCameras = false" class="close-btn">✕</button>
            </div>
            <div v-if="loadingCameras" class="cameras-loading">Загрузка...</div>
            <div v-else-if="cameras.length === 0" class="cameras-empty">Камеры не найдены</div>
            <div v-else class="cameras-list">
                <button v-for="cam in cameras" :key="cam.entity_id" class="camera-btn" @click="sendCameraSnapshot(cam.entity_id)">
                    <CameraIcon /> {{ cam.name }}
                </button>
            </div>
        </div>

        <div class="input-bar">
            <button @click="loadCameras" class="icon-btn" title="Камеры">
                <CameraIcon />
            </button>
            <input
                class="command-input"
                v-model="inputValue"
                @keydown.enter="sendCommand"
                placeholder="Напишите сообщение..."
            />
            <button @click="sendCommand" class="send-btn" :disabled="!inputValue.trim()">
                <SendIcon />
            </button>
        </div>
    </div>
</template>

<style scoped>
.dialog-page {
    display: flex;
    flex-direction: column;
    min-height: calc(100vh - var(--header-h, 64px) - var(--nav-h, 60px));
}

.messages-feed {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 12px;
    /* Отступ снизу, чтобы последнее сообщение не уезжало под input-bar */
    padding-bottom: 24px;
}

.empty-state {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    color: var(--text-secondary);
    gap: 8px;
    min-height: 50vh;
}

.empty-icon {
    font-size: 48px;
    color: var(--accent);
    margin-bottom: 16px;
    opacity: 0.6;
}

.empty-state h3 { font-size: 24px; font-weight: 600; color: var(--text-primary); }
.empty-state p { font-size: 14px; color: var(--text-secondary); }
.empty-state .hint { font-size: 12px; color: var(--text-muted); margin-top: 8px; }

.cameras-panel {
    position: fixed;
    bottom: calc(var(--nav-h, 60px) + 76px);
    left: 0;
    right: 0;
    max-width: 600px;
    margin: 0 auto;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius) var(--radius) 0 0;
    z-index: 50;
    max-height: 200px;
    overflow-y: auto;
}

.cameras-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    border-bottom: 1px solid var(--border);
    font-size: 13px;
    font-weight: 600;
}

.close-btn {
    background: none;
    border: none;
    color: var(--text-secondary);
    cursor: pointer;
    font-size: 16px;
}

.cameras-loading, .cameras-empty {
    padding: 16px;
    text-align: center;
    color: var(--text-muted);
    font-size: 13px;
}

.cameras-list {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 8px;
}

.camera-btn {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 12px;
    background: var(--bg-card);
    border: none;
    border-radius: var(--radius-sm);
    color: var(--text-primary);
    font-size: 13px;
    cursor: pointer;
    text-align: left;
}

.camera-btn:hover {
    background: var(--bg-hover);
}

/*
  ВАЖНО: input-bar НЕ position:fixed — теперь он в нормальном потоке,
  внизу страницы. Это убирает перекрытие нижней навигацией.
*/
.input-bar {
    display: flex;
    gap: 8px;
    padding: 12px 0;
    margin-top: auto;
}

.icon-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 44px;
    height: 44px;
    border-radius: 50%;
    background: var(--bg-input);
    border: 1px solid var(--border);
    color: var(--text-secondary);
    cursor: pointer;
    flex-shrink: 0;
    transition: all 0.2s;
}

.icon-btn:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
}

.command-input {
    flex: 1 1 auto;
    min-width: 0;
    background: var(--bg-input);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 12px 16px;
    font-size: 15px;
    color: var(--text-primary);
    outline: none;
    transition: border-color 0.2s;
}

.command-input::placeholder { color: var(--text-muted); }
.command-input:focus { border-color: var(--accent); }

.send-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 44px;
    height: 44px;
    border-radius: 50%;
    background: var(--accent);
    color: white;
    border: none;
    cursor: pointer;
    flex-shrink: 0;
    transition: background 0.2s, transform 0.1s;
}

.send-btn:hover:not(:disabled) { background: var(--accent-hover); transform: scale(1.05); }
.send-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.send-btn:active:not(:disabled) { transform: scale(0.95); }

.thinking-bubble { animation: fadeIn 0.2s ease-out; }
.thinking { display: flex; gap: 4px; align-items: center; padding: 14px 18px !important; }
.dot {
    width: 8px; height: 8px; border-radius: 50%;
    background: var(--text-muted); animation: bounce 1.4s infinite ease-in-out;
}
.dot:nth-child(1) { animation-delay: 0s; }
.dot:nth-child(2) { animation-delay: 0.2s; }
.dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce {
    0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
    40% { transform: scale(1); opacity: 1; }
}
</style>
