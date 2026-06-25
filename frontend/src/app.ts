import { createApp } from 'vue'
import { createRouter, createWebHashHistory } from 'vue-router';
import { interpret } from 'xstate';
import App from './App.vue'
import DialogPageVue from './components/dialog/DialogPage.vue';
import SettingsLayoutVue from './components/settings/SettingsLayout.vue';
import HeaderTitleVue from './components/ui/HeaderTitle.vue';
import AboutPageVue from './components/about/AboutPage.vue';
import TestingPageVue from './components/testing/TestingPage.vue';
import ThemePageVue from './components/settings/ThemeSettings.vue';
import ModelsPageVue from './components/models/ModelsPage.vue';
import { connectionStateMachine, type ProtocolRequirements } from './components/dialog/sm-connection';
import { textInputMachine } from './components/dialog/sm-input-text';
import { messageHistoryMachine } from './components/dialog/sm-message-history';
import { audioOutputMachine } from './components/dialog/sm-output-audio';
import { plaintextOutputMachine } from './components/dialog/sm-output-plaintext';
import { EventBus, eventBusKey } from './components/eventBus';
import { localRecognizerStateMachine } from './local-recognizer/sm';
import { inputStreamingStateMachine } from './audio-input-streaming/sm';

import z from 'zod';
import { fetchConfig, FRONTEND_CONFIG_SCOPE } from './components/config/service';
import { streamingSupported } from './audio-input-streaming/streamingService';
import { enableWakeLock } from './components/wakeLock';


const FrontendConfig = z.object({
    preferStreamingInput: z.boolean().default(true),
    audioInputEnabled: z.boolean().default(true),
    audioOutputEnabled: z.boolean().default(true),
    microphoneSampleRate: z.number(),
    hideConfiguration: z.boolean().default(false),
    requestWakeLock: z.boolean().default(true),
});

const DEFAULT_CONFIG: z.TypeOf<typeof FrontendConfig> = {
    preferStreamingInput: true,
    audioInputEnabled: true,
    audioOutputEnabled: true,
    microphoneSampleRate: 16000,
    hideConfiguration: false,
    requestWakeLock: true,
};

const loadConfig = async (): Promise<z.TypeOf<typeof FrontendConfig>> => {
    const tryLoad = async (retries = 3): Promise<z.TypeOf<typeof FrontendConfig>> => {
        try {
            const { config: rawConfig } = await fetchConfig(FRONTEND_CONFIG_SCOPE);
            return FrontendConfig.parse(rawConfig);
        } catch (error) {
            if (retries > 0) {
                console.warn(`Сервер недоступен, повтор через 3 сек... (осталось ${retries} попыток)`);
                await new Promise(r => setTimeout(r, 3000));
                return tryLoad(retries - 1);
            }
            console.warn('Сервер недоступен, используются настройки по умолчанию.');
            return DEFAULT_CONFIG;
        }
    }
    return tryLoad();
};

const getProtocolRequirements = ({
    audioInputEnabled,
    audioOutputEnabled,
    preferStreamingInput,
}: z.TypeOf<typeof FrontendConfig>): ProtocolRequirements => {
    const requirements: ProtocolRequirements = [];

    requirements.push(['in.text-direct', 'in.text-indirect']);

    if (audioOutputEnabled) {
        requirements.push(['out.audio.link']);
        requirements.push(['out.tts.serverside', 'out.text-plain']);
    } else {
        requirements.push(['out.text-plain'])
    }

    if (audioInputEnabled) {
        if (streamingSupported) {
            if (preferStreamingInput) {
                requirements.push(['in.stt.serverside', 'in.stt.clientside', 'in.text-indirect']);
            } else {
                requirements.push(['in.stt.clientside', 'in.text-indirect', 'in.stt.serverside']);
            }
        } else {
            requirements.push(['in.stt.clientside', 'in.text-indirect'])
        }
        requirements.push(['in.mute']);
    }

    return requirements;
}

export const initApplication = async () => {
    const config = await loadConfig();

    const { microphoneSampleRate, hideConfiguration, requestWakeLock } = config;

    if (requestWakeLock) {
      enableWakeLock();
    }

    const app = createApp(App);

    app.provide('frontendConfiguration', config);

    const eventBus = new EventBus();
    app.provide(eventBusKey, eventBus);

    app.provide(
        'connectionStateMachine',
        interpret(
            connectionStateMachine.withConfig(
                {},
                {
                    eventBus,
                    protocols: getProtocolRequirements(config),
                },
            )
        ).start()
    );

    app.provide(
        'textInputMachine',
        interpret(
            textInputMachine.withConfig(
                {},
                {
                    eventBus,
                },
            )
        ).start()
    );

    app.provide(
        'messageHistoryMachine',
        interpret(
            messageHistoryMachine.withConfig(
                {},
                {
                    eventBus,
                    messages: [],
                    thinking: false,
                },
            ),
        ).start()
    );

    app.provide(
        'plaintextOutputMachine',
        interpret(
            plaintextOutputMachine.withConfig(
                {},
                {
                    eventBus,
                },
            ),
        ).start()
    );

    app.provide(
        'audioOutputMachine',
        interpret(
            audioOutputMachine.withConfig(
                {},
                {
                    eventBus,
                },
            ),
        ).start()
    );

    app.provide(
        'localRecognizerMachine',
        interpret(
            localRecognizerStateMachine.withConfig(
                {},
                {
                    eventBus,
                    sampleRate: microphoneSampleRate,
                },
            ),
        ).start()
    );

    app.provide(
        'inputStreamerMachine',
        interpret(
            inputStreamingStateMachine.withConfig(
                {},
                {
                    eventBus,
                    sampleRate: microphoneSampleRate,
                },
            ),
        ).start()
    );

    const router = createRouter({
        history: createWebHashHistory(),
        routes: [
            // Главная: диалог (имя main) + страница настроек (имя settings)
            {
                path: '/',
                name: 'home',
                meta: { title: 'Eva', tab: 'chat' },
                components: {
                    main: DialogPageVue,
                    settings: SettingsLayoutVue,
                    heading: HeaderTitleVue,
                },
                props: {
                    heading: { text: 'Eva' },
                },
            },
            {
                path: '/testing',
                name: 'testing',
                meta: { title: 'Тестирование', tab: 'chat' },
                components: {
                    main: TestingPageVue,
                    heading: HeaderTitleVue,
                },
                props: {
                    heading: { text: 'Тестирование' },
                },
            },
            {
                path: '/models',
                name: 'models',
                meta: { title: 'Модели', tab: 'chat' },
                components: {
                    main: ModelsPageVue,
                    heading: HeaderTitleVue,
                },
                props: {
                    heading: { text: 'Модели' },
                },
            },
            {
                path: '/theme',
                name: 'theme',
                meta: { title: 'Тема оформления', tab: 'chat' },
                components: {
                    main: ThemePageVue,
                    heading: HeaderTitleVue,
                },
                props: {
                    heading: { text: 'Тема оформления' },
                },
            },
            {
                path: '/config',
                name: 'config',
                meta: { title: 'Настройки', tab: 'settings' },
                components: {
                    // На странице настроек "main" не рендерится — только настройки
                    settings: SettingsLayoutVue,
                    heading: HeaderTitleVue,
                },
                props: {
                    heading: { text: 'Настройки' },
                },
            },
            {
                path: '/about',
                name: 'about',
                meta: { title: 'О программе', tab: 'chat' },
                components: {
                    main: AboutPageVue,
                    heading: HeaderTitleVue,
                },
                props: {
                    heading: { text: 'О программе' },
                },
            },
            {
                path: '/:path(.*)*',
                redirect: '/',
            }
        ],
    });

    app.use(router);

    app.mount('#app')
}
