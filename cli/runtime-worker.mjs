import { prepareRuntime } from './installer.mjs';

// runtime-lock.py passes its lock as stdin. Keep that descriptor open, and
// inherit it in runtime preparation subprocesses even if the helper exits.
try {
  prepareRuntime(process.argv[2]);
} catch (error) {
  process.stderr.write(`AI-Shifu runtime: ${error.message}\n`);
  process.exitCode = 1;
}
