const $ = (id) => document.getElementById(id);

async function loadHealth() {
  try {
    const r = await fetch("/health");
    const h = await r.json();
    $("provider").textContent = `${h.provider} · ${h.model}`;
    $("provider").dataset.provider = h.provider;
  } catch {
    $("provider").textContent = "offline";
  }
}

$("form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const prompt = $("prompt").value.trim();
  if (!prompt) return;
  $("go").disabled = true;
  $("out").textContent = "Thinking…";
  const t0 = performance.now();
  try {
    const r = await fetch("/api/generate", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ prompt }),
    });
    const body = await r.json();
    if (!r.ok) throw new Error(body.detail || r.statusText);
    const ms = Math.round(performance.now() - t0);
    $("out").textContent = body.text;
    $("out").dataset.meta = `${body.provider} · ${body.model} · ${ms} ms`;
  } catch (err) {
    $("out").textContent = `Error: ${err.message}`;
    $("out").dataset.meta = "";
  } finally {
    $("go").disabled = false;
  }
});

loadHealth();
