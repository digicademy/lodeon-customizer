# LODEON Customizer

Use your own model in the Assistant of a LODEON instance you already use. The Customizer runs on your computer. It includes its runtime and works with any instance that permits personal models for your session.

## Downloads

Choose **latest** for your computer. These links become available after the first successful `main` pipeline and follow each subsequent successful build. All five archives undergo automated checks. The current `latest` workflow produces Windows builds without release signing and macOS builds without Developer ID signing or notarization.

| Platform | Latest download |
| --- | --- |
| Windows · x64 | [Download ZIP](https://gitlab.rlp.net/api/v4/projects/adwmainz%2Fdigicademy%2Flodeon%2Flodeon-customizer/jobs/artifacts/main/raw/dist/LODEON-Customizer-latest-windows-x86_64.zip?job=native-app%3A%20%5Bwindows-x86_64%5D) |
| macOS · Apple silicon | [Download ZIP](https://gitlab.rlp.net/api/v4/projects/adwmainz%2Fdigicademy%2Flodeon%2Flodeon-customizer/jobs/artifacts/main/raw/dist/LODEON-Customizer-latest-macos-arm64.zip?job=native-app%3A%20%5Bmacos-arm64%5D) |
| macOS · Intel | [Download ZIP](https://gitlab.rlp.net/api/v4/projects/adwmainz%2Fdigicademy%2Flodeon%2Flodeon-customizer/jobs/artifacts/main/raw/dist/LODEON-Customizer-latest-macos-x86_64.zip?job=native-app%3A%20%5Bmacos-x86_64%5D) |
| Linux · x64 | [Download TAR.GZ](https://gitlab.rlp.net/api/v4/projects/adwmainz%2Fdigicademy%2Flodeon%2Flodeon-customizer/jobs/artifacts/main/raw/dist/LODEON-Customizer-latest-linux-x86_64.tar.gz?job=native-app%3A%20%5Blinux-x86_64%5D) |
| Linux · ARM64 | [Download TAR.GZ](https://gitlab.rlp.net/api/v4/projects/adwmainz%2Fdigicademy%2Flodeon%2Flodeon-customizer/jobs/artifacts/main/raw/dist/LODEON-Customizer-latest-linux-arm64.tar.gz?job=native-app%3A%20%5Blinux-arm64%5D) |

[Latest build checksums](https://gitlab.rlp.net/api/v4/projects/adwmainz%2Fdigicademy%2Flodeon%2Flodeon-customizer/jobs/artifacts/main/raw/dist/SHA256SUMS?job=accepted-archives) · [Bundled Core revision](https://gitlab.rlp.net/api/v4/projects/adwmainz%2Fdigicademy%2Flodeon%2Flodeon-customizer/jobs/artifacts/main/raw/dist/CORE-REVISION?job=accepted-archives)

If your browser displays a development download as text, use **Save link as** on the platform link and keep the `.zip` or `.tar.gz` extension. [GitLab single-file artifact downloads](https://docs.gitlab.com/api/job_artifacts/#download-a-single-artifact-file-by-reference-name)

## Get the app and connect your first model

1. In the Assistant, open **Settings → Connect personal models**. Choose **Download LODEON Customizer** to open [Downloads](#downloads) in a new tab. **Setup and user guide** opens these instructions. If the menu entry is missing, check with your instance operator whether personal models are enabled for your session.
2. Choose the latest download for your computer. Extract the entire archive to a folder on your computer and open the app shown below. Keep the extracted files together.
3. The app opens a **local settings page** in your default browser. Copy the instance URL from your LODEON tab, including its deployment path, and choose **Save instance**. Use HTTPS for a hosted instance, for example `https://stories.example.org/lodeon/`. On the same computer you can also use HTTP with `localhost`, `127.0.0.1` or `[::1]`, for example `http://localhost:7014/lodeon/`. The permission applies to every path on that exact scheme, host and port.
4. On first launch the model list is empty. Choose **Personal models → Add model** and follow [Configure a personal model](#configure-a-personal-model).
5. Return to the **original LODEON tab**, choose **Connect** in the same dialog and allow local-network access if your browser asks. Close the dialog and select the model marked **Personal**. If you configured a personal default, it is already selected. Ask your question as usual.

| Your computer | Platform | Open after extraction |
| --- | --- | --- |
| Windows with an Intel or AMD 64-bit processor | **Windows · x64** (ZIP) | `LODEON-Customizer.exe` |
| Mac with an Apple M-series chip | **macOS · Apple silicon** (ZIP) | `LODEON-Customizer.app` |
| Mac with an Intel processor | **macOS · Intel** (ZIP) | `LODEON-Customizer.app` |
| Linux with glibc on an Intel or AMD 64-bit processor | **Linux · x64** (tar.gz) | `LODEON-Customizer` |
| Linux with glibc on a 64-bit ARM processor | **Linux · ARM64** (tar.gz) | `LODEON-Customizer` |

On a Mac, **Apple menu → About This Mac** identifies the chip.

## Configure a personal model

1. Choose **Personal models → Add model**. Enter a display name, select the provider and enter the provider’s exact model name. For Ollama, use the name of a model installed on your computer. Leave the endpoint blank to use `http://127.0.0.1:11434`. OpenAI and Anthropic also have default endpoints. For an OpenAI-compatible server, enter its API base URL.
2. Select **Use as my default model** if you want LODEON to select this profile when you connect. Under **Advanced settings** you can set temperature, top P, reasoning effort, prompt caching, limits, costs and Ollama keep-alive. The Core runtime validates the selected provider’s settings.
3. Choose **Save model**. For OpenAI and Anthropic, the edit page now offers a password field. Enter the **Provider API key** and choose **Save API key**. For a keyed OpenAI-compatible endpoint, select **Use a personal API key** when setting up the profile. A saved key can be replaced in this field and is never displayed.
4. In LODEON, connect or reconnect the tab to refresh the catalog. Use **Edit model** in the Customizer to change a profile later.

For example, a local Ollama model can use display name `My Ollama`, provider `Ollama` and model name `gemma4:12b` if that model is installed. Saving writes directly to `assistant.modelProfiles` in your local `config.yml`. **Local files** shows its location and the separate `models/.env` file used for provider keys. Brokers and their routing prompts are configured in the local files.

| System | Personal files |
| --- | --- |
| Windows | `%LOCALAPPDATA%\LODEON-Customizer\data\` |
| macOS | `~/Library/Application Support/LODEON-Customizer/data/` |
| Linux | `$XDG_DATA_HOME/LODEON-Customizer/data/`, defaulting to `~/.local/share/LODEON-Customizer/data/` |

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

## Test a development build

From the LODEON Core root, `--core .` builds against your current Core working tree, including local edits. To use a separate checkout, pass its path to `--core`. Quit any running Customizer first so its local smoke check can use port 8765.

From the Core root on macOS, build and open the verified app with

```sh
uv run --no-project --python 3.12 python vendor/lodeon-customizer/release/build.py --core . --output vendor/lodeon-customizer/dist/local &&
open vendor/lodeon-customizer/dist/local/LODEON-Customizer.app
```

Each local development build puts the tested app beside its archive and replaces the same-named copy in that output folder. Your personal settings live in the separate OS data folder. Both Intel and Apple Silicon use the same command.

With native Python 3.12 you can also run the build script with `python3.12` or, on Windows, `py -3.12`. On Windows and Linux, open the executable inside the output folder’s `LODEON-Customizer` directory. To test with the Assistant, enable `assistant.personalModels.enabled` on your instance, save its address in the app, then choose **Settings → Connect personal models → Connect** in that LODEON tab.

## Publish latest

First merge and push any required Core changes to **lodeon-core/main**. Then merge and push the tested Customizer changes to **lodeon-customizer/main**. That push starts the public build automatically. GitLab resolves Core `main` to one commit for all five platforms. Once the pipeline succeeds, the five [download links](#downloads) serve the new archives.

The pipeline needs the [five native runners](#build-environment). Allow public access to the build artifacts and enable **Settings → CI/CD → Artifacts → Keep artifacts from most recent successful jobs** so the downloads stay available between builds. GitLab serves these files as job artifacts. [GitLab artifact retention](https://docs.gitlab.com/ci/jobs/job_artifacts/#keep-artifacts-from-most-recent-successful-jobs)

### Optional versioned publication

For a future versioned release, the tag jobs also need access to the signing identities on Windows and macOS, and the Package Registry must allow public downloads.

1. **Prepare Core.** Merge any required runtime changes into `lodeon-core/main`. Tagged builds use the same Core `main` source policy as public `latest` builds.
2. **Push the Customizer release commit to `main`.** Its `pyproject.toml` project version and `lodeon.package.yml` version should both say `0.2.0` for the first release. For subsequent releases, update both files to the new version. Each successful `main` pipeline updates the development downloads automatically.
3. **Create the Customizer tag.** Open [Code → Tags → New tag](https://gitlab.rlp.net/adwmainz/digicademy/lodeon/lodeon-customizer/-/tags/new). Enter `v0.2.0` for **Tag name**, select the release commit under **Create from**, and choose **Create tag**. Leave release notes empty if that field is shown. The pipeline creates the Release entry after review. [GitLab tag instructions](https://docs.gitlab.com/user/project/repository/tags/#from-the-ui)
4. **Approve the desktop builds.** Open [Build → Pipelines](https://gitlab.rlp.net/adwmainz/digicademy/lodeon/lodeon-customizer/-/pipelines), select the pipeline for **v0.2.0**, and wait for the five **native-app** jobs. Download their artifacts and perform the [desktop review](#desktop-review). Then choose **Play** on **desktop-review**. A job stuck at **Pending** with a missing-runner message needs an online runner with the tag shown on that job.
5. **Check the publication.** Wait for **accepted-archives** to turn green. Open the [Releases page](https://gitlab.rlp.net/adwmainz/digicademy/lodeon/lodeon-customizer/-/releases) in a signed-out browser. **LODEON Customizer 0.2.0 → Assets** contains five native archives, `SHA256SUMS` and `CORE-REVISION`. The [latest reviewed release](https://gitlab.rlp.net/adwmainz/digicademy/lodeon/lodeon-customizer/-/releases/permalink/latest) now opens this version.

If you prefer the terminal for step 3, run the following yourself in the Customizer checkout at the already pushed release commit. Continue with step 4 in GitLab.

```sh
git tag -a v0.2.0 -m "LODEON Customizer 0.2.0"
git push origin v0.2.0
```

## Build environment

The build installs the model runtime from the selected Core source, bundles its matching resolver and defaults, and archives a native application with PyInstaller. It then extracts **that archive** into a fresh directory, isolates the user profile, starts the executable, saves an instance, checks origin restrictions, restarts it, invokes a credentialed local HTTP provider fixture through the bundled runtime and quits. No external model or provider key is needed.

The GitLab source job needs read access to Core. It downloads the archive by the resolved commit SHA and supplies those same inputs to all native jobs. For a private checkout, an authorized masked read-only `LODEON_CORE_READ_TOKEN` can be supplied to that job. CI uses the runner tags below and checks that Python actually runs on the requested OS and architecture.

| Runner tag | Deliverable | Release host |
| --- | --- | --- |
| `windows-x86_64` | ZIP, containing the Windows application | Native Windows x64, signing certificate and SignTool |
| `macos-arm64` | ZIP, containing the macOS app | Native Apple Silicon, Developer ID and notarization |
| `macos-x86_64` | ZIP, containing the macOS app | Native Intel Mac, Developer ID and notarization |
| `linux-x86_64` | tar.gz, containing the Linux application | Native glibc Linux x64 with binutils |
| `linux-arm64` | tar.gz, containing the Linux application | Native glibc Linux arm64 with binutils |

Use shell runners with Python 3.12 available as `python`, port 8765 free, and standard OS build tools. Build on the oldest OS/glibc version intended for each published binary and record the actual runner OS and architecture. Tagged macOS builds need `MACOS_SIGN_IDENTITY` and `MACOS_NOTARY_PROFILE` in the signing keychain. Tagged Windows builds need `WINDOWS_SIGN_THUMBPRINT` and `WINDOWS_TIMESTAMP_URL`. Signing access belongs on protected release runners/tags. Development candidates can be built unsigned.

## Desktop review

Open the extracted candidates through Finder, Explorer and the Linux desktop as an ordinary user in a clean profile. Verify that the default browser opens, entering the instance works, restarting preserves personal data, and quitting releases the port. From the compatible hosted Settings UI, verify connect, one model call and disconnect in Safari on macOS, Edge on Windows and Firefox on Linux with normal browser security. Record OS version, architecture, browser version and results on the release ticket before confirming the blocking **desktop-review** job.

After approval, **accepted-archives** uploads the files to the versioned Generic Package Registry, verifies their checksums through anonymous downloads and creates the GitLab Release. A retry reuses identical files. A different file at the same version stops publication. Keep released packages and release entries available to the public. Their lifetime is independent of CI job artifact expiry.
