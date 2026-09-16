<script setup lang="ts">
import GithubIcon from '~icons/simple-icons/github';
import TelegramIcon from '~icons/simple-icons/telegram';
</script>

<template>
    <div class="about-page">
        <div class="about-header">
            <div class="logo">E</div>
            <h1>Eva Voice Assistant</h1>
            <p class="version">v1.0.0</p>
        </div>

        <div class="about-section">
            <h2>О проекте</h2>
            <p>Eva - русский голосовой ассистент для умного дома и повседневных задач.</p>
            <p>Основан на Irene Voice Assistant от AlexBond.</p>
        </div>

        <div class="about-section">
            <h2>Возможности</h2>
            <ul>
                <li>Голосовое управление умным домом (Home Assistant)</li>
                <li>Диалоговые навыки с циклами и условиями</li>
                <li>Конструктор навыков (визуальный редактор)</li>
                <li>LLM интеграция (Ollama, LM Studio, OpenAI)</li>
                <li>Автоматизации с триггерами (состояние, время, текст)</li>
                <li>Таймеры и напоминания</li>
                <li>NTP синхронизация времени</li>
                <li>Vosk распознавание речи</li>
                <li>TTS озвучка ответов</li>
                <li>Камеры Home Assistant</li>
                <li>Zigbee/ZHA устройства</li>
                <li>Авто-создание навыков через LLM</li>
                <li>Docker деплой</li>
            </ul>
        </div>

        <div class="about-section">
            <h2>Интеграции</h2>
            <ul>
                <li>Home Assistant (управление умным домом)</li>
                <li>MQTT (IoT устройства)</li>
                <li>Zigbee2MQTT (Zigbee устройства)</li>
                <li>Яндекс Станция</li>
                <li>Google Home</li>
                <li>IKEA Trådfri / Philips Hue</li>
                <li>Tuya / Xiaomi Mi Home</li>
                <li>Spotify / Navidrome</li>
                <li>Telegram / Discord боты</li>
                <li>RSS ленты / FreshRSS</li>
                <li>Погода (wttr.in, Open-Meteo)</li>
                <li>Википедия</li>
            </ul>
        </div>

        <div class="about-links">
            <a class="link-card" href="https://github.com/mrSaT13/Eva">
                <GithubIcon />
                <span>GitHub</span>
            </a>
            <a class="link-card" href="https://t.me/irene_va">
                <TelegramIcon />
                <span>Telegram</span>
            </a>
        </div>

        <div class="about-footer">
            <p>Создатель: mrSaT13</p>
            <p>Создано с помощью открытых технологий</p>
        </div>
    </div>
</template>

<style scoped>
.about-page {
    display: flex;
    flex-direction: column;
    gap: 24px;
}

.about-header {
    text-align: center;
    padding: 32px 0;
}

.logo {
    width: 88px;
    height: 88px;
    border-radius: 28px;
    background: linear-gradient(135deg, #7c4dff 0%, #b388ff 50%, #40c4ff 100%);
    background-size: 200% 200%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 38px;
    font-weight: 800;
    color: white;
    margin: 0 auto 16px;
    box-shadow: 0 14px 48px rgba(124, 77, 255, 0.5), inset 0 1px 0 rgba(255,255,255,0.4);
    animation: eva-gradient-pan 6s ease infinite, eva-float 5s ease-in-out infinite;
}

.about-header h1 {
    font-size: 24px;
    font-weight: 600;
    margin-bottom: 4px;
}

.version {
    color: var(--text-muted);
    font-size: 14px;
}

.about-section {
    background: rgba(24, 24, 36, 0.68);
    backdrop-filter: blur(14px);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg, 22px);
    padding: 20px;
    box-shadow: 0 4px 18px rgba(0,0,0,0.25);
    animation: eva-fade-slide-up 0.4s var(--ease-smooth, cubic-bezier(0.22,1,0.36,1));
}

.about-section h2 {
    font-size: 16px;
    font-weight: 600;
    margin-bottom: 12px;
    color: var(--accent);
}

.about-section p {
    color: var(--text-secondary);
    margin-bottom: 8px;
}

.about-section ul {
    list-style: none;
    padding: 0;
}

.about-section li {
    padding: 8px 0;
    color: var(--text-secondary);
    border-bottom: 1px solid var(--border);
}

.about-section li:last-child {
    border-bottom: none;
}

.about-links {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
}

.link-card {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 16px;
    background: rgba(24,24,36,0.7);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg, 22px);
    color: var(--text-primary);
    transition: all 0.25s var(--ease-spring, cubic-bezier(0.34,1.4,0.64,1));
}

.link-card:hover {
    background: rgba(32,32,48,0.9);
    border-color: rgba(124,77,255,0.45);
    transform: translateY(-3px);
    box-shadow: 0 12px 32px rgba(124,77,255,0.25);
}

.about-footer {
    text-align: center;
    padding: 16px 0;
    color: var(--text-muted);
    font-size: 12px;
}
</style>
