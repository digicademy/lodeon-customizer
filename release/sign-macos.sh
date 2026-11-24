# Set up the native signing tools on the disposable, tag-only macOS runner.
set -euo pipefail
umask 077
: "${MACOS_SIGN_IDENTITY:?Missing Developer ID Application identity}"
keychain="$RUNNER_TEMP/release.keychain-db"
password=$(openssl rand -hex 32)
cert="$RUNNER_TEMP/signing.p12"
key="$RUNNER_TEMP/notary.p8"
trap 'rm -f "$cert" "$key"' EXIT
printf %s "$MACOS_CERTIFICATE_BASE64" | base64 -D > "$cert"
printf %s "$MACOS_NOTARY_KEY_BASE64" | base64 -D > "$key"
security create-keychain -p "$password" "$keychain"
security set-keychain-settings -lut 21600 "$keychain"
security unlock-keychain -p "$password" "$keychain"
security import "$cert" -k "$keychain" -P "$MACOS_CERTIFICATE_PASSWORD" -T /usr/bin/codesign
security set-key-partition-list -S apple-tool:,apple: -k "$password" "$keychain" >/dev/null
security list-keychains -d user -s "$keychain" "$HOME/Library/Keychains/login.keychain-db"
xcrun notarytool store-credentials customizer-release --key "$key" --key-id "$MACOS_NOTARY_KEY_ID" \
  --issuer "$MACOS_NOTARY_ISSUER"
printf 'MACOS_SIGN_IDENTITY=%s\nMACOS_NOTARY_PROFILE=customizer-release\n' "$MACOS_SIGN_IDENTITY" >> "$GITHUB_ENV"
