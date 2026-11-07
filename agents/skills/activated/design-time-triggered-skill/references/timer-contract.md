# Shared timer contract

All time-triggered skills in a project share Git-versioned `agents/scratch/timers.json` (or the configured scratch root). Keys identify independent workflows:

```json
{
  "version": 1,
  "timers": {
    "maintain-scratch": {
      "interval_days": 7,
      "last_completed_at": null
    }
  }
}
```

Use a positive numeric interval and UTC ISO-8601 completion timestamps. At the skill's observation event, an absent entry or null completion is due; otherwise due means elapsed time is at least the interval. Initialize missing entries with the skill's declared default and null completion. Merely checking, creating, or beginning work never advances the timer.

Malformed data, unsupported versions, invalid intervals, or future timestamps require reconciliation; do not overwrite the file or silently mark work fresh. Preserve recoverable history. A malformed completion is unverified, not evidence of success.

Run at most once per observation event; missed periods collapse into one pass unless the skill explicitly requires catch-up. Preserve the checked state across context compaction, but a genuinely fresh agent session is a new event. Explicit user requests may run maintenance outside this cadence.

Serialize maintenance writers for the shared scratch workspace. Re-read the timer under that coordination, merge only the owned entry, and atomically replace the file; atomic replacement alone does not prevent lost concurrent updates. Stamp completion only after the payload and its verification succeed. A completed review with no changes may count; interrupted, blocked, or prohibited work stays due. Respect task write scope and include state changes in authorized commits.

Timers record completed work, not locks or scheduled jobs. Without a host observing the declared event, nothing executes in the background.
