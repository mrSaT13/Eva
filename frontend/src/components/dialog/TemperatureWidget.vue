<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue';

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
        <div class="temp-icon">🌡️</div>
        <div class="temp-info">
            <div class="temp-value">{{ loading ? '...' : temp }}{{ unit }}</div>
            <div class="temp-name">{{ name }}</div>
        </div>
    </div>
</template>

<style scoped>
.temp-widget {
    display: flex; align-items: center; gap: 12px;
    background: linear-gradient(135deg, #1a237e22, #0d47a122);
    border: 1px solid #1565c044;
    border-radius: 16px; padding: 16px 20px;
    margin: 8px 0; max-width: 300px;
    animation: slideIn 0.3s ease-out;
}
.temp-icon { font-size: 32px; }
.temp-info { display: flex; flex-direction: column; }
.temp-value { font-size: 28px; font-weight: 700; color: #42a5f5; }
.temp-name { font-size: 12px; color: var(--text-muted); margin-top: 2px; }
@keyframes slideIn {
    from { opacity: 0; transform: translateY(-10px); }
    to { opacity: 1; transform: translateY(0); }
}
</style>
