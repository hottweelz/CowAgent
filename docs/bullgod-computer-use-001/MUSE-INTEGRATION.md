# Muse integration discovery

## Result

No usable external task interface was verified. The installed `/Applications/Muse.app`
identifies itself as Muse, bundle `com.meta.endo`, version `12.1`, signed by Meta
Platforms, Inc. Its `Info.plist` describes assistant actions such as sending
messages and email, managing notes, and organizing an inbox. This supports the
owner's identification of it as an assistant product; it does not define an
external task API or submission contract. The only owner project with Muse in
its name is `/Volumes/Predator SSD GM7 1TB/Projects/Muse Test`.
That workspace describes an optional design-skill evaluation, and says its
integration scope is still to be confirmed (`Muse Test/README.md:3-10`).
Its nested `save-the-polyesters` directory is a static Next.js parody website,
not the Muse app source or an integration package.

`/Users/jamestylee/Projects` does not exist on this host. The bounded search of
`/Volumes/Predator SSD GM7 1TB/Projects`, `/Applications`, and the user's
Applications folder found no other Muse-named project or app. The app's plist
contains scheme handlers for `hatch` and `endo-window`, but no MCP or CLI
manifest was found in the inspected bundle metadata. No external API endpoint,
request schema, authentication handoff, task lookup key, task status, logs, or
result retrieval contract is established by these findings.

## Integration route order

1. **Authenticated service interface:** none identified. The app's bundle
   metadata does not expose an external API contract. Do not guess a Meta
   endpoint or treat the CowAgent web API as a Muse API.
2. **MCP or CLI:** no supported interface or owner configuration was identified.
   The inspected plist has URL schemes, not a documented command or MCP server.
   `Muse Test` is design-skill work; its docs do not define a Muse task protocol.
3. **Browser:** no Muse web task interface was verified. CowAgent's own browser
   path is suitable for web-console work only when the target app and deliberate
   login are known ([CAPABILITY-MATRIX.md:11-13](CAPABILITY-MATRIX.md#L11)).
4. **Desktop:** Meta Muse is an installed desktop app, but its UI was not opened.
   No task submission or result-reading path was inspected. Treat it as a
   human-attended desktop target only until a documented interface is found.

## Evidence limits and next check

The installed app's bundle metadata is local evidence only. No app UI, account,
private app data, browser profile, or credential store was inspected. Therefore
there is no evidence of authenticated state, available tasks, task IDs, status,
logs, or results. The next useful check is the installed app's supported integration documentation
or a bounded owner-visible capability view for task submission and result lookup.
Do not build an adapter from the product name alone.
