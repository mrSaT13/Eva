<script setup lang="ts">
import { ref, onMounted } from 'vue';
import DownloadIcon from '~icons/material-symbols/download';
import CheckIcon from '~icons/material-symbols/check-circle';
import ErrorIcon from '~icons/material-symbols/error';
import LoadingIcon from '~icons/line-md/loading-twotone-loop';
import StarIcon from '~icons/material-symbols/star';
import StarOutlineIcon from '~icons/material-symbols/star-outline';

interface Model {
    id: string;
    name: string;
    description: string;
    size_mb: number;
    language: string;
    quality: string;
    installed: boolean;
    is_default?: boolean;
    progress?: { status: string; progress?: number; error?: string };
}

const models = ref<Model[]>([]);
const loading = ref(true);
const defaultModelId = ref('vosk-small-ru-0.22');
let pollInterval: number | null = null;

const loadDefault = () => {
    const saved = localStorage.getItem('eva-default-vosk-model');
    if (saved) defaultModelId.value = saved;
};

const saveDefault = (id: string) => {
    defaultModelId.value = id;
    localStorage.setItem('eva-default-vosk-model', id);
    models.value = models.value.map(m => ({ ...m, is_default: m.id === id }));
};

const fetchModels = async () => {
    try {
        const res = await fetch('/api/vosk_sherpa/models');
        if (res.ok) {
            models.value = (await res.json()).map((m: Model) => ({
                ...m, is_default: m.id === defaultModelId.value
            }));
        }
    } catch {} finally { loading.value = false; }
};

const download = async (id: string) => {
    try {
        await fetch('/api/vosk_sherpa/models/download', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model_id: id }),
        });
        startPolling();
    } catch {}
};

const startPolling = () => {
    if (pollInterval) return;
    pollInterval = window.setInterval(async () => {
        try {
            const res = await fetch('/api/vosk_sherpa/models/progress');
            if (res.ok) {
                const progress = await res.json();
                models.value = models.value.map(m => ({
                    ...m, progress: progress[m.id] || m.progress
                }));
                if (Object.values(progress).every((p: any) => p.status === 'ready' || p.status === 'error')) {
                    stopPolling();
                    fetchModels();
                }
            }
        } catch {}
    }, 1000);
};

const stopPolling = () => { if (pollInterval) { clearInterval(pollInterval); pollInterval = null; } };

onMounted(() => { loadDefault(); fetchModels(); });
</script>

<template>
    <div class="model-settings">
        <h2>Модели распознавания речи</h2>
        <p class="subtitle">Управление моделями VOSK для распознавания голоса</p>

        <div v-if="loading" class="loading"><LoadingIcon class="spin" /></div>

        <div v-else class="models-list">
            <div v-for="model in models" :key="model.id" class="model-card" :class="{ installed: model.installed }">
                <div class="model-info">
                    <h3>{{ model.name }}</h3>
                    <p>{{ model.description }}</p>
                    <div class="tags">
                        <span class="tag">{{ model.language === 'ru' ? 'Русский' : 'English' }}</span>
                        <span class="tag">{{ model.size_mb }} MB</span>
                    </div>
                </div>
                <div class="model-actions">
                    <div v-if="model.progress?.status === 'downloading'" class="progress">
                        <div class="progress-bar"><div class="progress-fill" :style="{ width: (model.progress.progress || 0) + '%' }"></div></div>
                        <span>{{ model.progress.progress }}%</span>
                    </div>
                    <button v-else-if="!model.installed" class="action-btn" @click="download(model.id)">
                        <DownloadIcon /> Скачать
                    </button>
                    <template v-else>
                        <button class="default-btn" :class="{ active: model.is_default }" @click="saveDefault(model.id)">
                            <StarIcon v-if="model.is_default" /><StarOutlineIcon v-else />
                            {{ model.is_default ? 'По умолчанию' : 'Выбрать' }}
                        </button>
                    </template>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.model-settings h2 { font-size: 20px; font-weight: 600; margin-bottom: 4px; }
.subtitle { color: var(--text-secondary); font-size: 13px; margin-bottom: 20px; }
.loading { display: flex; justify-content: center; padding: 40px; }
.spin { font-size: 32px; color: var(--accent); animation: spin 1s linear infinite; }

.models-list { display: flex; flex-direction: column; gap: 8px; }

.model-card {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px;
    background: var(--bg-card);
    border-radius: var(--radius-sm);
}

.model-card.installed { border-left: 3px solid var(--color-success); }

.model-info h3 { font-size: 14px; font-weight: 600; margin-bottom: 2px; }
.model-info p { font-size: 12px; color: var(--text-secondary); margin-bottom: 6px; }

.tags { display: flex; gap: 6px; }
.tag { padding: 2px 8px; border-radius: 10px; font-size: 11px; background: var(--accent-dim); color: var(--accent); }

.model-actions { display: flex; flex-direction: column; align-items: flex-end; gap: 8px; }

.progress { display: flex; align-items: center; gap: 8px; }
.progress-bar { width: 100px; height: 4px; background: var(--bg-input); border-radius: 2px; }
.progress-fill { height: 100%; background: var(--accent); border-radius: 2px; transition: width 0.3s; }

.action-btn {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 6px 12px;
    border-radius: var(--radius-sm);
    background: var(--accent);
    color: white;
    border: none;
    font-size: 12px;
    cursor: pointer;
}

.default-btn {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 4px 10px;
    border-radius: 12px;
    font-size: 11px;
    border: 1px solid var(--border);
    background: var(--bg-input);
    color: var(--text-secondary);
    cursor: pointer;
}

.default-btn.active { background: var(--accent-dim); border-color: var(--accent); color: var(--accent); }

@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
</style>
