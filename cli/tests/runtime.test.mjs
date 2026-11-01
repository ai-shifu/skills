import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { ensureRuntime, runtimePaths } from '../installer.mjs';

function fixture(t) {
  const root = mkdtempSync(join(tmpdir(), 'shifu-runtime-'));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  const requirements = join(root, 'skills', 'ai-shifu-course-creator', 'scripts', 'requirements.txt');
  mkdirSync(dirname(requirements), { recursive: true });
  writeFileSync(requirements, 'requests\n');
  const env = { ...process.env, AI_SHIFU_CONFIG_DIR: join(root, 'configuration'), AI_SHIFU_PYTHON: 'fixture-python' };
  const paths = runtimePaths(root, env);
  let dependenciesWork = true;
  let interpreterWorks = true;
  let installations = 0;
  let creations = 0;
  const execute = (command, args) => {
    if (command === 'fixture-python' && args.includes('venv')) {
      creations++;
      mkdirSync(dirname(paths.python), { recursive: true });
      writeFileSync(paths.python, 'fixture runtime');
      interpreterWorks = true;
    } else if (args.includes('pip')) {
      installations++;
      dependenciesWork = true;
    } else if (command === paths.python) {
      return { status: dependenciesWork && interpreterWorks ? 0 : 1 };
    }
    return { status: 0 };
  };
  return { root, env, paths, execute,
    breakDependencies: () => { dependenciesWork = false; },
    breakInterpreter: () => { interpreterWorks = false; },
    get installations() { return installations; },
    get creations() { return creations; },
  };
}

test('healthy cached runtimes remain local without reinstalling requirements', t => {
  const f = fixture(t);
  assert.equal(ensureRuntime(f.root, f.env, f.execute), f.paths.python);
  assert.equal(ensureRuntime(f.root, f.env, f.execute), f.paths.python);
  assert.equal(f.installations, 1);
  assert.equal(f.creations, 1);
  assert.equal(readFileSync(f.paths.marker, 'utf8'), 'ready\n');
});

test('setup rebuilds a cached runtime whose installed dependencies no longer import', t => {
  const f = fixture(t);
  ensureRuntime(f.root, f.env, f.execute);
  f.breakDependencies();
  ensureRuntime(f.root, f.env, f.execute);
  assert.equal(f.installations, 2);
  assert.equal(f.creations, 2);
  assert.ok(existsSync(f.paths.marker));
});

test('setup repairs a stale executable even when the ready marker still exists', t => {
  const f = fixture(t);
  ensureRuntime(f.root, f.env, f.execute);
  f.breakInterpreter();
  ensureRuntime(f.root, f.env, f.execute);
  assert.equal(f.installations, 2);
  assert.equal(f.creations, 2);
});
