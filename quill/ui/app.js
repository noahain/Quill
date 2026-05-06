(function () {
  const providerSelect = document.getElementById("provider-select");
  const nvidiaSection = document.getElementById("nvidia-section");
  const groqSection = document.getElementById("groq-section");
  const groqModelSelect = document.getElementById("groq-model-select");
  const apiKeyInput = document.getElementById("api-key");
  const toggleNvidiaKey = document.getElementById("toggle-nvidia-key");
  const groqApiKeyInput = document.getElementById("groq-api-key");
  const toggleGroqKey = document.getElementById("toggle-groq-key");
  const shortcutDisplay = document.getElementById("shortcut-display");
  const captureBtn = document.getElementById("capture-shortcut");
  const captureHint = document.getElementById("capture-hint");
  const saveBtn = document.getElementById("save-btn");
  const cancelBtn = document.getElementById("cancel-btn");

  const DEFAULT_SHORTCUT = "Ctrl + Shift + D";
  let currentShortcut = DEFAULT_SHORTCUT;
  let previousShortcut = currentShortcut;
  let capturing = false;
  let capturedKeys = new Set();
  let capturedOrder = [];

  function announce(message) {
    const liveRegion = document.getElementById("live-region");
    if (liveRegion) liveRegion.textContent = message;
  }

  function updateProviderUI() {
    var provider = providerSelect.value;
    if (provider === "groq") {
      nvidiaSection.classList.add("hidden");
      groqSection.classList.remove("hidden");
    } else {
      nvidiaSection.classList.remove("hidden");
      groqSection.classList.add("hidden");
    }
  }

  function loadSettings() {
    saveBtn.disabled = true;
    if (window.pywebview && window.pywebview.api) {
      window.pywebview.api.get_settings().then(function (settings) {
        apiKeyInput.value = settings.api_key || "";
        groqApiKeyInput.value = settings.groq_api_key || "";
        providerSelect.value = settings.provider || "nvidia";
        groqModelSelect.value = settings.groq_model || "whisper-large-v3";
        currentShortcut = settings.shortcut || DEFAULT_SHORTCUT;
        updateProviderUI();
        renderShortcut();
        saveBtn.disabled = false;
      }).catch(function (err) {
        console.error("Failed to load settings:", err);
        saveBtn.disabled = false;
      });
    } else {
      saveBtn.disabled = false;
    }
  }

  // Expose a global init function so Python can call it on window re-show
  window.quillInit = loadSettings;

  function renderShortcut() {
    shortcutDisplay.textContent = currentShortcut;
  }

  providerSelect.addEventListener("change", updateProviderUI);

  toggleNvidiaKey.addEventListener("click", function () {
    var isPassword = apiKeyInput.type === "password";
    apiKeyInput.type = isPassword ? "text" : "password";
    toggleNvidiaKey.textContent = isPassword ? "Hide" : "Show";
  });

  toggleGroqKey.addEventListener("click", function () {
    var isPassword = groqApiKeyInput.type === "password";
    groqApiKeyInput.type = isPassword ? "text" : "password";
    toggleGroqKey.textContent = isPassword ? "Hide" : "Show";
  });

  captureBtn.addEventListener("click", function () {
    previousShortcut = currentShortcut;
    capturing = true;
    capturedKeys.clear();
    capturedOrder = [];
    captureHint.classList.remove("hidden");
    captureBtn.textContent = "Press keys…";
    announce("Capture mode active. Press your desired key combination, or Escape to cancel.");
  });

  document.addEventListener("keydown", function (e) {
    if (!capturing) return;
    if (e.key === "Escape") {
      e.preventDefault();
      capturing = false;
      capturedKeys.clear();
      capturedOrder = [];
      currentShortcut = previousShortcut;
      renderShortcut();
      captureHint.classList.add("hidden");
      captureBtn.textContent = "Change";
      announce("Shortcut capture cancelled.");
      return;
    }
    e.preventDefault();
    var key = e.key;
    if (!capturedKeys.has(key)) {
      capturedKeys.add(key);
      capturedOrder.push(key);
    }
  });

  document.addEventListener("keyup", function (e) {
    if (!capturing) return;
    capturing = false;
    captureHint.classList.add("hidden");
    captureBtn.textContent = "Change";
    if (capturedOrder.length > 0) {
      currentShortcut = formatShortcut(capturedOrder);
      renderShortcut();
    }
  });

  function formatShortcut(keys) {
    var isMac = navigator.platform.toLowerCase().indexOf("mac") !== -1 ||
                navigator.userAgent.toLowerCase().indexOf("mac") !== -1;
    var modifiers = keys.filter(function (k) { return ["Control", "Shift", "Alt", "Meta"].indexOf(k) !== -1; });
    var normal = keys.filter(function (k) { return modifiers.indexOf(k) === -1; });
    var map = {
      Control: "Ctrl",
      Shift: "Shift",
      Alt: "Alt",
      Meta: isMac ? "Cmd" : "Win",
    };
    var parts = modifiers.map(function (m) { return map[m] || m; });
    if (normal.length > 0) parts.push(normal[normal.length - 1].toUpperCase());
    return parts.join(" + ");
  }

  saveBtn.addEventListener("click", function () {
    var settings = {
      api_key: apiKeyInput.value.trim(),
      groq_api_key: groqApiKeyInput.value.trim(),
      shortcut: currentShortcut,
      provider: providerSelect.value,
      groq_model: groqModelSelect.value,
    };
    if (window.pywebview && window.pywebview.api) {
      window.pywebview.api.save_settings(settings).then(function () {
        window.pywebview.api.close_window().catch(function (err) {
          console.error("Failed to close window:", err);
        });
      }).catch(function (err) {
        console.error("Failed to save settings:", err);
      });
    }
  });

  cancelBtn.addEventListener("click", function () {
    if (window.pywebview && window.pywebview.api) {
      window.pywebview.api.close_window().catch(function (err) {
        console.error("Failed to close window:", err);
      });
    }
  });

  loadSettings();
})();
