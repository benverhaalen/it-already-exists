# Acquire Android reference artifacts

Resolve a suggested product to its exact package, publisher, requested release
and architecture before acquisition. Name similarity is insufficient. Prefer a
user-supplied archive or publisher source when already available; retain an
immutable reference. A provider's metadata is evidence to check, not proof of
identity, completeness or safety.

## Optional APKCube route

[APKCube documents](https://apkcube.com/docs/api) catalogue search, versions,
architecture variants, checksums/signing metadata and short-lived download URLs.
Use its supported API or MCP rather than catalogue scraping. Its
[terms](https://apkcube.com/terms) prohibit scraping and bulk downloading.
Availability, paid-app delivery, removals and region restrictions limit coverage;
this is not an “any APK” guarantee. Refresh service contracts and charges before
using an established credit budget. Do not purchase credits automatically.

The bundled `scripts/reference_provider.py` offers a narrow ordinary-build route:

1. `apk-search "PRODUCT NAME" --output PRIVATE_SEARCH.json`; inspect package and
   publisher candidates against the user's intended reference.
2. `apk-versions EXACT_PACKAGE --output PRIVATE_VERSIONS.json`; choose the explicit
   build by release, architecture, minimum SDK, size and format. Do not silently
   substitute latest or ARM32 when another build was requested.
3. `apk-download EXACT_PACKAGE --apk-id SELECTED_ID --output PRIVATE_INPUT.apk
   --receipt PRIVATE_RECEIPT.json`; use the actual format's extension for XAPK/APKS.

Invoke these as `python scripts/reference_provider.py …` with `APKCUBE_API_KEY`
in the environment. Each command makes one API call. Search and version listing
are charged too. Output files must be new. The ordinary downloader checks returned
package/build identity, bounded size and SHA-256, refuses redirects, accepts only
the documented HTTPS R2 storage origin and sends no API credential to storage.
It withholds signed URLs from receipts and publishes bytes only after verification.
Unexpected download origins require inspection and a reviewed adapter change.

Run the existing `scripts/apk_intake.py` on the acquired artifact. Independently
check manifest identity, version, split completeness, native ABIs and signing
certificates with qualified Android tools. Provider hash agreement establishes
byte integrity against its response, not developer authenticity. Preserve the
certificate's independently established comparison source. Do not execute or
install the artifact during acquisition.

The helper does not request fetches, generate variants, resolve ambiguous names,
verify signatures, install applications or bypass availability restrictions.
For those cases inspect the documented API/MCP, retain request receipts and use
bounded status polling rather than repeating charged POSTs. An unavailable build
is an acquisition gap, not permission to swap the reference. Keep archives and
receipts private; publish only reusable mechanisms and qualified authored fixtures.
Live provider acquisition remains unqualified until demonstrated with configured
credentials and independently checked output.
