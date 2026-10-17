# detect_agent conformance data

These synthetic cases and the accompanying MIT license are copied unchanged from [ai-shifu/detect_agent](https://github.com/ai-shifu/detect_agent) version **0.1.5**, commit **9eee13ebdd8dcee22bd90b03125fa9f509a80be1**.

- Specification: [detect_agent.md](https://github.com/ai-shifu/detect_agent/blob/9eee13ebdd8dcee22bd90b03125fa9f509a80be1/detect_agent.md)
- Fixture source: [conformance/cases.json](https://github.com/ai-shifu/detect_agent/blob/9eee13ebdd8dcee22bd90b03125fa9f509a80be1/conformance/cases.json)
- Copyright (c) 2026 ai-shifu. Licensed under MIT; see `LICENSE`.

The native Python implementation lives in the Course Creator's `scripts/agent_detection.py`. Tests emulate environment lookup, filesystem probes, PATH separators and TTY capabilities. They never use the host's actual environment, filesystem or terminal state as conformance input.
