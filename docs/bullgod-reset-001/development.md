# BullGod development instance

This is an isolated local CowAgent console for development on this Mac. The
launcher copies tracked application source into a private system temporary
directory. CowAgent uses that copy and a separate data directory, home,
workspace, profile, password, and conversation store. It uses a selected CowAgent Python virtual environment for installed libraries. It does not copy
live configuration or credentials.

## Start and stop

Run these commands from the CowAgent checkout:

```sh
python3 scripts/bullgod_dev.py init --python '/absolute/path/to/cowagent/.venv/bin/python'
python3 scripts/bullgod_dev.py start /absolute/path/printed/by/init
python3 scripts/bullgod_dev.py stop /absolute/path/printed/by/init
```

`init` prints a new private root. Save that path. `start` prints the URL and
the path to the mode-0600 config file containing the random disposable password.
Read `web_password` from that file when signing in. The password is not printed
by the launcher or stored in the instance marker. The default URL is http://127.0.0.1:19892/.
`init --port 19893` selects another available port; port 9899 is rejected.
The launcher refuses to start if the port is occupied. Stop only signals the
recorded process when its identity still matches the instance. Starting the same
root again keeps its workspace, conversations, and configuration. Do not change
the bind port in the console: the sandbox permits only the port selected at
initialization. If you change the console password, use its current value.

To reset, run `init` again, then start the new root. This creates an empty
instance; it does not delete the old one. Stop the old instance first if you
want to reuse its port. System temporary directories may be cleared by macOS;
retain anything important elsewhere. Source is captured at `init` from tracked
working-tree files. Stage new application files before `init` so the snapshot
includes them. Create a new root to test a later source revision. This launcher never refreshes a
running instance's source.

## Isolation and limits

The macOS sandbox uses a default-deny policy. It allows process execution and
forking, sysctl reads, reads and writes inside the instance, reads of required
macOS and Python runtime paths, and inbound connections to the chosen loopback
port. It grants no Mach lookup, Apple Events, or task-port permissions. Child
processes inherit the sandbox. Outbound connections are denied, including provider and OAuth
connections. The service receives a small, explicit environment, not the
launcher's environment. The agent starts as BullGod with read-only
permissions. The owner can explicitly select workspace-write in the console for
a bounded action. The instance has no provider credentials or external API.
Subagents, self-evolution, and browser launch are disabled by default.
Same-account processes, the operating system, installed Python libraries and
this checkout are trusted. This is a local
development boundary, not a defense against a hostile user of this account.

A compatible virtual environment must use macOS Python.framework and already
contain CowAgent dependencies. The interpreter is selected for each new root;
no specific production checkout is required.

The actual console shell, authentication, profile, session list, workspace
read/write and restart persistence were checked. A synthetic message written
through CowAgent’s ConversationStore appeared in the real session list after
restart and was absent from a second instance. This was a store test, not a
natural conversation. The workspace persistence and synthetic conversation
checks used the prior launcher revision. The default-deny revision passed a fresh startup, console,
login, workspace and conversation-store read check. A safe outside-root canary
read and outbound loopback connection were denied. Unfiltered sandbox policy
checks also denied Mach lookup, Apple Events and privileged task-port access;
these checks do not prove every possible IPC operation.
Model responses and natural conversation quality were not tested; model and
network access are unavailable by default. No production instance is modified by these commands.
