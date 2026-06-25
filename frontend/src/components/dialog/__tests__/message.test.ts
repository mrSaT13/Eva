import { describe, it, expect } from 'vitest';
import { Message } from '../sm-message-history';

describe('Message schema', () => {
    it('should parse a valid message', () => {
        const msg = Message.parse({
            direction: 'in',
            text: 'Hello',
            timestamp: 1234567890,
        });

        expect(msg.direction).toBe('in');
        expect(msg.text).toBe('Hello');
        expect(msg.timestamp).toBe(1234567890);
    });

    it('should use defaults for optional fields', () => {
        const msg = Message.parse({
            direction: 'out',
        });

        expect(msg.direction).toBe('out');
        expect(msg.text).toBe('');
        expect(msg.type).toBe('text');
        expect(msg.image).toBeUndefined();
        expect(msg.imageUrl).toBeUndefined();
        expect(msg.timestamp).toBeUndefined();
    });

    it('should reject invalid direction', () => {
        expect(() => Message.parse({ direction: 'up' })).toThrow();
    });

    it('should parse timer message', () => {
        const msg = Message.parse({
            direction: 'out',
            type: 'timer',
            text: 'Таймер',
            timerDuration: 60,
            timerId: 'timer-1',
        });

        expect(msg.type).toBe('timer');
        expect(msg.timerDuration).toBe(60);
        expect(msg.timerId).toBe('timer-1');
    });

    it('should parse system message', () => {
        const msg = Message.parse({
            direction: 'in',
            type: 'system',
            text: 'Подключение установлено',
        });

        expect(msg.type).toBe('system');
    });
});
