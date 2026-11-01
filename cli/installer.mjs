import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { createRequire } from 'node:module';
import { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

export const packageRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
export const skillNames = [
  'ai-shifu-course-creator', 'ai-shifu-learning-report', 'course-direction-advisor',
];
export const packageInfo = JSON.parse(readFileSync(join(packageRoot, 'package.json'), 'utf8'));

function expandHome(value, home) {
  return value === '~' ? home : value.startsWith('~/') || value.startsWith('~\\') ? join(home, value.slice(2)) : value;
}

export function configDir(env = process.env, home = homedir()) {
  return resolve(expandHome(env.AI_SHIFU_CONFIG_DIR?.trim() ||
    join(env.XDG_CONFIG_HOME?.trim() || join(home, '.config'), 'ai-shifu'), home));
}

// Invoke npm's JavaScript entrypoint where available; never interpolate user
// arguments into a shell command (including on Windows).
export function npmCommand(args, env = process.env) {
  if (env.npm_execpath?.endsWith('.js')) return [process.execPath, env.npm_execpath, ...args];
  if (process.platform === 'win32') {
    const entry = join(dirname(process.execPath), 'node_modules', 'npm', 'bin', 'npm-cli.js');
    if (!existsSync(entry)) throw new Error('Cannot locate npm. Run this command through npx or npm.');
    return [process.execPath, entry, ...args];
  }
  return ['npm', ...args];
}

export function run(command, args, options = {}) {
  const result = spawnSync(command, args, { stdio: 'inherit', ...options });
  if (result.error) throw new Error(`Cannot run ${command}: ${result.error.message}`);
  if (result.status !== 0) throw new Error(`${command} exited with ${result.status ?? result.signal}`);
  return result;
}

export function runNpm(args, options = {}) {
  const [command, ...rest] = npmCommand(args, options.env);
  return run(command, rest, options);
}

export function skillsCommand(args, root = packageRoot) {
  const require = createRequire(join(root, 'package.json'));
  const metadataFile = require.resolve('skills/package.json');
  const metadata = JSON.parse(readFileSync(metadataFile, 'utf8'));
  const bin = typeof metadata.bin === 'string' ? metadata.bin : metadata.bin.skills;
  return [process.execPath, resolve(dirname(metadataFile), bin), ...args];
}

export function agentArgs(args) {
  if (!args.length) return [];
  if (args[0] !== '--agent' || args.length < 2 || args.slice(1).some(x => !/^[a-z0-9][a-z0-9-]*$/.test(x))) {
    throw new Error('Use --agent <agent-name> [agent-name ...], for example --agent codex claude-code.');
  }
  return args;
}

export function skillInstallArgs(root = packageRoot, agents = []) {
  return ['add', join(root, 'skills'), '--global', '--yes', '--json', '--skill', ...skillNames, ...agentArgs(agents)];
}

export function legacySkillDirs(env = process.env, home = homedir()) {
  const roots = [join(home, '.agents'), env.CODEX_HOME || join(home, '.codex'),
    env.CLAUDE_CONFIG_DIR || join(home, '.claude'), join(home, '.cursor'),
    join(home, '.workbuddy'), join(home, '.openclaw')];
  return [...new Set(roots.map(root => join(root, 'skills', skillNames[0])))];
}

export function defaultAgentArgs(env = process.env, home = homedir()) {
  // Codex selects the shared ~/.agents/skills directory used by universal
  // consumers. Explicit targets also avoid skills 1.7.4's automatic inclusion
  // of PromptScript, which has no global installation directory.
  const candidates = [
    ['claude-code', env.CLAUDE_CONFIG_DIR || join(home, '.claude')],
    ['cursor', join(home, '.cursor')],
    ['gemini-cli', join(home, '.gemini')],
    ['github-copilot', join(home, '.copilot')],
    ['openclaw', join(home, '.openclaw')],
    ['openclaw', join(home, '.clawdbot')],
    ['openclaw', join(home, '.moltbot')],
    ['codebuddy', join(home, '.codebuddy')],
    ['opencode', join(env.XDG_CONFIG_HOME || join(home, '.config'), 'opencode')],
    ['windsurf', join(home, '.codeium', 'windsurf')],
  ];
  return ['--agent', 'codex', ...new Set(candidates.filter(([, directory]) => existsSync(directory)).map(([name]) => name))];
}

export function preserveLegacyEnv(directories, env = process.env, home = homedir()) {
  const directory = configDir(env, home);
  const destination = join(directory, 'cli.env');
  const contents = new Map();
  for (const dir of directories) {
    const source = join(dir, '.env');
    if (!existsSync(source)) continue;
    const content = readFileSync(source);
    const digest = createHash('sha256').update(content).digest('hex');
    contents.set(digest, content);
  }
  if (!contents.size) return;
  const backup = join(directory, 'legacy-env');
  mkdirSync(backup, { recursive: true, mode: 0o700 });
  for (const [digest, content] of contents) {
    const file = join(backup, `${digest}.env`);
    if (!existsSync(file)) writeFileSync(file, content, { mode: 0o600, flag: 'wx' });
  }
  if (existsSync(destination)) return;
  if (contents.size > 1) {
    throw new Error(`Different legacy configurations were saved in ${backup}. Choose one as ${destination}, then retry installation.`);
  }
  writeFileSync(destination, [...contents.values()][0], { mode: 0o600, flag: 'wx' });
}

export function findPython(env = process.env, execute = spawnSync) {
  const candidates = env.AI_SHIFU_PYTHON ? [[env.AI_SHIFU_PYTHON]] :
    [['python3.13'], ['python3.12'], ['python3.11'], ['python3'], ['python'], ['py', '-3']];
  for (const [command, ...prefix] of candidates) {
    const result = execute(command, [...prefix, '-c',
      'import sys, venv; sys.exit(0 if sys.version_info >= (3, 11) else 1)'],
    { env, stdio: 'ignore' });
    if (!result.error && result.status === 0) return [command, ...prefix];
  }
  throw new Error('Install Python 3.11+ with venv support, or set AI_SHIFU_PYTHON to its executable.');
}

export function runtimePaths(root = packageRoot, env = process.env, home = homedir()) {
  const requirements = join(root, 'skills', skillNames[0], 'scripts', 'requirements.txt');
  const digest = createHash('sha256').update(readFileSync(requirements)).digest('hex').slice(0, 16);
  const directory = join(configDir(env, home), 'cli-runtime', digest);
  return { directory, requirements, marker: join(directory, '.ready'),
    python: join(directory, process.platform === 'win32' ? 'Scripts' : 'bin',
      process.platform === 'win32' ? 'python.exe' : 'python') };
}

function runtimeHealthy(paths, env, execute) {
  if (!existsSync(paths.marker) || !existsSync(paths.python)) return false;
  const result = execute(paths.python, ['-c', 'import requests, dotenv, PIL, pillow_heif'],
    { env, stdio: 'ignore', timeout: 10_000 });
  return !result.error && result.status === 0;
}

function runtimeRun(command, args, options, execute) {
  const result = execute(command, args, { stdio: 'inherit', ...options });
  if (result.error) throw new Error(`Cannot run ${command}: ${result.error.message}`);
  if (result.status !== 0) throw new Error(`${command} exited with ${result.status ?? result.signal}`);
}

export function ensureRuntime(root = packageRoot, env = process.env, execute = spawnSync) {
  const paths = runtimePaths(root, env);
  if (runtimeHealthy(paths, env, execute)) return paths.python;
  const [python, ...prefix] = findPython(env, execute);
  mkdirSync(dirname(paths.directory), { recursive: true, mode: 0o700 });
  // A cached interpreter can survive removal of its base Python on Windows,
  // or dependencies may have been removed. Rebuild that controlled directory.
  rmSync(paths.directory, { recursive: true, force: true });
  process.stderr.write('Preparing the isolated AI-Shifu Python runtime…\n');
  runtimeRun(python, [...prefix, '-m', 'venv', paths.directory], { env }, execute);
  runtimeRun(paths.python, ['-m', 'pip', 'install', '--disable-pip-version-check', '-r', paths.requirements],
    { env, stdio: ['inherit', 2, 2] }, execute);
  // Mark ready only after imports succeed, so failed installations can be retried.
  runtimeRun(paths.python, ['-c', 'import requests, dotenv, PIL, pillow_heif'], { env }, execute);
  writeFileSync(paths.marker, 'ready\n', { mode: 0o600 });
  return paths.python;
}

export function installSkills(agents = [], root = packageRoot, env = process.env) {
  const checked = agentArgs(agents);
  const [listCommand, ...listArgs] = skillsCommand(['list', '--global', '--json'], root);
  const listing = run(listCommand, listArgs, { env, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
  const installed = JSON.parse(listing.stdout);
  if (!Array.isArray(installed)) throw new Error('Cannot inspect installed Skills before migration.');
  const existing = installed.filter(skill => skill.name === skillNames[0] && typeof skill.path === 'string');
  preserveLegacyEnv([...legacySkillDirs(env), ...existing.map(skill => skill.path)], env);
  const [command, ...args] = skillsCommand(skillInstallArgs(root, checked.length ? checked : defaultAgentArgs(env)), root);
  const result = spawnSync(command, args, { env, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
  if (result.error) throw result.error;
  if (result.status !== 0) {
    throw new Error(`Skill synchronization failed: ${result.stdout || result.stderr || result.signal}`);
  }
  const outcomes = JSON.parse(result.stdout);
  if (!Array.isArray(outcomes) || skillNames.some(name =>
    !outcomes.some(item => item.name === name && item.status === 'installed')) ||
    outcomes.some(item => item.status !== 'installed')) {
    throw new Error('Skill synchronization did not install all three bundled Skills. Retry shifu skills install.');
  }
  process.stderr.write(`Installed Skills: ${skillNames.join(', ')}\n`);
}

export function setup(agents = []) {
  agentArgs(agents);
  ensureRuntime();
  installSkills(agents);
  process.stderr.write(`AI-Shifu ${packageInfo.version}: CLI runtime and all three Skills are installed. Restart your agent to load the Skills.\n`);
}

export function pythonInvocation(args, root = packageRoot, env = process.env) {
  return {
    args: [join(root, 'skills', skillNames[0], 'scripts', 'shifu-cli.py'), ...args],
    env: { ...env, AI_SHIFU_CLI_ENV_FILE: join(configDir(env), 'cli.env') },
  };
}
