import { assign, createMachine } from "xstate";
import { z } from "zod";
import { busConnector, EventBus } from "../eventBus";

export const Message = z.object({
    direction: z.enum(['in', 'out']),
    text: z.string().optional().default(''),
    image: z.string().optional(),
    imageUrl: z.string().optional(),
    timestamp: z.number().optional(),
    type: z.enum(['text', 'timer', 'image', 'system']).optional().default('text'),
    timerDuration: z.number().optional(),
    timerId: z.string().optional(),
});

export type Message = z.infer<typeof Message>;

export type Context = {
    eventBus: EventBus,
    messages: Message[],
    thinking: boolean,
};

export const messageHistoryMachine = createMachine<Context>(
    {
        id: 'messageHistory',
        predictableActionArguments: true,
        initial: 'active',
        invoke: {
            id: 'eventBus',
            src: 'eventBus',
        },
        states: {
            active: {
                on: {
                    HISTORY_ADD_MESSAGE: {
                        actions: ['storeMessage', 'scrollToBottom'],
                    },
                    THINKING_SET: {
                        actions: ['setThinking'],
                    },
                    IN_TEXT_COMMAND: {
                        actions: ['setThinkingOn', 'scrollToBottom'],
                    },
                },
            },
        },
    },
    {
        services: {
            eventBus: busConnector([
                'HISTORY_ADD_MESSAGE',
                'THINKING_SET',
                'IN_TEXT_COMMAND',
            ]),
        },
        actions: {
            storeMessage: assign({
                messages: ({ messages }, { data }) => {
                    const msg = Message.parse(data);
                    if (!msg.timestamp) msg.timestamp = Date.now();
                    return [...messages, msg];
                },
            }),
            setThinking: assign({
                thinking: (_, { data }) => !!data,
            }),
            setThinkingOn: assign({
                thinking: () => true,
            }),
            scrollToBottom: () => {
                setTimeout(() => {
                    const scrollContainer = document.querySelector('.main-content');
                    if (scrollContainer) {
                        scrollContainer.scrollTo({
                            top: scrollContainer.scrollHeight,
                            behavior: 'smooth'
                        });
                    }
                }, 100);
            },
        },
    }
);
