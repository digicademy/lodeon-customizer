# LODEON Customizer

LODEON Customizer is a standalone desktop app for connecting personal models to a compatible LODEON instance. The same download works with any instance that supports delegation. Python, the Core model runtime, the configuration resolver and the Package defaults ship inside the app.

## Start and configure

1. Extract the archive for your computer. Open **LODEON Customizer.app** on macOS, **LODEON Customizer.exe** on Windows, or **LODEON Customizer** on Linux. Keep the extracted application directory together.
2. The app opens its settings in your default browser. Enter the HTTPS address of your LODEON instance, including its deployment path, and choose **Save instance**. For example, enter `https://stories.example.org/lodeon/`. Browser authorization applies to the whole origin, including other paths on that origin.
3. The settings page shows the paths to your personal model configuration and credentials. Use **Quit Customizer** on that page to stop the app. Opening it again restores the saved configuration. Closing the browser tab leaves the app running.

The local settings address is `http://127.0.0.1:8765/`. The hosted **Settings → Connect personal models** action and the model editing form are planned. The current local form saves the instance address. Model definitions can already be edited in the displayed file.

| System | Personal files |
| --- | --- |
| Windows | `%LOCALAPPDATA%\LODEON Customizer\data\` |
| macOS | `~/Library/Application Support/LODEON Customizer/data/` |
| Linux | `$XDG_DATA_HOME/LODEON Customizer/data/`, defaulting to `~/.local/share/LODEON Customizer/data/` |

The first launch initializes `data/config.yml` from the packaged defaults. Zero models is a valid configuration. The local `instance` field holds the address. Define `assistant.modelProfiles`, `assistant.modelBrokers` and `assistant.defaultModel` using the same keys as any LODEON Package. For an already running Ollama on this computer use its ordinary loopback address. Save local settings or restart after editing the YAML. For keyed providers, put `NAME=value` in `data/models/.env` and reference `NAME` with `apiKeyEnv`. Keys are read at invocation and sent only to the configured provider. Keep the personal data directory private.

The hosted instance owns orchestration, tools, SPARQL and final synthesis. The browser relays a prepared model call and its result. Connecting a personal model gives the instance access to the public offer and call results. Provider keys remain local. Future capabilities such as Git transfer require separate authorization. [Protocol](PROTOCOL.md) · [Roadmap and browser evidence](ROADMAP.md)

## Configure a personal routing prompt

A broker that chooses among candidate models uses the prompt ID in its
`router.prompt` field. For example, for `router.prompt: choose-worker`,
add this entry to `data/runtime/prompts/registry.yml`. If you set
`assistant.promptRegistryFile`, use that path relative to `data/` instead.

```yaml
schemaVersion: 1
prompts:
  choose-worker:
    file: broker/choose-worker.md
    variables: [task, question, conversation_context, language, tools, evidence, candidates, objective]
```

Create `broker/choose-worker.md` beside that registry, for example:

```markdown
Select one model for {{task}}. The user's question is {{question}}.
Choose from {{candidates}} according to {{objective}}. Return only its ID.
```

Save the local settings or restart to load the files. Selecting that broker
for an operation shares this template with the instance. The model list shows
only public summaries. The router sees the rendered prompt and Core checks
its choice against the task's candidates. A broker using only fixed tasks
needs no local prompt file.

## Building and accepting a desktop release

For maintainers, from the Customizer checkout with native CPython 3.12:

```sh
python release/build.py --core /path/to/lodeon-core
```

The build installs the model runtime from that Core source, bundles its matching resolver and defaults, and archives a native application with PyInstaller. It then extracts **that archive** into a fresh directory, isolates the user profile, starts the executable, saves an instance, checks origin restrictions, restarts it, invokes a credentialed local HTTP provider fixture through the bundled runtime and quits. No external model or provider key is needed. Each passing build leaves one archive in `dist/`.

The GitLab pipeline resolves `LODEON_CORE_REF` to one commit for the entire release. It defaults to the coordinated Core feature branch during development. Set it to the intended Core revision for a release. The source job needs read access to Core. For a private checkout, an authorized masked read-only `LODEON_CORE_READ_TOKEN` can be supplied on the release runner. CI uses the runner tags below and checks that Python actually runs on the requested OS and architecture.

| Runner tag | Deliverable | Release host |
| --- | --- | --- |
| `windows-x86_64` | ZIP, containing the Windows application | Native Windows x64, signing certificate and SignTool |
| `macos-arm64` | ZIP, containing the macOS app | Native Apple Silicon, Developer ID and notarization |
| `macos-x86_64` | ZIP, containing the macOS app | Native Intel Mac, Developer ID and notarization |
| `linux-x86_64` | tar.gz, containing the Linux application | Native glibc Linux x64 with binutils |
| `linux-arm64` | tar.gz, containing the Linux application | Native glibc Linux arm64 with binutils |

Use shell runners with Python 3.12 available as `python`, port 8765 free, and standard OS build tools. Build on the oldest OS/glibc version intended for each published binary and record the actual runner OS and architecture. Tagged macOS builds need `MACOS_SIGN_IDENTITY` and `MACOS_NOTARY_PROFILE` in the signing keychain. Tagged Windows builds need `WINDOWS_SIGN_THUMBPRINT` and `WINDOWS_TIMESTAMP_URL`. Signing access belongs on protected release runners/tags. Development candidates can be built unsigned.

For each tag, the release reviewer opens the extracted candidates through Finder, Explorer and the Linux desktop as an ordinary user in a clean profile. Verify that the default browser opens, entering the instance works, restarting preserves personal data, and quitting releases the port. From the compatible hosted Settings UI, verify connect, one model call and disconnect in Safari on macOS, Edge on Windows and Firefox on Linux with normal browser security. Record OS version, architecture, browser version and results on the release ticket before confirming the blocking **desktop-review** job. A missing Settings client or a browser that blocks loopback leaves this review open. These user-visible checks complement the automated executable tests.

The five native jobs must all pass. The final job lists the checksums of their archives and the exact Core commit. Candidate archives remain attached to the native jobs for maintainer publication. A development build or a previous container release does not establish desktop release acceptance.
