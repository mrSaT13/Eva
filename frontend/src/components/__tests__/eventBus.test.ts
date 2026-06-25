import { describe, it, expect } from 'vitest';
import { EventBus, BusEvent, busConnector } from '../eventBus';

describe('EventBus', () => {
    it('should dispatch events with data', () => {
        const bus = new EventBus();
        let received: any = null;

        bus.addEventListener('TEST_EVENT', ((e: BusEvent) => {
            received = e.data;
        }) as EventListener);

        bus.send('TEST_EVENT', { value: 42 });

        expect(received).toEqual({ value: 42 });
    });

    it('should handle multiple listeners', () => {
        const bus = new EventBus();
        const calls: number[] = [];

        bus.addEventListener('EVT', (() => calls.push(1)) as EventListener);
        bus.addEventListener('EVT', (() => calls.push(2)) as EventListener);

        bus.send('EVT', null);

        expect(calls).toEqual([1, 2]);
    });

    it('should remove listener on cleanup', () => {
        const bus = new EventBus();
        let count = 0;

        const listener = (() => count++) as EventListener;
        bus.addEventListener('EVT', listener);
        bus.send('EVT', null);
        expect(count).toBe(1);

        bus.removeEventListener('EVT', listener);
        bus.send('EVT', null);
        expect(count).toBe(1);
    });
});

describe('busConnector', () => {
    it('should create an invoke callback that bridges eventBus to xstate', () => {
        const bus = new EventBus();
        const connector = busConnector(['TEST_EVENT']);
        const actor = (connector as any)({ eventBus: bus });

        const receivedEvents: any[] = [];
        const callback = (event: any) => receivedEvents.push(event);

        const cleanup = actor(callback, () => {});

        bus.send('TEST_EVENT', { text: 'hello' });

        expect(receivedEvents.length).toBe(1);
        expect(receivedEvents[0].type).toBe('TEST_EVENT');
        expect(receivedEvents[0].data).toEqual({ text: 'hello' });

        cleanup();
    });
});
