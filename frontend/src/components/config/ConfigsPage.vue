<script setup lang="ts">
import { useMachine } from '@xstate/vue';

import { configMachine } from './sm';
import ConfigEditPanel from './ConfigEditPanel.vue';
import { computed } from '@vue/reactivity';

import LoadingIcon from '~icons/line-md/loading-twotone-loop'
import ErrorIcon from '~icons/material-symbols/error-outline'
import SettingsIcon from '~icons/material-symbols/tune'

const sm = useMachine(configMachine, {
    context: {
        error: null,
        configs: [],
    }
});

const editingConfig = computed(() => sm.state.value.context.configs?.[sm.state.value.context.editing]);
</script>

<template>
    <div class="configs-page">
        <div class="configs-header">
            <h1>Настройки</h1>
            <p class="subtitle">Управление плагинами и параметрами</p>
        </div>

        <div v-if="sm.state.value.matches('loading')" class="loading-state">
            <LoadingIcon class="spinner" />
            <p>Загрузка настроек...</p>
        </div>

        <div v-else-if="sm.state.value.matches('loadingError')" class="error-state">
            <ErrorIcon class="error-icon" />
            <h2>Ошибка загрузки</h2>
            <p>{{ sm.state.value.context.error }}</p>
        </div>

        <div v-else class="configs-list">
            <div
                v-for="(config, index) in sm.state.value.context.configs"
                :key="config.scope"
                class="config-card"
            >
                <div class="config-icon">
                    <SettingsIcon />
                </div>
                <div class="config-info">
                    <h3>{{ config.scope }}</h3>
                    <p v-if="config.comment">{{ config.comment }}</p>
                </div>
                <button class="config-btn" @click="sm.send('EDIT', { data: index })">
                    Настроить
                </button>
            </div>
        </div>

        <div class="configs-hint">
            <p>Для применения некоторых изменений может потребоваться перезапуск</p>
        </div>

        <ConfigEditPanel
            :open="sm.state.value.matches('editing')"
            :config="editingConfig"
            :onCancel="() => sm.send('CANCEL')"
            :onSave="data => sm.send('SAVE', { data })"
        />
    </div>
</template>

<style scoped>
.configs-page {
    display: flex;
    flex-direction: column;
    gap: 16px;
}

.configs-header h1 {
    font-size: 24px;
    font-weight: 600;
    margin-bottom: 4px;
}

.subtitle {
    color: var(--text-secondary);
    font-size: 14px;
}

.loading-state, .error-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 64px 0;
    text-align: center;
    gap: 16px;
}

.spinner {
    font-size: 48px;
    color: var(--accent);
}

.error-icon {
    font-size: 48px;
    color: var(--color-error);
}

.configs-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.config-card {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 16px 18px;
    background: rgba(24, 24, 36, 0.7);
    backdrop-filter: blur(14px);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg, 22px);
    transition: all 0.25s var(--ease-smooth, cubic-bezier(0.22,1,0.36,1));
    box-shadow: 0 4px 18px rgba(0,0,0,0.25);
}

.config-card:hover {
    background: rgba(30, 30, 44, 0.85);
    border-color: rgba(124,77,255,0.4);
    transform: translateY(-2px);
    box-shadow: 0 10px 32px rgba(0,0,0,0.35), 0 4px 18px rgba(124,77,255,0.2);
}

.config-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 44px;
    height: 44px;
    border-radius: 14px;
    background: linear-gradient(135deg, rgba(124,77,255,0.35), rgba(64,196,255,0.22));
    border: 1px solid rgba(124,77,255,0.35);
    color: #d3c2ff;
    font-size: 20px;
    flex-shrink: 0;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.15);
}

.config-info {
    flex: 1;
    min-width: 0;
}

.config-info h3 {
    font-size: 14px;
    font-weight: 600;
    margin-bottom: 2px;
}

.config-info p {
    font-size: 12px;
    color: var(--text-muted);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.config-btn {
    padding: 9px 18px;
    border-radius: var(--radius-pill, 999px);
    background: rgba(124,77,255,0.16);
    border: 1px solid rgba(124,77,255,0.4);
    color: #cdb7ff;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.25s var(--ease-spring, cubic-bezier(0.34,1.4,0.64,1));
    white-space: nowrap;
}

.config-btn:hover {
    background: linear-gradient(135deg, #7c4dff, #40c4ff);
    border-color: transparent;
    color: white;
    transform: translateY(-1px);
    box-shadow: 0 6px 20px rgba(124,77,255,0.45);
}

.config-btn:active { transform: scale(0.96); }

.configs-hint {
    text-align: center;
    padding: 16px 0;
    color: var(--text-muted);
    font-size: 12px;
}
</style>
