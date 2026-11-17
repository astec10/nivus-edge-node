import assert from 'node:assert/strict';
import test from 'node:test';

import { prepareSessionRequest } from '../src/utils/sessionTransportCore.js';
import { meetsPasswordPolicy } from '../src/utils/passwordPolicy.js';

test('cookie session requests remove legacy bearer headers', () => {
  const config = prepareSessionRequest({
    headers: { Authorization: 'Bearer browser-token', 'Content-Type': 'application/json' },
  });
  assert.equal(config.withCredentials, true);
  assert.equal(config.headers.Authorization, undefined);
  assert.equal(config.headers['Content-Type'], 'application/json');
});

test('cookie session requests clear AxiosHeaders authorization', () => {
  const deleted = [];
  const headers = { delete: name => deleted.push(name) };
  prepareSessionRequest({ headers });
  assert.deepEqual(deleted, ['Authorization']);
});

test('password policy matches the UI requirements', () => {
  assert.equal(meetsPasswordPolicy('Nivus123'), true);
  assert.equal(meetsPasswordPolicy('12345678'), false);
  assert.equal(meetsPasswordPolicy('Nivusabc'), false);
  assert.equal(meetsPasswordPolicy('N1short'), false);
  assert.equal(meetsPasswordPolicy('A'.repeat(257) + '1'), false);
});
