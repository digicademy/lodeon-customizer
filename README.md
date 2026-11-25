# LODEON Customizer

Use your own model in the Assistant of a LODEON instance you already use. The Customizer runs on your computer. It includes its runtime and works with any instance that permits personal models for your session.

**[Download the app](https://adwmainz.pages.gitlab.rlp.net/digicademy/lodeon/lodeon-customizer/)** · **[Customizer User Guide](https://adwmainz.pages.gitlab.rlp.net/digicademy/lodeon/lodeon-documentation/user-guide/customizer/)**

This README covers the package format, local development, verification and publication. The User Guide walks through connecting a workbench, adding a personal model, editing an instance model and resetting its settings.

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

## Instance settings and connections

The Customizer stores temperature and Top P overrides in `instanceModelSettings` in `.data/customizer.yml`, keyed by the saved instance URL and model ID. **Reset settings** removes that model’s overrides. The connected tab refreshes its effective values when Model information opens, while it is visible, or when the window regains focus. Changes to the personal model or broker catalog require reconnection.

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

After all five pass, **Send successful build to GitLab** starts a publication pipeline for the mirrored ref. Ordinary GitLab instance runners import the archives from that exact GitHub run. They verify its workflow, ref and Customizer commit and check that all archives used one Core revision. Once **accepted-archives** succeeds on `main`, the [download page](https://adwmainz.pages.gitlab.rlp.net/digicademy/lodeon/lodeon-customizer/) offers the new build and its checksums. A subsequent Pages job deploys the site on the main branch. The site reads published versioned downloads from the public GitLab Releases API. A failed build leaves the previous successful downloads available. [GitLab publication pipelines](https://gitlab.rlp.net/adwmainz/digicademy/lodeon/lodeon-customizer/-/pipelines)

### One-time setup for maintainers

| Where | Setting |
| --- | --- |
| GitLab → Settings → Repository → Mirroring repositories | Push from GitLab to `digicademy/lodeon-customizer` on GitHub. Include `main` and any release tags. Enable GitHub Actions on the mirror. |
| GitLab → Settings → CI/CD → Pipeline trigger tokens | Create a trigger for this project with permission to run a pipeline on `main`. Copy its token into the **GitHub mirror** under **Settings → Secrets and variables → Actions → New repository secret** as **`GITLAB_TRIGGER_TOKEN`**. |
| GitHub → Settings → Developer settings → Fine-grained personal access tokens | Select only `digicademy/lodeon-customizer` and grant **Actions → Read-only**. Store the token in the **GitLab project** under **Settings → CI/CD → Variables** as **`GITHUB_ACTIONS_READ_TOKEN`**, masked and protected. Protect `main` and any release tags that need this variable. |
| GitLab → Settings → CI/CD | Enable instance runners for untagged jobs and **Artifacts → Keep artifacts from most recent successful jobs**. Allow public access to pipeline artifacts. Each platform uses a separate GitLab job archive. |

The trigger starts a pipeline. The read token downloads Actions artifacts. Keep the GitHub credential used for GitLab push mirroring separate. The public Core checkout needs no credential. [GitLab pipeline triggers](https://docs.gitlab.com/ci/triggers/) · [GitHub artifact download permissions](https://docs.github.com/en/rest/actions/artifacts#download-an-artifact) · [GitLab artifact retention](https://docs.gitlab.com/ci/jobs/job_artifacts/#keep-artifacts-from-most-recent-successful-jobs)

**First publication.** Follow the mirrored commit on the GitHub Actions page and then the GitLab pipeline linked in the handoff job log. Open a download and **SHA256SUMS** from the download page in a signed-out browser. If the handoff fails after a successful build, fix the trigger setup and re-run **Send successful build to GitLab** on GitHub. If the import fails, check the read token and retry the failed GitLab job. For a GitLab runner error `413 Request Entity Too Large`, check the project's maximum job artifact size against the largest single platform archive. A superseded commit is skipped or fails the SHA check if the ref moves during the handoff.

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
