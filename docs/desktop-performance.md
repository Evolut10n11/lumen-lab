# Desktop performance guardrails

Lumen's Windows desktop application currently starts a packaged Python engine as a fresh process for each bridge request. That makes fresh-process engine latency a useful regression signal even though it is not the same thing as total GUI startup or interaction latency.

## v0.2.2 baseline

The post-merge Windows Installer run for `v0.2.2` measured the existing black-box engine contract on a GitHub-hosted Windows runner. Each measurement covered six real fresh-process requests spanning bootstrap, onboarding, progress persistence, restart, and locale switching.

| Engine under test | Median | Slowest sample |
| --- | ---: | ---: |
| Standalone PyInstaller engine | 1051 ms | 2309 ms |
| Engine from the installed NSIS bundle | 875 ms | 1103 ms |

These numbers are evidence from one hosted CI run, not a product SLO. Hosted runners vary in CPU scheduling, filesystem cache state, antivirus activity, and machine load.

## CI regression budget

The Windows Installer workflow applies deliberately loose limits to the same black-box contract:

- median fresh-process latency must be at most **2500 ms**;
- every individual sample must be at most **5000 ms**.

The limits are intentionally well above the v0.2.2 baseline. Their purpose is to catch severe regressions such as unexpectedly expensive imports, packaging changes, or startup work moving into every engine request without making CI flaky over normal runner variance.

`packaging/check_engine_text.py` keeps these limits opt-in. Running the script with only `--engine` reports timing without failing on performance. CI supplies `--max-median-ms 2500 --max-sample-ms 5000` for both the standalone executable and the engine copied from the installed bundle.

## What this does not measure

This guard does not claim to measure:

- time from clicking the Lumen icon until the window is visible;
- WebView initialization or React rendering;
- perceived time until the first useful screen is interactive;
- long-lived engine throughput, because the current bridge launches a fresh process per request;
- performance on a representative end-user hardware distribution.

Those need separate instrumentation before they can become user-facing performance objectives.

## Changing the budget

Do not tighten or loosen the CI budget from a single run. First compare several Windows runs and record why the new threshold is appropriate. If the engine lifecycle changes, keep the old measurements as historical evidence and define a new benchmark that matches the new architecture rather than forcing incompatible numbers into the existing guard.
