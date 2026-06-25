<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import DownloadIcon from '~icons/material-symbols/download';
import CheckIcon from '~icons/material-symbols/check-circle';
import ErrorIcon from '~icons/material-symbols/error';
import LoadingIcon from '~icons/line-md/loading-twotone-loop';
import RefreshIcon from '~icons/material-symbols/refresh';
import StarIcon from '~icons/material-symbols/star';
import StarOutlineIcon from '~icons/material-symbols/star-outline';

interface ModelInfo {
    id: string;
    name: string;
    description: string;
    size_mb: number;
    language: string;
    quality: string;
    installed: boolean;
    path: string | null;
    is_default?: boolean;
    progress?: {
        status: string;
        progress?: number;
        error?: string;
    };
}

const models = ref<ModelInfo[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);
const defaultModelId = ref<string>('vosk-small-ru-0.22');
let pollInterval: number | null = null;

const STORAGE_KEY = 'eva-default-vosk-model';

const loadDefaultModel = () => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) defaultModelId.value = saved;
};

const saveDefaultModel = (modelId: string) => {
    defaultModelId.value = modelId;
    localStorage.setItem(STORAGE_KEY, modelId);
    // Обновляем флаги is_default
    models.value = models.value.map(m => ({
        ...m,
        is_default: m.id === modelId,
    }));
};

const fetchModels = async () => {
    try {
        const response = await fetch('/api/vosk_sherpa/models');
        if (response.ok) {
            const data = await response.json();
            models.value = data.map((m: ModelInfo) => ({
                ...m,
                is_default: m.id === defaultModelId.value,
            }));
        }
    } catch (e) {
        error.value = 'Ошибка загрузки списка моделей';
    } finally {
        loading.value = false;
    }
};

const downloadModel = async (modelId: string) => {
    try {
        const response = await fetch('/api/vosk_sherpa/models/download', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model_id: modelId }),
        });
        if (response.ok) {
            // Начинаем опрос прогресса
            startPolling();
        }
    } catch (e) {
        error.value = 'Ошибка запуска скачивания';
    }
};

const startPolling = () => {
    if (pollInterval) return;
    pollInterval = window.setInterval(async () => {
        try {
            const response = await fetch('/api/vosk_sherpa/models/progress');
            if (response.ok) {
                const progress = await response.json();
                // Обновляем прогресс в моделях
                models.value = models.value.map(m => ({
                    ...m,
                    progress: progress[m.id] || m.progress,
                }));

                // Проверяем, все ли загрузки завершены
                const allDone = Object.values(progress).every(
                    (p: any) => p.status === 'ready' || p.status === 'error'
                );
                if (allDone) {
                    stopPolling();
                    fetchModels(); // Обновляем список
                }
            }
        } catch {}
    }, 1000);
};

const stopPolling = () => {
    if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
    }
};

const getStatusIcon = (model: ModelInfo) => {
    if (model.installed) return 'check';
    if (model.progress?.status === 'downloading') return 'loading';
    if (model.progress?.status === 'error') return 'error';
    return 'download';
};

const getStatusText = (model: ModelInfo) => {
    if (model.installed) return 'Установлена';
    if (model.progress?.status === 'downloading') return `${model.progress.progress || 0}%`;
    if (model.progress?.status === 'extracting') return 'Извлечение...';
    if (model.progress?.status === 'error') return model.progress.error || 'Ошибка';
    return 'Скачать';
};

const getLanguageLabel = (lang: string) => {
    const labels: Record<string, string> = { ru: 'Русский', en: 'English' };
    return labels[lang] || lang;
};

const getQualityLabel = (q: string) => {
    const labels: Record<string, string> = { standard: 'Стандарт', high: 'Высокое' };
    return labels[q] || q;
};

onMounted(() => {
    loadDefaultModel();
    fetchModels();
});

onUnmounted(() => {
    stopPolling();
});
</script>

<template>
    <div class="models-page">
        <div class="models-header">
            <h1>Модели распознавания речи</h1>
            <p class="subtitle">Управление моделями VOSK для распознавания голоса</p>
        </div>

        <div v-if="loading" class="loading-state">
            <LoadingIcon class="spinner" />
            <p>Загрузка списка моделей...</p>
        </div>

        <div v-else-if="error" class="error-state">
            <ErrorIcon class="error-icon" />
            <p>{{ error }}</p>
            <button class="retry-btn" @click="fetchModels">
                <RefreshIcon /> Повторить
            </button>
        </div>

        <div v-else class="models-list">
            <div
                v-for="model in models"
                :key="model.id"
                class="model-card"
                :class="{ installed: model.installed, downloading: model.progress?.status === 'downloading' }"
            >
                <div class="model-info">
                    <h3>{{ model.name }}</h3>
                    <p class="model-desc">{{ model.description }}</p>
                    <div class="model-meta">
                        <span class="tag lang">{{ getLanguageLabel(model.language) }}</span>
                        <span class="tag quality">{{ getQualityLabel(model.quality) }}</span>
                        <span class="tag size">{{ model.size_mb }} MB</span>
                    </div>
                </div>

                <div class="model-status">
                    <div v-if="model.progress?.status === 'downloading'" class="progress-bar">
                        <div class="progress-fill" :style="{ width: (model.progress.progress || 0) + '%' }"></div>
                    </div>

                    <button
                        v-if="!model.installed && model.progress?.status !== 'downloading' && model.progress?.status !== 'extracting'"
                        class="action-btn download"
                        @click="downloadModel(model.id)"
                    >
                        <DownloadIcon />
                        {{ getStatusText(model) }}
                    </button>

                    <div v-else-if="model.progress?.status === 'downloading'" class="progress-text">
                        <LoadingIcon class="spin" />
                        {{ model.progress.progress || 0 }}%
                    </div>

                    <div v-else-if="model.progress?.status === 'extracting'" class="progress-text">
                        <LoadingIcon class="spin" />
                        Извлечение...
                    </div>

                    <div v-else-if="model.installed" class="installed-actions">
                        <div class="installed-badge">
                            <CheckIcon />
                            Установлена
                        </div>
                        <button
                            class="default-btn"
                            :class="{ active: model.is_default }"
                            @click="saveDefaultModel(model.id)"
                            :title="model.is_default ? 'Модель по умолчанию' : 'Сделать по умолчанию'"
                        >
                            <StarIcon v-if="model.is_default" />
                            <StarOutlineIcon v-else />
                            {{ model.is_default ? 'По умолчанию' : 'Выбрать' }}
                        </button>
                    </div>

                    <div v-else-if="model.progress?.status === 'error'" class="error-text">
                        <ErrorIcon />
                        {{ model.progress.error }}
                    </div>
                </div>
            </div>
        </div>

        <div class="models-info">
            <p>Модели загружаются с alphacephei.com. Первая загрузка может занять несколько минут.</p>
            <p>VOSK 0.54 — новая модель с улучшенным качеством распознавания.</p>
        </div>
    </div>
</template>

<style scoped>
.models-page {
    display: flex;
    flex-direction: column;
    gap: 20px;
}

.models-header h1 {
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

.retry-btn {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 20px;
    background: var(--accent);
    color: white;
    border: none;
    border-radius: var(--radius-sm);
    cursor: pointer;
}

.models-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.model-card {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 20px;
    background: var(--bg-card);
    border-radius: var(--radius);
    transition: background 0.2s;
}

.model-card:hover {
    background: var(--bg-hover);
}

.model-card.installed {
    border-left: 3px solid var(--color-success);
}

.model-card.downloading {
    border-left: 3px solid var(--accent);
}

.model-info {
    flex: 1;
}

.model-info h3 {
    font-size: 16px;
    font-weight: 600;
    margin-bottom: 4px;
}

.model-desc {
    font-size: 13px;
    color: var(--text-secondary);
    margin-bottom: 8px;
}

.model-meta {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
}

.tag {
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 500;
}

.tag.lang {
    background: var(--accent-dim);
    color: var(--accent);
}

.tag.quality {
    background: rgba(76, 175, 80, 0.15);
    color: #4caf50;
}

.tag.size {
    background: rgba(255, 152, 0, 0.15);
    color: #ff9800;
}

.model-status {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 8px;
    min-width: 140px;
}

.progress-bar {
    width: 100%;
    height: 6px;
    background: var(--bg-input);
    border-radius: 3px;
    overflow: hidden;
}

.progress-fill {
    height: 100%;
    background: var(--accent);
    border-radius: 3px;
    transition: width 0.3s;
}

.action-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 16px;
    border-radius: var(--radius-sm);
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    transition: background 0.2s;
    border: none;
}

.action-btn.download {
    background: var(--accent);
    color: white;
}

.action-btn.download:hover {
    background: var(--accent-hover);
}

.progress-text {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 13px;
    color: var(--accent);
}

.spin {
    animation: spin 1s linear infinite;
}

@keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}

.installed-badge {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 13px;
    color: var(--color-success);
}

.installed-actions {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 8px;
}

.default-btn {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 4px 10px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
    border: 1px solid var(--border);
    background: var(--bg-input);
    color: var(--text-secondary);
}

.default-btn:hover {
    border-color: var(--accent);
    color: var(--accent);
}

.default-btn.active {
    background: var(--accent-dim);
    border-color: var(--accent);
    color: var(--accent);
}

.error-text {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 13px;
    color: var(--color-error);
}

.models-info {
    padding: 16px;
    background: var(--bg-card);
    border-radius: var(--radius);
    font-size: 12px;
    color: var(--text-muted);
}

.models-info p {
    margin-bottom: 4px;
}

.models-info p:last-child {
    margin-bottom: 0;
}
</style>
