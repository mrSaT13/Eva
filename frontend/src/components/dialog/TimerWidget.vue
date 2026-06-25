<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue';
import TimerIcon from '~icons/material-symbols/timer';
import StopwatchIcon from '~icons/material-symbols/av-timer';
import PauseIcon from '~icons/material-symbols/pause';
import PlayIcon from '~icons/material-symbols/play-arrow';
import StopIcon from '~icons/material-symbols/stop';

interface Timer {
    id: string;
    duration: number;
    remaining: number;
    message: string;
    active: boolean;
}

interface Stopwatch {
    id: string;
    label: string;
    elapsed: number;
    paused: boolean;
}

const timers = ref<Timer[]>([]);
const stopwatches = ref<Stopwatch[]>([]);
const newLabel = ref('');
let pollInterval: ReturnType<typeof setInterval> | null = null;

const formatCountdown = (seconds: number) => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    return `${m}:${String(s).padStart(2, '0')}`;
};

const formatElapsed = (seconds: number) => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    return `${m}:${String(s).padStart(2, '0')}`;
};

const progress = (t: Timer) => {
    if (!t.duration) return 0;
    return ((t.duration - t.remaining) / t.duration) * 100;
};

const hasActiveItems = computed(() => timers.value.length > 0 || stopwatches.value.length > 0);

const poll = async () => {
    try {
        const r = await fetch('/api/plugin_timer/status');
        if (r.ok) {
            const data = await r.json();
            timers.value = data.timers || [];
            stopwatches.value = data.stopwatches || [];
        }
    } catch {}
};

const startPolling = () => {
    if (pollInterval) return;
    poll();
    pollInterval = setInterval(poll, 2000);
};

const stopPolling = () => {
    if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
    }
};

const startStopwatch = async () => {
    try {
        await fetch('/api/plugin_timer/stopwatch/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ label: newLabel.value || 'Секундомер' }),
        });
        newLabel.value = '';
        startPolling();
        poll();
    } catch {}
};

const pauseStopwatch = async (id: string) => {
    try {
        await fetch(`/api/plugin_timer/stopwatch/${id}/pause`, { method: 'POST' });
        poll();
    } catch {}
};

const stopStopwatch = async (id: string) => {
    try {
        await fetch(`/api/plugin_timer/stopwatch/${id}/stop`, { method: 'POST' });
        poll();
    } catch {}
};

onMounted(async () => {
    await poll();
    if (hasActiveItems.value) {
        startPolling();
    }
});

onUnmounted(() => {
    stopPolling();
});

watch(hasActiveItems, (active) => {
    if (active) {
        startPolling();
    } else {
        stopPolling();
    }
});
</script>

<template>
    <div class="timer-widget" v-if="timers.length || stopwatches.length">
        <div v-for="t in timers" :key="t.id" class="timer-card">
            <div class="timer-header">
                <TimerIcon class="icon" />
                <span class="label">{{ t.message || 'Таймер' }}</span>
            </div>
            <div class="timer-display" :class="{ finished: !t.active }">
                {{ t.active ? formatCountdown(t.remaining) : '00:00' }}
            </div>
            <div class="progress-bar">
                <div class="progress-fill" :style="{ width: progress(t) + '%' }"></div>
            </div>
            <div v-if="!t.active" class="finished-text">Время вышло!</div>
        </div>

        <div v-for="sw in stopwatches" :key="sw.id" class="timer-card stopwatch-card">
            <div class="timer-header">
                <StopwatchIcon class="icon" />
                <span class="label">{{ sw.label }}</span>
                <span v-if="sw.paused" class="paused-badge">пауза</span>
            </div>
            <div class="timer-display">{{ formatElapsed(sw.elapsed) }}</div>
            <div class="controls">
                <button class="ctrl-btn" @click="pauseStopwatch(sw.id)" :title="sw.paused ? 'Продолжить' : 'Пауза'">
                    <PlayIcon v-if="sw.paused" />
                    <PauseIcon v-else />
                </button>
                <button class="ctrl-btn stop-btn" @click="stopStopwatch(sw.id)" title="Стоп">
                    <StopIcon />
                </button>
            </div>
        </div>

        <div class="new-stopwatch">
            <input v-model="newLabel" placeholder="Метка..." class="sw-input" @keydown.enter="startStopwatch" />
            <button class="start-btn" @click="startStopwatch">Старт</button>
        </div>
    </div>
</template>

<style scoped>
.timer-widget {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    padding: 8px 0;
    border-bottom: 1px solid var(--border, rgba(255,255,255,0.05));
}

.timer-card {
    background: var(--bg-card);
    border: 1px solid var(--border, rgba(255,255,255,0.1));
    border-radius: 12px;
    padding: 12px 16px;
    min-width: 180px;
    flex: 1;
}

.timer-header {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 6px;
}

.icon {
    font-size: 18px;
    color: var(--accent);
}

.label {
    font-size: 12px;
    color: var(--text-secondary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.paused-badge {
    font-size: 10px;
    background: var(--accent);
    color: #fff;
    padding: 1px 6px;
    border-radius: 8px;
    margin-left: auto;
}

.timer-display {
    font-size: 32px;
    font-weight: 700;
    text-align: center;
    font-variant-numeric: tabular-nums;
    color: var(--accent);
    letter-spacing: 1px;
}

.timer-display.finished {
    color: var(--text-muted);
}

.progress-bar {
    height: 3px;
    background: var(--bg-input, rgba(255,255,255,0.05));
    border-radius: 2px;
    margin-top: 8px;
    overflow: hidden;
}

.progress-fill {
    height: 100%;
    background: var(--accent);
    border-radius: 2px;
    transition: width 1s linear;
}

.finished-text {
    text-align: center;
    margin-top: 6px;
    font-size: 12px;
    font-weight: 600;
    color: #4caf50;
}

.controls {
    display: flex;
    justify-content: center;
    gap: 8px;
    margin-top: 8px;
}

.ctrl-btn {
    background: var(--bg-input, rgba(255,255,255,0.08));
    border: none;
    border-radius: 8px;
    padding: 6px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-primary);
    transition: background 0.15s;
}

.ctrl-btn:hover {
    background: var(--accent);
    color: #fff;
}

.stop-btn:hover {
    background: #ef5350;
}

.new-stopwatch {
    display: flex;
    gap: 6px;
    width: 100%;
}

.sw-input {
    flex: 1;
    background: var(--bg-input, rgba(255,255,255,0.08));
    border: 1px solid var(--border, rgba(255,255,255,0.1));
    border-radius: 8px;
    padding: 6px 10px;
    color: var(--text-primary);
    font-size: 13px;
}

.start-btn {
    background: var(--accent);
    color: #fff;
    border: none;
    border-radius: 8px;
    padding: 6px 14px;
    font-size: 13px;
    cursor: pointer;
}

.start-btn:hover {
    opacity: 0.9;
}
</style>
