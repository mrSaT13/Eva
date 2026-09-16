<script setup lang="ts">
import { ref } from 'vue';
import ThemeIcon from '~icons/material-symbols/palette';
import PluginIcon from '~icons/material-symbols/extension';
import SkillIcon from '~icons/material-symbols/psychology';
import IntegrationIcon from '~icons/material-symbols/hub';
import AutomationIcon from '~icons/material-symbols/bolt';
import TestIcon from '~icons/material-symbols/biotech';
import ModelIcon from '~icons/material-symbols/database';
import LLMIcon from '~icons/material-symbols/psychology';

import ThemeSettings from './ThemeSettings.vue';
import PluginSettings from './PluginSettings.vue';
import SkillSettings from './SkillSettings.vue';
import IntegrationSettings from './IntegrationSettings.vue';
import AutomationSettings from './AutomationSettings.vue';
import TestSettings from './TestSettings.vue';
import ModelSettings from '../models/ModelSettings.vue';
import LLMSettings from './LLMSettings.vue';

const activeSection = ref('theme');

const sections = [
    { id: 'theme', label: 'Тема', icon: ThemeIcon },
    { id: 'llm', label: 'LLM', icon: LLMIcon },
    { id: 'plugins', label: 'Плагины', icon: PluginIcon },
    { id: 'skills', label: 'Навыки', icon: SkillIcon },
    { id: 'integrations', label: 'Интеграции', icon: IntegrationIcon },
    { id: 'automations', label: 'Автоматизации', icon: AutomationIcon },
    { id: 'models', label: 'Модели', icon: ModelIcon },
    { id: 'testing', label: 'Тесты', icon: TestIcon },
];
</script>

<template>
    <div class="settings-layout">
        <div class="settings-sidebar">
            <h2>Настройки</h2>
            <nav class="settings-nav">
                <button
                    v-for="section in sections"
                    :key="section.id"
                    class="nav-btn"
                    :class="{ active: activeSection === section.id }"
                    @click="activeSection = section.id"
                >
                    <component :is="section.icon" />
                    <span>{{ section.label }}</span>
                </button>
            </nav>
        </div>

        <div class="settings-content">
            <ThemeSettings v-if="activeSection === 'theme'" />
            <LLMSettings v-else-if="activeSection === 'llm'" />
            <PluginSettings v-else-if="activeSection === 'plugins'" />
            <SkillSettings v-else-if="activeSection === 'skills'" />
            <IntegrationSettings v-else-if="activeSection === 'integrations'" />
            <AutomationSettings v-else-if="activeSection === 'automations'" />
            <ModelSettings v-else-if="activeSection === 'models'" />
            <TestSettings v-else-if="activeSection === 'testing'" />
        </div>
    </div>
</template>

<style scoped>
.settings-layout {
    display: flex;
    gap: 20px;
    align-items: flex-start;
    max-width: 1280px;
    margin: 0 auto;
    width: 100%;
    padding: 16px 0 32px;
}

.settings-sidebar {
    width: 230px;
    background: rgba(20, 20, 30, 0.6);
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 14px 10px;
    flex-shrink: 0;
}

.settings-sidebar h2 {
    font-size: 13px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-muted);
    padding: 4px 14px 12px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 10px;
}

.settings-nav {
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.nav-btn {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 11px 14px;
    background: transparent;
    border: 1px solid transparent;
    border-radius: 12px;
    color: var(--text-secondary);
    font-size: 14px;
    cursor: pointer;
    transition: background-color 0.2s, color 0.2s;
    text-align: left;
    width: 100%;
}

.nav-btn:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
}

.nav-btn.active {
    background: rgba(124, 77, 255, 0.18);
    color: #fff;
    border-color: rgba(124,77,255,0.35);
}

.nav-btn span {
    font-size: 13px;
}

.settings-content {
    flex: 1;
    min-width: 0;
    padding: 0 0 32px;
}

@media (max-width: 900px) {
    .settings-layout {
        flex-direction: column;
    }

    .settings-sidebar {
        width: 100%;
        padding: 10px;
    }

    .settings-nav {
        flex-direction: row;
        overflow-x: auto;
        padding: 0 12px;
        gap: 4px;
    }

    .nav-btn {
        padding: 8px 12px;
        white-space: nowrap;
    }

    .nav-btn.active {
        border-right: none;
        border-bottom: 3px solid var(--accent);
    }
}
</style>
