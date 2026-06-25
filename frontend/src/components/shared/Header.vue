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
    width: 36px;
    height: 36px;
    border-radius: 50%;
    transition: background 0.2s, transform 0.2s;
    text-decoration: none;
}

.nav-btn:hover {
    background: var(--bg-hover);
}

a.router-link-exact-active {
    color: var(--accent);
    background: var(--accent-dim);
}

.home-btn:hover {
    transform: scale(1.05);
}
</style>
