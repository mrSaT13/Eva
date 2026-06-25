<template>
    <main class="container">
        <slot></slot>
    </main>
</template>

<style>
.container {
    max-width: 100vw;
    width: 600px;
    padding: 16px;
    margin: 0 auto;
    min-height: 100%;
    position: relative;
}

@media (max-width: 640px) {
    .container {
        width: 100%;
        padding: 12px;
    }
}
</style>
