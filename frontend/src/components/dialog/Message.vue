<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue';
import TimerIcon from '~icons/material-symbols/timer';

const props = defineProps<{
    message: {
        text: string,
        direction: 'in' | 'out',
        image?: string,
        imageUrl?: string,
        timestamp?: number,
        type?: 'text' | 'timer' | 'image' | 'system',
        timerDuration?: number,
        timerId?: string,
    }
}>();

const timeLeft = ref(0);
const timerActive = ref(false);
let interval: ReturnType<typeof setInterval> | null = null;

const formatTime = (ts?: number) => {
    if (!ts) return '';
    const d = new Date(ts);
    return d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
};

const formatCountdown = (seconds: number) => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    return `${m}:${String(s).padStart(2, '0')}`;
};

const countdown = computed(() => formatCountdown(timeLeft.value));
const progress = computed(() => {
    if (!props.message.timerDuration) return 0;
    return ((props.message.timerDuration - timeLeft.value) / props.message.timerDuration) * 100;
});

onMounted(() => {
    if (props.message.type === 'timer' && props.message.timerDuration) {
        timeLeft.value = props.message.timerDuration;
        timerActive.value = true;
        interval = setInterval(() => {
            if (timeLeft.value > 0) {
                timeLeft.value--;
            } else {
                timerActive.value = false;
                if (interval) clearInterval(interval);
            }
        }, 1000);
    }
});

onUnmounted(() => {
    if (interval) clearInterval(interval);
});
</script>

<template>
    <div class="message" :class="{
        'message-in': props.message.direction === 'in',
        'message-out': props.message.direction === 'out',
        'message-system': props.message.type === 'system',
        'message-timer': props.message.type === 'timer',
    }">
        <div v-if="props.message.type === 'timer'" class="timer-widget">
            <div class="timer-header">
                <TimerIcon class="timer-icon" />
                <span class="timer-label">{{ props.message.text || 'Таймер' }}</span>
            </div>
            <div class="timer-display" :class="{ finished: !timerActive }">
                {{ timerActive ? countdown : '00:00' }}
            </div>
            <div class="timer-progress">
                <div class="timer-progress-bar" :style="{ width: progress + '%' }"></div>
            </div>
            <div v-if="!timerActive && timeLeft === 0" class="timer-finished">Время вышло!</div>
        </div>

        <template v-else>
            <div v-if="props.message.image" class="message-image">
                <img :src="props.message.image" alt="Изображение" @error="(e: any) => e.target.style.display='none'" />
            </div>
            <div v-if="props.message.imageUrl" class="message-image">
                <img :src="props.message.imageUrl" alt="Изображение" @error="(e: any) => e.target.style.display='none'" />
            </div>
            <div v-if="props.message.text" class="message-bubble">
                {{ props.message.text }}
            </div>
        </template>

        <div v-if="props.message.timestamp" class="message-time">
            {{ formatTime(props.message.timestamp) }}
        </div>
    </div>
</template>

<style scoped>
.message {
    display: flex;
    flex-direction: column;
    max-width: 82%;
}

.message-in { align-self: flex-start; }
.message-out { align-self: flex-end; }
.message-system { align-self: center; max-width: 92%; }

.message-image { margin-bottom: 6px; }
.message-image img {
    max-width: 100%; max-height: 320px;
    border-radius: 18px; object-fit: cover;
    border: 1px solid var(--border);
    box-shadow: var(--shadow-card, 0 8px 28px rgba(0,0,0,0.35));
}

.message-bubble {
    padding: 13px 17px; border-radius: 20px;
    font-size: 14px; line-height: 1.6; word-break: break-word;
}
.message-in .message-bubble {
    background: rgba(255,255,255,0.06);
    border: 1px solid var(--border);
    border-bottom-left-radius: 6px;
}
.message-out .message-bubble {
    background: linear-gradient(135deg, rgba(124,77,255,0.3), rgba(91,140,255,0.2));
    border: 1px solid rgba(124, 77, 255, 0.35);
    border-bottom-right-radius: 6px;
}
.message-system .message-bubble {
    background: var(--accent-soft, rgba(124,77,255,0.1));
    border: 1px dashed rgba(124,77,255,0.4);
    text-align: center;
    color: var(--text-secondary);
    font-size: 12.5px;
}

.message-time {
    font-size: 10px; color: var(--text-muted);
    margin-top: 4px; padding: 0 4px;
}
.message-out .message-time { text-align: right; }

.timer-widget {
    background: rgba(22, 22, 34, 0.85);
    border: 1px solid rgba(124,77,255,0.35);
    border-radius: 20px; padding: 18px; min-width: 210px;
    position: relative;
    overflow: hidden;
}
.timer-widget::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, #7c4dff, #40c4ff);
}
.timer-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.timer-icon { font-size: 20px; color: var(--accent); }
.timer-label { font-size: 13px; font-weight: 500; color: var(--text-secondary); }
.timer-display {
    font-size: 44px; font-weight: 800; text-align: center;
    font-variant-numeric: tabular-nums;
    color: #c9b8ff;
    letter-spacing: 2px;
}
.timer-display.finished { color: var(--text-muted); }
.timer-progress {
    height: 6px; background: rgba(255,255,255,0.08); border-radius: 4px;
    margin-top: 12px; overflow: hidden;
}
.timer-progress-bar {
    height: 100%; background: linear-gradient(90deg, #7c4dff, #5b8cff); border-radius: 4px;
    transition: width 1s linear;
}
.timer-finished {
    text-align: center; margin-top: 8px;
    font-size: 14px; font-weight: 600; color: #4caf50;
}

@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}
</style>
