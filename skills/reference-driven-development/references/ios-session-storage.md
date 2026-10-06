# Qualify native iOS session storage

Separate service authentication, native session persistence and the client wire
contract. A server response can be correct while Keychain access fails or the
compiled client never receives the current-user initialization value.

Use the native SDK's local service mode when supported. Qualify creation,
profile update, sign-out, sign-in, failed credentials and cleanup against that
controlled authority. Keep tokens and credentials out of logs and receipts.

Add `scripts/fixtures/keychain/KeychainControl.swift` to an owned iOS application
and call `RDDQualifyKeychain()` in an opt-in control. It creates one unique item
in the app's default group, reads and compares its value, then deletes it. The
fixture logs status codes only. It does not test shared groups, access after
restart, accessibility while locked, migration or physical-device signing.
It passed in an iOS 26.3 ARM64 Simulator application alongside native Firebase
Auth 12.19.0 local account controls. This is bounded fixture evidence.

If an operation reports `errSecMissingEntitlement`, inspect the built and
installed artifact and its actual storage operation. Do not assume that adding
an entitlement to a source file makes it available at runtime. Configure
entitlements on the app target; a command-line setting applied to every package
target can also affect dependencies.

For Simulator builds, use Xcode's supported build/signing path. Xcode can embed
simulated XML and DER entitlements in `__TEXT,__entitlements` and
`__TEXT,__ents_der`. Applying restricted device entitlements directly to an
ad-hoc signature can instead prevent macOS from launching the executable.
Inspect host launch logs separately from simulator application logs. Do not
publish or reuse a developer identity or assume simulator permission proves
physical-device entitlement availability.

After native sign-in passes, verify the compiled client's initial session,
state listener, profile prerequisites and complete journey. Forward the actual
upstream plugin registry constants through Core initialization rather than
handcrafting user dictionaries or returning an empty map. Keep fast persona
setup separate from qualification of the original credential-entry flow.

Primary implementation references:

- [Firebase Apple SDK](https://github.com/firebase/firebase-ios-sdk).
- [FlutterFire plugin registry](https://github.com/firebase/flutterfire/blob/main/packages/firebase_core/firebase_core/ios/firebase_core/Sources/firebase_core/FLTFirebasePluginRegistry.m).
- [Apple Keychain entitlement](https://developer.apple.com/documentation/bundleresources/entitlements/keychain-access-groups).
- [Simulator entitlement embedding](https://github.com/madsmtm/embed_entitlements).
