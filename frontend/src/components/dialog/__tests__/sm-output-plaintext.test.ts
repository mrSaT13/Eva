import { describe, it, expect, beforeEach } from 'vitest';
import { interpret } from 'xstate';
import { plaintextOutputMachine } from '../sm-output-plaintext';
import { EventBus } from '../../eventBus';

describe('plaintextOutputMachine', () => {
    let eventBus: EventBus;

    beforeEach(() => {
        eventBus = new EventBus();
    });

    it('should start in inactive state', () => {
        const machine = plaintextOutputMachine.withConfig({}, { eventBus });
        const service = interpret(machine).start();
        expect(service.state.value).toBe('inactive');
        service.stop();
    });

    it('should transition to active on WS_READY', () => {
        const machine = plaintextOutputMachine.withConfig({}, { eventBus });
        const service = interpret(machine).start();

        eventBus.send('WS_READY(out.text-plain)', null);
        expect(service.state.value).toBe('active');
        service.stop();
    });

    it('should add outgoing message to history', () => {
        const machine = plaintextOutputMachine.withConfig({}, { eventBus });
        const service = interpret(machine).start();

        const historyEvents: any[] = [];
        eventBus.addEventListener('HISTORY_ADD_MESSAGE', ((e: any) => {
            historyEvents.push(e.data);
        }) as EventListener);

        eventBus.send('WS_READY(out.text-plain)', null);
        eventBus.send('WS_RECEIVED(out.text-plain/text)', { text: 'Ответ ассистента' });

        expect(historyEvents.length).toBe(1);
        expect(historyEvents[0].direction).toBe('out');
        expect(historyEvents[0].text).toBe('Ответ ассистента');
        service.stop();
    });

    it('should set thinking to false on message received', () => {
        const machine = plaintextOutputMachine.withConfig({}, { eventBus });
        const service = interpret(machine).start();

        const thinkingEvents: any[] = [];
        eventBus.addEventListener('THINKING_SET', ((e: any) => {
            thinkingEvents.push(e.data);
        }) as EventListener);

        eventBus.send('WS_READY(out.text-plain)', null);
        eventBus.send('WS_RECEIVED(out.text-plain/text)', { text: 'test' });

        expect(thinkingEvents.length).toBe(1);
        expect(thinkingEvents[0]).toBe(false);
        service.stop();
    });

    it('should go inactive on WS_DISCONNECTED', () => {
        const machine = plaintextOutputMachine.withConfig({}, { eventBus });
        const service = interpret(machine).start();

        eventBus.send('WS_READY(out.text-plain)', null);
        expect(service.state.value).toBe('active');

        eventBus.send('WS_DISCONNECTED', null);
        expect(service.state.value).toBe('inactive');
        service.stop();
    });
});
