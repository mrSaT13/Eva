<template>
    <header class="header">
        <slot></slot>
    </header>
</template>

<style>
.header {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    height: var(--header-h, 64px);
    background: rgba(26, 26, 26, 0.92);
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 16px;
    z-index: var(--z-header, 100);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    padding-top: env(safe-area-inset-top, 0);
}
</style>
