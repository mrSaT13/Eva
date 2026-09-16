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
    background: rgba(11, 11, 16, 0.72);
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 16px;
    z-index: var(--z-header, 100);
    backdrop-filter: blur(20px) saturate(170%);
    -webkit-backdrop-filter: blur(20px) saturate(170%);
    padding-top: env(safe-area-inset-top, 0);
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.35);
}

.header::after {
    content: '';
    position: absolute;
    bottom: -1px;
    left: 8%;
    right: 8%;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(124,77,255,0.5), rgba(64,196,255,0.35), transparent);
    pointer-events: none;
}
</style>
