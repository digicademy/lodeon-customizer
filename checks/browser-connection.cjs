// Disposable Step 1 counterpart. It has no provider, files, or model executor.
const assert = require("node:assert/strict");
const { randomBytes, randomUUID } = require("node:crypto");
const { mkdtemp, readFile, rm } = require("node:fs/promises");
const http = require("node:http");
const https = require("node:https");
const os = require("node:os");
const path = require("node:path");
const { chromium, firefox, webkit } = require("playwright-core");

const approved = "https://example.com";
const other = "https://example.org";
const token = () => randomBytes(32).toString("base64url");
const catalog = {
  revision: "fixture-1",
  models: [{
    target: { source: "personal", serviceId: randomUUID(), profileId: "sample" },
    label: "Example model", provider: "ollama", generation: {},
    promptCaching: { enabled: false, retention: "default" }, limits: {},
  }],
};

async function counterpart() {
  const ticket = token();
  const grant = token();
  const connectionId = randomUUID();
  let grantExpires = 0;
  const events = [];
  const tls = Boolean(process.env.CHECK_CERT);
  const server = tls ? https.createServer({
    cert: await readFile(process.env.CHECK_CERT), key: await readFile(process.env.CHECK_KEY),
  }) : http.createServer();
  server.on("request", (req, res) => {
    const { method, url, headers } = req;
    const reply = (status, body) => {
      events.push({ origin: headers.origin, method, url, status });
      res.writeHead(status, { "Cache-Control": "no-store", "Content-Type": "application/json" });
      res.end(body === undefined ? undefined : JSON.stringify(body));
    };
    if (headers.host !== `127.0.0.1:${server.address().port}` || headers.origin !== approved) {
      return reply(403);
    }
    res.setHeader("Vary", "Origin");
    res.setHeader("Access-Control-Allow-Origin", approved);
    const routeMethod = { "/v1/pair": "POST", "/v1/catalog": "GET", "/v1/invoke": "POST" }[url];
    if (!routeMethod) return reply(404);
    if (method === "OPTIONS") {
      if (headers["access-control-request-method"] !== routeMethod) return reply(405);
      res.setHeader("Access-Control-Allow-Methods", routeMethod);
      res.setHeader("Access-Control-Allow-Headers", "Authorization, Content-Type");
      return reply(204);
    }
    if (method !== routeMethod) return reply(405);
    if (url === "/v1/pair") {
      if (grantExpires || headers.authorization !== `Bearer ${ticket}`) return reply(403);
      grantExpires = Date.now() + 60_000;
      return reply(200, { connectionId, grant, expiresInSeconds: 60 });
    }
    if (Date.now() >= grantExpires || headers.authorization !== `Bearer ${grant}`) return reply(403);
    if (url === "/v1/catalog") return reply(200, catalog);
    return reply(501); // The prototype never dispatches an invocation.
  });
  await new Promise((resolve, reject) => {
    server.once("error", reject).listen(0, "127.0.0.1", resolve);
  });
  const base = `${tls ? "https" : "http"}://127.0.0.1:${server.address().port}`;
  return { server, events, ticket, base };
}

function assertRejected(base, headers) {
  const client = new URL(base).protocol === "https:" ? https : http;
  return new Promise((resolve, reject) => {
    const req = client.get(base + "/v1/catalog", { headers }, res => {
      res.resume();
      if (res.statusCode === 403 && !res.headers["access-control-allow-origin"]) resolve();
      else reject(new Error(`expected origin/host rejection, got ${res.statusCode}`));
    });
    req.on("error", reject);
  });
}

function request(page, base, route, method, credential) {
  return page.evaluate(async ({ url, method, credential }) => {
    try {
      const response = await fetch(url, {
        method, headers: { Authorization: `Bearer ${credential}` },
        credentials: "omit", redirect: "error", referrerPolicy: "no-referrer",
        signal: AbortSignal.timeout(7000),
      });
      return { status: response.status, body: response.ok ? await response.json() : null };
    } catch (error) {
      return { status: null, error: error.name };
    }
  }, { url: base + route, method, credential });
}

async function securePage(context, origin) {
  const page = await context.newPage();
  const response = await page.goto(origin, { waitUntil: "domcontentloaded" });
  assert.equal(response.status(), 200);
  assert.equal(await page.evaluate(() => isSecureContext && location.origin), origin);
  return page;
}

async function check(browser, type, fixture) {
  const { base, ticket, events } = fixture;
  const context = await browser.newContext();
  const diagnostics = [];
  context.on("requestfailed", req => {
    if (req.url().startsWith(base + "/")) diagnostics.push([req.method(), req.url(), req.failure()?.errorText]);
  });
  try {
    const allowed = await securePage(context, approved);
    allowed.on("console", message => {
      if (message.type() === "error") diagnostics.push(message.text());
    });
    const denied = await securePage(context, other);
    let permission = "engine default";
    if (type === "chromium") {
      const session = await context.newCDPSession(allowed);
      const { targetInfo } = await session.send("Target.getTargetInfo");
      const setPermission = (origin, setting) => session.send("Browser.setPermission", {
        permission: { name: "loopback-network" }, setting, origin,
        browserContextId: targetInfo.browserContextId,
      });
      const readPermission = () => allowed.evaluate(async () =>
        (await navigator.permissions.query({ name: "loopback-network" })).state);
      permission = await readPermission();
      assert.equal(permission, "prompt");
      await setPermission(approved, "denied");
      assert.equal(await readPermission(), "denied");
      assert.equal((await request(allowed, base, "/v1/pair", "POST", ticket)).status, null);
      assert.equal(events.length, 0);
      await setPermission(approved, "granted");
      await setPermission(other, "granted");
      await Promise.all([allowed.reload(), denied.reload()]);
      assert.equal(await readPermission(), "granted");
      permission = "prompt, denied, granted (per-origin browser permission)";
    }
    for (const route of ["/v1/pair", "/v1/invoke"]) {
      const blocked = await request(denied, base, route, "POST", "dummy");
      assert.equal(blocked.status, null, "unapproved origin could read a response");
    }
    const paired = await request(allowed, base, "/v1/pair", "POST", ticket);
    assert.equal(paired.status, 200, `pair failed (${paired.error || paired.status})`);
    const retrieved = await request(allowed, base, "/v1/catalog", "GET", paired.body.grant);
    assert.equal(retrieved.status, 200);
    assert.deepEqual(retrieved.body, catalog);
    assert.equal((await request(allowed, base, "/v1/pair", "POST", ticket)).status, 403);

    for (const route of ["/v1/pair", "/v1/invoke"]) {
      assert(events.some(e => e.origin === other && e.url === route && e.method === "OPTIONS" && e.status === 403));
      assert(!events.some(e => e.origin === other && e.method !== "OPTIONS"));
    }
    assert(events.some(e => e.origin === approved && e.method === "OPTIONS" && e.status === 204));
    const authorization = `Bearer ${paired.body.grant}`;
    // On HTTP the alternate Host reaches the server independently of TLS hostname validation.
    if (base.startsWith("http:")) {
      await assertRejected(base, { authorization, origin: approved, host: "unexpected.invalid" });
    }
    await assertRejected(base, { authorization, origin: other });
    await assertRejected(base, { authorization, origin: "null" });
    await assertRejected(base, { authorization });
    console.log(type, browser.version(), "pair=200 catalog=200 reused-ticket=403",
      "foreign pair/invoke preflights=403 foreign/null/missing-origin=403", permission);
  } catch (error) {
    console.error({ diagnostics, events });
    throw error;
  } finally {
    await context.close();
  }
}

async function main() {
  const type = process.argv[2];
  const engine = { chromium, firefox, webkit }[type];
  assert(engine, "pass chromium, firefox or webkit");
  const profile = await mkdtemp(path.join(os.tmpdir(), "customizer-browser-"));
  const fixture = await counterpart();
  let browser;
  try {
    // Use the installed Chromium browser with its native sandbox and default web policies.
    const options = type === "chromium" ? {
      executablePath: process.env.CHROMIUM_PATH, ignoreDefaultArgs: true,
      args: ["--headless", "--remote-debugging-pipe", "--no-first-run", `--user-data-dir=${profile}`],
    } : {};
    browser = await engine.launch(options);
    console.log("checking", type, browser.version());
    await check(browser, type, fixture);
  } finally {
    await browser?.close();
    await new Promise(resolve => fixture.server.close(resolve));
    await rm(profile, { recursive: true, force: true });
  }
}

main().catch(error => { console.error(error.message); process.exitCode = 1; });
