import { describe, it, expect, vi, beforeEach } from 'vitest';
import { interpret } from 'xstate';
import { messageHistoryMachine } from '../sm-message-history';
import { EventBus } from '../../eventBus';

describe('messageHistoryMachine', () => {
    let eventBus: EventBus;

    beforeEach(() => {
        eventBus = new EventBus();
    });

    it('should start with empty messages', () => {
        const machine = messageHistoryMachine.withConfig({}, {
            eventBus,
            messages: [],
            thinking: false,
        });

        const service = interpret(machine).start();
        expect(service.state.context.messages).toEqual([]);
        expect(service.state.context.thinking).toBe(false);
        service.stop();
    });

    it('should add message to history', () => {
        const machine = messageHistoryMachine.withConfig({}, {
            eventBus,
            messages: [],
            thinking: false,
        });

        const service = interpret(machine).start();

        eventBus.send('HISTORY_ADD_MESSAGE', {
            direction: 'in',
            text: 'Привет!',
        });

        expect(service.state.context.messages).toHaveLength(1);
        expect(service.state.context.messages[0].text).toBe('Привет!');
        expect(service.state.context.messages[0].direction).toBe('in');
        expect(service.state.context.messages[0].timestamp).toBeDefined();
        service.stop();
    });

    it('should add multiple messages', () => {
        const machine = messageHistoryMachine.withConfig({}, {
            eventBus,
            messages: [],
            thinking: false,
        });

        const service = interpret(machine).start();

        eventBus.send('HISTORY_ADD_MESSAGE', { direction: 'in', text: 'Первое' });
        eventBus.send('HISTORY_ADD_MESSAGE', { direction: 'out', text: 'Второе' });

        expect(service.state.context.messages).toHaveLength(2);
        expect(service.state.context.messages[0].text).toBe('Первое');
        expect(service.state.context.messages[1].text).toBe('Второе');
        service.stop();
    });

    it('should set thinking state', () => {
        const machine = messageHistoryMachine.withConfig({}, {
            eventBus,
            messages: [],
            thinking: false,
        });

        const service = interpret(machine).start();

        eventBus.send('THINKING_SET', true);
        expect(service.state.context.thinking).toBe(true);

        eventBus.send('THINKING_SET', false);
        expect(service.state.context.thinking).toBe(false);
        service.stop();
    });

    it('should set thinking on IN_TEXT_COMMAND', () => {
        const machine = messageHistoryMachine.withConfig({}, {
            eventBus,
            messages: [],
            thinking: false,
        });

        const service = interpret(machine).start();

        eventBus.send('IN_TEXT_COMMAND', 'test');
        expect(service.state.context.thinking).toBe(true);
        service.stop();
    });
});
