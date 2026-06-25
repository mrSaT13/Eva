<script setup lang="ts">
const props = defineProps<{
    text?: string,
}>();
</script>

<template>
    <span class="header-title">{{ props.text }}</span>
</template>

<style>
.header-title {
    font-size: 18px;
    font-weight: 600;
    letter-spacing: 0.5px;
}
</style>
