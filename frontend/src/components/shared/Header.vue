<script setup lang="ts">
import HeaderUI from '../ui/Header.vue';
import ConnectionStatus from './ConnectionStatus.vue';
import MicrophoneStatus from './MicrophoneStatus.vue';

import AboutIcon from '~icons/material-symbols/help-outline-rounded'
import HomeIcon from '~icons/material-symbols/home'
import { inject } from 'vue';

// В шапке больше нет дублей: testing/models/theme/config доступны через
// таб "Настройки" в нижней навигации. Здесь только "На главную" и "О программе".
</script>

<template>
    <HeaderUI>
        <div class="header-left">
            <ConnectionStatus />
            <MicrophoneStatus />
        </div>
        <div class="header-center">
            <RouterView name="heading" />
        </div>
        <div class="header-right">
            <RouterLink to="/" title="На главную" class="icon-button nav-btn home-btn">
                <HomeIcon />
            </RouterLink>
            <RouterLink to="/about" title="О программе" class="icon-button nav-btn">
                <AboutIcon />
            </RouterLink>
        </div>
    </HeaderUI>
</template>

<style scoped>
.header-left, .header-center, .header-right {
    display: flex;
    align-items: center;
    gap: 8px;
}

.header-left {
    flex: 1;
}

.header-center {
    flex: 0 0 auto;
}

.header-right {
    flex: 1;
    justify-content: flex-end;
}

.nav-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 38px;
    height: 38px;
    border-radius: 12px;
    background: var(--bg-input);
    border: 1px solid var(--border);
    transition: background-color 0.2s, border-color 0.2s;
    text-decoration: none;
}

.nav-btn:hover {
    background: var(--bg-hover);
    border-color: var(--border-strong, rgba(255,255,255,0.14));
}

a.router-link-exact-active {
    color: #fff;
    background: linear-gradient(135deg, #7c4dff, #5b8cff);
    border-color: transparent;
}

.home-btn:hover {
    transform: scale(1.05);
}
</style>
