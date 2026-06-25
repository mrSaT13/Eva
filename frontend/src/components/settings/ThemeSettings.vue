<script setup lang="ts">
import { ref, watch, onMounted } from 'vue';
import SaveIcon from '~icons/material-symbols/save';
import CheckIcon from '~icons/material-symbols/check';

interface ThemeSettings {
    accentColor: string;
    bgColor: string;
    fontSize: number;
    darkMode: boolean;
    borderRadius: number;
}

const STORAGE_KEY = 'eva-theme-settings';
const defaults: ThemeSettings = { accentColor: '#7c4dff', bgColor: '#0f0f0f', fontSize: 14, darkMode: true, borderRadius: 12 };
const settings = ref<ThemeSettings>({ ...defaults });
const saved = ref(false);

const presetAccents = [
    { name: 'Фиолетовый', value: '#7c4dff' },
    { name: 'Синий', value: '#2196f3' },
    { name: 'Зелёный', value: '#4caf50' },
    { name: 'Оранжевый', value: '#ff9800' },
    { name: 'Красный', value: '#f44336' },
    { name: 'Розовый', value: '#e91e63' },
];

const presetBgs = [
    { name: 'Чёрный', value: '#0f0f0f' },
    { name: 'Тёмно-серый', value: '#1a1a1a' },
    { name: 'Серый', value: '#2d2d2d' },
    { name: 'Тёмно-синий', value: '#0d1117' },
    { name: 'Белый', value: '#f5f5f5' },
    { name: 'Светло-серый', value: '#e8e8e8' },
];

const loadSettings = () => {
    try { const s = localStorage.getItem(STORAGE_KEY); if (s) settings.value = { ...defaults, ...JSON.parse(s) }; } catch {}
};

const saveSettings = () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings.value));
    applySettings();
    saved.value = true;
    setTimeout(() => saved.value = false, 2000);
};

const applySettings = () => {
    const r = document.documentElement;
    const s = settings.value;
    r.style.setProperty('--accent', s.accentColor);
    r.style.setProperty('--accent-hover', s.accentColor + 'cc');
    r.style.setProperty('--accent-dim', s.accentColor + '26');
    r.style.setProperty('--radius', s.borderRadius + 'px');
    r.style.setProperty('--bg-primary', s.darkMode ? s.bgColor : '#f5f5f5');
    r.style.setProperty('--bg-secondary', s.darkMode ? lighten(s.bgColor, 10) : '#ffffff');
    r.style.setProperty('--bg-card', s.darkMode ? lighten(s.bgColor, 15) : '#ffffff');
    r.style.setProperty('--text-primary', s.darkMode ? '#e0e0e0' : '#1a1a1a');
    r.style.setProperty('--text-secondary', s.darkMode ? '#a0a0a0' : '#666');
    r.style.setProperty('--border', s.darkMode ? lighten(s.bgColor, 20) : '#e0e0e0');
};

function lighten(hex: string, p: number): string {
    hex = hex.replace('#', '');
    const r = Math.min(255, parseInt(hex.substring(0, 2), 16) + Math.round(255 * p / 100));
    const g = Math.min(255, parseInt(hex.substring(2, 4), 16) + Math.round(255 * p / 100));
    const b = Math.min(255, parseInt(hex.substring(4, 6), 16) + Math.round(255 * p / 100));
    return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
}

onMounted(() => { loadSettings(); applySettings(); });
watch(settings, () => applySettings(), { deep: true });
</script>

<template>
    <div class="theme-settings">
        <h2>Настройки темы</h2>

        <div class="section">
            <h3>Цвет акцента</h3>
            <div class="color-grid">
                <button v-for="c in presetAccents" :key="c.value" class="color-btn" :class="{ active: settings.accentColor === c.value }" :style="{ background: c.value }" @click="settings.accentColor = c.value" :title="c.name" />
                <input type="color" v-model="settings.accentColor" class="color-input" />
            </div>
        </div>

        <div class="section">
            <h3>Цвет фона</h3>
            <div class="color-grid">
                <button v-for="b in presetBgs" :key="b.value" class="color-btn bg" :class="{ active: settings.bgColor === b.value }" :style="{ background: b.value }" @click="settings.bgColor = b.value" :title="b.name" />
                <input type="color" v-model="settings.bgColor" class="color-input" />
            </div>
        </div>

        <div class="section">
            <h3>Тёмная тема</h3>
            <label class="toggle"><input type="checkbox" v-model="settings.darkMode" /><span class="slider"></span></label>
        </div>

        <div class="section">
            <h3>Скругление углов: {{ settings.borderRadius }}px</h3>
            <input type="range" v-model.number="settings.borderRadius" min="0" max="24" step="2" class="range" />
        </div>

        <button class="save-btn" @click="saveSettings">
            <CheckIcon v-if="saved" /><SaveIcon v-else />
            {{ saved ? 'Сохранено!' : 'Сохранить' }}
        </button>
    </div>
</template>

<style scoped>
.theme-settings h2 { font-size: 20px; font-weight: 600; margin-bottom: 20px; }
.section { margin-bottom: 24px; }
.section h3 { font-size: 14px; font-weight: 600; margin-bottom: 12px; color: var(--accent); }

.color-grid { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.color-btn { width: 36px; height: 36px; border-radius: 50%; border: 3px solid transparent; cursor: pointer; transition: transform 0.2s; }
.color-btn:hover { transform: scale(1.1); }
.color-btn.active { border-color: var(--text-primary); transform: scale(1.15); }
.color-btn.bg { border: 2px solid var(--border); }
.color-input { width: 36px; height: 36px; border: none; border-radius: 50%; cursor: pointer; padding: 0; }

.toggle { position: relative; width: 48px; height: 26px; display: inline-block; }
.toggle input { opacity: 0; width: 0; height: 0; }
.slider { position: absolute; cursor: pointer; inset: 0; background: var(--bg-input); border-radius: 13px; transition: background 0.3s; }
.slider::before { content: ''; position: absolute; height: 20px; width: 20px; left: 3px; bottom: 3px; background: var(--text-primary); border-radius: 50%; transition: transform 0.3s; }
.toggle input:checked + .slider { background: var(--accent); }
.toggle input:checked + .slider::before { transform: translateX(22px); }

.range { width: 100%; accent-color: var(--accent); }

.save-btn {
    display: flex; align-items: center; gap: 6px;
    padding: 10px 20px; border-radius: var(--radius-sm);
    background: var(--accent); color: white; border: none;
    font-size: 14px; cursor: pointer; transition: background 0.2s;
}
.save-btn:hover { background: var(--accent-hover); }
</style>
