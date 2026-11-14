const API = "https://change2md.vercel.app/api/convert";
const form = document.getElementById("form");
const input = document.getElementById("url");
const submit = document.getElementById("submit");
const status = document.getElementById("status");
const result = document.getElementById("result");
const output = document.getElementById("output");
const next = document.getElementById("next");
let nextOffset = 0;

async function currentPage() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tab && tab.url && /^https:/.test(tab.url)) input.value = tab.url;
}

function busy(value) {
  submit.disabled = value;
  next.disabled = value;
  submit.textContent = value ? "Converting…" : "Convert page";
}

async function convert(append = false) {
  if (!input.value.startsWith("https://")) {
    status.textContent = "Enter a public HTTPS URL.";
    status.className = "error";
    return;
  }
  busy(true);
  status.className = "";
  status.textContent = "Converting…";
  try {
    const response = await fetch(API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: input.value, offset: append ? nextOffset : 0, max_chars: 200000 }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Conversion failed.");
    output.textContent = append ? `${output.textContent}\n${data.markdown}` : data.markdown;
    nextOffset = data.next_offset || 0;
    next.hidden = !data.has_more;
    result.hidden = false;
    status.textContent = data.has_more ? "Chunk ready; more are available." : "Markdown ready.";
  } catch (error) {
    status.textContent = error.message || "Conversion failed.";
    status.className = "error";
  } finally {
    busy(false);
  }
}

form.addEventListener("submit", (event) => { event.preventDefault(); convert(false); });
next.addEventListener("click", () => convert(true));
document.getElementById("copy").addEventListener("click", async () => {
  await navigator.clipboard.writeText(output.textContent);
  status.textContent = "Markdown copied.";
});
document.getElementById("download").addEventListener("click", () => {
  const blob = new Blob([output.textContent], { type: "text/markdown;charset=utf-8" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "page.md";
  link.click();
  URL.revokeObjectURL(link.href);
});
currentPage();
