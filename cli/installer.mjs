import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { createRequire } from 'node:module';
import { chmodSync, cpSync, existsSync, lstatSync, mkdirSync, mkdtempSync, readFileSync,
  readdirSync, rmSync, writeFileSync } from 'node:fs';
import { homedir, tmpdir } from 'node:os';
import { basename, dirname, isAbsolute, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

export const packageRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
export const skillNames = [
  'ai-shifu-course-creator', 'ai-shifu-learning-report', 'course-direction-advisor',
];
const supportedAgents = ['codex', 'claude-code', 'cursor', 'gemini-cli', 'github-copilot',
  'openclaw', 'codebuddy', 'opencode', 'windsurf'];
export const packageInfo = JSON.parse(readFileSync(join(packageRoot, 'package.json'), 'utf8'));

function expandHome(value, home) {
  return value === '~' ? home : value.startsWith('~/') || value.startsWith('~\\') ? join(home, value.slice(2)) : value;
}

function processConfigDir(env = process.env, home = homedir()) {
  return resolve(expandHome(env.AI_SHIFU_CONFIG_DIR?.trim() ||
    join(env.XDG_CONFIG_HOME?.trim() || join(home, '.config'), 'ai-shifu'), home));
}

export function configDir(env = process.env, home = homedir()) {
  const root = processConfigDir(env, home);
  if (env.AI_SHIFU_CONFIG_DIR?.trim()) return root;
  const pointer = join(root, 'cli-config-root.json');
  let value;
  try {
    value = JSON.parse(readFileSync(pointer, 'utf8'));
  } catch (error) {
    if (error.code === 'ENOENT') return root;
    throw new Error(`Cannot read npm configuration root pointer: ${pointer}`);
  }
  if (!value || Array.isArray(value) || Object.keys(value).sort().join(',') !== 'config_dir,schema_version' ||
    value.schema_version !== 1 || typeof value.config_dir !== 'string' ||
    !value.config_dir || value.config_dir.includes('\0') || !isAbsolute(value.config_dir)) {
    throw new Error(`Invalid npm configuration root pointer: ${pointer}`);
  }
  return resolve(value.config_dir);
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
  if (args.slice(1).some(name => !supportedAgents.includes(name))) {
    throw new Error(`Supported agents: ${supportedAgents.join(', ')}.`);
  }
  return args;
}

export function skillInstallArgs(root = packageRoot, agents = []) {
  return ['add', join(root, 'skills'), '--global', '--yes', '--json', '--skill', ...skillNames, ...agentArgs(agents)];
}

function agentRoots(env, home) {
  const openclaw = ['.openclaw', '.clawdbot', '.moltbot'].map(name => join(home, name));
  return {
    codex: join(home, '.agents'),
    'claude-code': expandHome(env.CLAUDE_CONFIG_DIR || join(home, '.claude'), home),
    cursor: join(home, '.cursor'),
    'gemini-cli': join(home, '.gemini'),
    'github-copilot': join(home, '.copilot'),
    openclaw: openclaw.find(directory => existsSync(directory)) || openclaw[0],
    codebuddy: join(home, '.codebuddy'),
    opencode: join(expandHome(env.XDG_CONFIG_HOME || join(home, '.config'), home), 'opencode'),
    windsurf: join(home, '.codeium', 'windsurf'),
  };
}

export function legacySkillDirs(env = process.env, home = homedir(), agents = ['--agent', 'codex']) {
  const roots = agentRoots(env, home);
  const selected = agentArgs(agents).slice(1);
  // Every selected installer target also writes the shared canonical directory.
  return [...new Set([roots.codex, ...selected.map(name => roots[name])])]
    .map(root => join(root, 'skills', skillNames[0]));
}

export function defaultAgentArgs(env = process.env, home = homedir()) {
  // Codex selects the shared ~/.agents/skills directory used by universal
  // consumers. Explicit targets also avoid skills 1.7.4's automatic inclusion
  // of PromptScript, which has no global installation directory.
  return ['--agent', 'codex', ...Object.entries(agentRoots(env, home))
    .filter(([name, directory]) => name !== 'codex' && existsSync(directory)).map(([name]) => name)];
}

export function preserveLegacyEnv(directories, env = process.env, home = homedir()) {
  if (!directories.some(directory => existsSync(join(directory, '.env')))) return;
  env = pythonEnvironment(env);
  let [python, ...prefix] = findPython(env);
  const probe = spawnSync(python, [...prefix, '-c', 'import dotenv'], { env, stdio: 'ignore' });
  if (probe.error || probe.status !== 0) {
    python = ensureRuntime(packageRoot, env);
    prefix = [];
  }
  // Profile migration/logout own the same lock, parser, and credential receipt.
  // Node never reads secret contents before acquiring that transaction lock.
  const result = spawnSync(python, [...prefix, join(packageRoot, 'cli', 'migrate-config.py'),
    processConfigDir(env, home), join(packageRoot, 'skills', skillNames[0], '.env.example'), ...directories],
  { env, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
  if (result.error) throw result.error;
  if (result.status !== 0) throw new Error(result.stderr.trim() || 'Legacy configuration migration failed.');
  const migration = JSON.parse(result.stdout);
  if (migration.imported_profiles?.length) {
    process.stderr.write(`Legacy configuration profile(s): ${migration.imported_profiles.map(name => JSON.stringify(name)).join(', ')}. Inspect accounts with shifu profile list.\n`);
  }
  return migration;
}

export function pythonEnvironment(env = process.env) {
  return Object.fromEntries(Object.entries(env).filter(([key]) =>
    !['PYTHONHOME', 'PYTHONPATH'].includes(key.toUpperCase())));
}

export function findPython(env = process.env, execute = spawnSync) {
  env = pythonEnvironment(env);
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

export function ensureRuntime(root = packageRoot, env = process.env) {
  env = pythonEnvironment(env);
  const paths = runtimePaths(root, env);
  let launcher;
  try {
    launcher = findPython(env);
  } catch (error) {
    if (env.AI_SHIFU_PYTHON || !existsSync(paths.python)) throw error;
    // The runtime may still work after its system Python was removed from
    // PATH. Recheck it under the native lock before accepting the cache.
    launcher = findPython({ ...env, AI_SHIFU_PYTHON: paths.python });
  }
  const [python, ...prefix] = launcher;
  run(python, [...prefix, join(packageRoot, 'cli', 'runtime-lock.py'), `${paths.directory}.lock`,
    '--prepare', paths.directory, paths.requirements, paths.python], { env });
  return paths.python;
}

export function installSkills(agents = [], root = packageRoot, env = process.env) {
  const checked = agentArgs(agents);
  const home = (process.platform === 'win32' ? env.USERPROFILE || env.HOME : env.HOME || env.USERPROFILE) || homedir();
  const selectedAgents = checked.length ? checked : defaultAgentArgs(env, home);
  preserveLegacyEnv(legacySkillDirs(env, home, selectedAgents), env, home);
  const metadata = JSON.parse(readFileSync(join(root, 'package.json'), 'utf8'));
  const marker = { schema_version: 1, distribution: 'npm', version: metadata.version };
  const staging = mkdtempSync(join(tmpdir(), 'ai-shifu-skills-'));
  // Source packages may be read-only. Change only temporary directory modes.
  const writable = directory => {
    chmodSync(directory, 0o700);
    for (const entry of readdirSync(directory, { withFileTypes: true })) {
      if (entry.isDirectory()) writable(join(directory, entry.name));
    }
  };
  try {
    for (const name of skillNames) {
      const destination = join(staging, 'skills', name);
      cpSync(join(root, 'skills', name), destination, {
        recursive: true,
        filter(source) {
          const filename = basename(source);
          return !lstatSync(source).isSymbolicLink() &&
            !['.git', '__pycache__', '__pypackages__', 'node_modules', '.venv', '.DS_Store'].includes(filename) &&
            !(filename.startsWith('.env') && filename !== '.env.example') &&
            !filename.startsWith('.update-check') && !/\.py[co]$/.test(filename);
        },
      });
      writable(destination);
      writeFileSync(join(destination, '.ai-shifu-cli.json'), JSON.stringify(marker) + '\n');
    }
    const [command, ...args] = skillsCommand(skillInstallArgs(staging, selectedAgents), root);
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
  } finally {
    writable(staging);
    rmSync(staging, { recursive: true, force: true, maxRetries: 3, retryDelay: 100 });
  }
  process.stderr.write(`Installed Skills: ${skillNames.join(', ')}\n`);
}

export function setup(agents = []) {
  agentArgs(agents);
  const initialRoot = configDir();
  ensureRuntime();
  installSkills(agents);
  if (configDir() !== initialRoot) ensureRuntime();
  process.stderr.write(`AI-Shifu ${packageInfo.version}: CLI runtime and all three Skills are installed. Restart your agent to load the Skills.\n`);
}

export function pythonInvocation(args, root = packageRoot, env = process.env) {
  return {
    args: [join(root, 'skills', skillNames[0], 'scripts', 'shifu-cli.py'), ...args],
    env: { ...pythonEnvironment(env), AI_SHIFU_CONFIG_DIR: configDir(env),
      AI_SHIFU_CLI_ENV_FILE: join(configDir(env), 'cli.env'),
      AI_SHIFU_CLI_DISTRIBUTION: 'npm' },
  };
}
