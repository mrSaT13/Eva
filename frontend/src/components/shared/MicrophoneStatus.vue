<script setup lang="ts">
import { useActor } from '@xstate/vue';
import { inject, computed } from 'vue';
import type { ActorRef } from 'xstate';

import MicIcon from '~icons/material-symbols/mic-rounded'
import MicOffIcon from '~icons/material-symbols/mic-off-rounded'
import LoadingIcon from '~icons/line-md/loading-twotone-loop'

const clientSTTMachine = useActor<ActorRef<any, any>>(inject('localRecognizerMachine') as any);
const serverSTTMachine = useActor<ActorRef<any, any>>(inject('inputStreamerMachine') as any);

const isListening = computed(() => {
    return serverSTTMachine.state.value.hasTag('active') ||
           clientSTTMachine.state.value.matches('active.sttClientSide');
});

const isStarting = computed(() => {
    return serverSTTMachine.state.value.hasTag('enabled') && !serverSTTMachine.state.value.hasTag('active') ||
           clientSTTMachine.state.value.hasTag('starting');
});

const hasError = computed(() => {
    return clientSTTMachine.state.value.hasTag('error') || serverSTTMachine.state.value.hasTag('error');
});

const isOff = computed(() => {
    return clientSTTMachine.state.value.matches('inactive') && !serverSTTMachine.state.value.hasTag('enabled');
});
</script>

<template>
    <div class="mic-status" :class="{ listening: isListening, starting: isStarting, error: hasError, off: isOff }">
        <template v-if="hasError">
            <span class="mic-icon" title="Ошибка микрофона">
                <MicOffIcon />
            </span>
            <span class="mic-label">Ошибка</span>
        </template>
        <template v-else-if="isOff">
            <span class="mic-icon" title="Микрофон выключен">
                <MicOffIcon />
            </span>
            <span class="mic-label">Микрофон выкл</span>
        </template>
        <template v-else-if="isListening">
            <span class="mic-icon pulse" title="Микрофон активен">
                <MicIcon />
            </span>
            <span class="mic-label">Слушаю...</span>
        </template>
        <template v-else-if="isStarting">
            <span class="mic-icon" title="Запуск микрофона">
                <MicIcon />
                <LoadingIcon class="loading-icon" />
            </span>
            <span class="mic-label">Запуск...</span>
        </template>
        <template v-else>
            <span class="mic-icon" title="Микрофон готов">
                <MicIcon />
            </span>
            <span class="mic-label">Готов</span>
        </template>
    </div>
</template>

<style scoped>
.mic-status {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 4px 10px;
    border-radius: 20px;
    background: var(--bg-card);
    transition: background 0.3s;
}

.mic-status.listening {
    background: rgba(76, 175, 80, 0.2);
}

.mic-status.starting {
    background: rgba(255, 152, 0, 0.2);
}

.mic-status.error {
    background: rgba(244, 67, 54, 0.2);
}

.mic-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
    font-size: 18px;
}

.mic-status.listening .mic-icon {
    color: #4caf50;
}

.mic-status.starting .mic-icon {
    color: #ff9800;
}

.mic-status.error .mic-icon {
    color: #f44336;
}

.mic-status.off .mic-icon {
    color: var(--text-muted);
}

.loading-icon {
    position: absolute;
    font-size: 18px;
}

.mic-label {
    font-size: 11px;
    color: var(--text-secondary);
    white-space: nowrap;
}

.mic-status.listening .mic-label {
    color: #4caf50;
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}

.pulse {
    animation: pulse 1.5s ease-in-out infinite;
}
</style>
