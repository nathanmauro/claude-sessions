#!/usr/bin/env bash
# Demo output for the CLI screenshot — curated, deterministic, no PII.
# Mirrors the column layout from `agent_sessions/cli/main.py::_cmd_ls`.
set -euo pipefail

printf '$ agent-sessions ls --limit 8\n'
printf '  AGE  RUN  PROJECT                   TITLE                                                         SESSION_ID\n'
printf '   1h  yes  orbital-cli               Wire up the new router with deferred imports                  01k5c4xa-2ed2-426c-80ff-2f817655b45e\n'
printf '   3h       lighthouse-api            Background job retries — exponential backoff                  01k5b9zd-a3b4-482b-b6a6-9fce64e32d21\n'
printf '   7h       portfolio-site            Dark mode tokens + system-preference detection                01k5a2qb-5608-4d14-89ae-55d86d05da25\n'
printf '   1d       orbital-cli               Migrate feature flags to OpenFeature                          01k59lkp-d0c4-4d6f-9c93-1769ee991689\n'
printf '   1d       lighthouse-api            OTel tracing on the ingest pipeline                           01k58hh1-1d98-44f8-a0d0-09dec10d743d\n'
printf '   2d       portfolio-site            Dynamic OG images for blog posts                              01k57e4w-e906-4a66-8d31-ed574cd81a40\n'
printf '   3d       orbital-cli               Tighten error envelopes on the public API                     01k56qz3-f58c-4b51-8baf-c5014b101c98\n'
printf '   4d       lighthouse-api            Migrate config loader to pydantic-settings                    01k55mt7-3e92-4e95-bc96-21f5feb5ae77\n'
