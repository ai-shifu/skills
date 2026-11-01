import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync,
  statSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { agentArgs, configDir, defaultAgentArgs, findPython, packageInfo, packageRoot, preserveLegacyEnv,
  pythonInvocation, runtimePaths, skillInstallArgs, skillsCommand } from '../installer.mjs';

function temporary(t) {
  const dir = mkdtempSync(join(tmpdir(), 'ai-shifu-cli-'));
  t.after(() => rmSync(dir, { recursive: true, force: true }));
  return dir;
}

function isolatedEnv(home) {
  return { ...process.env, HOME: home, USERPROFILE: home, CODEX_HOME: join(home, '.codex'),
    CLAUDE_CONFIG_DIR: join(home, '.claude'), XDG_CONFIG_HOME: join(home, '.config'),
    AI_SHIFU_CONFIG_DIR: join(home, '.config', 'ai-shifu'),
    APPDATA: join(home, 'AppData', 'Roaming'), LOCALAPPDATA: join(home, 'AppData', 'Local') };
}

test('versions and bundled Skills are discoverable without a Python runtime', t => {
  const env = { ...isolatedEnv(temporary(t)), AI_SHIFU_PYTHON: 'missing-python-executable' };
  for (const args of [['--version'], ['skills', 'list']]) {
    const result = spawnSync(process.execPath, [join(packageRoot, 'cli', 'shifu.mjs'), ...args],
      { env, encoding: 'utf8' });
    assert.equal(result.status, 0, result.stderr);
    if (args[0] === '--version') assert.equal(result.stdout.trim(), packageInfo.version);
    else assert.equal(JSON.parse(result.stdout).skills.length, 3);
  }
  assert.equal(existsSync(configDir(env)), false);
});

test('Skill installation uses the exact packaged sources and validates agent flags', () => {
  const args = skillInstallArgs('/a package', ['--agent', 'codex', 'claude-code']);
  assert.deepEqual(args.slice(0, 6), ['add', join('/a package', 'skills'), '--global', '--yes', '--json', '--skill']);
  assert.ok(args.includes('ai-shifu-learning-report'));
  assert.deepEqual(agentArgs(['--agent', 'codex']), ['--agent', 'codex']);
  assert.throws(() => agentArgs(['--agent']), /--agent/);
  assert.throws(() => agentArgs(['--agent', 'codex', '--all']), /--agent/);
});

test('automatic targets include the shared directory and only detected separate agents', t => {
  const home = temporary(t);
  const env = isolatedEnv(home);
  assert.deepEqual(defaultAgentArgs(env, home), ['--agent', 'codex']);
  mkdirSync(join(home, '.claude'));
  mkdirSync(join(home, '.cursor'));
  assert.deepEqual(defaultAgentArgs(env, home), ['--agent', 'codex', 'claude-code', 'cursor']);
  assert.equal(configDir({ AI_SHIFU_CONFIG_DIR: '~/custom' }, home), join(home, 'custom'));
});

test('preserves legacy configuration and private backup before replacing Skills', t => {
  const home = temporary(t);
  const env = isolatedEnv(home);
  const skill = join(home, 'legacy');
  mkdirSync(skill);
  const content = 'AI_SHIFU_BASE_URL=https://example.com\n';
  writeFileSync(join(skill, '.env'), content);
  preserveLegacyEnv([skill], env, home);
  const target = join(configDir(env), 'cli.env');
  assert.equal(readFileSync(target, 'utf8'), content);
  const digest = createHash('sha256').update(content).digest('hex');
  assert.equal(readFileSync(join(configDir(env), 'legacy-env', `${digest}.env`), 'utf8'), content);
  if (process.platform !== 'win32') assert.equal(statSync(target).mode & 0o777, 0o600);
  writeFileSync(target, 'selected=true\n');
  preserveLegacyEnv([skill], env, home);
  assert.equal(readFileSync(target, 'utf8'), 'selected=true\n');
});

test('different legacy configurations stop synchronization until one is chosen', t => {
  const home = temporary(t);
  const env = isolatedEnv(home);
  const sources = ['first', 'second'].map((name, i) => {
    const dir = join(home, name);
    mkdirSync(dir);
    writeFileSync(join(dir, '.env'), `service=${i}\n`);
    return dir;
  });
  assert.throws(() => preserveLegacyEnv(sources, env, home), /Different legacy configurations/);
  assert.equal(existsSync(join(configDir(env), 'cli.env')), false);
  assert.equal(readdirSync(join(configDir(env), 'legacy-env')).length, 2);
});

test('an untouched environment template does not suppress later legacy migration', t => {
  const home = temporary(t);
  const env = isolatedEnv(home);
  const source = join(home, 'old-skill');
  mkdirSync(source);
  const saved = 'SHIFU_DISABLE_ANALYTICS=1\n';
  writeFileSync(join(source, '.env'), saved);
  const configuration = configDir(env);
  mkdirSync(configuration, { recursive: true });
  writeFileSync(join(configuration, 'cli.env'),
    readFileSync(join(packageRoot, 'skills', 'ai-shifu-course-creator', '.env.example')));
  preserveLegacyEnv([source], env, home);
  assert.equal(readFileSync(join(configuration, 'cli.env'), 'utf8'), saved);
});

test('Python passthrough preserves business arguments and selects external configuration', t => {
  const env = isolatedEnv(temporary(t));
  const args = ['--profile', 'teaching', 'status', 'course-123'];
  const invocation = pythonInvocation(args, packageRoot, env);
  assert.deepEqual(invocation.args.slice(1), args);
  assert.equal(invocation.env.AI_SHIFU_CLI_ENV_FILE, join(configDir(env), 'cli.env'));
  const paths = runtimePaths(packageRoot, env);
  assert.ok(paths.directory.startsWith(configDir(env)));
  assert.ok(!paths.directory.startsWith(packageRoot));
});

test('Python detection rejects old interpreters and honors an explicit executable', () => {
  const calls = [];
  const execute = (command, args) => { calls.push([command, args]); return { status: command === 'python3.11' ? 0 : 1 }; };
  assert.deepEqual(findPython({}, execute), ['python3.11']);
  assert.equal(calls.length, 3);
  assert.throws(() => findPython({ AI_SHIFU_PYTHON: '/invalid/python' }, execute), /Python 3.11/);
});

test('local npm postinstall does not install a runtime or mutate Skills', t => {
  const env = { ...isolatedEnv(temporary(t)), npm_config_global: 'false' };
  const result = spawnSync(process.execPath, [join(packageRoot, 'cli', 'postinstall.mjs')], { env });
  assert.equal(result.status, 0);
  assert.equal(existsSync(configDir(env)), false);
});

test('real Skills installer copies all bundled Skills, migrates env and supports repeat upgrades', t => {
  const home = temporary(t);
  const env = isolatedEnv(home);
  const legacy = join(home, '.agents', 'skills', 'ai-shifu-course-creator');
  mkdirSync(legacy, { recursive: true });
  writeFileSync(join(legacy, '.env'), 'SHIFU_DISABLE_ANALYTICS=1\n');
  writeFileSync(join(legacy, 'SKILL.md'), '---\nname: ai-shifu-course-creator\ndescription: Legacy\n---\n');
  const unrelated = join(home, '.agents', 'skills', 'unrelated');
  mkdirSync(unrelated, { recursive: true });
  writeFileSync(join(unrelated, 'SKILL.md'), 'unrelated skill\n');
  for (let i = 0; i < 2; i++) {
    const result = spawnSync(process.execPath,
      [join(packageRoot, 'cli', 'shifu.mjs'), 'skills', 'install', ...(i ? ['--agent', 'codex'] : [])],
      { env, encoding: 'utf8', timeout: 30_000 });
    assert.equal(result.status, 0, result.stderr + result.stdout);
    for (const name of ['ai-shifu-course-creator', 'ai-shifu-learning-report', 'course-direction-advisor']) {
      assert.ok(existsSync(join(home, '.agents', 'skills', name, 'SKILL.md')), name);
    }
    assert.equal(readFileSync(join(configDir(env), 'cli.env'), 'utf8'), 'SHIFU_DISABLE_ANALYTICS=1\n');
    assert.equal(existsSync(join(legacy, '.env')), false);
    assert.equal(readFileSync(join(unrelated, 'SKILL.md'), 'utf8'), 'unrelated skill\n');
  }
  const [command, ...args] = skillsCommand(['list', '--global', '--json']);
  const listing = spawnSync(command, args, { env, encoding: 'utf8' });
  assert.equal(listing.status, 0, listing.stderr);
  assert.ok(JSON.parse(listing.stdout).some(skill => skill.name === 'ai-shifu-learning-report'));
});

test('a blocked agent directory fails installation instead of reporting success', t => {
  const home = temporary(t);
  const env = isolatedEnv(home);
  mkdirSync(env.CLAUDE_CONFIG_DIR, { recursive: true });
  writeFileSync(join(env.CLAUDE_CONFIG_DIR, 'skills'), 'blocked');
  const result = spawnSync(process.execPath,
    [join(packageRoot, 'cli', 'shifu.mjs'), 'skills', 'install', '--agent', 'claude-code'],
    { env, encoding: 'utf8', timeout: 30_000 });
  assert.equal(result.status, 1);
  assert.match(result.stderr, /Skill synchronization failed/);
  assert.doesNotMatch(result.stderr, /all three Skills are installed/);
});
