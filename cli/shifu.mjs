#!/usr/bin/env node
import { spawnSync } from 'node:child_process';
import { agentArgs, ensureRuntime, installSkills, packageInfo, pythonInvocation, runNpm,
  setup, skillNames } from './installer.mjs';

const args = process.argv.slice(2);
try {
  if (args[0] === '--version' || args[0] === '-v') {
    console.log(packageInfo.version);
  } else if (args[0] === 'install') {
    const agents = agentArgs(args.slice(1));
    runNpm(['install', '--global', '--ignore-scripts', `${packageInfo.name}@${packageInfo.version}`]);
    setup(agents);
  } else if (args[0] === 'setup') {
    setup(args.slice(1));
  } else if (args[0] === 'update') {
    const agents = agentArgs(args.slice(1));
    // The new package owns installation; never sync the old package's Skills.
    runNpm(['exec', '--yes', '--package', `${packageInfo.name}@latest`, '--', 'shifu', 'install', ...agents]);
  } else if (args[0] === 'skills') {
    if (args[1] === 'list' && args.length === 2) {
      console.log(JSON.stringify({ version: packageInfo.version, skills: skillNames }, null, 2));
    } else if (args[1] === 'install') {
      installSkills(args.slice(2));
    } else {
      throw new Error('Use shifu skills list or shifu skills install [--agent <name> ...].');
    }
  } else {
    if (args.includes('--help') || args.includes('-h') || !args.length) {
      process.stderr.write('Installation: shifu install | shifu setup | shifu update | shifu skills install [--agent <name> ...] | shifu skills list | shifu --version\n\n');
    }
    const python = ensureRuntime();
    const invocation = pythonInvocation(args);
    const result = spawnSync(python, invocation.args, { env: invocation.env, stdio: 'inherit' });
    if (result.error) throw result.error;
    process.exitCode = result.status ?? 1;
  }
} catch (error) {
  process.stderr.write(`AI-Shifu: ${error.message}\n`);
  process.exitCode = 1;
}
