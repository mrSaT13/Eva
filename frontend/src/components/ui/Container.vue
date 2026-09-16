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
}

@media (min-width: 1400px) {
    .container {
        width: 800px;
    }
}

@media (max-width: 640px) {
    .container {
        width: 100%;
        padding: 14px 12px 20px;
    }
}
</style>
