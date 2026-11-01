import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { chmodSync, existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync,
  statSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { agentArgs, configDir, defaultAgentArgs, findPython, installSkills, packageInfo, packageRoot, preserveLegacyEnv,
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
  assert.throws(() => agentArgs(['--agent', 'unknown-agent']), /Supported agents/);
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
  mkdirSync(env.CLAUDE_CONFIG_DIR, { recursive: true });
  for (let i = 0; i < 2; i++) {
    const result = spawnSync(process.execPath,
      [join(packageRoot, 'cli', 'shifu.mjs'), 'skills', 'install', ...(i ? ['--agent', 'codex'] : [])],
      { env, encoding: 'utf8', timeout: 30_000 });
    assert.equal(result.status, 0, result.stderr + result.stdout);
    for (const name of ['ai-shifu-course-creator', 'ai-shifu-learning-report', 'course-direction-advisor']) {
      assert.ok(existsSync(join(home, '.agents', 'skills', name, 'SKILL.md')), name);
      const marker = { schema_version: 1, distribution: 'npm', version: packageInfo.version };
      for (const installation of [join(home, '.agents', 'skills'), join(env.CLAUDE_CONFIG_DIR, 'skills')]) {
        assert.deepEqual(JSON.parse(readFileSync(join(installation, name, '.ai-shifu-cli.json'), 'utf8')), marker);
      }
      assert.equal(existsSync(join(packageRoot, 'skills', name, '.ai-shifu-cli.json')), false);
      assert.equal(existsSync(join(packageRoot, 'skills', name, '.env')), false);
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

test('a targeted Codex install leaves an unrelated Claude configuration out of migration', t => {
  const home = temporary(t);
  const env = isolatedEnv(home);
  const claudeSkill = join(env.CLAUDE_CONFIG_DIR, 'skills', 'ai-shifu-course-creator');
  mkdirSync(claudeSkill, { recursive: true });
  writeFileSync(join(claudeSkill, '.env'), 'SHIFU_DISABLE_ANALYTICS=1\n');
  const result = spawnSync(process.execPath,
    [join(packageRoot, 'cli', 'shifu.mjs'), 'skills', 'install', '--agent', 'codex'],
    { env, encoding: 'utf8', timeout: 30_000 });
  assert.equal(result.status, 0, result.stderr);
  assert.equal(existsSync(join(configDir(env), 'cli.env')), false);
  assert.equal(existsSync(join(configDir(env), 'legacy-env')), false);
  assert.equal(readFileSync(join(claudeSkill, '.env'), 'utf8'), 'SHIFU_DISABLE_ANALYTICS=1\n');
});

test('stages npm metadata from a read-only source and removes staging after success or failure', t => {
  const home = mkdtempSync(join(tmpdir(), 'ai-shifu-readonly-'));
  const readonly = [];
  t.after(() => {
    for (const source of readonly) {
      chmodSync(source, 0o700);
      chmodSync(join(source, 'nested'), 0o700);
    }
    rmSync(home, { recursive: true, force: true });
  });
  const root = join(home, 'package');
  const env = isolatedEnv(home);
  mkdirSync(root);
  writeFileSync(join(root, 'package.json'), JSON.stringify({ name: '@ai-shifu/cli', version: '9.8.7' }));
  const dependency = join(root, 'node_modules', 'skills');
  mkdirSync(dependency, { recursive: true });
  writeFileSync(join(dependency, 'package.json'), JSON.stringify({ name: 'skills', bin: './fixture.mjs', type: 'module' }));
  const trace = join(home, 'stage-path');
  writeFileSync(join(dependency, 'fixture.mjs'), `
    import { cpSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
    import { join } from 'node:path';
    if (process.argv[2] === 'list') console.log('[]');
    else {
      const source = process.argv[3];
      writeFileSync(process.env.STAGING_TRACE, source);
      const names = ['ai-shifu-course-creator', 'ai-shifu-learning-report', 'course-direction-advisor'];
      const outcomes = names.map(name => {
        const target = join(process.env.HOME, '.agents', 'skills', name);
        mkdirSync(target, { recursive: true });
        cpSync(join(source, name), target, { recursive: true });
        return { name, status: process.env.FAIL_INSTALL ? 'failed' : 'installed', path: target };
      });
      console.log(JSON.stringify(outcomes));
      process.exitCode = process.env.FAIL_INSTALL ? 1 : 0;
    }
  `);
  const sources = ['ai-shifu-course-creator', 'ai-shifu-learning-report', 'course-direction-advisor'].map(name => {
    const source = join(root, 'skills', name);
    mkdirSync(join(source, 'nested'), { recursive: true });
    writeFileSync(join(source, 'SKILL.md'), `---\nname: ${name}\ndescription: fixture\n---\n`);
    writeFileSync(join(source, '.env.example'), 'SHIFU_TOKEN=\n');
    writeFileSync(join(source, '.env'), 'SHIFU_TOKEN=must-not-copy\n');
    writeFileSync(join(source, '.env.local'), 'must-not-copy\n');
    mkdirSync(join(source, '__pycache__'));
    writeFileSync(join(source, '__pycache__', 'cached.pyc'), 'must-not-copy');
    chmodSync(join(source, 'nested'), 0o555);
    chmodSync(source, 0o555);
    readonly.push(source);
    return source;
  });
  for (const fail of [false, true]) {
    const installationEnv = { ...env, STAGING_TRACE: trace, ...(fail ? { FAIL_INSTALL: '1' } : {}) };
    if (fail) assert.throws(() => installSkills(['--agent', 'codex'], root, installationEnv), /Skill synchronization failed/);
    else installSkills(['--agent', 'codex'], root, installationEnv);
    const stagedSource = readFileSync(trace, 'utf8');
    assert.equal(existsSync(stagedSource), false, 'staged sources must be cleaned after every outcome');
    for (const source of sources) {
      const name = source.split(/[\\/]/).at(-1);
      const target = join(home, '.agents', 'skills', name);
      assert.deepEqual(JSON.parse(readFileSync(join(target, '.ai-shifu-cli.json'), 'utf8')),
        { schema_version: 1, distribution: 'npm', version: '9.8.7' });
      assert.equal(existsSync(join(target, '.env')), false);
      assert.equal(existsSync(join(target, '.env.local')), false);
      assert.equal(existsSync(join(target, '__pycache__')), false);
      assert.equal(readFileSync(join(target, '.env.example'), 'utf8'), 'SHIFU_TOKEN=\n');
      assert.equal(existsSync(join(source, '.ai-shifu-cli.json')), false);
      assert.equal(readFileSync(join(source, '.env'), 'utf8'), 'SHIFU_TOKEN=must-not-copy\n');
    }
  }
});
