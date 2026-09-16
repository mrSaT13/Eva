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
import CloseIcon from '~icons/material-symbols/close'

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
        <div class="sticky-top">
            <TimerWidget />
            <TemperatureWidget :entityId="tempEntityId" :visible="showTempWidget" />
        </div>
        <div class="messages-feed" ref="feed">
            <template v-for="message in historySm.state.value.context.messages" :key="message.id">
                <Message :message="message" />
            </template>
            <div v-if="historySm.state.value.context.messages.length === 0" class="empty-state">
                <div class="empty-orb">
                    <div class="orb-core">E</div>
                    <div class="orb-ring"></div>
                </div>
                <h3>Eva</h3>
                <p>Начните диалог с голосовым ассистентом</p>
                <p class="hint">Скажите «Ева» или напишите сообщение</p>
                <div class="empty-chips">
                    <span class="chip">Включи свет</span>
                    <span class="chip">Поставь таймер</span>
                    <span class="chip">Какая погода?</span>
                </div>
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
                <button @click="showCameras = false" class="close-btn"><CloseIcon /></button>
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
    min-height: calc(100vh - var(--header-h, 64px) - var(--nav-h, 68px));
    position: relative;
    max-width: 760px;
    margin: 0 auto;
    width: 100%;
}

.sticky-top {
    position: sticky;
    top: 0;
    z-index: 10;
    background: transparent;
    padding-top: 12px;
}

.messages-feed {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 14px;
    padding: 12px 4px 24px;
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
    min-height: 52vh;
    animation: eva-fade-slide-up 0.5s var(--ease-smooth, cubic-bezier(0.22,1,0.36,1));
}

.empty-orb {
    position: relative;
    width: 120px;
    height: 120px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 12px;
}

.orb-core {
    width: 76px;
    height: 76px;
    border-radius: 26px;
    background: linear-gradient(135deg, #7c4dff 0%, #b388ff 50%, #40c4ff 100%);
    background-size: 200% 200%;
    animation: eva-gradient-pan 6s ease infinite, eva-float 4s ease-in-out infinite;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 34px;
    font-weight: 800;
    color: #fff;
    box-shadow: 0 12px 44px rgba(124, 77, 255, 0.5), inset 0 1px 0 rgba(255,255,255,0.35);
}

.orb-ring {
    position: absolute;
    inset: 0;
    border-radius: 50%;
    background: conic-gradient(from 0deg, rgba(124,77,255,0.5), rgba(64,196,255,0.35), transparent 65%, rgba(124,77,255,0.5));
    -webkit-mask: radial-gradient(farthest-side, transparent calc(100% - 3px), #000 calc(100% - 2px));
    mask: radial-gradient(farthest-side, transparent calc(100% - 3px), #000 calc(100% - 2px));
    animation: eva-orb-spin 9s linear infinite;
    opacity: 0.9;
}

.empty-state h3 {
    font-size: 26px;
    font-weight: 800;
    letter-spacing: 0.02em;
    background: linear-gradient(135deg, #fff, #b388ff 60%, #40c4ff);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
}
.empty-state p { font-size: 14px; color: var(--text-secondary); }
.empty-state .hint { font-size: 12px; color: var(--text-muted); margin-top: 4px; }

.empty-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    justify-content: center;
    margin-top: 16px;
}

.chip {
    font-size: 12px;
    padding: 8px 14px;
    border-radius: var(--radius-pill, 999px);
    background: var(--bg-input);
    border: 1px solid var(--border);
    color: var(--text-secondary);
    backdrop-filter: blur(12px);
    transition: all 0.25s var(--ease-smooth, cubic-bezier(0.22,1,0.36,1));
    cursor: default;
}

.chip:hover {
    border-color: rgba(124,77,255,0.5);
    color: var(--text-primary);
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(124,77,255,0.25);
}

.cameras-panel {
    position: fixed;
    bottom: calc(var(--nav-h, 68px) + 76px);
    left: 0;
    right: 0;
    max-width: 600px;
    margin: 0 auto;
    background: rgba(22, 22, 32, 0.85);
    backdrop-filter: blur(20px) saturate(170%);
    -webkit-backdrop-filter: blur(20px) saturate(170%);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg, 22px);
    box-shadow: var(--shadow-lg, 0 12px 40px rgba(0,0,0,0.45));
    z-index: 50;
    max-height: 240px;
    overflow-y: auto;
    animation: eva-fade-slide-up 0.3s var(--ease-smooth, cubic-bezier(0.22,1,0.36,1));
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
    background: var(--bg-input);
    border: 1px solid transparent;
    border-radius: var(--radius-sm, 10px);
    color: var(--text-primary);
    font-size: 13px;
    cursor: pointer;
    text-align: left;
    transition: all 0.22s var(--ease-smooth, cubic-bezier(0.22,1,0.36,1));
}

.camera-btn:hover {
    background: var(--bg-hover);
    border-color: rgba(124,77,255,0.35);
    transform: translateX(3px);
}

/*
  Floating glass input-pill, sticky внизу
*/
.input-bar {
    display: flex;
    gap: 8px;
    align-items: center;
    padding: 10px;
    margin-top: auto;
    position: sticky;
    bottom: 8px;
    z-index: 20;
    background: rgba(20, 20, 30, 0.78);
    backdrop-filter: blur(20px) saturate(170%);
    -webkit-backdrop-filter: blur(20px) saturate(170%);
    border: 1px solid var(--border);
    border-radius: var(--radius-pill, 999px);
    box-shadow: var(--shadow-lg, 0 12px 40px rgba(0,0,0,0.45));
    transition: border-color 0.25s, box-shadow 0.25s;
}

.input-bar:focus-within {
    border-color: rgba(124,77,255,0.55);
    box-shadow: 0 0 0 1px rgba(124,77,255,0.3), 0 12px 44px rgba(124,77,255,0.3);
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
    transition: all 0.25s var(--ease-spring, cubic-bezier(0.34,1.4,0.64,1));
}

.icon-btn:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
    transform: translateY(-1px) scale(1.04);
    border-color: rgba(124,77,255,0.4);
}

.icon-btn:active { transform: scale(0.94); }

.command-input {
    flex: 1 1 auto;
    min-width: 0;
    background: transparent;
    border: none;
    padding: 12px 8px;
    font-size: 15px;
    color: var(--text-primary);
    outline: none;
}

.command-input::placeholder { color: var(--text-muted); }

.send-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 44px;
    height: 44px;
    border-radius: 50%;
    background: linear-gradient(135deg, #7c4dff 0%, #9e7bff 50%, #40c4ff 130%);
    background-size: 180% 180%;
    color: white;
    border: none;
    cursor: pointer;
    flex-shrink: 0;
    box-shadow: 0 4px 20px rgba(124, 77, 255, 0.5), inset 0 1px 0 rgba(255,255,255,0.3);
    transition: all 0.25s var(--ease-spring, cubic-bezier(0.34,1.4,0.64,1));
}

.send-btn:hover:not(:disabled) {
    filter: brightness(1.1);
    transform: scale(1.06) translateY(-1px);
    box-shadow: 0 8px 28px rgba(124, 77, 255, 0.6);
    animation: eva-gradient-pan 2s ease infinite;
}
.send-btn:disabled { opacity: 0.35; cursor: not-allowed; filter: grayscale(0.4); }
.send-btn:active:not(:disabled) { transform: scale(0.93); }

.thinking-bubble { animation: eva-fade-slide-up 0.25s ease-out; }
.thinking {
    display: flex; gap: 5px; align-items: center; padding: 16px 20px !important;
    background: var(--bg-card) !important;
    border: 1px solid var(--border);
    position: relative;
    overflow: hidden;
}
.thinking::after {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(90deg, transparent, rgba(124,77,255,0.14), transparent);
    background-size: 400px 100%;
    animation: eva-shimmer 1.6s linear infinite;
}
.dot {
    width: 8px; height: 8px; border-radius: 50%;
    background: linear-gradient(135deg, var(--accent, #7c4dff), var(--accent-3, #40c4ff));
    animation: bounce 1.4s infinite ease-in-out;
}
.dot:nth-child(1) { animation-delay: 0s; }
.dot:nth-child(2) { animation-delay: 0.2s; }
.dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce {
    0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
    40% { transform: scale(1); opacity: 1; }
}
</style>
