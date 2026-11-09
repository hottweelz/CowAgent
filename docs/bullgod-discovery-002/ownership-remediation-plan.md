# Ownership remediation proposal — not authorized or executed

The approved root mode change is complete: `0775` became `0755`. The APFS volume
still ignores ownership. Final trusted discovery therefore rejects it before
registry loading or selection. This proposal concerns a different, volume-wide
setting and requires separate authorization.

## Read-only impact evidence

The [metadata assessment](ownership-impact.json) found 20 top-level directories
and one file. Four relevant directory roles (repository, runtime data, runtime
workspace and shared Codex data) have current read/write/search access. Reported
owner/group IDs do not establish stored ownership while ownership is ignored.

The current-user process inventory found 173 processes with a working directory
or open file on this volume, including the original CowAgent process, Codex and
ChatGPT. Roles overlap. This is a point-in-time dependency inventory, not a list
of 173 independently running tasks. Eleven open-file observations and two
working-directory observations were unavailable. Other users and privileged
processes were not inspected. No recursive volume scan, file contents, private
memory, process arguments or environment were read.

The evidence establishes a wider impact than this repository. It does **not**
prove that enforcing stored ownership will preserve every application's access.

## Documented operation and limits

The installed Apple `diskutil(8)` manual describes `enableOwnership` and
`disableOwnership` as root operations on the current OS's per-volume ownership
database. The policy persists across eject, remount and reboot on that OS; it is
not stored on the target volume. The documented operation applies existing
on-disk owner/group IDs, not a recursive owner rewrite.

`mount(8)` describes ownership-ignored presentation. The SDK `getattrlist(2)`
owner/group fields correspond to the `stat` fields, so those observations do not
provide an independent stored-owner audit. Python `statvfs` also omits the native
ownership-ignore flag; the reviewed discovery guard uses `statfs64`/`fstatfs64`.

The read documentation does not establish whether the current mount updates
immediately or needs a remount. A remount or service restart is outside the
proposed authorization. Disabling ownership can restore the prior policy, but
cannot undo file changes made by active applications during an enabled interval.

## Proposed bounded operation, only after explicit approval

1. Revalidate the named volume's identity, mounted device, mode and ownership
   flag. Capture current CowAgent health, profile/configuration hashes and known
   path access. Stop if the target differs from the reviewed volume.
2. With administrator authorization, run the documented operation against that
   verified device: `sudo /usr/sbin/diskutil enableOwnership <verified-device>`.
3. Check both `diskutil info` and native mount flags. Check existing access and
   CowAgent health before any discovery read. If the current mount remains
   ownership-ignored, do not remount it to force success.
4. If access/health changes, the flag does not take effect, or trusted path
   checks still fail, restore the prior policy using
   `sudo /usr/sbin/diskutil disableOwnership <same-verified-device>`, verify it,
   and report the result. Do not repair file owners, modes, profiles or memories.
5. Only if those checks pass, run the existing guarded read-only acceptance
   against actual identities and retained authority. Preserve expired approvals;
   do not contact models, create tasks, replay task IDs or start runtimes.
6. Record the actual result and before/after metadata. A storage change cannot
   turn expired or absent capability proof into current authority.

Administrator access and the volume-wide setting change are not covered by the
earlier root-mode approval. No operation in this proposal has been performed.
Keeping the live gate blocked is the safe alternative while this decision is
pending. Application source and previously validated CI are unchanged.
