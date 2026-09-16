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
    --bg-primary: #0b0b10;
    --bg-secondary: #14141c;
    --bg-card: rgba(30, 30, 42, 0.72);
    --bg-input: rgba(255, 255, 255, 0.06);
    --bg-hover: rgba(255, 255, 255, 0.09);
    --bg-nav: rgba(14, 14, 20, 0.78);
    --text-primary: #f2f1fa;
    --text-secondary: #b3b0c7;
    --text-muted: #6f6c87;
    --accent: #7c4dff;
    --accent-2: #b388ff;
    --accent-3: #40c4ff;
    --accent-hover: #9e7bff;
    --accent-dim: rgba(124, 77, 255, 0.16);
    --gradient-accent: linear-gradient(135deg, #7c4dff 0%, #b388ff 48%, #40c4ff 100%);
    --gradient-bg: radial-gradient(1200px 600px at 15% -10%, rgba(124,77,255,0.18), transparent 60%),
        radial-gradient(900px 500px at 90% 0%, rgba(64,196,255,0.12), transparent 55%),
        radial-gradient(800px 600px at 50% 110%, rgba(179,136,255,0.1), transparent 60%);
    --msg-in: rgba(46, 125, 50, 0.22);
    --msg-out: linear-gradient(135deg, rgba(124,77,255,0.32), rgba(64,196,255,0.2));
    --border: rgba(255, 255, 255, 0.08);
    --shadow: 0 2px 12px rgba(0, 0, 0, 0.4);
    --shadow-lg: 0 12px 40px rgba(0, 0, 0, 0.45), 0 2px 8px rgba(124, 77, 255, 0.15);
    --shadow-glow: 0 0 0 1px rgba(124,77,255,0.25), 0 8px 32px rgba(124,77,255,0.35);
    --radius: 16px;
    --radius-sm: 10px;
    --radius-lg: 22px;
    --radius-pill: 999px;
    --header-h: 64px;
    --nav-h: 68px;
    --z-header: 100;
    --z-nav: 100;
    --z-overlay: 200;
    --color-error: #ff6b6b;
    --color-success: #51e08c;
    --color-warning: #ffb74d;
    --font: 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif;
    --font-mono: 'JetBrains Mono', 'Fira Code', monospace;
    --ease-spring: cubic-bezier(0.34, 1.4, 0.64, 1);
    --ease-smooth: cubic-bezier(0.22, 1, 0.36, 1);
}

* { box-sizing: border-box; margin: 0; padding: 0; }

html, body, #app {
    height: 100%;
}

body {
    background: var(--bg-primary);
    background-image: var(--gradient-bg);
    background-attachment: fixed;
    color: var(--text-primary);
    font-family: var(--font);
    font-size: 14px;
    line-height: 1.55;
    letter-spacing: 0.01em;
    -webkit-font-smoothing: antialiased;
    overflow: hidden;
}

a { color: var(--accent-2); text-decoration: none; }
a:hover { color: var(--accent-hover); }

::selection { background: rgba(124,77,255,0.45); color: #fff; }

::-webkit-scrollbar { width: 8px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
    background: linear-gradient(180deg, rgba(124,77,255,0.5), rgba(64,196,255,0.35));
    border-radius: 8px;
}

.icon-button, .icon-button:visited { color: var(--text-secondary); transition: color 0.2s; }
.icon-button:hover:not(:disabled) { color: var(--accent-2); }
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
    /* header (64) сверху и плавающая nav снизу — запас, чтобы контент не уезжал под них */
    padding-top: var(--header-h);
    padding-bottom: calc(var(--nav-h) + 28px);
    -webkit-overflow-scrolling: touch;
    position: relative;
    z-index: 1;
}

/*
  Адаптация под ширину экрана:
  - сама полоса на всю ширину (ПК использует место, мобила — всё доступное)
  - узкие страницы (чат) ограничивают себя сами изнутри (DialogPage: 720px)
  - широкие (настройки) занимают до 1280px
*/
.tab-pane {
    min-height: 100%;
    width: 100%;
    margin: 0 auto;
    padding: 0 20px;
}

@media (max-width: 640px) {
    .tab-pane {
        padding: 0 12px;
    }
}

.bottom-nav {
    position: fixed;
    bottom: 10px;
    left: 50%;
    transform: translateX(-50%);
    width: min(420px, calc(100% - 24px));
    height: var(--nav-h);
    background: var(--bg-nav);
    backdrop-filter: blur(20px) saturate(170%);
    -webkit-backdrop-filter: blur(20px) saturate(170%);
    border: 1px solid var(--border);
    border-radius: var(--radius-pill);
    display: flex;
    justify-content: center;
    gap: 6px;
    z-index: var(--z-nav);
    padding: 6px;
    padding-bottom: calc(6px + env(safe-area-inset-bottom, 0));
    box-shadow: var(--shadow-lg);
}

.nav-item {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    background: transparent;
    border: none;
    border-radius: var(--radius-pill);
    color: var(--text-muted);
    cursor: pointer;
    transition: background-color 0.2s, color 0.2s;
    padding: 10px 14px;
    position: relative;
}

.nav-item:hover {
    color: var(--text-secondary);
    background: var(--bg-hover);
}

.nav-item.active {
    color: #fff;
    background: linear-gradient(135deg, #7c4dff, #5b8cff);
    box-shadow: 0 4px 16px rgba(124, 77, 255, 0.35);
}

.nav-item.active:hover {
    filter: brightness(1.06);
}

.nav-icon {
    font-size: 22px;
    width: 22px;
    height: 22px;
    display: flex;
}

.nav-label {
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.02em;
}
</style>
