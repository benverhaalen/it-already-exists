# Surfaces and evidence

Scope recorded September 13, 2026. This is a proposed capability map, not a list of implemented adapters or a claim that every application exposes every channel.

An input is how an investigation starts. A surface is a part of the target that can be observed or interrogated. One input can expose many surfaces, and several inputs can provide evidence about the same target. In `it-already-exists`, the default purpose is to adapt useful properties into the user's product; faithful reconstruction is a separately selected mode.

## Inputs the project should eventually accept

| Target/input | Evidence to seek | Useful reference output | Main limit |
| --- | --- | --- | --- |
| Website or web app: URL and optionally an authenticated session | Screenshots, DOM, layout and styles, accessibility, actions, client assets, network and persistence behavior | Responsive design specification, component states, navigation and workflow tests | Browser access exposes the client and observed responses, not complete server implementation or every account state |
| Installed Mac app, `.app`, `.dmg`, or `.pkg` | Windows and menus, accessibility, shortcuts, interaction recordings, bundle resources, document behavior; internals where in scope | Desktop interaction specification, window behavior, menu and shortcut map, resource inventory | Installer contents and a running app provide different evidence; some controls expose little accessibility information |
| Windows app: installed application, `.exe`, `.msi`, or package | UI Automation, screenshots, keyboard and pointer actions, resources, saved files; binary/runtime inspection where available | Desktop workflow and visual reference, input/output and integration contracts | An EXE can be an installer rather than the actual app; runtime fidelity requires a suitable Windows environment |
| Linux application or package | Accessibility through AT-SPI where exposed, window recordings, CLI interfaces, package assets, filesystem behavior | Desktop or service specification and repeatable workflows | Toolkit and display environment affect observability and appearance |
| Android app: APK, required split APKs, or installed app | Manifest, resources, framework/native clues, UI hierarchy, gestures, lifecycle, network and saved-state observations | Screen atlas, feature contracts, interaction and persistence tests | A package may need additional splits, services, account state, or device features before it is a usable reference |
| iOS/iPadOS app: installed app or available build/package | UI automation where supported, recordings, accessibility, gestures, lifecycle, available resources | Mobile interaction, motion, layout, and behavior specification | Build format, signing, device access, and automation availability constrain what can run and be inspected |
| Electron or another hybrid application | Combine desktop observation with web/runtime and package inspection where exposed | Links between web components and native menus, files, notifications, and windows | This is a framework classification across operating systems; do not assume all hybrid applications expose browser debugging |
| CLI tool, service, library, or plugin | Inputs, outputs, errors, exit codes, streams, files and side effects; source or binary interfaces where available | Executable compatibility cases and behavioral contract, even with no graphical UI | Timing, environment and hidden dependencies can change behavior; finite examples do not identify every algorithm |
| API or network protocol | Requests, responses, schemas, streaming events, ordering, reconnects and error behavior | API contract, protocol state model, test fixtures or a compatible simulator | Captured traffic describes exercised paths; replayed responses do not recreate arbitrary server logic |
| Document, project file, export, database sample, or asset bundle | Structure, relationships, metadata, round trips, rendered output and changes after controlled edits | File-format mapping, importer/exporter tests, template or design reference | One file rarely reveals the full format or every supported feature |
| Screenshots, video, demo recordings, manuals, or design files | Visible layout, text, motion, demonstrated sequences, documented rules | Annotated reference atlas, measurements and hypotheses to verify | Passive evidence cannot answer a new interactive question; documentation can differ from deployed behavior |
| Games, canvas applications, creative tools, audio software, or 3D software | Frames over time, audio, gestures, scene/output changes, project files and exposed APIs | Motion, rendering, interaction or signal-processing reference | Pixels and audio may carry information missing from accessibility trees; performance and hardware are part of the comparison |
| Embedded device or physical interface | Camera/audio observations, controls, display states, accessible ports, protocol traces and available firmware | Interface and protocol specification, compatibility tests or a behavioral simulator | Requires device-specific acquisition and measurement; exact physical replication is a separate engineering problem |

Platform observation foundations are documented by [Chrome DOMSnapshot](https://chromedevtools.github.io/devtools-protocol/tot/DOMSnapshot/), [Apple AXUIElement](https://developer.apple.com/documentation/applicationservices/axuielement), [Windows UI Automation](https://learn.microsoft.com/en-us/windows/win32/winauto/entry-uiautocore-overview), [Linux AT-SPI](https://gnome.pages.gitlab.gnome.org/at-spi2-core/libatspi/), [Android UI Automator](https://developer.android.com/training/testing/other-components/ui-automator), and [Apple XCUIAutomation](https://developer.apple.com/documentation/XCUIAutomation). Package inspection examples include [Android apkanalyzer](https://developer.android.com/tools/apkanalyzer) and [Electron ASAR](https://www.electronjs.org/docs/latest/tutorial/asar-archives). These sources establish individual mechanisms, not an end-to-end reconstruction system.

## Evidence channels shared across inputs

1. Appearance: geometry, typography, assets, colors, shadows, motion, audio, and rendering over time.
2. Interaction: clicks, typing, gestures, focus, shortcuts, drag/drop, navigation, menus, and system dialogs.
3. State and history: what changes after earlier actions, reload, restart, a second session, permission changes, or delayed completion.
4. Data and communication: requests, responses, subscriptions, local storage, databases, imports, exports, and files.
5. Implementation: source, package resources, symbols, bytecode, native code, dependencies, and runtime traces where inspection is allowed and technically available.
6. Environment: platform version, viewport, scale, input device, locale, theme, account role, connectivity, and hardware.
7. External effects: notifications, clipboard, opened links, documents written, audio produced, and changes visible to another client.

No channel substitutes for all the others. The same screenshot can conceal different saved state. A function name can suggest a feature without showing when users reach it. A successful request does not prove that the UI or persisted result is correct.

The proposed AOI contribution is a continuous observation layer: track relevant regions and changes while an agent is planning or executing a sequence. Pair it with native events and structured observations where available. It cannot reveal hidden server state, inaccessible code, or transitions that were never observed. Its latency, capture coverage and cost benefits still need measurement in this project.

## Combining evidence without conflating products

A Kalshi APK, a session with its Android app, its website and a screen recording can all belong to one investigation. Keep their platform, version, time, role and environment attached to every claim. A behavior found on the website is a hypothesis for the Android app until checked there. Conflicting evidence should remain visible.

## Outputs by purpose

| Purpose | Appropriate deliverable |
| --- | --- |
| Reference one property | Measurements, annotated evidence, interaction rules and the reason the property works |
| Reuse a design or interaction pattern | A portable specification with original-specific details identified and adaptation choices explicit |
| Reproduce a component or workflow | Preconditions, action sequence, visual and behavioral expectations, edge cases and regression checks |
| Reconstruct an application | Versioned app specification, implementation, original-versus-candidate comparisons, tested coverage and unresolved differences |

The system should ask what property matters: appearance, behavior, motion, performance, compatibility, architecture, or some combination. Recreating the same internal architecture is unnecessary when the actual objective is to reference a visible interaction.

## Access workflows

In source-assisted work, implementation evidence can inform the builder and direct reuse can be compared with regeneration. In strict clean-room work, permitted observation methods are declared for the analyst, and the builder receives only approved specifications, examples, tests and explicitly permitted assets. Merely putting files in different directories is not an enforced information boundary.

For either workflow, report observed, extracted, inferred, contradicted, and unknown claims distinctly. Claiming no detected difference requires a declared comparison scope, environment and test set; it does not establish universal equivalence.
