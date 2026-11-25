// GitLab creates the release only after its public downloads have passed verification.
const list = document.querySelector("#release-list");
const api = "https://gitlab.rlp.net/api/v4/projects/62371/releases";
const notice = document.createElement("p");
notice.className = "fine";
list.append(notice);

function releaseEntry(release) {
  const entry = document.createElement("details");
  const title = document.createElement("summary");
  title.textContent = release.tag_name;
  const files = document.createElement("ul");
  for (const asset of release.assets.links) {
    const url = new URL(asset.url);
    if (url.origin !== "https://gitlab.rlp.net" || asset.link_type !== "package") continue;
    const row = document.createElement("li");
    const link = document.createElement("a");
    link.href = url.href;
    link.textContent = asset.name;
    row.append(link);
    files.append(row);
  }
  entry.append(title, files);
  return entry;
}

async function showReleases(page) {
  notice.textContent = "Checking for versioned releases…";
  try {
    const response = await fetch(api + "?per_page=10&page=" + page, { credentials: "omit" });
    if (!response.ok) throw new Error();
    const releases = await response.json();
    for (const release of releases) list.insertBefore(releaseEntry(release), notice);
    notice.textContent = page === 1 && releases.length === 0
      ? "The first versioned release has yet to be published. The latest builds are available above."
      : "";
    if (response.headers.get("x-next-page")) {
      const more = document.createElement("button");
      more.type = "button";
      more.textContent = "Show older releases";
      more.addEventListener("click", () => { more.remove(); showReleases(page + 1); });
      list.append(more);
    }
  } catch {
    notice.textContent = "The release list could not be loaded. Open GitLab below to see the downloads.";
  }
}
showReleases(1);
