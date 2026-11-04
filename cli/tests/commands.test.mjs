import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { copyFileSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';
import { packageRoot } from '../installer.mjs';

function fixture(t) {
  const directory = mkdtempSync(join(tmpdir(), 'shifu-command-'));
  t.after(() => rmSync(directory, { recursive: true, force: true }));
  const log = join(directory, 'operations.jsonl');
  const actualInstaller = pathToFileURL(join(packageRoot, 'cli', 'installer.mjs')).href;

  function addPackage(version) {
    const root = join(directory, `package-${version}`);
    mkdirSync(join(root, 'cli'), { recursive: true });
    mkdirSync(join(root, 'skills', 'ai-shifu-course-creator'), { recursive: true });
    writeFileSync(join(root, 'package.json'), JSON.stringify({ name: '@ai-shifu/cli', version }));
    writeFileSync(join(root, 'skills', 'ai-shifu-course-creator', 'SKILL.md'), `Skill from ${version}\n`);
    copyFileSync(join(packageRoot, 'cli', 'shifu.mjs'), join(root, 'cli', 'shifu.mjs'));
    // Exercise the real command dispatcher. Only npm and setup side effects are
    // replaced; agent validation comes from the production installer.
    writeFileSync(join(root, 'cli', 'installer.mjs'), `
      export * from ${JSON.stringify(actualInstaller)};
      import { appendFileSync, readFileSync } from 'node:fs';
      import { spawnSync } from 'node:child_process';
      import { fileURLToPath } from 'node:url';
      const root = fileURLToPath(new URL('../', import.meta.url));
      export const packageInfo = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));
      function record(operation) {
        appendFileSync(process.env.AI_SHIFU_COMMAND_LOG, JSON.stringify({ package: packageInfo.version, ...operation }) + '\\n');
      }
      export function runNpm(args) {
        record({ kind: 'npm', args });
        if (process.env.AI_SHIFU_TEST_NPM_FAIL === '1') throw new Error('simulated npm failure');
        if (args[0] === 'exec') {
          const command = args.slice(args.indexOf('--') + 1);
          if (command.shift() !== 'shifu') throw new Error('expected shifu executable');
          const result = spawnSync(process.execPath, [process.env.AI_SHIFU_TEST_LATEST_ROOT + '/cli/shifu.mjs', ...command], {
            env: process.env, encoding: 'utf8',
          });
          if (result.status !== 0) throw new Error(result.stderr || 'latest command failed');
        }
      }
      export function setup(agents) {
        const skill = readFileSync(new URL('../skills/ai-shifu-course-creator/SKILL.md', import.meta.url), 'utf8');
        record({ kind: 'setup', agents, source: root, skill });
      }
    `);
    return root;
  }

  function invoke(root, args, extraEnv = {}) {
    const result = spawnSync(process.execPath, [join(root, 'cli', 'shifu.mjs'), ...args], {
      env: { ...process.env, AI_SHIFU_COMMAND_LOG: log, ...extraEnv }, encoding: 'utf8',
    });
    let operations = [];
    try {
      operations = readFileSync(log, 'utf8').trim().split('\n').filter(Boolean).map(line => JSON.parse(line));
    } catch (error) {
      if (error.code !== 'ENOENT') throw error;
    }
    return { result, operations };
  }
  return { addPackage, invoke };
}

test('install pins the invoking package version before setting up its bundled Skills', t => {
  const { addPackage, invoke } = fixture(t);
  const root = addPackage('2.3.0');
  const { result, operations } = invoke(root, ['install', '--agent', 'codex', 'claude-code']);
  assert.equal(result.status, 0, result.stderr);
  assert.deepEqual(operations.map(operation => operation.kind), ['npm', 'setup']);
  assert.deepEqual(operations[0].args, ['install', '--global', '--ignore-scripts', '@ai-shifu/cli@2.3.0']);
  assert.equal(operations[1].package, '2.3.0');
  assert.equal(operations[1].skill, 'Skill from 2.3.0\n');
  assert.deepEqual(operations[1].agents, ['--agent', 'codex', 'claude-code']);
});

test('update delegates install and setup to the latest package with the selected agents', t => {
  const { addPackage, invoke } = fixture(t);
  const previous = addPackage('2.2.1');
  const latest = addPackage('2.3.0');
  const { result, operations } = invoke(previous, ['update', '--agent', 'claude-code'], {
    AI_SHIFU_TEST_LATEST_ROOT: latest,
  });
  assert.equal(result.status, 0, result.stderr);
  assert.deepEqual(operations[0].args, ['exec', '--yes', '--package', '@ai-shifu/cli@latest', '--', 'shifu', 'install', '--agent', 'claude-code']);
  assert.deepEqual(operations[1].args, ['install', '--global', '--ignore-scripts', '@ai-shifu/cli@2.3.0']);
  const setup = operations.filter(operation => operation.kind === 'setup');
  assert.equal(setup.length, 1, 'the old package must not set up its own Skills');
  assert.equal(setup[0].package, '2.3.0');
  assert.equal(setup[0].skill, 'Skill from 2.3.0\n');
  assert.deepEqual(setup[0].agents, ['--agent', 'claude-code']);
});

for (const command of ['install', 'update']) {
  test(`${command} rejects invalid agent arguments before invoking npm`, t => {
    const { addPackage, invoke } = fixture(t);
    const { result, operations } = invoke(addPackage('2.3.0'), [command, '--agent', 'codex', '--all']);
    assert.equal(result.status, 1);
    assert.match(result.stderr, /Use --agent/);
    assert.deepEqual(operations, []);
  });
}

test('a failed npm install does not set up Skills or report success', t => {
  const { addPackage, invoke } = fixture(t);
  const { result, operations } = invoke(addPackage('2.3.0'), ['install'], { AI_SHIFU_TEST_NPM_FAIL: '1' });
  assert.equal(result.status, 1);
  assert.match(result.stderr, /simulated npm failure/);
  assert.deepEqual(operations.map(operation => operation.kind), ['npm']);
});
