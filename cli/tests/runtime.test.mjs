import test from 'node:test';
import assert from 'node:assert/strict';
import { spawn, spawnSync } from 'node:child_process';
import { once } from 'node:events';
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { ensureRuntime, findPython, pythonEnvironment, pythonInvocation, runtimePaths } from '../installer.mjs';

const helper = fileURLToPath(new URL('../runtime-lock.py', import.meta.url));

function fixture(t) {
  const root = mkdtempSync(join(tmpdir(), 'shifu-runtime-'));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  const requirements = join(root, 'skills', 'ai-shifu-course-creator', 'scripts', 'requirements.txt');
  mkdirSync(dirname(requirements), { recursive: true });
  writeFileSync(requirements, 'requests\n');
  const env = pythonEnvironment({ ...process.env, AI_SHIFU_CONFIG_DIR: join(root, 'configuration') });
  const paths = runtimePaths(root, env);
  return { root, env, paths };
}

function pythonCommand() {
  return findPython(pythonEnvironment(process.env));
}

function workerSource() {
  return `
import importlib.util, json, os, subprocess, sys, time
from pathlib import Path
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('runtime_lock', ${JSON.stringify(helper)})
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
root = Path(os.environ['FIXTURE_ROOT'])
paths = json.loads(os.environ['FIXTURE_PATHS'])
directory = Path(paths['directory'])
imports = directory / 'imports-work'
def fake_run(command, **options):
    if command[1:3] == ['-m', 'venv']:
        with (root / 'creations').open('a', newline='\\n') as count:
            count.write('created\\n')
        if os.environ.get('PREPARATION_GATE'):
            (root / 'worker-pid').write_text(str(os.getpid()))
            while not Path(os.environ['PREPARATION_GATE']).exists():
                time.sleep(0.025)
        if os.environ.get('MUTATOR_GATE'):
            (root / 'worker-pid').write_text(str(os.getpid()))
            mutator = "import os,time; from pathlib import Path; Path(os.environ['MUTATOR_PID']).write_text(str(os.getpid())); exec(\\\"while not Path(os.environ['MUTATOR_GATE']).exists(): time.sleep(0.025)\\\")"
            subprocess.run([sys.executable, '-c', mutator], stdin=options['stdin'], check=True)
        time.sleep(0.15)
        Path(paths['python']).parent.mkdir(parents=True, exist_ok=True)
        Path(paths['python']).write_text('fixture runtime')
        (root / 'broken-interpreter').unlink(missing_ok=True)
    elif 'pip' in command:
        imports.write_text('ready')
    elif command[0] == paths['python']:
        code = 0 if imports.exists() and not (root / 'broken-interpreter').exists() else 1
        if options.get('check') and code:
            raise subprocess.CalledProcessError(code, command)
        return subprocess.CompletedProcess(command, code)
    return subprocess.CompletedProcess(command, 0)
def prepare():
    return module.prepare_runtime(paths['directory'], paths['requirements'], paths['python'], sys.stdin.buffer, run=fake_run)
`;
}

function runCase(f, statements) {
  const [python, ...prefix] = pythonCommand();
  const result = spawnSync(python, [...prefix, '-c', workerSource() + statements], {
    env: { ...f.env, FIXTURE_ROOT: f.root, FIXTURE_PATHS: JSON.stringify(f.paths) }, encoding: 'utf8',
  });
  assert.equal(result.status, 0, result.stderr);
  return JSON.parse(result.stdout);
}

test('healthy cached runtimes remain local without reinstalling requirements', t => {
  const f = fixture(t);
  assert.equal(runCase(f, `
prepare()
prepare()
print(json.dumps((root / 'creations').read_text()))
`), 'created\n');
  assert.equal(readFileSync(f.paths.marker, 'utf8'), 'ready\n');
});

test('setup rebuilds a cached runtime whose installed dependencies no longer import', t => {
  const f = fixture(t);
  assert.equal(runCase(f, `
prepare()
imports.unlink()
prepare()
print(json.dumps((root / 'creations').read_text()))
`), 'created\ncreated\n');
  assert.ok(existsSync(f.paths.marker));
});

test('setup repairs a stale executable even when the ready marker still exists', t => {
  const f = fixture(t);
  assert.equal(runCase(f, `
prepare()
(root / 'broken-interpreter').write_text('broken')
prepare()
print(json.dumps((root / 'creations').read_text()))
`), 'created\ncreated\n');
});

test('a validation timeout preserves the cached interpreter and dependencies for retry', t => {
  const f = fixture(t);
  const outcome = runCase(f, `
prepare()
def slow_run(command, **options):
    raise subprocess.TimeoutExpired(command, 10)
try:
    module.prepare_runtime(paths['directory'], paths['requirements'], paths['python'], sys.stdin.buffer, run=slow_run)
except RuntimeError as error:
    message = str(error)
else:
    raise AssertionError('validation timeout must not start a rebuild')
print(json.dumps({'message': message, 'creations': (root / 'creations').read_text(),
    'marker': Path(paths['marker']).read_text(), 'dependencies': imports.read_text()}))
`);
  assert.match(outcome.message, /timed out.*left unchanged.*retry/);
  assert.equal(outcome.creations, 'created\n');
  assert.equal(outcome.marker, 'ready\n');
  assert.equal(outcome.dependencies, 'ready');
});

test('a healthy cached interpreter can launch setup with no system Python on PATH', t => {
  const f = fixture(t);
  const [python, ...prefix] = pythonCommand();
  const created = spawnSync(python, [...prefix, '-m', 'venv', '--without-pip', f.paths.directory], {
    env: f.env, encoding: 'utf8',
  });
  assert.equal(created.status, 0, created.stderr);
  const inspected = spawnSync(f.paths.python, ['-c', "import sysconfig; print(sysconfig.get_paths()['purelib'])"], {
    env: f.env, encoding: 'utf8',
  });
  assert.equal(inspected.status, 0, inspected.stderr);
  const modules = inspected.stdout.trim();
  mkdirSync(modules, { recursive: true });
  for (const name of ['requests', 'dotenv', 'PIL', 'pillow_heif']) writeFileSync(join(modules, `${name}.py`), '');
  writeFileSync(f.paths.marker, 'ready\n');
  const env = { ...f.env };
  for (const key of Object.keys(env)) if (key.toUpperCase() === 'PATH' || key === 'AI_SHIFU_PYTHON') delete env[key];
  env.PATH = '';
  assert.equal(ensureRuntime(f.root, env), f.paths.python);
  assert.equal(readFileSync(f.paths.marker, 'utf8'), 'ready\n');
  assert.equal(existsSync(join(f.root, 'creations')), false);
});

test('a cached launcher that fails its locked recheck is preserved for external repair', t => {
  const f = fixture(t);
  const outcome = runCase(f, `
prepare()
imports.unlink()
sys.prefix = str(directory)
try:
    prepare()
except RuntimeError as error:
    message = str(error)
else:
    raise AssertionError('a running cached interpreter must not remove itself')
print(json.dumps({'message': message, 'creations': (root / 'creations').read_text(),
    'marker': Path(paths['marker']).read_text(), 'python': Path(paths['python']).read_text()}))
`);
  assert.match(outcome.message, /left unchanged.*AI_SHIFU_PYTHON.*external/);
  assert.equal(outcome.creations, 'created\n');
  assert.equal(outcome.marker, 'ready\n');
  assert.equal(outcome.python, 'fixture runtime');
});

test('Python detection and commands discard inherited module overrides', t => {
  const f = fixture(t);
  const env = { ...f.env, PYTHONHOME: '/unrelated/python', PythonPath: '/unrelated/modules', AI_SHIFU_PYTHON: 'fixture-python' };
  const calls = [];
  findPython(env, (command, args, options) => { calls.push(options.env); return { status: 0 }; });
  for (const calledEnv of calls) {
    assert.equal(Object.keys(calledEnv).some(key => ['PYTHONHOME', 'PYTHONPATH'].includes(key.toUpperCase())), false);
    assert.equal(calledEnv.AI_SHIFU_PYTHON, 'fixture-python');
  }
  const invocation = pythonInvocation(['site'], f.root, env);
  assert.equal(invocation.env.PYTHONHOME, undefined);
  assert.equal(invocation.env.PythonPath, undefined);
  assert.equal(invocation.env.AI_SHIFU_CLI_DISTRIBUTION, 'npm');
  assert.equal(invocation.env.AI_SHIFU_CLI_ENV_FILE, join(f.env.AI_SHIFU_CONFIG_DIR, 'cli.env'));
  assert.equal(env.PYTHONHOME, '/unrelated/python');
});

function launch(f, driver, extra = {}) {
  const [python, ...prefix] = pythonCommand();
  return spawn(python, [...prefix, helper, `${f.paths.directory}.lock`, python, ...prefix, driver], {
    env: { ...f.env, FIXTURE_ROOT: f.root, FIXTURE_PATHS: JSON.stringify(f.paths), ...extra },
    stdio: ['ignore', 'ignore', 'pipe'],
  });
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

async function waitForPid(filename) {
  for (let attempt = 0; attempt < 200; attempt++) {
    if (existsSync(filename)) {
      const pid = Number(readFileSync(filename, 'utf8'));
      if (Number.isSafeInteger(pid) && pid > 0) return pid;
    }
    await new Promise(resolve => setTimeout(resolve, 25));
  }
  assert.fail(`expected worker signal: ${filename}`);
}

test('parallel first commands share one initialized runtime', async t => {
  const f = fixture(t);
  const driver = join(f.root, 'runtime-child.py');
  writeFileSync(driver, workerSource() + '\nprepare()\n');
  const children = [0, 1, 2].map(() => launch(f, driver));
  for (const outcome of await Promise.all(children.map(watchChild))) assert.equal(outcome.code, 0, outcome.stderr);
  assert.equal(readFileSync(join(f.root, 'creations'), 'utf8'), 'created\n');
  assert.ok(existsSync(f.paths.marker));
});

for (const mutatorSurvives of [false, true]) test(
  mutatorSurvives ? 'an orphaned mutator retains exclusivity after its helper and worker are killed' :
    'an orphaned worker retains exclusivity after its lock helper is killed', async t => {
  const f = fixture(t);
  const driver = join(f.root, 'runtime-child.py');
  writeFileSync(driver, workerSource() + '\nprepare()\n');
  const [python, ...prefix] = pythonCommand();
  const lock = `${f.paths.directory}.lock`;
  const gate = join(f.root, 'continue-preparation');
  const mutatorPidFile = join(f.root, 'mutator-pid');
  const holder = launch(f, driver, mutatorSurvives ?
    { MUTATOR_GATE: gate, MUTATOR_PID: mutatorPidFile } : { PREPARATION_GATE: gate });
  const holderOutcome = watchChild(holder);
  const waiters = [];
  let workerPid;
  let mutatorPid;
  try {
    workerPid = await waitForPid(join(f.root, 'worker-pid'));
    if (mutatorSurvives) mutatorPid = await waitForPid(mutatorPidFile);
    holder.kill('SIGKILL');
    await holderOutcome;
    if (mutatorSurvives) kill(workerPid);
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
      const child = launch(f, driver);
      waiters.push(child);
      outcomes.push(watchChild(child));
    }
    await new Promise(resolve => setTimeout(resolve, 300));
    assert.equal(readFileSync(join(f.root, 'creations'), 'utf8'), 'created\n');
    assert.equal(existsSync(f.paths.marker), false);
    writeFileSync(gate, 'continue');
    for (const outcome of await Promise.all(outcomes)) assert.equal(outcome.code, 0, outcome.stderr);
    assert.equal(readFileSync(join(f.root, 'creations'), 'utf8'), mutatorSurvives ? 'created\ncreated\n' : 'created\n');
    assert.ok(existsSync(f.paths.marker));
  } finally {
    kill(holder.pid);
    for (const waiter of waiters) kill(waiter.pid);
    kill(workerPid);
    kill(mutatorPid);
  }
});
