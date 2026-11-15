# Grok Bot integration discovery

## Result

The installed target is `/Applications/Grok Bot.app`, an Electron app. Its
`Contents/Info.plist` identifies bundle `com.anysphere.sand`, display name
`Grok Bot`, and version `1.1.0`. Code-signing metadata names Anysphere
Incorporated; the plist copyright field says SpaceXAI. The packaged
`Contents/Resources/app.asar` manifest identifies product `Grok Bot`, version
`1.1.0`, description `Grok Bot desktop agent`, and main entry
`dist/electron-main/main.cjs`. This identifies the local app package, but does
not establish an official public Grok API or supported CowAgent integration.

The static package contains renderer chunks named
`chunk-tasks-sidebar-list-5rdZEW0N.js`,
`chunk-custom-mcp-form-QklklxmN.js`, and
`chunk-grok-bot-team-custom-mcp-BovN6J6b.js`. These names show that the app
includes related UI code. They do not prove that the installed account has
these features enabled, that an MCP server is configured, or that a supported
external task API exists. The app's Anysphere signing authority and its
SpaceXAI copyright text are recorded as separate package identity fields; neither
alone proves the supported service contract. No separate Grok Bot source
repository was found in the bounded project search. No task IDs, statuses, logs,
or results were read. CowAgent's own MCP support is only a transport capability;
it needs an explicitly configured server
([CAPABILITY-MATRIX.md:15](CAPABILITY-MATRIX.md#L15)).

## Integration route order

1. **Authenticated service interface:** none verified. Missing evidence is the
   supported endpoint, request/response schema, authentication handoff, stable
   task lookup key, status semantics, log access, and result retrieval contract.
   Do not infer API routes from packaged UI bundles or submit a task to a guessed
   endpoint. Official service documentation and an owner-authorized, read-only
   capability check are required before using this route.
2. **MCP or CLI:** the app bundle has custom-MCP UI chunks, but no owner
   configuration or supported CLI was verified. Missing evidence is the
   configured server/command, auth scope, accepted input/output schema, task
   identity and polling/result semantics. Do not read its private app
   database or credentials to discover configuration. An owner-approved MCP
   endpoint would need documented auth, tool schemas, task IDs, status and
   result semantics before CowAgent can use it.
3. **Browser:** no separate Grok Bot web app or authenticated browser target was
   verified. CowAgent browser automation can serve a deliberately authenticated
   web console, but it does not prove that this desktop app exposes one
   ([CAPABILITY-MATRIX.md:11-13](CAPABILITY-MATRIX.md#L13)).
4. **Desktop:** this is the only verified local form of the target. The app UI
   was not opened and no task was submitted. Current evidence supports only
   human-attended use; no automated desktop control path has been established.

## Evidence limits and next check

The evidence is app metadata and non-secret packaged-manifest/path inspection.
No credentials, environment values, private browser profiles, app databases,
service processes, or live network endpoints were inspected. App authentication,
the enabled UI, owner configuration, supported MCP/CLI/API interfaces, and
task/result lifecycle remain unknown. Obtain the installed app's supported integration
documentation or a safe, read-only in-app capability view before selecting an
adapter. This audit did not have an app desktop-control backend in use. A real
desktop task would need exact action authorization and explicit computer-use capability; CowAgent's desktop bridge has no generic input or
screen-capture surface ([CAPABILITY-MATRIX.md:14](CAPABILITY-MATRIX.md#L14)).
