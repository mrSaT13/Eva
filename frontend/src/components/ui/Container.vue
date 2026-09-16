<template>
    <main class="container">
        <slot></slot>
    </main>
</template>

<style>
.container {
    max-width: 100vw;
    width: 760px;
    padding: 20px 16px 24px;
    margin: 0 auto;
    min-height: 100%;
    position: relative;
    animation: eva-fade-slide-up 0.35s cubic-bezier(0.22,1,0.36,1);
}

@media (max-width: 640px) {
    .container {
        width: 100%;
        padding: 14px 12px 20px;
    }
}
</style>
