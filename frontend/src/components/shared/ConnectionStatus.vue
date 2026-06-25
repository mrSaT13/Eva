<script setup lang="ts">
import { useActor } from '@xstate/vue';
import { computed, inject } from 'vue';
import type { ActorRef } from 'xstate';

const conn = useActor<ActorRef<any, any>>(inject('connectionStateMachine') as any);

const title = computed(() => {
    if (conn.state.value.matches('active.connecting')) {
        return 'Подключаюсь к серверу...'
    }
    if (conn.state.value.matches('disconnected')) {
        return 'Не удалось подключиться к серверу'
    }
    if (conn.state.value.matches('active.connected')) {
        return 'Подключение установлено'
    }
    return 'Статус подключения неизвестен'
});
</script>

<template>
    <div
        class="connection-status"
        :class="{
            connecting: conn.state.value.matches('active.connecting'),
            disconnected: conn.state.value.matches('disconnected'),
            connected: conn.state.value.matches('active.connected'),
        }"
        :title="title"
    />
</template>

<style scoped>
.connection-status {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--text-muted);
    transition: background 0.3s, box-shadow 0.3s;
}

.connection-status.connecting {
    background: var(--color-warning);
    box-shadow: 0 0 8px var(--color-warning);
    animation: pulse 1.5s ease-in-out infinite;
}

.connection-status.disconnected {
    background: var(--color-error);
    box-shadow: 0 0 8px var(--color-error);
}

.connection-status.connected {
    background: var(--color-success);
    box-shadow: 0 0 8px var(--color-success);
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}
</style>
