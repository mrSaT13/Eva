<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue';
import ThermometerIcon from '~icons/material-symbols/thermometer';

const props = defineProps<{
    entityId?: string;
    visible: boolean;
}>();

const temp = ref<string>('');
const unit = ref<string>('');
const name = ref<string>('');
const loading = ref(true);

const fetchTemp = async () => {
    if (!props.entityId) return;
    loading.value = true;
    try {
        const r = await fetch(`/api/eva_skills/ha/entities?filter=${props.entityId}`);
        if (r.ok) {
            const data = await r.json();
            const entity = (data.entities || []).find((e: any) => e.entity_id === props.entityId);
            if (entity) {
                temp.value = entity.state;
                unit.value = entity.unit || '°C';
                name.value = entity.friendly_name || entity.entity_id;
            }
        }
    } catch {}
    loading.value = false;
};

watch(() => props.visible, (v) => { if (v) fetchTemp(); });
onMounted(() => { if (props.visible) fetchTemp(); });
</script>

<template>
    <div v-if="visible && entityId" class="temp-widget">
        <div class="temp-icon"><ThermometerIcon /></div>
        <div class="temp-info">
            <div class="temp-value">{{ loading ? '...' : temp }}{{ unit }}</div>
            <div class="temp-name">{{ name }}</div>
        </div>
    </div>
</template>

<style scoped>
.temp-widget {
    display: flex; align-items: center; gap: 12px;
    background: linear-gradient(135deg, rgba(124,77,255,0.18), rgba(64,196,255,0.14));
    backdrop-filter: blur(14px);
    border: 1px solid rgba(124,77,255,0.35);
    border-radius: 18px; padding: 14px 18px;
    margin: 8px 0; max-width: 320px;
    box-shadow: 0 8px 28px rgba(124,77,255,0.2);
    animation: eva-fade-slide-up 0.3s var(--ease-smooth, cubic-bezier(0.22,1,0.36,1));
}
.temp-icon { font-size: 32px; background: linear-gradient(135deg, #b388ff, #40c4ff); -webkit-background-clip: text; background-clip: text; }
.temp-info { display: flex; flex-direction: column; }
.temp-value { font-size: 28px; font-weight: 800; background: linear-gradient(135deg, #fff, #40c4ff); -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; font-variant-numeric: tabular-nums; }
.temp-name { font-size: 12px; color: var(--text-muted); margin-top: 2px; }
</style>
