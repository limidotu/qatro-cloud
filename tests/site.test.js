import { test } from 'node:test';
import assert from 'node:assert/strict';
import { normalizeRepository, workflowUrl } from '../site/app.js';

test('only accepts an owner/repository, never a URL or credential', () => {
  assert.equal(normalizeRepository(' example/qatro-cloud '), 'example/qatro-cloud');
  for (const input of ['https://evil.test/a', 'owner/repo/../../other', 'owner/..', 'user@host/repo', 'owner/repo?token=x', '<script>/x']) assert.equal(normalizeRepository(input), null);
});
test('controls only open the selected GitHub workflow', () => {
  assert.equal(workflowUrl('example/qatro-cloud', 'start'), 'https://github.com/example/qatro-cloud/actions/workflows/start.yml');
  assert.equal(workflowUrl('example/qatro-cloud', 'delete'), null);
  assert.equal(workflowUrl('https://evil.test/a', 'start'), null);
});
