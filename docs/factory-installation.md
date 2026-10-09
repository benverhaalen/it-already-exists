# Install the reference-driven factory

Use the native Claude Code or Codex conversation. The installed skill supplies
the method and local helpers. It does not replace either host, change the active
model, or start an inference service. Python 3.10 or later and POSIX are required.

From this checkout, run:

```sh
python3 tools/install_factory.py install --enable-policy
python3 tools/install_factory.py doctor
```

The installer stages the complete skill, then changes these discovery entries:

- Codex: `~/.agents/skills/reference-driven-development`
- Claude Code: `~/.claude/skills/reference-driven-development`

`--enable-policy` adds one short owned block to `~/.codex/AGENTS.md` and
`~/.claude/CLAUDE.md`. It selects the method for substantial product or artifact
work, including work where the user has not supplied references.
Existing instructions remain outside that block. Exact prior bytes are backed up
privately. Omit the flag for skill-only installation. It installs no hooks or
second Jev server and changes no host permissions or model settings.

Refresh the native skill inventory or start a new conversation. Use
`$reference-driven-development` in Codex, or ask Claude Code to use the
`reference-driven-development` skill. Discovery, invocation, application, and
accepted product behavior are separate checks. Doctor reports the first two as
unproved until a native entry exercise supplies evidence; file installation alone
does not establish current-session activation.

## Release identity and ownership

Releases live at
`~/.local/share/it-already-exists/factory/releases/<archive-sha256>/`.
Each retains the deterministic capsule, manifest, receipt, and extracted skill.
All supporting scripts, references, fixtures, and selected upstream procedures
travel together. Original upstream bytes, Git blob hashes, source revision and
license are checked. Upstream `SKILL.md` files are retained as `SKILL.md.source`
so they do not become accidental nested discovery entries.

The authored export has an explicit reviewed filename inventory. Unknown new
references or scripts are rejected; every retained module and selected fixture
license is required. Cold copied factory, procedure and project-control CLI
imports and the actual source selector are checked before activation. These
checks do not establish native invocation or product quality.

Hashes identify content; they are not signatures or legal clearance. Staged
files are read-only by convention. Doctor compares the entire inventory,
including added files or directories, missing resources and redirected links.
It reports drift and does not repair it silently.

Doctor checks the complete reviewed inventory for the installed release's edition,
not the newest source edition. Adding a helper does not corrupt an older release.
It reports both editions; a valid older release does not contain newer helpers.
Untagged early capsules require an exact retained inventory. Source packaging
still requires every current export, and unknown editions or incomplete closures
are rejected. New archive staging requires the current edition; historical
inspection does not relax initial admission.

An absent discovery entry is safe to create. A symlink whose literal target is
this checkout's exact canonical skill directory can be migrated; its original
target is retained. Arbitrary symlinks, directories and files are collisions.
The installer stops before changing discovery entries. It never merges an
unknown personal skill folder into a release.

Keep personal preferences outside immutable releases. Existing native global
instructions remain canonical. The optional private overlay location
`~/.config/it-already-exists/factory/` is reported, never automatically copied,
loaded, packaged, or modified by this installer. Project state and transcripts
remain in their existing homes. Installation metadata is not another task store.

## Stage, update and recover

Stage without activating:

```sh
python3 tools/install_factory.py stage
python3 tools/install_factory.py activate <release-sha256> --enable-policy
```

Run `install` again after reviewing source changes. The new source produces a
new release identity. The previous release stays readable. Existing pinned
tasks can continue using its resolved root; the installer does not restart
sessions or promise that a host which rereads a mutable discovery path will
stay pinned. Qualify each host's actual consuming path before making that claim.

Undo the last activation, or remove owned entries:

```sh
python3 tools/install_factory.py rollback
python3 tools/install_factory.py remove
```

Rollback restores the preceding pointers and policy state. Removal restores
the original source symlinks, if migrated, or removes entries created by this
installer. Both retain every release and private backup. They refuse changed
owned pointers or modified managed blocks. Edits outside a managed policy block
are preserved. An unchanged global file can be restored byte-for-byte.
Its prior permission mode is preserved during these changes.

Maintenance is serialized under an installer-owned lock. A durable intent
precedes changes across the two host roots. If interrupted, doctor reports
`pending_recovery`; inspect the paths, then choose:

```sh
python3 tools/install_factory.py recover complete
python3 tools/install_factory.py recover rollback
```

Recovery accepts only the recorded before/after pointers and owned policy
blocks. An unexpected change stops reconciliation. The lock coordinates this
installer; it does not fence unrelated editors or native host actions. Atomic
pointer/file replacement and last-moment comparisons have that bounded scope.

Installation-state schema 1 is supported. Unknown schemas are preserved and
rejected. The installer performs no migration of project records or native
session state; rollback cannot imply compatibility with a newer product schema.

## Portable archive and isolated qualification

The same reviewed closure can be distributed as a deterministic archive:

```sh
python3 tools/package_rdd.py --output /path/to/new-rdd.zip
python3 tools/install_factory.py install --archive /path/to/new-rdd.zip
```

Use the installer from this repository. It validates the archive before
extraction and rejects traversal, duplicate entries, unreviewed paths, incomplete
closure, altered source or mismatched manifests. Portable packaging retains no
installation registry, global instructions, account information or private logs.

Qualify installation outside your real home:

```sh
python3 tools/install_factory.py --home /path/to/temporary-home install
python3 tools/install_factory.py --home /path/to/temporary-home doctor
python3 -m unittest discover -s tests -p test_factory_installation.py -v
```

Doctor makes no model calls. It checks release content, owned pointers, policy,
available native CLI paths, platform and maintenance state. It distinguishes
those checks from native skill discovery, actual invocation, applied methods,
domain tooling, independent product acceptance and measured speed/cost/fidelity.
Missing host or domain capabilities need scoped qualification; installation
does not make every architectural component operational.
