(() => {
  "use strict";

  const GA_ID = "G-H0QB1FC8VN";
  const CLARITY_ID = "yztl1nx9mv";
  const CONSENT_KEY = "change2md-analytics-consent";
  const packages = {
    "change2md-0.2.0-py3-none-any.whl": "python_cli_sdk",
    "change2md-typescript-sdk-0.2.0.tgz": "typescript_sdk",
    "change2md-browser-extension-0.2.0.zip": "browser_extension",
    "change2md-0.2.0.tar.gz": "python_source",
    "SHA256SUMS": "checksums",
  };
  let sessionChoice = null;
  let gaInjected = false;
  let clarityInjected = false;

  function getConsent() {
    try {
      const choice = localStorage.getItem(CONSENT_KEY);
      return choice === "granted" || choice === "denied" ? choice : null;
    } catch {
      return sessionChoice;
    }
  }

  function storeConsent(choice) {
    sessionChoice = choice;
    try {
      localStorage.setItem(CONSENT_KEY, choice);
    } catch {
      // The session fallback preserves the choice when storage is unavailable.
    }
  }

  window.dataLayer = window.dataLayer || [];
  window.gtag = window.gtag || function () {
    window.dataLayer.push(arguments);
  };
  window.gtag("consent", "default", {
    ad_storage: "denied",
    ad_user_data: "denied",
    ad_personalization: "denied",
    analytics_storage: getConsent() === "granted" ? "granted" : "denied",
  });
  window.gtag("js", new Date());
  window.gtag("config", GA_ID, {
    send_page_view: false,
    content_group: "change2md",
    allow_google_signals: false,
    allow_ad_personalization_signals: false,
  });

  function loadAnalytics() {
    if (!gaInjected) {
      gaInjected = true;
      const script = document.createElement("script");
      script.async = true;
      script.src = `https://www.googletagmanager.com/gtag/js?id=${GA_ID}`;
      document.head.appendChild(script);
    }
    if (!clarityInjected) {
      clarityInjected = true;
      window.clarity = window.clarity || Object.assign(function () {
        (window.clarity.q = window.clarity.q || []).push(arguments);
      }, { q: [] });
      const script = document.createElement("script");
      script.async = true;
      script.src = `https://www.clarity.ms/tag/${CLARITY_ID}`;
      document.head.appendChild(script);
    }
    window.clarity("consentv2", { ad_Storage: "denied", analytics_Storage: "granted" });
  }

  function track(event, parameters = {}) {
    if (getConsent() !== "granted") return;
    const payload = {
      content_group: "change2md",
      app_id: "change2md",
      page_path: window.location.pathname,
      ...parameters,
    };
    window.gtag("event", event, payload);
    window.clarity?.("set", "app_id", "change2md");
    window.clarity?.("set", "page_path", payload.page_path);
    if (payload.package_id) window.clarity?.("set", "package_id", payload.package_id);
    window.clarity?.("event", event);
  }

  function clearGaCookies() {
    const host = window.location.hostname;
    const domains = ["", host, `.${host}`, `.${host.split(".").slice(-2).join(".")}`];
    for (const cookie of document.cookie.split(";")) {
      const name = cookie.split("=")[0].trim();
      if (!/^_ga(_|$)/.test(name)) continue;
      for (const domain of domains) {
        document.cookie = `${name}=; Max-Age=0; path=/${domain ? `; domain=${domain}` : ""}`;
      }
    }
  }

  const banner = document.getElementById("analytics-consent");
  const showSettings = () => {
    banner.hidden = false;
    banner.querySelector("[data-consent=granted]").focus();
  };

  if (getConsent() === null) banner.hidden = false;
  if (getConsent() === "granted") {
    loadAnalytics();
    track("page_view", { page_location: location.href, page_title: document.title });
  }

  banner.addEventListener("click", (event) => {
    const choice = event.target.closest("[data-consent]")?.dataset.consent;
    if (!choice) return;
    storeConsent(choice);
    banner.hidden = true;
    window.gtag("consent", "update", { analytics_storage: choice });
    if (choice === "granted") {
      loadAnalytics();
      track("page_view", { page_location: location.href, page_title: document.title });
    } else {
      clearGaCookies();
      window.clarity?.("consentv2", { ad_Storage: "denied", analytics_Storage: "denied" });
      window.clarity?.("consent", false);
    }
  });

  document.getElementById("privacy-settings").addEventListener("click", showSettings);
  document.addEventListener("click", (event) => {
    const link = event.target.closest('a[href*="/releases/download/v0.2.0/"]');
    if (!link) return;
    const fileName = link.href.split("/").pop();
    const packageId = packages[fileName];
    if (!packageId) return;
    track("download_click", {
      package_id: packageId,
      release_version: "0.2.0",
      file_name: fileName,
    });
  });
})();
