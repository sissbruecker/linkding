
import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:9090';
const TOKEN = __ENV.LINKDING_TOKEN;

if (!TOKEN) {
    throw new Error('LINKDING_TOKEN não foi configurado.');
}

const headers = {
    headers: {
        Authorization: `Token ${TOKEN}`,
        'Content-Type': 'application/json',
    },
    timeout: '30s',
};

export const options = {
    scenarios: {
        validacao: {
            executor: 'constant-vus',
            vus: 1,
            duration: '10s',
            startTime: '0s',
            gracefulStop: '5s',
        },
        carga_baixa: {
            executor: 'constant-vus',
            vus: 5,
            duration: '1m',
            startTime: '15s',
            gracefulStop: '5s',
        },
        carga_moderada: {
            executor: 'constant-vus',
            vus: 10,
            duration: '1m',
            startTime: '1m20s',
            gracefulStop: '5s',
        },
        carga_alta: {
            executor: 'constant-vus',
            vus: 20,
            duration: '1m',
            startTime: '2m25s',
            gracefulStop: '5s',
        },
        stress: {
            executor: 'constant-vus',
            vus: 50,
            duration: __ENV.STRESS_DURATION || '1m',
            startTime: '3m30s',
            gracefulStop: '5s',
        },
        limite: {
            executor: 'constant-vus',
            vus: 100,
            duration: __ENV.LIMIT_DURATION || '1m',
            startTime: '4m35s',
            gracefulStop: '5s',
        },
    },

    thresholds: {
        http_req_duration: ['p(95)<1000'],
        http_req_failed: ['rate<0.01'],
        checks: ['rate>0.99'],
    },
};

export default function () {
    const response = http.get(
        `${BASE_URL}/api/bookmarks/?limit=20`,
        headers
    );

    check(response, {
        'Status HTTP 200': (r) => r.status === 200,
    });

    sleep(1);
}


