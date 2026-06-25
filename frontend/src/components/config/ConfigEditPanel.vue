<script setup lang="ts">
import { ref, watch } from 'vue';
import { Vue3JsonEditor } from 'vue3-json-editor';
import Markdown from 'vue3-markdown-it';
import type { Config } from './service';

import CloseIcon from '~icons/material-symbols/close'

const props = defineProps<{
    open: boolean,
    config?: Config,
    onCancel: () => void,
    onSave: (cfg: Config) => void,
}>()

const value = ref();

watch(
    () => props.open ? props.config : null,
    (currentConfig) => {
        value.value = currentConfig?.config;
    }
);

const handleChange = (v: object) => {
    value.value = v;
}

const save = () => {
    if (props.config) {
        const updated = { ...props.config, config: value.value };
        props.onSave(updated);
    }
}
</script>

<template>
    <Teleport to="body">
        <Transition name="panel">
            <aside v-if="open && config" class="edit-panel" tabindex="-1" @keyup.esc="onCancel">
                <div class="panel-header">
                    <h2>{{ config.scope }}</h2>
                    <button class="close-btn" @click="onCancel">
                        <CloseIcon />
                    </button>
                </div>

                <div class="panel-content">
                    <div class="comment-section" v-if="config.comment">
                        <Markdown :source="config.comment" :linkify="true" />
                    </div>
                    <div class="editor-section">
                        <Vue3JsonEditor
                            v-model="value"
                            @json-change="handleChange"
                            mode="tree"
                            :show-btns="false"
                            :expanded-on-start="true"
                        />
                    </div>
                </div>

                <div class="panel-footer">
                    <button class="btn-cancel" @click="onCancel">Отмена</button>
                    <button class="btn-save" @click="save">Сохранить</button>
                </div>
            </aside>
        </Transition>
    </Teleport>
</template>

<style scoped>
.edit-panel {
    position: fixed;
    top: 0;
    right: 0;
    bottom: 0;
    width: 480px;
    max-width: 100vw;
    background: var(--bg-secondary);
    border-left: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    z-index: var(--z-overlay);
    box-shadow: -4px 0 24px rgba(0, 0, 0, 0.4);
}

.panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 20px;
    border-bottom: 1px solid var(--border);
}

.panel-header h2 {
    font-size: 16px;
    font-weight: 600;
}

.close-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: transparent;
    border: none;
    color: var(--text-secondary);
    cursor: pointer;
    transition: background 0.2s;
}

.close-btn:hover {
    background: var(--bg-hover);
}

.panel-content {
    flex: 1;
    overflow-y: auto;
    padding: 16px 20px;
}

.comment-section {
    margin-bottom: 16px;
    padding: 12px;
    background: var(--bg-card);
    border-radius: var(--radius-sm);
    font-size: 13px;
    color: var(--text-secondary);
    line-height: 1.6;
}

.editor-section {
    min-height: 300px;
}

.panel-footer {
    display: flex;
    gap: 8px;
    padding: 16px 20px;
    border-top: 1px solid var(--border);
}

.btn-cancel, .btn-save {
    flex: 1;
    padding: 12px;
    border-radius: var(--radius-sm);
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: background 0.2s;
    border: none;
}

.btn-cancel {
    background: var(--bg-card);
    color: var(--text-primary);
}

.btn-cancel:hover {
    background: var(--bg-hover);
}

.btn-save {
    background: var(--accent);
    color: white;
}

.btn-save:hover {
    background: var(--accent-hover);
}

/* Transition */
.panel-enter-active, .panel-leave-active {
    transition: transform 0.3s ease, opacity 0.3s ease;
}

.panel-enter-from, .panel-leave-to {
    transform: translateX(100%);
    opacity: 0;
}
</style>

<style>
/* JSON Editor dark theme overrides */
.jsoneditor {
    background: var(--bg-card) !important;
    border-color: var(--border) !important;
    border-radius: var(--radius-sm) !important;
}

.jsoneditor-tree {
    background: var(--bg-card) !important;
}

.jsoneditor-code {
    background: var(--bg-input) !important;
}

.jsoneditor-menu {
    background: var(--bg-secondary) !important;
    border-color: var(--border) !important;
}

.jsoneditor-menu > button {
    color: var(--text-secondary) !important;
}

.jsoneditor-menu > button:hover {
    color: var(--text-primary) !important;
}
</style>
