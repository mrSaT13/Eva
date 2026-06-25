<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import CheckIcon from '~icons/material-symbols/check-circle';
import ErrorIcon from '~icons/material-symbols/error';
import LoadingIcon from '~icons/line-md/loading-twotone-loop';
import AddIcon from '~icons/material-symbols/add';
import DeleteIcon from '~icons/material-symbols/delete';
import PlayIcon from '~icons/material-symbols/play-arrow';
import SendIcon from '~icons/material-symbols/send';
import EditIcon from '~icons/material-symbols/edit';
import CloseIcon from '~icons/material-symbols/close';

interface Trigger { type: string; entity_id?: string; time?: string; event?: string; condition?: string; }
interface Action { type: string; entity_id?: string; service?: string; data?: any; message?: string; }
interface Automation { id: string; name: string; trigger: Trigger; actions: Action[]; enabled: boolean; }

interface HAEntity { entity_id: string; state: string; name: string; domain: string; }
interface TriggerType { type: string; name: string; icon: string; fields: string[]; }
interface ActionType { type: string; name: string; icon: string; fields: string[]; }

const automations = ref<Automation[]>([]);
const loading = ref(true);
const haDevices = ref<HAEntity[]>([]);
const deviceFilter = ref('');
const deviceSearch = ref('');
const deviceDomains = computed(() => {
    const domains = new Set(haDevices.value.map(d => d.domain));
    return Array.from(domains).sort();
});
const filteredDevices = computed(() => {
    let list = haDevices.value;
    if (deviceFilter.value) list = list.filter(d => d.domain === deviceFilter.value);
    if (deviceSearch.value) {
        const q = deviceSearch.value.toLowerCase();
        list = list.filter(d => d.name.toLowerCase().includes(q) || d.entity_id.toLowerCase().includes(q));
    }
    return list;
});

const selectDevice = (entityId: string) => {
    newAuto.trigger.entity_id = entityId;
    const device = haDevices.value.find(d => d.entity_id === entityId);
    if (device) deviceFilter.value = device.domain;
};
const triggerTypes = ref<TriggerType[]>([]);
const actionTypes = ref<ActionType[]>([]);
const haStatus = ref<{ connected: boolean; error?: string } | null>(null);

const showCreate = ref(false);
const editingId = ref<string | null>(null);
const newAuto = ref<{ name: string; trigger: Trigger; actions: Action[] }>({
    name: '', trigger: { type: 'time', time: '08:00' }, actions: []
});
const testResult = ref<any>(null);
const sendingId = ref<string | null>(null);

const fetchAutomations = async () => {
    try { const r = await fetch('/api/automations/'); if (r.ok) automations.value = await r.json(); } catch {} finally { loading.value = false; }
};
const fetchHADevices = async () => {
    try { const r = await fetch('/api/automations/ha/devices'); if (r.ok) haDevices.value = await r.json(); } catch {}
};
const fetchTriggerTypes = async () => {
    try { const r = await fetch('/api/automations/ha/trigger_types'); if (r.ok) triggerTypes.value = await r.json(); } catch {}
};
const fetchActionTypes = async () => {
    try { const r = await fetch('/api/automations/ha/action_types'); if (r.ok) actionTypes.value = await r.json(); } catch {}
};
const checkHA = async () => {
    try { const r = await fetch('/api/automations/ha_status'); if (r.ok) haStatus.value = await r.json(); } catch {}
};

const createAutomation = async () => {
    if (!newAuto.value.name) return;
    try {
        const r = await fetch('/api/automations/', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(newAuto.value) });
        if (r.ok) { automations.value.push(await r.json()); showCreate.value = false; resetForm(); }
    } catch {}
};

const updateAutomation = async () => {
    if (!editingId.value) return;
    try {
        const r = await fetch(`/api/automations/${editingId.value}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(newAuto.value) });
        if (r.ok) { const updated = await r.json(); const idx = automations.value.findIndex(a => a.id === editingId.value); if (idx >= 0) automations.value[idx] = updated; editingId.value = null; resetForm(); }
    } catch {}
};

const deleteAutomation = async (id: string) => {
    try { await fetch(`/api/automations/${id}`, { method: 'DELETE' }); automations.value = automations.value.filter(a => a.id !== id); } catch {}
};

const toggleAutomation = async (auto: Automation) => {
    try { await fetch(`/api/automations/${auto.id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ enabled: !auto.enabled }) }); auto.enabled = !auto.enabled; } catch {}
};

const testAutomation = async (id: string) => {
    sendingId.value = id; testResult.value = null;
    try { const r = await fetch(`/api/automations/${id}/test`, { method: 'POST' }); testResult.value = await r.json(); } catch { testResult.value = { status: 'error' }; }
    finally { sendingId.value = null; setTimeout(() => testResult.value = null, 3000); }
};

const startEdit = (auto: Automation) => {
    editingId.value = auto.id;
    newAuto.value = { name: auto.name, trigger: { ...auto.trigger }, actions: auto.actions.map(a => ({ ...a })) };
    showCreate.value = true;
};

const resetForm = () => {
    newAuto.value = { name: '', trigger: { type: 'time', time: '08:00' }, actions: [] };
};

const addAction = (type: string) => {
    const action: Action = { type, data: {} };
    if (type === 'service') { action.service = 'light.turn_on'; action.entity_id = ''; action.data = {}; }
    if (type === 'notify' || type === 'speak' || type === 'reply') { action.message = ''; }
    if (type === 'delay') { action.data = { seconds: 60 }; }
    newAuto.value.actions.push(action);
};

const removeAction = (index: number) => { newAuto.value.actions.splice(index, 1); };

const getDomainIcon = (domain: string) => {
    const icons: Record<string, string> = { light: 'bulb', switch: 'toggle_on', sensor: 'thermostat', binary_sensor: 'motion_sensor', climate: 'thermostat', media_player: 'play_circle', cover: 'blinds', lock: 'lock', fan: 'air' };
    return icons[domain] || 'devices';
};

const getEntityName = (eid: string) => {
    const device = haDevices.value.find(d => d.entity_id === eid);
    return device ? device.name : eid;
};

onMounted(() => { checkHA(); fetchTriggerTypes(); fetchActionTypes(); fetchHADevices(); fetchAutomations(); });
</script>

<template>
    <div class="auto-page">
        <div class="auto-header">
            <div><h2>Автоматизации</h2><p class="subtitle">Сценарии и правила автоматизации</p></div>
            <button class="add-btn" @click="showCreate = !showCreate; editingId = null; resetForm()"><AddIcon /> Создать</button>
        </div>

        <div v-if="haStatus" class="ha-bar" :class="{ ok: haStatus.connected, err: !haStatus.connected }">
            <component :is="haStatus.connected ? CheckIcon : ErrorIcon" />
            {{ haStatus.connected ? 'Home Assistant подключён' : (haStatus.error || 'HA не настроен') }}
        </div>

        <!-- Create/Edit Form -->
        <div v-if="showCreate" class="create-form">
            <div class="form-header">
                <h3>{{ editingId ? 'Редактировать сценарий' : 'Новый сценарий' }}</h3>
                <button class="close-btn" @click="showCreate = false; editingId = null"><CloseIcon /></button>
            </div>

            <input v-model="newAuto.name" placeholder="Название сценария" class="form-input" />

            <!-- Trigger Section -->
            <div class="section-card">
                <div class="section-label">Если</div>
                <div class="trigger-options">
                    <button v-for="tt in triggerTypes" :key="tt.type" class="option-btn" :class="{ active: newAuto.trigger.type === tt.type }" @click="newAuto.trigger = { type: tt.type }">
                        {{ tt.name }}
                    </button>
                </div>

                <div v-if="newAuto.trigger.type === 'time'" class="trigger-detail">
                    <input v-model="newAuto.trigger.time" type="time" class="form-input" />
                </div>
                <div v-else-if="newAuto.trigger.type === 'state'" class="trigger-detail">
                    <input v-model="deviceSearch" placeholder="Поиск устройства..." class="form-input" />
                    <select v-model="deviceFilter" class="form-select sm">
                        <option value="">Все типы</option>
                        <option v-for="d in deviceDomains" :key="d" :value="d">{{ d }}</option>
                    </select>
                    <select :value="newAuto.trigger.entity_id" @change="selectDevice(($event.target as HTMLSelectElement).value)" class="form-select">
                        <option value="">Выберите устройство ({{ filteredDevices.length }})</option>
                        <option v-for="d in filteredDevices" :key="d.entity_id" :value="d.entity_id">{{ d.name }} ({{ d.state }})</option>
                    </select>
                    <input v-model="newAuto.trigger.condition" placeholder="Состояние (on/off)" class="form-input" />
                </div>
                <div v-else-if="newAuto.trigger.type === 'sun'" class="trigger-detail">
                    <select v-model="newAuto.trigger.event" class="form-select">
                        <option value="sunrise">Восход</option>
                        <option value="sunset">Закат</option>
                    </select>
                </div>
                <div v-else-if="newAuto.trigger.type === 'manual'" class="trigger-detail">
                    <input v-model="newAuto.trigger.condition" placeholder="Фраза (например: я пришел домой)" class="form-input" />
                </div>
                <div v-else-if="newAuto.trigger.type === 'text_command'" class="trigger-detail">
                    <input v-model="newAuto.trigger.condition" placeholder="Текст или паттерн (например: включи свет)" class="form-input" />
                </div>
            </div>

            <!-- Actions Section -->
            <div class="section-card">
                <div class="section-label">Тогда</div>
                <div class="action-list">
                    <div v-for="(action, idx) in newAuto.actions" :key="idx" class="action-item">
                        <span class="action-num">{{ idx + 1 }}.</span>
                        <div class="action-detail">
                            <template v-if="action.type === 'service'">
                                <input v-model="deviceSearch" placeholder="Поиск..." class="form-input sm" />
                                <select v-model="action.entity_id" class="form-select sm">
                                    <option value="">Устройство</option>
                                    <option v-for="d in filteredDevices" :key="d.entity_id" :value="d.entity_id">{{ d.name }}</option>
                                </select>
                                <select v-model="action.service" class="form-select sm">
                                    <option value="light.turn_on">Включить</option>
                                    <option value="light.turn_off">Выключить</option>
                                    <option value="switch.turn_on">Включить розетку</option>
                                    <option value="switch.turn_off">Выключить розетку</option>
                                    <option value="cover.open_cover">Открыть</option>
                                    <option value="cover.close_cover">Закрыть</option>
                                </select>
                            </template>
                            <template v-else-if="action.type === 'notify' || action.type === 'speak' || action.type === 'reply'">
                                <input v-model="action.message" placeholder="Текст сообщения" class="form-input sm" />
                            </template>
                            <template v-else-if="action.type === 'delay'">
                                <input v-model.number="action.data.seconds" type="number" class="form-input sm" placeholder="Секунды" />
                                <span class="unit">сек</span>
                            </template>
                        </div>
                        <button class="remove-btn" @click="removeAction(idx)"><DeleteIcon /></button>
                    </div>
                </div>
                <div class="add-actions">
                    <button v-for="at in actionTypes" :key="at.type" class="add-action-btn" @click="addAction(at.type)">
                        + {{ at.name }}
                    </button>
                </div>
            </div>

            <div class="form-footer">
                <button class="cancel-btn" @click="showCreate = false; editingId = null">Отмена</button>
                <button class="save-btn" @click="editingId ? updateAutomation() : createAutomation()">
                    {{ editingId ? 'Сохранить' : 'Создать' }}
                </button>
            </div>
        </div>

        <!-- Automations List -->
        <div v-if="loading" class="loading"><LoadingIcon class="spin" /></div>
        <div v-else class="auto-list">
            <div v-for="auto in automations" :key="auto.id" class="auto-card" :class="{ disabled: !auto.enabled }">
                <div class="auto-top">
                    <div class="auto-name">{{ auto.name }}</div>
                    <div class="auto-btns">
                        <button class="icon-btn" @click="toggleAutomation(auto)" :title="auto.enabled ? 'Выкл' : 'Вкл'">
                            <PlayIcon :class="{ active: auto.enabled }" />
                        </button>
                        <button class="icon-btn" @click="startEdit(auto)" title="Редактировать"><EditIcon /></button>
                        <button class="icon-btn" @click="testAutomation(auto.id)" :disabled="sendingId === auto.id" title="Тест">
                            <LoadingIcon v-if="sendingId === auto.id" class="spin" />
                            <SendIcon v-else />
                        </button>
                        <button class="icon-btn del" @click="deleteAutomation(auto.id)" title="Удалить"><DeleteIcon /></button>
                    </div>
                </div>
                <div class="auto-body">
                    <div class="auto-trigger">
                        <span class="label">Если:</span> {{ auto.trigger.type === 'time' ? 'Время ' + auto.trigger.time : auto.trigger.type === 'state' ? getEntityName(auto.trigger.entity_id || '') + ' -> ' + (auto.trigger.condition || '?') : auto.trigger.type === 'sun' ? (auto.trigger.event === 'sunrise' ? 'Восход' : 'Закат') : auto.trigger.type === 'manual' ? '"' + (auto.trigger.condition || '?') + '"' : auto.trigger.type }}
                    </div>
                    <div class="auto-actions-list">
                        <span class="label">Тогда:</span>
                        <span v-for="(a, i) in auto.actions" :key="i" class="action-tag">
                            {{ a.type === 'service' ? a.service + ' ' + getEntityName(a.entity_id || '') : a.type === 'speak' ? 'Озвучить "' + (a.message || '') + '"' : a.type === 'reply' ? 'Ответить "' + (a.message || '') + '"' : a.type === 'notify' ? 'Уведомить' : a.type === 'delay' ? 'Задержка ' + (a.data?.seconds || 0) + 'с' : a.type }}
                        </span>
                    </div>
                </div>
                <div v-if="testResult && testResult.status" class="test-bar" :class="testResult.status">
                    {{ testResult.status === 'ok' ? 'Выполнено' : 'Ошибка' }}
                </div>
            </div>
        </div>

        <div v-if="!loading && automations.length === 0 && !showCreate" class="empty">
            <p>Нет сценариев. Нажмите "Создать" для добавления.</p>
        </div>
    </div>
</template>

<style scoped>
.auto-page h2 { font-size: 20px; font-weight: 600; margin-bottom: 4px; }
.subtitle { color: var(--text-secondary); font-size: 13px; }
.auto-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; }
.add-btn { display: flex; align-items: center; gap: 6px; padding: 8px 16px; border-radius: var(--radius-sm); background: var(--accent); color: white; border: none; font-size: 13px; cursor: pointer; }
.add-btn:hover { background: var(--accent-hover); }

.ha-bar { display: flex; align-items: center; gap: 8px; padding: 10px 14px; border-radius: var(--radius-sm); margin-bottom: 16px; font-size: 13px; }
.ha-bar.ok { background: rgba(76,175,80,0.1); color: #4caf50; }
.ha-bar.err { background: rgba(255,152,0,0.1); color: #ff9800; }

.create-form { background: var(--bg-card); border-radius: var(--radius); padding: 20px; margin-bottom: 20px; }
.form-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.form-header h3 { font-size: 16px; font-weight: 600; }
.close-btn { background: none; border: none; color: var(--text-secondary); cursor: pointer; padding: 4px; }

.form-input, .form-select { width: 100%; padding: 10px 12px; border: 1px solid var(--border); border-radius: var(--radius-sm); background: var(--bg-input); color: var(--text-primary); font-size: 14px; margin-bottom: 12px; }
.form-input:focus, .form-select:focus { outline: none; border-color: var(--accent); }
.form-input.sm, .form-select.sm { width: auto; flex: 1; margin-bottom: 0; }

.section-card { background: var(--bg-input); border-radius: var(--radius-sm); padding: 16px; margin-bottom: 12px; }
.section-label { font-size: 12px; font-weight: 600; color: var(--accent); text-transform: uppercase; margin-bottom: 12px; }

.trigger-options { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }
.option-btn { padding: 8px 14px; border-radius: var(--radius-sm); background: var(--bg-card); border: 1px solid var(--border); color: var(--text-secondary); font-size: 13px; cursor: pointer; }
.option-btn:hover { border-color: var(--accent); }
.option-btn.active { background: var(--accent); color: white; border-color: var(--accent); }

.trigger-detail { margin-top: 8px; }

.action-list { display: flex; flex-direction: column; gap: 8px; margin-bottom: 12px; }
.action-item { display: flex; align-items: center; gap: 8px; }
.action-num { font-size: 13px; color: var(--text-muted); min-width: 20px; }
.action-detail { flex: 1; display: flex; gap: 8px; align-items: center; }
.unit { font-size: 12px; color: var(--text-muted); }
.remove-btn { background: none; border: none; color: var(--text-muted); cursor: pointer; padding: 4px; }
.remove-btn:hover { color: var(--color-error); }

.add-actions { display: flex; flex-wrap: wrap; gap: 6px; }
.add-action-btn { padding: 6px 12px; border-radius: var(--radius-sm); background: var(--bg-card); border: 1px dashed var(--border); color: var(--text-secondary); font-size: 12px; cursor: pointer; }
.add-action-btn:hover { border-color: var(--accent); color: var(--accent); }

.form-footer { display: flex; gap: 8px; justify-content: flex-end; margin-top: 16px; }
.cancel-btn, .save-btn { padding: 10px 20px; border-radius: var(--radius-sm); font-size: 14px; cursor: pointer; }
.cancel-btn { background: var(--bg-input); border: 1px solid var(--border); color: var(--text-secondary); }
.save-btn { background: var(--accent); border: none; color: white; }

.loading { display: flex; justify-content: center; padding: 40px; }
.spin { animation: spin 1s linear infinite; }

.auto-list { display: flex; flex-direction: column; gap: 8px; }
.auto-card { background: var(--bg-card); border-radius: var(--radius-sm); overflow: hidden; transition: opacity 0.2s; }
.auto-card.disabled { opacity: 0.5; }

.auto-top { display: flex; justify-content: space-between; align-items: center; padding: 14px 16px 8px; }
.auto-name { font-size: 15px; font-weight: 600; }
.auto-btns { display: flex; gap: 4px; }

.icon-btn { display: flex; align-items: center; justify-content: center; width: 32px; height: 32px; border-radius: 50%; background: none; border: none; color: var(--text-secondary); cursor: pointer; }
.icon-btn:hover { background: var(--bg-hover); color: var(--text-primary); }
.icon-btn.del:hover { color: var(--color-error); }
.icon-btn .active { color: var(--color-success); }

.auto-body { padding: 0 16px 14px; font-size: 13px; }
.auto-trigger, .auto-actions-list { margin-bottom: 4px; }
.label { color: var(--accent); font-weight: 500; }
.action-tag { display: inline-block; padding: 2px 8px; background: var(--bg-input); border-radius: 8px; margin: 2px 4px 2px 0; font-size: 12px; color: var(--text-secondary); }

.test-bar { padding: 6px 16px; font-size: 12px; font-weight: 500; }
.test-bar.ok { background: rgba(76,175,80,0.1); color: #4caf50; }
.test-bar.error { background: rgba(244,67,54,0.1); color: #f44336; }

.empty { text-align: center; padding: 40px; color: var(--text-muted); }
</style>
