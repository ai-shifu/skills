import test from 'node:test';
import assert from 'node:assert/strict';
import { assertPublicationVersion, checkPublication, npmLatest } from '../check-publication.mjs';

test('first publication and releases newer than latest are allowed', () => {
  assert.doesNotThrow(() => assertPublicationVersion('2.2.1', null));
  for (const [version, latest] of [['2.2.1', '2.2.0'], ['2.10.0', '2.9.99'], ['3.0.0', '2.99.99']]) {
    assert.doesNotThrow(() => assertPublicationVersion(version, latest));
  }
});

test('older releases cannot replace npm latest', () => {
  for (const [version, latest] of [['2.2.0', '2.2.1'], ['2.9.99', '2.10.0'], ['2.99.99', '3.0.0']]) {
    assert.throws(() => assertPublicationVersion(version, latest), /older CLI/);
  }
  assert.doesNotThrow(() => assertPublicationVersion('2.2.1', '2.2.1'));
});

test('candidate and published latest must use canonical stable versions', () => {
  for (const value of ['2.2.1-rc.1', '02.2.1', '2.2', '', 'v2.2.1']) {
    assert.throws(() => assertPublicationVersion(value, null), /stable CLI/);
    assert.throws(() => assertPublicationVersion('2.2.1', value), /not a stable version/);
  }
});

test('only structured npm E404 is accepted as a first publication', () => {
  assert.equal(npmLatest({ status: 1, stdout: JSON.stringify({ error: { code: 'E404' } }) }), null);
  for (const code of ['E401', 'E403', 'ECONNRESET', 'ETIMEDOUT']) {
    assert.throws(() => npmLatest({ status: 1, stdout: JSON.stringify({ error: { code } }) }), new RegExp(code));
  }
  assert.throws(() => npmLatest({ status: 1, stdout: 'npm error E404' }), /did not return JSON/);
  assert.throws(() => npmLatest({ status: 0, stdout: '{}' }), /missing dist-tag/);
  assert.throws(() => npmLatest({ error: new Error('offline') }), /offline/);
});

test('the publication gate queries the public npm latest for this package', () => {
  const result = checkPublication((command, args, options) => {
    assert.ok(args.includes('@ai-shifu/cli'));
    assert.ok(args.includes('dist-tags.latest'));
    assert.ok(args.includes('--registry=https://registry.npmjs.org'));
    assert.equal(options.timeout, 30_000);
    return { status: 0, stdout: '"1.0.0"' };
  });
  assert.ok(result.version);
  assert.equal(result.latest, '1.0.0');
});
