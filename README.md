# LODEON Customizer

Use your own model in the Assistant of a LODEON instance you already use. The Customizer runs on your computer. It includes its runtime and works with any instance that permits personal models for your session.

## Get the app and connect your first model

1. In the Assistant, open **Settings → Connect personal models**. Choose **Download LODEON Customizer** to open the public [GitLab Releases](https://gitlab.rlp.net/adwmainz/digicademy/lodeon/lodeon-customizer/-/releases) page in a new tab. **Setup and user guide** opens this README. If the menu entry is missing, check with your instance operator whether personal models are enabled for your session.
2. In the newest release, choose the download for your computer from the table below. Extract the entire archive to a folder on your computer and open the app. Keep the extracted files together.
3. The app opens a **local settings page** in your default browser. Enter the HTTPS address of the LODEON instance you use, including its deployment path, and choose **Save instance**. For example, enter `https://stories.example.org/lodeon/`. This authorizes pages on that browser origin, including other paths on it.
4. On first launch the model list is empty. Add your first model in the local file shown on the settings page using [Configure a personal model](#configure-a-personal-model) below. You do this once per model.
5. Return to the **original LODEON tab**, choose **Connect** in the same dialog and allow local-network access if your browser asks. Close the dialog and select the model marked **Personal**. If you configured a personal default, it is already selected. Ask your question as usual.

| Your computer | Release download | Open after extraction |
| --- | --- | --- |
| Windows with an Intel or AMD 64-bit processor | **Windows · x64** (ZIP) | `LODEON Customizer.exe` |
| Mac with an Apple M-series chip | **macOS · Apple silicon** (ZIP) | `LODEON Customizer.app` |
| Mac with an Intel processor | **macOS · Intel** (ZIP) | `LODEON Customizer.app` |
| Linux with glibc on an Intel or AMD 64-bit processor | **Linux · x64** (tar.gz) | `LODEON Customizer` |
| Linux with glibc on a 64-bit ARM processor | **Linux · ARM64** (tar.gz) | `LODEON Customizer` |

On a Mac, **Apple menu → About This Mac** identifies the chip. A release lists the five applications separately from GitLab's automatic source archives. An empty Releases page means a desktop release has yet to be published.

## Configure a personal model

The settings page shows the exact path to your personal `config.yml`. For example, to use a model already installed in Ollama on the same computer, open that file in a text editor. Keep the saved `instance` line. In a fresh configuration, replace the empty `assistant` section with the following. For an existing setup, add the profile under its existing `modelProfiles` mapping. Replace `gemma4:12b` with the exact name of your installed model.

```yaml
assistant:
  defaultModel: local-ollama
  modelProfiles:
    local-ollama:
      label: My Ollama
      provider: ollama
      model: gemma4:12b
      baseURL: http://127.0.0.1:11434
      promptCaching: {enabled: false, retention: default}
```

Save the file, reload the local settings page and choose **Save instance** to apply it, or quit and reopen the app. For a provider that requires a key, set `apiKeyEnv` in its profile to a name such as `PERSONAL_API_KEY` and put `PERSONAL_API_KEY=your-key` in the displayed `models/.env` file. The app reads the key on each invocation and sends it only to that provider. Define additional profiles, brokers and the default in YAML. The local page lets you change an existing model's temperature directly. Clear it to restore the configured default.

| System | Personal files |
| --- | --- |
| Windows | `%LOCALAPPDATA%\LODEON Customizer\data\` |
| macOS | `~/Library/Application Support/LODEON Customizer/data/` |
| Linux | `$XDG_DATA_HOME/LODEON Customizer/data/`, defaulting to `~/.local/share/LODEON Customizer/data/` |

## Reconnect, disconnect or quit

Keep the app running while using Chat, **Check Tools** or suggested questions with a personal model. Each LODEON tab connects separately. After an Editor reload, a local configuration change or an app restart, return to **Settings → Connect personal models** and reconnect. Use **Disconnect** first if the tab still shows a connection. The model selector and **Model information** show personal and instance targets in alphabetical order.

If **Connect** fails, open the Customizer again. Its settings page is at `http://127.0.0.1:8765/`. Check the saved instance address and the browser's local-network permission. If the connection succeeds but the selector has no personal model, check that you added a profile and applied the file as described above.

Choose **Disconnect** to release just the current tab. Choose **Quit Customizer** on the local settings page to stop the app. Closing the local settings tab leaves it running. Your local configuration is available the next time you start it.

The hosted instance owns orchestration, tools, SPARQL and final synthesis. The connected tab passes prepared model calls to the Customizer and returns their results to Core. A mixed broker uses the same connection for its local workers. Core calls its authorized instance workers directly. Provider keys remain local. Future capabilities such as Git transfer require separate authorization. [Protocol](PROTOCOL.md) · [Roadmap and browser evidence](ROADMAP.md)

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

For each tag, open **Build → Pipelines** in the Customizer project and select the tag pipeline. Each **native-app** job provides a candidate archive for its platform under its job artifacts. Open the extracted candidates through Finder, Explorer and the Linux desktop as an ordinary user in a clean profile. Verify that the default browser opens, entering the instance works, restarting preserves personal data, and quitting releases the port. From the compatible hosted Settings UI, verify connect, one model call and disconnect in Safari on macOS, Edge on Windows and Firefox on Linux with normal browser security. Record OS version, architecture, browser version and results on the release ticket before confirming the blocking **desktop-review** job.

Use a release tag matching the version in `pyproject.toml`, for example `v0.2.0` for version `0.2.0`. After the five native jobs pass and a maintainer approves **desktop-review**, **accepted-archives** uploads the five reviewed archives, `SHA256SUMS` and `CORE-REVISION` to the project's versioned Generic Package Registry. It verifies that each file downloads anonymously with the expected checksum and creates the GitLab Release with clearly named links. Retrying with identical files reuses them. A different file at the same version stops publication.

Keep released package versions and their release entries available to the public. These downloads are independent of CI job artifact expiry. Ordinary branch pipelines produce temporary candidates for review. Users go directly to [GitLab Releases](https://gitlab.rlp.net/adwmainz/digicademy/lodeon/lodeon-customizer/-/releases).
