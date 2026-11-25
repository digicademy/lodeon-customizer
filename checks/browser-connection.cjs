// Exercise an extracted application with default browser security and an isolated user directory.
const assert = require("node:assert/strict");
const { spawn } = require("node:child_process");
const { once } = require("node:events");
const { mkdtemp, rm } = require("node:fs/promises");
const os = require("node:os");
const path = require("node:path");
const { setTimeout: delay } = require("node:timers/promises");
const { chromium, firefox, webkit } = require("playwright-core");

const local = "http://127.0.0.1:8765";
const approved = "https://stories.example.org";
const foreign = "https://other.example.org";

async function main() {
  const [type, executable] = process.argv.slice(2);
  const engine = { chromium, firefox, webkit }[type];
  assert(engine && executable, "Pass chromium, firefox or webkit and the extracted app executable.");
  const dir = await mkdtemp(path.join(os.tmpdir(), "customizer-browser-"));
  const data = path.join(dir, "data");
  const app = spawn(path.resolve(executable), ["--no-browser", "--data", data], { stdio: "inherit" });
  const exit = once(app, "exit");
  let browser;
  try {
    for (let i = 0; i < 200; i++) {
      assert.equal(app.exitCode, null, "App exited before the test");
      try {
        const page = await fetch(local);
        assert((await page.text()).includes(data), "Another service is using the test port");
        break;
      } catch (error) {
        if (error.cause?.code !== "ECONNREFUSED" || i === 199) throw error;
        await delay(200);
      }
    }
    const options = type === "chromium" ? {
      executablePath: process.env.CHROMIUM_PATH, ignoreDefaultArgs: true,
      args: ["--headless", "--remote-debugging-pipe", "--no-first-run", "--user-data-dir=" + path.join(dir, "browser")],
    } : {};
    browser = await engine.launch(options);
    const context = await browser.newContext();
    const settings = await context.newPage();
    await settings.emulateMedia({ colorScheme: "dark" });
    await settings.goto(local);
    await settings.getByRole("button", {name: "Help", exact: true}).click();
    const help = settings.getByRole("dialog", {name: "LODEON Customizer Help"});
    await help.getByRole("heading", {name: "Build information"}).waitFor();
    await help.getByText("Customizer revision", {exact: true}).waitFor();
    await settings.keyboard.press("Escape");
    await help.waitFor({state: "hidden"});
    await settings.getByRole("button", { name: "Switch to day theme" }).click();
    await settings.reload();
    await settings.getByRole("button", { name: "Switch to night theme" }).waitFor();
    const bounds = locator => locator.boundingBox();
    const header = settings.locator("header.ld-topbar");
    const label = await bounds(header.locator('label[for="field-instance"]'));
    const input = await bounds(header.getByRole("textbox", { name: "Instance connection" }));
    assert(label.x + label.width <= input.x && Math.abs(label.y + label.height / 2 - input.y - input.height / 2) <= 1);
    const save = await bounds(header.getByRole("button", { name: "Save instance" }));
    const quit = await bounds(header.getByRole("button", { name: "Quit Customizer" }));
    assert.equal(save.y, quit.y);
    assert.equal(save.height, quit.height);
    assert.equal((await bounds(settings.getByRole("heading", {name: "Models", exact: true}))).y,
                 (await bounds(settings.getByRole("heading", {name: "Local package"}))).y);
    await settings.locator("header").getByRole("textbox", { name: "Instance connection", exact: true }).fill(approved + "/lodeon/");
    await settings.getByRole("button", { name: "Save instance" }).click();
    await settings.getByText("Instance saved.").waitFor();

    async function hostedPage(origin) {
      const page = await context.newPage();
      // Supply just the hosted HTML. All loopback requests use the real network.
      await page.route(origin + "/", route => route.fulfill({ contentType: "text/html", body: "<title>Test</title>" }));
      await page.goto(origin);
      assert.equal(await page.evaluate(() => isSecureContext && location.origin), origin);
      return page;
    }
    const allowed = await hostedPage(approved);
    const blocked = await hostedPage(foreign);
    if (type === "chromium") {
      const session = await context.newCDPSession(allowed);
      const { targetInfo } = await session.send("Target.getTargetInfo");
      for (const origin of [approved, foreign]) {
        await session.send("Browser.setPermission", { permission: { name: "loopback-network" },
          setting: "granted", origin, browserContextId: targetInfo.browserContextId });
      }
    }
    async function connect(page) {
      const { status, count, grant } = await page.evaluate(async base => {
        const options = { credentials: "omit", redirect: "error", referrerPolicy: "no-referrer" };
        const pair = await fetch(base + "/v1/connect", { ...options, method: "POST",
          headers: { "Content-Type": "application/json" }, body: JSON.stringify({models: true}) });
        if (!pair.ok) throw Error("Connect failed " + pair.status);
        const { grant } = await pair.json();
        const auth = { ...options, headers: { Authorization: "Bearer " + grant } };
        const catalog = await fetch(base + "/v1/targets", auth);
        const { models } = await catalog.json();
        return { status: catalog.status, count: models.length, grant };
      }, local);
      await settings.bringToFront();
      await header.getByText("Connected", {exact: true}).waitFor();
      const disconnected = await page.evaluate(async ({base, grant}) =>
        (await fetch(base + "/v1/disconnect", {method: "POST", credentials: "omit",
          headers: {Authorization: "Bearer " + grant}})).status, {base: local, grant});
      await header.getByText("Disconnected", {exact: true}).waitFor();
      return [status, count, disconnected];
    }
    await assert.rejects(connect(blocked), /fetch|network|load failed/i);
    assert.deepEqual(await connect(allowed), [200, 0, 204]);
    await settings.getByRole("link", { name: "Add model" }).click();
    await settings.getByLabel("Display name", { exact: true }).fill("Personal Ollama");
    await settings.getByLabel("Provider model name", { exact: true }).fill("fixture-model");
    await settings.getByLabel("Use as my default model", { exact: true }).check();
    await settings.getByRole("button", { name: "Save model" }).click();
    await settings.getByRole("heading", { name: "Edit model" }).waitFor();
    await settings.getByText("Advanced settings", { exact: true }).click();
    await settings.getByLabel("Temperature", { exact: true }).fill("0.4");
    await settings.getByRole("button", { name: "Save model" }).click();
    await settings.locator("main").getByRole("status").waitFor();
    assert.deepEqual(await connect(allowed), [200, 1, 204]);
    await settings.goto(local);
    await settings.getByRole("link", { name: "Add broker" }).click();
    await settings.getByRole("checkbox", { name: /Personal Ollama/ }).check();
    const pool = settings.locator("[data-pool]");
    const source = pool.getByRole("button", { name: /Personal Ollama/ });
    const fallbacks = settings.locator('[data-task="plan"] [data-role="fallbacks"]');
    await source.dragTo(fallbacks);
    const assigned = fallbacks.locator("[data-model]");
    await assigned.waitFor();
    await assigned.dragTo(pool);
    await assigned.waitFor({ state: "detached" });
    await settings.getByRole("button", { name: "Quit Customizer" }).click();
    assert.equal((await exit)[0], 0);
    console.log(type, browser.version(), "local settings, hosted connect/catalog/disconnect and foreign-origin denial passed.");
  } finally {
    if (app.exitCode === null && app.signalCode === null) app.kill();
    await browser?.close();
    await exit;
    await rm(dir, { recursive: true, force: true });
  }
}
main().catch(error => { console.error(error.message); process.exitCode = 1; });
