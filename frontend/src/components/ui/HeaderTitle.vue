<script setup lang="ts">
const props = defineProps<{
    text?: string,
}>();
</script>

<template>
    <span class="header-title"><span class="header-dot"></span>{{ props.text }}</span>
</template>

<style>
.header-title {
    display: inline-flex;
    align-items: center;
    gap: 9px;
    font-size: 17px;
    font-weight: 700;
    letter-spacing: 0.04em;
    background: linear-gradient(135deg, #fff 20%, #b388ff 60%, #40c4ff 100%);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
}

.header-dot {
    width: 9px;
    height: 9px;
    border-radius: 50%;
    background: linear-gradient(135deg, #7c4dff, #40c4ff);
    box-shadow: 0 0 12px rgba(124, 77, 255, 0.9);
    animation: eva-pulse-glow 2.4s ease-in-out infinite;
    -webkit-text-fill-color: initial;
    flex-shrink: 0;
}
</style>
