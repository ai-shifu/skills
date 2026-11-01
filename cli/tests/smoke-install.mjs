/** Real npm lifecycle smoke test. Runs separately because it installs Python dependencies. */
import assert from 'node:assert/strict';
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { packageInfo, packageRoot, run, runNpm, runtimePaths, skillNames } from '../installer.mjs';

const temporary = mkdtempSync(join(tmpdir(), 'ai-shifu-install-smoke-'));
try {
  const home = join(temporary, 'home');
  const prefix = join(temporary, 'global');
  const configuration = join(temporary, 'configuration');
  mkdirSync(home, { recursive: true });
  const npmrc = join(temporary, 'npmrc');
  writeFileSync(npmrc, '');
  const environment = {
    ...process.env,
    HOME: home,
    USERPROFILE: home,
    CODEX_HOME: join(home, '.codex'),
    CLAUDE_CONFIG_DIR: join(home, '.claude'),
    XDG_CONFIG_HOME: join(home, '.config'),
    AI_SHIFU_CONFIG_DIR: configuration,
    npm_config_prefix: prefix,
    npm_config_cache: join(temporary, 'npm-cache'),
    npm_config_userconfig: npmrc,
    npm_config_ignore_scripts: 'false',
    SHIFU_DISABLE_ANALYTICS: '1',
  };
  // Never allow the developer's service or token overrides into an isolated install.
  for (const key of ['SHIFU_BASE_URL', 'SHIFU_TOKEN', 'AI_SHIFU_CLI_ENV_FILE', 'PYTHONHOME', 'PYTHONPATH']) {
    delete environment[key];
  }
  const packed = runNpm(['pack', '--ignore-scripts', '--json', '--pack-destination', temporary], {
    cwd: packageRoot, env: environment, encoding: 'utf8', stdio: ['ignore', 'pipe', 'inherit'],
  });
  const artifacts = JSON.parse(packed.stdout);
  assert.equal(artifacts.length, 1, 'npm pack must produce one installable package');
  const archive = join(temporary, artifacts[0].filename);
  runNpm(['install', '--global', '--prefix', prefix, '--allow-scripts=@ai-shifu/cli', archive], {
    cwd: temporary, env: environment,
  });

  const installedRoot = join(prefix, ...(process.platform === 'win32' ? [] : ['lib']), 'node_modules', '@ai-shifu', 'cli');
  const entrypoint = join(installedRoot, 'cli', 'shifu.mjs');
  assert.ok(existsSync(entrypoint), 'npm must install the CLI entrypoint');

  // Check before invoking shifu: otherwise a later setup could conceal a skipped postinstall hook.
  const assertInstalledSkills = () => {
    for (const name of skillNames) {
      const installedSkill = join(home, '.agents', 'skills', name, 'SKILL.md');
      assert.ok(existsSync(installedSkill), `postinstall must install ${name}`);
      assert.equal(readFileSync(installedSkill, 'utf8'), readFileSync(join(installedRoot, 'skills', name, 'SKILL.md'), 'utf8'));
    }
  };
  assertInstalledSkills();
  assert.ok(existsSync(runtimePaths(installedRoot, environment, home).marker), 'postinstall must prepare the Python runtime');

  function shifu(arguments_) {
    return run(process.execPath, [entrypoint, ...arguments_], {
      cwd: temporary, env: environment, encoding: 'utf8', stdio: ['ignore', 'pipe', 'inherit'],
    }).stdout;
  }
  assert.equal(shifu(['--version']).trim(), packageInfo.version);
  const site = JSON.parse(shifu(['site']));
  assert.equal(site.status, 'selection_required', 'a clean install must not inherit an account');
  assert.ok(existsSync(join(configuration, 'cli.env')), 'runtime configuration belongs in the user directory');
  shifu(['setup', '--agent', 'codex']);
  assertInstalledSkills();
  assert.ok(!existsSync(join(installedRoot, '.env')), 'the installed npm package must remain free of runtime configuration');
  assert.ok(!existsSync(join(installedRoot, 'skills', skillNames[0], '.env')), 'the bundled Skill must remain free of runtime configuration');
  console.log(`Real npm install passed: shifu ${packageInfo.version}, Python runtime, and all three Skills.`);
} finally {
  rmSync(temporary, { recursive: true, force: true, maxRetries: 3, retryDelay: 100 });
}
