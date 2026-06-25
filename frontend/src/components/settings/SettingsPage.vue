<script setup lang="ts">
import { ref, watch, onMounted } from 'vue';
import PaletteIcon from '~icons/material-symbols/palette';
import DarkModeIcon from '~icons/material-symbols/dark-mode';
import TextFieldsIcon from '~icons/material-symbols/text-fields';
import SaveIcon from '~icons/material-symbols/save';
import CheckIcon from '~icons/material-symbols/check';

interface ThemeSettings {
    accentColor: string;
    bgColor: string;
    fontSize: number;
    darkMode: boolean;
    borderRadius: number;
    messageStyle: 'modern' | 'classic';
}

const STORAGE_KEY = 'eva-theme-settings';

const defaults: ThemeSettings = {
    accentColor: '#7c4dff',
    bgColor: '#0f0f0f',
    fontSize: 14,
    darkMode: true,
    borderRadius: 12,
    messageStyle: 'modern',
};

const settings = ref<ThemeSettings>({ ...defaults });
const saved = ref(false);

const presetAccents = [
    { name: 'Фиолетовый', value: '#7c4dff' },
    { name: 'Синий', value: '#2196f3' },
    { name: 'Зелёный', value: '#4caf50' },
    { name: 'Оранжевый', value: '#ff9800' },
    { name: 'Красный', value: '#f44336' },
    { name: 'Розовый', value: '#e91e63' },
    { name: 'Бирюзовый', value: '#00bcd4' },
    { name: 'Indigo', value: '#3f51b5' },
];

const presetBgs = [
    { name: 'Чёрный', value: '#0f0f0f', dark: true },
    { name: 'Тёмно-серый', value: '#1a1a1a', dark: true },
    { name: 'Серый', value: '#2d2d2d', dark: true },
    { name: 'Тёмно-синий', value: '#0d1117', dark: true },
    { name: 'Тёмно-зелёный', value: '#0a1a0a', dark: true },
    { name: 'Белый', value: '#f5f5f5', dark: false },
    { name: 'Светло-серый', value: '#e8e8e8', dark: false },
    { name: 'Кремовый', value: '#faf8f5', dark: false },
];

const loadSettings = () => {
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (raw) {
            const parsed = JSON.parse(raw);
            settings.value = { ...defaults, ...parsed };
        }
    } catch (e) {
        console.warn('Ошибка загрузки настроек:', e);
    }
};

const saveSettings = () => {
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(settings.value));
        applySettings();
        saved.value = true;
        setTimeout(() => { saved.value = false; }, 2000);
    } catch (e) {
        console.error('Ошибка сохранения настроек:', e);
    }
};

const applySettings = () => {
    const root = document.documentElement;
    const s = settings.value;

    root.style.setProperty('--accent', s.accentColor);
    root.style.setProperty('--accent-hover', s.accentColor + 'cc');
    root.style.setProperty('--accent-dim', s.accentColor + '26');
    root.style.setProperty('--font-size', s.fontSize + 'px');
    root.style.setProperty('--radius', s.borderRadius + 'px');
    root.style.setProperty('--radius-sm', Math.max(s.borderRadius - 4, 4) + 'px');

    if (s.darkMode) {
        root.style.setProperty('--bg-primary', s.bgColor);
        root.style.setProperty('--bg-secondary', lighten(s.bgColor, 10));
        root.style.setProperty('--bg-card', lighten(s.bgColor, 15));
        root.style.setProperty('--bg-input', lighten(s.bgColor, 20));
        root.style.setProperty('--bg-hover', lighten(s.bgColor, 25));
        root.style.setProperty('--text-primary', '#e0e0e0');
        root.style.setProperty('--text-secondary', '#a0a0a0');
        root.style.setProperty('--text-muted', '#666');
        root.style.setProperty('--border', lighten(s.bgColor, 20));
        root.style.setProperty('--msg-in', '#1e3a1e');
        root.style.setProperty('--msg-out', '#2a1e3a');
    } else {
        const lightBg = s.bgColor === '#0f0f0f' ? '#f5f5f5' : s.bgColor;
        root.style.setProperty('--bg-primary', lightBg);
        root.style.setProperty('--bg-secondary', '#ffffff');
        root.style.setProperty('--bg-card', '#ffffff');
        root.style.setProperty('--bg-input', '#f0f0f0');
        root.style.setProperty('--bg-hover', '#e8e8e8');
        root.style.setProperty('--text-primary', '#1a1a1a');
        root.style.setProperty('--text-secondary', '#666666');
        root.style.setProperty('--text-muted', '#999');
        root.style.setProperty('--border', '#e0e0e0');
        root.style.setProperty('--msg-in', '#e8f5e9');
        root.style.setProperty('--msg-out', '#f3e5f5');
    }

    root.style.setProperty('--shadow', `0 2px 12px rgba(0,0,0,${s.darkMode ? '0.4' : '0.1'})`);
};

function lighten(hex: string, percent: number): string {
    hex = hex.replace('#', '');
    const r = Math.min(255, parseInt(hex.substring(0, 2), 16) + Math.round(255 * percent / 100));
    const g = Math.min(255, parseInt(hex.substring(2, 4), 16) + Math.round(255 * percent / 100));
    const b = Math.min(255, parseInt(hex.substring(4, 6), 16) + Math.round(255 * percent / 100));
    return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
}

onMounted(() => {
    loadSettings();
    applySettings();
});

watch(settings, () => {
    applySettings();
}, { deep: true });
</script>

<template>
    <div class="settings-page">
        <h1>Настройки темы</h1>

        <div class="settings-section">
            <div class="section-header">
                <PaletteIcon />
                <h2>Цвет акцента</h2>
            </div>
            <div class="color-grid">
                <button
                    v-for="color in presetAccents"
                    :key="color.value"
                    class="color-btn"
                    :class="{ active: settings.accentColor === color.value }"
                    :style="{ background: color.value }"
                    @click="settings.accentColor = color.value"
                    :title="color.name"
                />
                <div class="custom-color">
                    <input type="color" v-model="settings.accentColor" class="color-input" />
                    <span>{{ settings.accentColor }}</span>
                </div>
            </div>
        </div>

        <div class="settings-section">
            <div class="section-header">
                <PaletteIcon />
                <h2>Цвет фона</h2>
            </div>
            <div class="color-grid">
                <button
                    v-for="bg in presetBgs"
                    :key="bg.value"
                    class="color-btn"
                    :class="{ active: settings.bgColor === bg.value }"
                    :style="{ background: bg.value, border: '2px solid ' + (bg.dark ? '#555' : '#ccc') }"
                    @click="settings.bgColor = bg.value"
                    :title="bg.name"
                />
                <div class="custom-color">
                    <input type="color" v-model="settings.bgColor" class="color-input" />
                    <span>{{ settings.bgColor }}</span>
                </div>
            </div>
        </div>

        <div class="settings-section">
            <div class="section-header">
                <DarkModeIcon />
                <h2>Режим отображения</h2>
            </div>
            <div class="toggle-row">
                <span>Тёмная тема</span>
                <label class="toggle">
                    <input type="checkbox" v-model="settings.darkMode" />
                    <span class="toggle-slider"></span>
                </label>
            </div>
        </div>

        <div class="settings-section">
            <div class="section-header">
                <TextFieldsIcon />
                <h2>Текст</h2>
            </div>
            <div class="slider-row">
                <span>Размер шрифта: {{ settings.fontSize }}px</span>
                <input type="range" v-model.number="settings.fontSize" min="12" max="20" step="1" />
            </div>
            <div class="slider-row">
                <span>Скругление углов: {{ settings.borderRadius }}px</span>
                <input type="range" v-model.number="settings.borderRadius" min="0" max="24" step="2" />
            </div>
        </div>

        <div class="settings-section">
            <div class="section-header">
                <SaveIcon />
                <h2>Стиль сообщений</h2>
            </div>
            <div class="radio-group">
                <label class="radio-option">
                    <input type="radio" v-model="settings.messageStyle" value="modern" />
                    <span>Современный</span>
                </label>
                <label class="radio-option">
                    <input type="radio" v-model="settings.messageStyle" value="classic" />
                    <span>Классический</span>
                </label>
            </div>
        </div>

        <button class="save-btn" @click="saveSettings">
            <CheckIcon v-if="saved" />
            <SaveIcon v-else />
            {{ saved ? 'Сохранено!' : 'Сохранить настройки' }}
        </button>

        <p class="hint">Настройки применяются автоматически и сохраняются в браузере</p>
    </div>
</template>

<style scoped>
.settings-page {
    display: flex;
    flex-direction: column;
    gap: 20px;
}

h1 {
    font-size: 24px;
    font-weight: 600;
    margin-bottom: 8px;
}

.hint {
    text-align: center;
    font-size: 12px;
    color: var(--text-muted);
}

.settings-section {
    background: var(--bg-card);
    border-radius: var(--radius);
    padding: 20px;
}

.section-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 16px;
    color: var(--accent);
}

.section-header h2 {
    font-size: 14px;
    font-weight: 600;
}

.color-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: center;
}

.color-btn {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    border: 3px solid transparent;
    cursor: pointer;
    transition: transform 0.2s, border-color 0.2s;
}

.color-btn:hover {
    transform: scale(1.1);
}

.color-btn.active {
    border-color: var(--text-primary);
    transform: scale(1.15);
}

.custom-color {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-left: 8px;
}

.color-input {
    width: 36px;
    height: 36px;
    border: none;
    border-radius: 50%;
    cursor: pointer;
    padding: 0;
}

.color-input::-webkit-color-swatch-wrapper {
    padding: 0;
}

.color-input::-webkit-color-swatch {
    border: 2px solid var(--border);
    border-radius: 50%;
}

.custom-color span {
    font-size: 12px;
    color: var(--text-muted);
    font-family: var(--font-mono);
}

.toggle-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.toggle {
    position: relative;
    width: 48px;
    height: 26px;
}

.toggle input {
    opacity: 0;
    width: 0;
    height: 0;
}

.toggle-slider {
    position: absolute;
    cursor: pointer;
    inset: 0;
    background: var(--bg-input);
    border-radius: 13px;
    transition: background 0.3s;
}

.toggle-slider::before {
    content: '';
    position: absolute;
    height: 20px;
    width: 20px;
    left: 3px;
    bottom: 3px;
    background: var(--text-primary);
    border-radius: 50%;
    transition: transform 0.3s;
}

.toggle input:checked + .toggle-slider {
    background: var(--accent);
}

.toggle input:checked + .toggle-slider::before {
    transform: translateX(22px);
}

.slider-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
}

.slider-row:last-child {
    margin-bottom: 0;
}

.slider-row span {
    font-size: 13px;
    color: var(--text-secondary);
}

.slider-row input[type="range"] {
    flex: 1;
    margin-left: 16px;
    accent-color: var(--accent);
}

.radio-group {
    display: flex;
    gap: 16px;
}

.radio-option {
    display: flex;
    align-items: center;
    gap: 6px;
    cursor: pointer;
    font-size: 13px;
    color: var(--text-secondary);
}

.radio-option input[type="radio"] {
    accent-color: var(--accent);
}

.save-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 14px 24px;
    background: var(--accent);
    color: white;
    border: none;
    border-radius: var(--radius);
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: background 0.2s, transform 0.2s;
}

.save-btn:hover {
    background: var(--accent-hover);
    transform: translateY(-2px);
}

.save-btn:active {
    transform: translateY(0);
}
</style>
