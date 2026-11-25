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

1. In the Assistant, open **Settings → Customize Workbench**. Choose **Download LODEON Customizer** to open [Downloads](#downloads) in a new tab. **User Guide** opens these instructions. If the menu entry is missing, check with your instance operator whether Customizer connections are enabled for your session.
2. Choose the latest download for your computer. Extract the entire archive to a folder on your computer and open the app shown below. Keep the extracted files together.
3. The app opens a **local settings page** in your default browser. Enter the URL from your LODEON tab under **Instance connection** in the header, including its deployment path, and choose **Save**. Use HTTPS for a hosted instance, for example `https://stories.example.org/lodeon/`. On the same computer you can also use HTTP with `localhost`, `127.0.0.1` or `[::1]`, for example `http://localhost:7014/lodeon/`. The permission applies to every path on that exact scheme, host and port.
   Use the moon or sun button in the header to switch between the Editor’s day and night themes. The app starts with your system preference and remembers your choice in this browser across pages and restarts.
4. On first launch the model list is empty. Choose **Models → Personal models → Add model** and follow [Configure a personal model](#configure-a-personal-model).
5. Return to the **original LODEON tab**, choose **Connect** in the same dialog and allow local-network access if your browser asks. Once the status turns green, close the dialog and select the model marked **Personal**. If you configured a personal default, it is already selected. Ask your question as usual.

| Your computer | Platform | Open after extraction |
| --- | --- | --- |
| Windows with an Intel or AMD 64-bit processor | **Windows · x64** (ZIP) | `LODEON-Customizer.exe` |
| Mac with an Apple M-series chip | **macOS · Apple silicon** (ZIP) | `LODEON-Customizer.app` |
| Mac with an Intel processor | **macOS · Intel** (ZIP) | `LODEON-Customizer.app` |
| Linux with glibc on an Intel or AMD 64-bit processor | **Linux · x64** (tar.gz) | `LODEON-Customizer` |
| Linux with glibc on a 64-bit ARM processor | **Linux · ARM64** (tar.gz) | `LODEON-Customizer` |

On a Mac, **Apple menu → About This Mac** identifies the chip.

You can change the instance in the header from any model or broker form. Saving the instance returns to the overview. If a form has unsaved edits, you can cancel the switch and finish editing. Choose the **ⓘ** beside a field label to read its help. The same control works with the keyboard.

## Configure a personal model

1. Choose **Models → Personal models → Add model**. Enter a display name, select the provider and enter the provider’s exact model name. For Ollama, use the name of a model installed on your computer. Leave the endpoint blank to use `http://127.0.0.1:11434`. OpenAI and Anthropic also have default endpoints. For an OpenAI-compatible server, enter its API base URL.
2. The first model or broker is preselected as the package default. **Use as my default model** also selects this target when you connect. Under **Advanced settings** you can set temperature, top P, reasoning effort, prompt caching, limits, costs and Ollama keep-alive. The Core runtime validates the selected provider’s settings.
3. Choose **Save model**. For OpenAI and Anthropic, the edit page now offers a password field. Enter the **Provider API key** and choose **Save API key**. For a keyed OpenAI-compatible endpoint, select **Use a personal API key** when setting up the profile. A saved key can be replaced in this field and is never displayed.
4. In LODEON, connect or reconnect the tab to refresh the catalog. Use **Edit** beside a personal model to change it later.

For example, a local Ollama model can use display name `My Ollama`, provider `Ollama` and model name `gemma4:12b` if that model is installed. Saving writes directly to `assistant.modelProfiles` in your local `config.yml`. Provider keys entered in the form go into `.env` in the package folder.

To remove a personal model or broker, choose **Remove** beside its name and confirm on the next page. If a broker uses the model, open the listed broker and change its membership first. Removing your personal default also clears that default. Provider keys and routing prompt files stay in the settings folder. Reconnect the LODEON tab to refresh its selector.

## Choose, reload or install a local package

Under **Local package**, use **Choose folder…** to select a directory. You can also type its absolute path and select **Use folder**. An empty directory starts a package. The app remembers the selected directory for the next launch. **Reload configuration** reads the current package from disk, including edits made in a text editor. Switching or reloading revokes active connections. Return to **Customize Workbench** in the LODEON tab to reconnect.

Set **Package ID** and **Version**, then choose **Save package**. A new manifest starts with `local/<folder-name>` and version `0.1.0`. Each package in an instance registry needs a distinct ID.

| File | Purpose |
| --- | --- |
| `lodeon.package.yml` | Core package manifest with the ID and version. |
| `config.yml` | Portable Core configuration, including model and broker definitions. Routed broker prompts belong under the configured prompt registry. |
| `.env` | Created when you save a provider key. You can also add endpoint variables here. |
| `.data/customizer.yml` | Private service identity, approved instance URL and per-instance sampling preferences. |
| `.gitignore` | Excludes local credentials, private settings, runtime data and caches. |

To install the package on an instance, add the directory that contains the manifest to the ordered `packages` list in that instance’s package registry. Include the manifest, configuration and any routing prompts when sharing it. Core excludes `.data` and `.env` from assembly. Supply provider variables through the target instance’s environment and use endpoints reachable from that instance. A mixed broker needs its referenced instance models. If this is the only model package, select a default model or broker. Clearing the default allows another package to supply it.

On first launch the app uses the following default folder.

| System | Personal files |
| --- | --- |
| Windows | `%LOCALAPPDATA%\LODEON-Customizer\data\` |
| macOS | `~/Library/Application Support/LODEON-Customizer/data/` |
| Linux | `$XDG_DATA_HOME/LODEON-Customizer/data/`, defaulting to `~/.local/share/LODEON-Customizer/data/` |

## Customize an instance model

1. Save the instance address and connect from **Settings → Customize Workbench** in that LODEON tab.
2. Open **Models → Instance models → Refresh list** in the Customizer. Choose **Edit settings** beside a model.
3. Enter your **Temperature** or **Top P**. Each field shows the current instance value. A blank field inherits that value. Choose **Save settings**, then disconnect and reconnect the LODEON tab.
4. Select the same instance model in LODEON. **Model information** shows the effective values. The instance runs the model with its own provider credentials and limits. A personal broker also uses these values when it selects that instance worker. Disconnect to use the instance defaults again.

The Customizer saves these overrides under `instanceModelSettings` in `.data/customizer.yml`, keyed by the saved instance URL and model ID. Projects retain the ordinary model ID. A changed list of available instance models requires a new connection.

## Configure a broker

Choose **Models → Personal models → Add broker**. Select the local and connected instance models under **Broker members**. Each selected member reveals its routing hint. You can also enter an offline member’s ID manually. Choose the router model and describe its routing objective.

New tasks start empty. Under **Task routing**, drag one selected model into **Worker** for each fixed task, or one or more into **Candidates** for a routed task. Add **Fallbacks** in the order they should be tried, if needed. Drag an assignment between areas to move it, onto another chip to reorder it, or back to **Selected models** to remove it. You can also select a model and choose **Assign**, use **←** to move it earlier, or **×** to remove it. When switching a task with several candidates to **Fixed**, choose its single worker explicitly.

Choose **Save broker** to apply your assignments. If any task uses routing, enter your Markdown in **Routing prompt** on the broker’s edit page, then choose **Save prompt**. For example, `Choose one of {{candidates}} for {{task}} given {{question}}. Return the model ID.` The form saves the registry entry and Markdown in the selected folder. A fixed-only broker is ready after saving its policy. Reconnect your LODEON tab and select the broker. Use **Edit** beside the broker to revisit these settings.

## Reconnect, disconnect or quit

Keep the app running while using Chat, **Check Tools** or suggested questions with a personal model. Each LODEON tab connects separately. The local header shows **Connected** while there is an active grant for the saved instance. It returns to **Disconnected** after the last grant ends. The connected tab highlights **Customize Workbench** in the Settings menu. After an Editor reload, a local configuration change or an app restart, return to **Settings → Customize Workbench** and reconnect. Use **Disconnect** first if the tab still shows a connection. The model selector and **Model information** show personal and instance targets in alphabetical order.

If **Connect** fails, open the Customizer again. Its settings page is at `http://127.0.0.1:8765/`. Check the saved instance address and the browser's local-network permission. If the connection succeeds but the selector has no personal model, check that you added a profile and applied the file as described above.

If the Linux desktop cannot open the browser automatically, open <http://127.0.0.1:8765/> in your browser. If the page is unreachable, run `./LODEON-Customizer --no-browser` from the extracted app folder, leave the terminal open and reload the page.

Choose **Disconnect** to release just the current tab. Choose **Quit** in the local settings header to stop the app. Closing the local settings tab leaves it running. Your local configuration is available the next time you start it.

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

The build compiles the desktop interface with the selected Core checkout’s Tailwind stylesheet, theme control and locked frontend tools. It installs Node and npm in the private build environment. The installed app works offline without a frontend toolchain.

Each local development build puts the tested app beside its archive and replaces the same-named copy in that output folder. Your personal settings live in the selected settings folder. Both Intel and Apple Silicon use the same command.

With native Python 3.12 you can also run the build script with `python3.12` or, on Windows, `py -3.12`. On Windows and Linux, open the executable inside the output folder’s `LODEON-Customizer` directory. To test with the Assistant, enable both `customizer.enabled` and `assistant.customizeModels` on your instance, save its address in the app, then choose **Settings → Customize Workbench → Connect** in that LODEON tab.

## Publish latest

Merge any required Core changes into **lodeon-core/main** first. Then merge the tested Customizer changes into **lodeon-customizer/main on GitLab RLP**. That is the complete routine release procedure. The GitLab push mirror starts **Build desktop apps** on GitHub. It resolves the public GitLab Core `main` once, builds the same Customizer and Core revisions on five native hosts, and tests each extracted archive. [GitHub build runs](https://github.com/digicademy/lodeon-customizer/actions/workflows/desktop.yml)

After all five pass, **Send successful build to GitLab** starts a publication pipeline for the mirrored ref. Ordinary GitLab instance runners import the archives from that exact GitHub run. They verify its workflow, ref and Customizer commit and check that all archives used one Core revision. Once **accepted-archives** succeeds on `main`, the five links under **Downloads** and their checksums refer to the new build. A failed build leaves the previous successful downloads available. [GitLab publication pipelines](https://gitlab.rlp.net/adwmainz/digicademy/lodeon/lodeon-customizer/-/pipelines)

### One-time setup for maintainers

| Where | Setting |
| --- | --- |
| GitLab → Settings → Repository → Mirroring repositories | Push from GitLab to `digicademy/lodeon-customizer` on GitHub. Include `main` and any release tags. Enable GitHub Actions on the mirror. |
| GitLab → Settings → CI/CD → Pipeline trigger tokens | Create a trigger for this project with permission to run a pipeline on `main`. Copy its token into the **GitHub mirror** under **Settings → Secrets and variables → Actions → New repository secret** as **`GITLAB_TRIGGER_TOKEN`**. |
| GitHub → Settings → Developer settings → Fine-grained personal access tokens | Select only `digicademy/lodeon-customizer` and grant **Actions → Read-only**. Store the token in the **GitLab project** under **Settings → CI/CD → Variables** as **`GITHUB_ACTIONS_READ_TOKEN`**, masked and protected. Protect `main` and any release tags that need this variable. |
| GitLab → Settings → CI/CD | Enable instance runners for untagged jobs and **Artifacts → Keep artifacts from most recent successful jobs**. Allow public access to pipeline artifacts. Each platform uses a separate GitLab job archive. |

The trigger starts a pipeline. The read token downloads Actions artifacts. Keep the GitHub credential used for GitLab push mirroring separate. The public Core checkout needs no credential. [GitLab pipeline triggers](https://docs.gitlab.com/ci/triggers/) · [GitHub artifact download permissions](https://docs.github.com/en/rest/actions/artifacts#download-an-artifact) · [GitLab artifact retention](https://docs.gitlab.com/ci/jobs/job_artifacts/#keep-artifacts-from-most-recent-successful-jobs)

**First publication.** Follow the mirrored commit on the GitHub Actions page and then the GitLab pipeline linked in the handoff job log. Open a download and **SHA256SUMS** from this README in a signed-out browser. If the handoff fails after a successful build, fix the trigger setup and re-run **Send successful build to GitLab** on GitHub. If the import fails, check the read token and retry the failed GitLab job. For a GitLab runner error `413 Request Entity Too Large`, check the project's maximum job artifact size against the largest single platform archive. A superseded commit is skipped or fails the SHA check if the ref moves during the handoff.

### Optional versioned publication

1. Prepare signing once for reviewed releases. On the mirror create the **release-signing** GitHub Actions environment, allow only protected release tags matching `v*` to deploy, and enter the environment secrets below. Allow public downloads from the GitLab Package Registry.
2. Merge the required Core and Customizer changes. Match the version in both `pyproject.toml` and `lodeon.package.yml`. Create the corresponding GitLab tag, for example `v0.2.0`, at the tested Customizer commit. The mirrored tag starts a signed build against one revision of GitLab Core `main`. [Create a GitLab tag](https://gitlab.rlp.net/adwmainz/digicademy/lodeon/lodeon-customizer/-/tags/new)
3. In the GitLab tag pipeline, download the five **native-app** artifacts and perform the [desktop review](#desktop-review). Choose **Play** on **desktop-review** after review. **accepted-archives** verifies the public versioned files and creates the Release entry. [Reviewed releases](https://gitlab.rlp.net/adwmainz/digicademy/lodeon/lodeon-customizer/-/releases)

| Tagged build | Secrets in the GitHub `release-signing` environment |
| --- | --- |
| macOS | `MACOS_CERTIFICATE_BASE64` (Developer ID Application identity exported as a base64 PKCS#12), `MACOS_CERTIFICATE_PASSWORD`, `MACOS_SIGN_IDENTITY` (identity name), `MACOS_NOTARY_KEY_BASE64` (base64 App Store Connect team API key in P8 format), `MACOS_NOTARY_KEY_ID` and `MACOS_NOTARY_ISSUER`. |
| Windows | `WINDOWS_CERTIFICATE_BASE64` (base64 PFX with an importable code-signing key), `WINDOWS_CERTIFICATE_PASSWORD` and `WINDOWS_TIMESTAMP_URL` (RFC 3161 timestamp service). This signing step requires a certificate whose issuance policy permits import on the runner. |

## Build environment

The hosted runners use native CPython 3.12. Each build installs the model runtime from the pinned Core source, bundles its matching resolver and defaults, then packages the app with PyInstaller. The smoke test extracts the archive into a fresh directory, starts it with isolated user data, saves an instance, checks origin restrictions, restarts the app and invokes a credentialed local HTTP provider fixture.

| Platform | GitHub-hosted runner | Archive |
| --- | --- | --- |
| Windows x64 | `windows-2022` | ZIP |
| macOS Apple silicon | `macos-15` | ZIP |
| macOS Intel | `macos-15-intel` | ZIP |
| Linux x64 | `ubuntu-22.04` | tar.gz |
| Linux ARM64 | `ubuntu-22.04-arm` | tar.gz |

Each job checks the OS and CPU architecture before building. Local development uses the checkout passed to `--core`. Both publication channels use the same public Core repository on GitLab. If Core becomes private, the source job accepts the optional read-only GitHub Actions secret `LODEON_CORE_READ_TOKEN`. [GitHub-hosted runner reference](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)

## Desktop review

Open the extracted candidates through Finder, Explorer and the Linux desktop as an ordinary user in a clean profile. Verify that the default browser opens, entering the instance works, restarting preserves personal data, and quitting releases the port. From the compatible hosted Settings UI, verify connect, one model call and disconnect in Safari on macOS, Edge on Windows and Firefox on Linux with normal browser security. Record OS version, architecture, browser version and results on the release ticket before confirming the blocking **desktop-review** job.

After approval, **accepted-archives** uploads the files to the versioned Generic Package Registry, verifies their checksums through anonymous downloads and creates the GitLab Release. A retry reuses identical files. A different file at the same version stops publication. Keep released packages and release entries available to the public. Their lifetime is independent of CI job artifact expiry.
