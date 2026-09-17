# Lantern CLI Launch Checklist

Use this checklist for a release candidate (RC) of the fictional open-source Lantern CLI. Replace every `Owner: [name/role]` placeholder before the launch gate. Check an item only when its stated evidence exists and its pass condition is satisfied.

## 1. Release metadata

- [ ] **Version and release identity**
  - Owner: [name/role]
  - Observable evidence: The version, release tag, target branch/commit, release date, and release-channel fields below are complete and mutually consistent.
  - Pass condition: No field is blank, and the version shown by the built CLI exactly matches the intended release tag.

| Field | Value |
| --- | --- |
| Version | `[version]` |
| Release tag | `[tag]` |
| Target commit | `[full commit SHA]` |
| Release channel | `[stable / prerelease]` |
| Planned release date/time | `[ISO 8601 timestamp and time zone]` |
| Release coordinator | `[name/role]` |
| Rollback owner | `[name/role]` |

- [ ] **Scope and change inventory**
  - Owner: [name/role]
  - Observable evidence: A finalized list links every user-visible change, bug fix, breaking change, dependency change, and deferred item to its issue or change record.
  - Pass condition: Every change in the target commit is categorized; breaking changes and deferred known issues are explicitly marked.

- [ ] **Artifact inventory and checksums**
  - Owner: [name/role]
  - Observable evidence: A manifest lists every intended package or binary, its platform and architecture, filename, size, and cryptographic checksum.
  - Pass condition: The inventory contains no unexpected or duplicate artifact, and each checksum matches a cleanly produced RC artifact.

## 2. Documentation readiness

- [ ] **Installation and upgrade instructions**
  - Owner: [name/role]
  - Observable evidence: Reviewed instructions cover fresh installation, upgrade, version verification, uninstallation, and platform-specific prerequisites.
  - Pass condition: A reviewer can follow each documented path from a clean supported environment without undocumented steps.

- [ ] **CLI reference and examples**
  - Owner: [name/role]
  - Observable evidence: Command, option, argument, environment-variable, configuration, exit-code, and example documentation reflects the RC behavior.
  - Pass condition: Every public command and option in the RC is documented, and all published examples complete with the documented result.

- [ ] **Release notes and migration guidance**
  - Owner: [name/role]
  - Observable evidence: Draft release notes identify highlights, fixes, breaking changes, deprecations, upgrade steps, compatibility notes, and known limitations.
  - Pass condition: A user of the previous supported version can determine whether the release affects them and how to migrate safely.

- [ ] **Support and contribution paths**
  - Owner: [name/role]
  - Observable evidence: Documentation identifies where to report bugs and security issues, how to request help, and which versions are supported.
  - Pass condition: All referenced paths are present in the release materials and contain clear submission expectations.

## 3. Cross-platform package checks

### macOS

- [ ] **Install, execute, upgrade, and uninstall on macOS**
  - Owner: [name/role]
  - Observable evidence: A test record identifies the macOS version and architecture and captures successful clean install, `lantern --version`, representative command execution, upgrade from the previous supported version, and uninstall.
  - Pass condition: Every operation exits as documented, the expected version runs without an unexpected security warning, and uninstall removes only Lantern-owned files.

- [ ] **macOS package integrity**
  - Owner: [name/role]
  - Observable evidence: The downloaded package checksum matches the release manifest; applicable signing or notarization status is recorded.
  - Pass condition: Integrity matches the manifest, and every claimed signing or notarization check succeeds.

### Windows

- [ ] **Install, execute, upgrade, and uninstall on Windows**
  - Owner: [name/role]
  - Observable evidence: A test record identifies the Windows version and architecture and captures successful clean install, `lantern --version`, representative command execution in supported shells, upgrade, and uninstall.
  - Pass condition: Every operation exits as documented, command discovery works after installation, and uninstall removes only Lantern-owned files.

- [ ] **Windows package integrity**
  - Owner: [name/role]
  - Observable evidence: The downloaded package checksum matches the release manifest; applicable signature and reputation-warning results are recorded.
  - Pass condition: Integrity matches the manifest, every claimed signature validates, and no unexplained blocking warning remains.

### Linux

- [ ] **Install, execute, upgrade, and uninstall on Linux**
  - Owner: [name/role]
  - Observable evidence: Test records identify each supported distribution, version, architecture, shell, and package format and capture clean install, `lantern --version`, representative command execution, upgrade, and uninstall.
  - Pass condition: All documented supported combinations pass, dependencies resolve as documented, and uninstall removes only Lantern-owned files.

- [ ] **Linux package integrity and permissions**
  - Owner: [name/role]
  - Observable evidence: Package checksums match the release manifest, installed paths and file permissions are recorded, and any repository metadata or package signatures are verified.
  - Pass condition: Integrity checks succeed, no installed file is unexpectedly writable or executable, and every claimed signature validates.

### Platform parity

- [ ] **Behavioral parity across supported platforms**
  - Owner: [name/role]
  - Observable evidence: A comparison record shows results for help, version, configuration discovery, paths containing spaces/non-ASCII characters, standard input/output, exit codes, and interruption handling on macOS, Windows, and Linux.
  - Pass condition: Behavior matches the documented contract on every supported platform, or each intentional difference is documented.

## 4. Security and secret scanning

- [ ] **Source, history, artifact, and documentation secret scan**
  - Owner: [name/role]
  - Observable evidence: Dated scan reports cover the target source tree, relevant version-control history, generated release artifacts, examples, fixtures, logs, and documentation.
  - Pass condition: No active credential, token, private key, or sensitive endpoint remains; every alert is resolved or documented as a reviewed false positive.

- [ ] **Dependency and vulnerability review**
  - Owner: [name/role]
  - Observable evidence: A dependency inventory and dated vulnerability results include direct and transitive production dependencies, with disposition for every finding.
  - Pass condition: No unresolved vulnerability exceeds the project's written release threshold, and accepted exceptions have an owner, rationale, and review date.

- [ ] **Artifact provenance and least-privilege behavior**
  - Owner: [name/role]
  - Observable evidence: The build source and target commit are recorded; runtime tests show requested permissions, network access, filesystem writes, and subprocess execution for representative commands.
  - Pass condition: Artifacts are traceable to the target commit, and Lantern performs no undocumented privileged, network, filesystem, or subprocess action.

- [ ] **Security reporting instructions**
  - Owner: [name/role]
  - Observable evidence: The release materials contain a private vulnerability-reporting path, expected response information, and supported-version scope.
  - Pass condition: A reporter can identify the correct confidential reporting process without using a public issue.

## 5. Accessibility of terminal output

- [ ] **Color-independent meaning and contrast review**
  - Owner: [name/role]
  - Observable evidence: Captured output for success, warning, error, prompt, progress, and diff-like states is reviewed in color, with color disabled, and under common light and dark terminal themes.
  - Pass condition: Meaning never depends on color alone, text remains legible in tested themes, and a documented no-color mode or convention works consistently.

- [ ] **Screen-reader and plain-text usability**
  - Owner: [name/role]
  - Observable evidence: A test record captures representative output through a screen reader or linear text review, including help, errors, prompts, tables, and progress updates.
  - Pass condition: Reading order is coherent; labels precede values; errors identify the problem and next action; decorative characters do not obscure meaning.

- [ ] **Non-interactive and reduced-motion behavior**
  - Owner: [name/role]
  - Observable evidence: Tests capture output when redirected to a file or pipe, in a non-interactive terminal, with animations/spinners disabled, and at narrow terminal widths.
  - Pass condition: No essential information is lost, output does not hang or corrupt logs, and wrapping or fallback formatting remains understandable.

- [ ] **Help language and error clarity**
  - Owner: [name/role]
  - Observable evidence: A review log covers top-level help, command help, invalid input, missing configuration, permission failure, and network failure messages.
  - Pass condition: Messages use plain language, distinguish warnings from errors, state actionable recovery steps, and return documented exit codes.

## 6. Rollback readiness

- [ ] **Rollback trigger and authority**
  - Owner: [name/role]
  - Observable evidence: Written triggers define when to hold, withdraw, deprecate, or replace a release, and identify who can authorize each action.
  - Pass condition: Each trigger is observable, each action has one accountable decision owner, and the escalation path is explicit.

- [ ] **Previous-version recovery**
  - Owner: [name/role]
  - Observable evidence: A rehearsal record shows installation or restoration of the previous supported version on macOS, Windows, and Linux after installing the RC.
  - Pass condition: The previous version becomes runnable on all supported platforms without loss of user data or undocumented manual repair.

- [ ] **Configuration and data compatibility**
  - Owner: [name/role]
  - Observable evidence: Backup, migration, and downgrade tests use representative configuration and data, including malformed and partially migrated states.
  - Pass condition: Downgrade preserves or restores user data and configuration, or irreversible changes are explicitly gated, backed up, and documented before upgrade.

- [ ] **Rollback procedure and verification**
  - Owner: [name/role]
  - Observable evidence: A timed runbook records exact steps to stop distribution, restore or point users to the last good version, communicate status, verify package endpoints, and preserve incident evidence.
  - Pass condition: The rehearsal completes within `[maximum rollback time]`, verification confirms only the intended version is offered, and follow-up ownership is assigned.

## 7. Announcement draft review

- [ ] **Announcement accuracy and completeness**
  - Owner: [name/role]
  - Observable evidence: The final draft is checked against the release notes and artifact inventory and includes the version, highlights, upgrade path, breaking changes, known limitations, support path, and release link placeholders.
  - Pass condition: Every factual claim maps to verified release evidence, no unsupported compatibility or security claim remains, and all placeholders are intentionally ready for release-time substitution.

- [ ] **Audience, clarity, and accessibility review**
  - Owner: [name/role]
  - Observable evidence: A reviewer records feedback on plain language, heading/link clarity, concise alternative text for any visual, and distinction between required actions and optional features.
  - Pass condition: Blocking feedback is resolved, links have descriptive labels, and readers can identify whether and how they must act.

- [ ] **Publication plan approval**
  - Owner: [name/role]
  - Observable evidence: An approved matrix lists each intended channel, draft/version owner, scheduled order, final approver, and correction or withdrawal procedure.
  - Pass condition: Every intended channel has an owner and approved copy; no announcement has been published before the final gate.

## 8. Final release gate

- [ ] **Gate evidence packet complete**
  - Owner: [name/role]
  - Observable evidence: All checklist items link to their final evidence; every exception includes severity, impact, mitigation, owner, and review date.
  - Pass condition: No required item lacks evidence or an approved exception, and no Stop condition is open.

| Decision | Select one | Required condition | Authorized by | Evidence recorded at |
| --- | --- | --- | --- | --- |
| **GO** | [ ] | Every required item passes; no release-blocking defect or security issue is open; rollback is rehearsed; announcement is approved. | `[name/role]` | `[link/path]` |
| **HOLD** | [ ] | A bounded, recoverable gap remains; an owner, corrective action, and reassessment time are recorded; nothing is published or promoted meanwhile. | `[name/role]` | `[link/path]` |
| **STOP** | [ ] | A secret exposure, uncontained security issue, artifact-integrity failure, data-loss risk, failed rollback, unsupported-platform failure, or materially misleading release claim exists. | `[name/role]` | `[link/path]` |

**Gate timestamp:** `[ISO 8601 timestamp and time zone]`
**Decision rationale:** `[concise rationale]`
**Next review, if HOLD:** `[ISO 8601 timestamp and time zone]`
**Sign-off:** `[name/role]`

## Known limitations

- This checklist is project-agnostic and does not define Lantern CLI's actual supported operating-system versions, architectures, package managers, release-risk thresholds, or signing requirements.
- It verifies observable release evidence, not the absence of all defects or vulnerabilities.
- Screen-reader behavior, terminal rendering, package trust prompts, and rollback behavior vary by environment; representative tests do not prove universal compatibility.
- Owner, evidence-location, timing, and threshold placeholders must be resolved by the project before a **GO** decision.
