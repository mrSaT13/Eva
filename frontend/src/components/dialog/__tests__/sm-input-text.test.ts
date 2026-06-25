import { describe, it, expect, beforeEach } from 'vitest';
import { interpret } from 'xstate';
import { textInputMachine } from '../sm-input-text';
import { EventBus } from '../../eventBus';

describe('textInputMachine', () => {
    let eventBus: EventBus;

    beforeEach(() => {
        eventBus = new EventBus();
    });

    it('should start in inactive state', () => {
        const machine = textInputMachine.withConfig({}, { eventBus });
        const service = interpret(machine).start();
        expect(service.state.value).toBe('inactive');
        service.stop();
    });

    it('should transition to indirect_protocol on WS_READY', () => {
        const machine = textInputMachine.withConfig({}, { eventBus });
        const service = interpret(machine).start();

        eventBus.send('WS_READY(in.text-indirect)', null);
        expect(service.state.value).toBe('indirect_protocol');
        service.stop();
    });

    it('should transition to direct_protocol on WS_READY', () => {
        const machine = textInputMachine.withConfig({}, { eventBus });
        const service = interpret(machine).start();

        eventBus.send('WS_READY(in.text-direct)', null);
        expect(service.state.value).toBe('direct_protocol');
        service.stop();
    });

    it('should send WS_SEND on indirect message', () => {
        const machine = textInputMachine.withConfig({}, { eventBus });
        const service = interpret(machine).start();

        const sentEvents: any[] = [];
        eventBus.addEventListener('WS_SEND', ((e: any) => {
            sentEvents.push(e.data);
        }) as EventListener);

        eventBus.send('WS_READY(in.text-indirect)', null);
        eventBus.send('IN_TEXT_COMMAND', 'Тестовое сообщение');

        expect(sentEvents.length).toBeGreaterThanOrEqual(1);
        const textMsg = sentEvents.find(e => e.type === 'in.text-indirect/text');
        expect(textMsg).toBeDefined();
        expect(textMsg.text).toBe('Тестовое сообщение');
        service.stop();
    });

    it('should send HISTORY_ADD_MESSAGE on input', () => {
        const machine = textInputMachine.withConfig({}, { eventBus });
        const service = interpret(machine).start();

        const historyEvents: any[] = [];
        eventBus.addEventListener('HISTORY_ADD_MESSAGE', ((e: any) => {
            historyEvents.push(e.data);
        }) as EventListener);

        eventBus.send('WS_READY(in.text-indirect)', null);
        eventBus.send('IN_TEXT_COMMAND', 'Привет');

        expect(historyEvents.length).toBe(1);
        expect(historyEvents[0].direction).toBe('in');
        expect(historyEvents[0].text).toBe('Привет');
        service.stop();
    });

    it('should go inactive on WS_DISCONNECTED', () => {
        const machine = textInputMachine.withConfig({}, { eventBus });
        const service = interpret(machine).start();

        eventBus.send('WS_READY(in.text-indirect)', null);
        expect(service.state.value).toBe('indirect_protocol');

        eventBus.send('WS_DISCONNECTED', null);
        expect(service.state.value).toBe('inactive');
        service.stop();
    });
});
