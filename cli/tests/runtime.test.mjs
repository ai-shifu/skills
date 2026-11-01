import test from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { findPython, prepareRuntime, pythonEnvironment, pythonInvocation, runtimePaths } from '../installer.mjs';

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
  assert.equal(prepareRuntime(f.root, f.env, f.execute), f.paths.python);
  assert.equal(prepareRuntime(f.root, f.env, f.execute), f.paths.python);
  assert.equal(f.installations, 1);
  assert.equal(f.creations, 1);
  assert.equal(readFileSync(f.paths.marker, 'utf8'), 'ready\n');
});

test('setup rebuilds a cached runtime whose installed dependencies no longer import', t => {
  const f = fixture(t);
  prepareRuntime(f.root, f.env, f.execute);
  f.breakDependencies();
  prepareRuntime(f.root, f.env, f.execute);
  assert.equal(f.installations, 2);
  assert.equal(f.creations, 2);
  assert.ok(existsSync(f.paths.marker));
});

test('setup repairs a stale executable even when the ready marker still exists', t => {
  const f = fixture(t);
  prepareRuntime(f.root, f.env, f.execute);
  f.breakInterpreter();
  prepareRuntime(f.root, f.env, f.execute);
  assert.equal(f.installations, 2);
  assert.equal(f.creations, 2);
});

test('Python detection, runtime preparation and commands discard inherited module overrides', t => {
  const f = fixture(t);
  const env = { ...f.env, PYTHONHOME: '/unrelated/python', PythonPath: '/unrelated/modules' };
  const calls = [];
  const execute = (command, args, options) => {
    calls.push(options.env);
    return f.execute(command, args, options);
  };
  findPython(env, execute);
  prepareRuntime(f.root, env, execute);
  prepareRuntime(f.root, env, execute);
  for (const calledEnv of calls) {
    assert.equal(Object.keys(calledEnv).some(key => ['PYTHONHOME', 'PYTHONPATH'].includes(key.toUpperCase())), false);
    assert.equal(calledEnv.AI_SHIFU_PYTHON, 'fixture-python');
  }
  const invocation = pythonInvocation(['site'], f.root, env);
  assert.equal(invocation.env.PYTHONHOME, undefined);
  assert.equal(invocation.env.PythonPath, undefined);
  assert.equal(invocation.env.AI_SHIFU_CLI_DISTRIBUTION, 'npm');
  assert.equal(invocation.env.AI_SHIFU_CLI_ENV_FILE, join(f.env.AI_SHIFU_CONFIG_DIR, 'cli.env'));
  assert.equal(env.PYTHONHOME, '/unrelated/python', 'the caller environment must remain unchanged');
  assert.equal(pythonEnvironment({ PATH: 'preserved', PYTHONPATH: 'ignored' }).PATH, 'preserved');
});

function runtimeChildSource() {
  return `
    import { existsSync, mkdirSync, writeFileSync, appendFileSync } from 'node:fs';
    import { dirname, join } from 'node:path';
    import { prepareRuntime, runtimePaths } from ${JSON.stringify(new URL('../installer.mjs', import.meta.url).href)};
    const root = process.env.FIXTURE_ROOT;
    const paths = runtimePaths(root, process.env);
    const imports = join(paths.directory, 'imports-work');
    const execute = (command, args) => {
      if (command === 'fixture-python' && args.includes('venv')) {
        appendFileSync(join(root, 'creations'), 'created\\n');
        Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 250);
        mkdirSync(dirname(paths.python), { recursive: true });
        writeFileSync(paths.python, 'fixture runtime');
      } else if (args.includes('pip')) {
        writeFileSync(imports, 'ready');
      } else if (command === paths.python) {
        return { status: existsSync(imports) ? 0 : 1 };
      }
      return { status: 0 };
    };
    console.log(prepareRuntime(root, { ...process.env, AI_SHIFU_PYTHON: 'fixture-python' }, execute));
  `;
}

test('parallel first commands share one initialized runtime', async t => {
  const f = fixture(t);
  const driver = join(f.root, 'runtime-child.mjs');
  writeFileSync(driver, runtimeChildSource());
  const [python, ...prefix] = findPython(process.env);
  const helper = fileURLToPath(new URL('../runtime-lock.py', import.meta.url));
  const children = [0, 1, 2].map(() => spawn(python, [...prefix, helper, `${f.paths.directory}.lock`, process.execPath, driver], {
    env: { ...f.env, FIXTURE_ROOT: f.root }, stdio: ['ignore', 'pipe', 'pipe'],
  }));
  const outcomes = await Promise.all(children.map(async child => {
    let stderr = '';
    child.stderr.on('data', data => { stderr += data; });
    const [code] = await once(child, 'exit');
    return { code, stderr };
  }));
  for (const outcome of outcomes) assert.equal(outcome.code, 0, outcome.stderr);
  assert.equal(readFileSync(join(f.root, 'creations'), 'utf8'), 'created\n');
  assert.ok(existsSync(f.paths.marker));
});

test('an exited initializer leaves the persistent lock file reusable by all waiters', async t => {
  const f = fixture(t);
  const driver = join(f.root, 'runtime-child.mjs');
  writeFileSync(driver, runtimeChildSource());
  const [python, ...prefix] = findPython(process.env);
  const helper = fileURLToPath(new URL('../runtime-lock.py', import.meta.url));
  const lock = `${f.paths.directory}.lock`;
  const acquired = join(f.root, 'lock-acquired');
  const sleeper = `require('node:fs').writeFileSync(${JSON.stringify(acquired)}, String(process.pid)); setTimeout(() => {}, 30_000);`;
  const holder = spawn(python, [...prefix, helper, lock, process.execPath, '-e', sleeper],
    { stdio: 'ignore' });
  let workerPid;
  t.after(() => {
    holder.kill('SIGKILL');
    if (workerPid) try { process.kill(workerPid, 'SIGKILL'); } catch (error) {
      if (error.code !== 'ESRCH') throw error;
    }
  });
  for (let attempt = 0; !existsSync(acquired) && attempt < 100; attempt++) {
    await new Promise(resolve => setTimeout(resolve, 25));
  }
  assert.ok(existsSync(acquired), 'the holder must acquire the native lock');
  workerPid = Number(readFileSync(acquired, 'utf8'));
  const exited = once(holder, 'exit');
  holder.kill('SIGKILL');
  await exited;
  process.kill(workerPid, 'SIGKILL');
  workerPid = undefined;
  assert.ok(existsSync(lock));
  const waiters = [0, 1, 2].map(() => spawn(python, [...prefix, helper, lock, process.execPath, driver], {
    env: { ...f.env, FIXTURE_ROOT: f.root }, stdio: ['ignore', 'pipe', 'pipe'],
  }));
  const outcomes = await Promise.all(waiters.map(async child => {
    let stderr = '';
    child.stderr.on('data', data => { stderr += data; });
    return { code: (await once(child, 'exit'))[0], stderr };
  }));
  for (const outcome of outcomes) assert.equal(outcome.code, 0, outcome.stderr);
  assert.equal(readFileSync(join(f.root, 'creations'), 'utf8'), 'created\n');
  assert.ok(existsSync(lock));
});
