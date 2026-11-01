import test from 'node:test';
import assert from 'node:assert/strict';
import { spawn, spawnSync } from 'node:child_process';
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
    import { spawnSync } from 'node:child_process';
    import { existsSync, mkdirSync, writeFileSync, appendFileSync } from 'node:fs';
    import { dirname, join } from 'node:path';
    import { prepareRuntime, runtimePaths } from ${JSON.stringify(new URL('../installer.mjs', import.meta.url).href)};
    const root = process.env.FIXTURE_ROOT;
    const paths = runtimePaths(root, process.env);
    const imports = join(paths.directory, 'imports-work');
    const execute = (command, args) => {
      if (command === 'fixture-python' && args.includes('venv')) {
        appendFileSync(join(root, 'creations'), 'created\\n');
        if (process.env.PREPARATION_GATE) {
          writeFileSync(join(root, 'worker-pid'), String(process.pid));
          while (!existsSync(process.env.PREPARATION_GATE)) {
            Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 25);
          }
        }
        if (process.env.MUTATOR_GATE) {
          writeFileSync(join(root, 'worker-pid'), String(process.pid));
          const mutator = "const fs=require('node:fs'); fs.writeFileSync(process.env.MUTATOR_PID, String(process.pid)); while(!fs.existsSync(process.env.MUTATOR_GATE)) Atomics.wait(new Int32Array(new SharedArrayBuffer(4)),0,0,25);";
          spawnSync(process.execPath, ['-e', mutator], { stdio: 'inherit' });
        }
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

async function waitForFile(filename) {
  for (let attempt = 0; !existsSync(filename) && attempt < 200; attempt++) {
    await new Promise(resolve => setTimeout(resolve, 25));
  }
  assert.ok(existsSync(filename), `expected worker signal: ${filename}`);
}

function watchChild(child) {
  let stderr = '';
  child.stderr?.on('data', data => { stderr += data; });
  return once(child, 'exit').then(([code]) => ({ code, stderr }));
}

function kill(pid) {
  if (!pid) return;
  try { process.kill(pid, 'SIGKILL'); } catch (error) {
    if (error.code !== 'ESRCH') throw error;
  }
}

for (const mutatorSurvives of [false, true]) test(
  mutatorSurvives ? 'an orphaned mutator retains exclusivity after its helper and worker are killed' :
    'an orphaned worker retains exclusivity after its lock helper is killed', async t => {
  const f = fixture(t);
  const driver = join(f.root, 'runtime-child.mjs');
  writeFileSync(driver, runtimeChildSource());
  const [python, ...prefix] = findPython(process.env);
  const helper = fileURLToPath(new URL('../runtime-lock.py', import.meta.url));
  const lock = `${f.paths.directory}.lock`;
  const gate = join(f.root, 'continue-preparation');
  const mutatorPidFile = join(f.root, 'mutator-pid');
  const holder = spawn(python, [...prefix, helper, lock, process.execPath, driver], {
    env: { ...f.env, FIXTURE_ROOT: f.root, ...(mutatorSurvives ?
      { MUTATOR_GATE: gate, MUTATOR_PID: mutatorPidFile } : { PREPARATION_GATE: gate }) },
    stdio: ['ignore', 'ignore', 'pipe'],
  });
  const holderOutcome = watchChild(holder);
  const waiters = [];
  let workerPid;
  let mutatorPid;
  try {
    await waitForFile(join(f.root, 'worker-pid'));
    workerPid = Number(readFileSync(join(f.root, 'worker-pid'), 'utf8'));
    if (mutatorSurvives) {
      await waitForFile(mutatorPidFile);
      mutatorPid = Number(readFileSync(mutatorPidFile, 'utf8'));
    }
    holder.kill('SIGKILL');
    await holderOutcome;
    if (mutatorSurvives) kill(workerPid);
    assert.ok(existsSync(lock));
    const probe = spawnSync(python, [...prefix, '-c', `
import errno, os, sys
try:
    with open(sys.argv[1], 'a+b') as lock:
        if os.name == 'nt':
            import msvcrt
            lock.write(b'\\0')
            lock.flush()
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
except OSError as error:
    if error.errno in (errno.EACCES, errno.EAGAIN) or getattr(error, 'winerror', None) == 32:
        sys.exit(75)
    raise
`, lock], { encoding: 'utf8' });
    assert.equal(probe.status, 75, `a competing process must still observe a held lock: ${probe.stderr}`);
    const outcomes = [];
    for (const i of [0, 1, 2]) {
      const child = spawn(python, [...prefix, helper, lock, process.execPath, driver], {
        env: { ...f.env, FIXTURE_ROOT: f.root }, stdio: ['ignore', 'pipe', 'pipe'],
      });
      waiters.push(child);
      outcomes.push(watchChild(child));
    }
    await new Promise(resolve => setTimeout(resolve, 400));
    assert.equal(readFileSync(join(f.root, 'creations'), 'utf8'), 'created\n',
      'waiters must not rebuild while the original mutation process remains alive');
    assert.equal(existsSync(f.paths.marker), false);
    writeFileSync(gate, 'continue');
    for (const outcome of await Promise.all(outcomes)) assert.equal(outcome.code, 0, outcome.stderr);
    assert.equal(readFileSync(join(f.root, 'creations'), 'utf8'), mutatorSurvives ? 'created\ncreated\n' : 'created\n');
    assert.ok(existsSync(f.paths.marker));
    assert.ok(existsSync(lock));
  } finally {
    kill(holder.pid);
    for (const waiter of waiters) kill(waiter.pid);
    kill(workerPid);
    kill(mutatorPid);
  }
});
