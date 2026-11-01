import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { configDir, pythonInvocation, runtimePaths } from '../installer.mjs';

function fixture(t) {
  const home = mkdtempSync(join(tmpdir(), 'shifu-config-root-'));
  t.after(() => rmSync(home, { recursive: true, force: true }));
  const base = join(home, '.config', 'ai-shifu');
  const env = { HOME: home, USERPROFILE: home, XDG_CONFIG_HOME: join(home, '.config') };
  const selected = join(home, 'original-profile-root');
  mkdirSync(base, { recursive: true });
  function pointer(value) {
    writeFileSync(join(base, 'cli-config-root.json'), typeof value === 'string' ? value : JSON.stringify(value));
  }
  return { home, base, env, selected, pointer };
}

test('Node and forwarded Python commands keep the recorded original profile root', t => {
  const f = fixture(t);
  f.pointer({ schema_version: 1, config_dir: f.selected });
  assert.equal(configDir(f.env, f.home), f.selected);
  const invocation = pythonInvocation(['profile', 'list'], undefined, f.env);
  assert.equal(invocation.env.AI_SHIFU_CONFIG_DIR, f.selected);
  assert.equal(invocation.env.AI_SHIFU_CLI_ENV_FILE, join(f.selected, 'cli.env'));
  assert.ok(runtimePaths(undefined, f.env, f.home).directory.startsWith(f.selected));
});

test('an explicit process configuration root wins without reading a pointer', t => {
  const f = fixture(t);
  f.pointer('invalid json');
  assert.equal(configDir({ ...f.env, AI_SHIFU_CONFIG_DIR: f.selected }, f.home), f.selected);
});

test('malformed, relative and unrecognized root pointers fail closed', t => {
  const f = fixture(t);
  for (const document of ['[]', 'not json', { schema_version: true, config_dir: f.selected },
    { schema_version: 1, config_dir: 'relative' }, { schema_version: 1, config_dir: f.selected, extra: true }]) {
    f.pointer(document);
    assert.throws(() => configDir(f.env, f.home), /configuration root pointer/);
  }
});
