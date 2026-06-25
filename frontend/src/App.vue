<script setup lang="ts">
import { computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import Header from './components/shared/Header.vue';

const route = useRoute();
const router = useRouter();

const activeTab = computed<'chat' | 'settings'>(() => {
    return route.meta.tab === 'settings' ? 'settings' : 'chat';
});

const onChangeTab = (tab: 'chat' | 'settings') => {
    if (tab === 'settings') {
        if (activeTab.value === 'settings') return;
        router.push('/config');
    } else {
        if (activeTab.value === 'chat' && (route.path === '/' || route.path === '')) return;
        router.push('/');
    }
};
</script>

<template>
  <div class="app-layout">
    <Header :activeTab="activeTab" @change-tab="onChangeTab" />

    <main class="main-content">
      <!--
        В каждый момент времени виден только один слот, чтобы не было
        "одно на другом". Слоты выбираются по метаданным маршрута:
          - tab === 'settings' -> показываем named-view "settings" (страница настроек)
          - иначе -> показываем named-view "main" (чат / тестирование / модели / тема / о программе)
      -->
      <div v-show="activeTab !== 'settings'" class="tab-pane">
        <RouterView name="main" />
      </div>
      <div v-show="activeTab === 'settings'" class="tab-pane">
        <RouterView name="settings" />
      </div>
    </main>

    <nav class="bottom-nav">
      <button
        class="nav-item"
        :class="{ active: activeTab === 'chat' }"
        @click="onChangeTab('chat')"
      >
        <svg class="nav-icon" viewBox="0 0 24 24" fill="currentColor"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"/></svg>
        <span class="nav-label">Чат</span>
      </button>
      <button
        class="nav-item"
        :class="{ active: activeTab === 'settings' }"
        @click="onChangeTab('settings')"
      >
        <svg class="nav-icon" viewBox="0 0 24 24" fill="currentColor"><path d="M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.07.62-.07.94s.02.64.07.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z"/></svg>
        <span class="nav-label">Настройки</span>
      </button>
    </nav>
  </div>
</template>

<style>
:root {
    --bg-primary: #0f0f0f;
    --bg-secondary: #1a1a1a;
    --bg-card: #242424;
    --bg-input: #2a2a2a;
    --bg-hover: #333;
    --bg-nav: #141414;
    --text-primary: #e0e0e0;
    --text-secondary: #a0a0a0;
    --text-muted: #666;
    --accent: #7c4dff;
    --accent-hover: #9e7bff;
    --accent-dim: rgba(124, 77, 255, 0.15);
    --msg-in: #1e3a1e;
    --msg-out: #2a1e3a;
    --border: #333;
    --shadow: 0 2px 12px rgba(0, 0, 0, 0.4);
    --radius: 12px;
    --radius-sm: 8px;
    --header-h: 64px;
    --nav-h: 60px;
    --z-header: 100;
    --z-nav: 100;
    --z-overlay: 200;
    --color-error: #ff5252;
    --color-success: #4caf50;
    --color-warning: #ff9800;
    --font: 'Segoe UI', system-ui, -apple-system, sans-serif;
    --font-mono: 'JetBrains Mono', 'Fira Code', monospace;
}

* { box-sizing: border-box; margin: 0; padding: 0; }

html, body, #app {
    height: 100%;
}

body {
    background: var(--bg-primary);
    color: var(--text-primary);
    font-family: var(--font);
    font-size: 14px;
    line-height: 1.5;
    -webkit-font-smoothing: antialiased;
    overflow: hidden;
}

a { color: var(--accent); text-decoration: none; }
a:hover { color: var(--accent-hover); }

::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: var(--bg-secondary); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }

.icon-button, .icon-button:visited { color: var(--text-secondary); transition: color 0.2s; }
.icon-button:hover:not(:disabled) { color: var(--accent); }
</style>

<style scoped>
.app-layout {
    display: flex;
    flex-direction: column;
    height: 100vh;
    overflow: hidden;
}

.main-content {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    /* header (64) сверху и nav (60) снизу — отступы, чтобы ничего не уезжало под них */
    padding-top: var(--header-h);
    padding-bottom: var(--nav-h);
    -webkit-overflow-scrolling: touch;
}

.tab-pane {
    min-height: 100%;
}

.bottom-nav {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    height: var(--nav-h);
    background: var(--bg-nav);
    border-top: 1px solid var(--border);
    display: flex;
    justify-content: center;
    gap: 0;
    z-index: var(--z-nav);
    padding-bottom: env(safe-area-inset-bottom, 0);
}

.nav-item {
    flex: 1;
    max-width: 120px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 4px;
    background: none;
    border: none;
    color: var(--text-muted);
    cursor: pointer;
    transition: color 0.2s;
    padding: 8px;
}

.nav-item:hover {
    color: var(--text-secondary);
}

.nav-item.active {
    color: var(--accent);
}

.nav-icon {
    font-size: 22px;
}

.nav-label {
    font-size: 11px;
    font-weight: 500;
}
</style>
