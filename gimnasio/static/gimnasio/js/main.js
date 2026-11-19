/* =========================================================
   SONIDOS Y ALERTA GLOBAL DE ACCESO
========================================================= */

function reproducirSonidoAcceso(tipo) {
  try {
    const audioContext = new (
      window.AudioContext || window.webkitAudioContext
    )();

    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();

    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);

    if (tipo === "success") {
      oscillator.frequency.setValueAtTime(880, audioContext.currentTime);
      oscillator.frequency.setValueAtTime(
        1200,
        audioContext.currentTime + 0.12,
      );
    } else if (tipo === "warning") {
      oscillator.frequency.setValueAtTime(600, audioContext.currentTime);
      oscillator.frequency.setValueAtTime(450, audioContext.currentTime + 0.15);
    } else {
      oscillator.frequency.setValueAtTime(220, audioContext.currentTime);
      oscillator.frequency.setValueAtTime(180, audioContext.currentTime + 0.18);
    }

    gainNode.gain.setValueAtTime(0.18, audioContext.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(
      0.001,
      audioContext.currentTime + 0.35,
    );

    oscillator.start(audioContext.currentTime);
    oscillator.stop(audioContext.currentTime + 0.35);
  } catch (error) {
    console.log("No se pudo reproducir sonido:", error);
  }
}

function cerrarAlertaGlobalAcceso() {
  const overlay = document.getElementById("globalAccessOverlay");

  if (overlay) {
    overlay.style.display = "none";
  }
}

function mostrarAlertaGlobalAcceso(tipo, cliente, mensaje) {
  const overlay = document.getElementById("globalAccessOverlay");
  const card = document.getElementById("globalAccessCard");
  const icon = document.getElementById("globalAccessIcon");
  const title = document.getElementById("globalAccessTitle");
  const client = document.getElementById("globalAccessClient");
  const message = document.getElementById("globalAccessMessage");

  if (!overlay || !card || !icon || !title || !client || !message) {
    alert(`${cliente}: ${mensaje}`);
    return;
  }

  card.classList.remove("success", "danger", "warning");

  if (tipo === "success") {
    card.classList.add("success");
    icon.innerHTML = `<i class="bx bx-check"></i>`;
    title.textContent = "ACCESO PERMITIDO";
  } else if (tipo === "warning") {
    card.classList.add("warning");
    icon.innerHTML = `<i class="bx bx-time-five"></i>`;
    title.textContent = "QR ESCANEADO RECIENTEMENTE";
  } else {
    card.classList.add("danger");
    icon.innerHTML = `<i class="bx bx-x"></i>`;
    title.textContent = "ACCESO DENEGADO";
  }

  client.textContent = cliente || "Cliente";
  message.textContent = mensaje || "Validación realizada.";

  overlay.style.display = "flex";

  reproducirSonidoAcceso(tipo);

  setTimeout(() => {
    cerrarAlertaGlobalAcceso();
  }, 5000);
}

/* =========================================================
   LIMPIAR CÓDIGO QR
========================================================= */

function extraerCodigoQrGlobal(texto) {
  let codigo = texto.trim();

  if (codigo.includes("/validar-qr/")) {
    const partes = codigo.split("/validar-qr/");
    codigo = partes[1].replaceAll("/", "");
  }

  return codigo;
}

/* =========================================================
   VALIDAR QR EN BACKEND
========================================================= */

let globalQrBloqueado = false;

async function validarQrGlobal(codigo) {
  if (globalQrBloqueado) return;

  globalQrBloqueado = true;

  try {
    const codigoLimpio = extraerCodigoQrGlobal(codigo);

    const response = await fetch(`/validar-qr/${codigoLimpio}/`);
    const data = await response.json();

    if (data.status === "ok" || data.status === "success") {
      mostrarAlertaGlobalAcceso(
        "success",
        data.cliente || "Cliente",
        data.motivo || data.mensaje || "Acceso permitido",
      );
    } else if (data.status === "duplicado") {
      mostrarAlertaGlobalAcceso(
        "warning",
        data.cliente || "Cliente",
        data.motivo || "Este QR ya fue escaneado recientemente.",
      );
    } else {
      mostrarAlertaGlobalAcceso(
        "danger",
        data.cliente || "Cliente no identificado",
        data.motivo || data.mensaje || "Acceso denegado",
      );
    }
  } catch (error) {
    console.error(error);

    mostrarAlertaGlobalAcceso(
      "danger",
      "Error",
      "No se pudo validar el código QR.",
    );
  }

  setTimeout(() => {
    globalQrBloqueado = false;
  }, 2500);
}

/* =========================================================
   ESCÁNER GLOBAL POR LECTOR USB TIPO TECLADO
========================================================= */

let globalQrBuffer = "";
let globalQrTimer = null;

document.addEventListener("keydown", function (event) {
  const target = event.target;
  const tag = target.tagName ? target.tagName.toLowerCase() : "";

  const escribiendoEnCampo =
    tag === "input" || tag === "textarea" || tag === "select";

  if (escribiendoEnCampo) {
    return;
  }

  if (globalQrTimer) {
    clearTimeout(globalQrTimer);
  }

  if (event.key === "Enter") {
    const codigo = globalQrBuffer.trim();

    globalQrBuffer = "";

    if (codigo.length >= 8) {
      validarQrGlobal(codigo);
    }

    return;
  }

  if (event.key.length === 1) {
    globalQrBuffer += event.key;
  }

  globalQrTimer = setTimeout(() => {
    globalQrBuffer = "";
  }, 500);
});

/* =========================================================
   ESCÁNER GLOBAL CON CÁMARA DEL TELÉFONO
========================================================= */

let globalCameraScanner = null;
let globalCameraActivo = false;
let globalCameraBloqueado = false;

function abrirEscanerGlobalCamara() {
  const modal = document.getElementById("globalCameraModal");
  const result = document.getElementById("globalCameraResult");

  if (!modal || !result) {
    alert("No se encontró el modal del escáner en base.html.");
    return;
  }

  if (typeof Html5QrcodeScanner === "undefined") {
    alert("No cargó la librería html5-qrcode. Revisa base.html.");
    return;
  }

  modal.style.display = "flex";
  result.className = "global-camera-result";
  result.textContent = "Iniciando cámara...";

  if (globalCameraActivo) return;

  globalCameraActivo = true;
  globalCameraBloqueado = false;

  globalCameraScanner = new Html5QrcodeScanner(
    "globalCameraReader",
    {
      fps: 8,
      qrbox: {
        width: 260,
        height: 260,
      },
    },
    false,
  );

  globalCameraScanner.render(onGlobalCameraScanSuccess);
}

function cerrarEscanerGlobalCamara() {
  const modal = document.getElementById("globalCameraModal");

  if (modal) {
    modal.style.display = "none";
  }

  if (globalCameraScanner) {
    globalCameraScanner
      .clear()
      .then(() => {
        globalCameraScanner = null;
        globalCameraActivo = false;
        globalCameraBloqueado = false;
      })
      .catch(() => {
        globalCameraScanner = null;
        globalCameraActivo = false;
        globalCameraBloqueado = false;
      });
  } else {
    globalCameraActivo = false;
    globalCameraBloqueado = false;
  }
}

async function onGlobalCameraScanSuccess(decodedText) {
  if (globalCameraBloqueado) return;

  globalCameraBloqueado = true;

  const result = document.getElementById("globalCameraResult");

  try {
    const codigo = extraerCodigoQrGlobal(decodedText);

    if (result) {
      result.className = "global-camera-result";
      result.textContent = "Validando acceso...";
    }

    const response = await fetch(`/validar-qr/${codigo}/`);
    const data = await response.json();

    if (data.status === "ok" || data.status === "success") {
      if (result) {
        result.className = "global-camera-result";
        result.innerHTML = `
                    ✅ ACCESO PERMITIDO<br>
                    ${data.cliente || "Cliente"}<br>
                    ${data.motivo || data.mensaje || "Acceso permitido"}
                `;
      }

      mostrarAlertaGlobalAcceso(
        "success",
        data.cliente || "Cliente",
        data.motivo || data.mensaje || "Acceso permitido",
      );
    } else if (data.status === "duplicado") {
      if (result) {
        result.className = "global-camera-result warning";
        result.innerHTML = `
                    ⚠️ QR ESCANEADO RECIENTEMENTE<br>
                    ${data.cliente || "Cliente"}<br>
                    ${data.motivo || "Este QR ya fue escaneado recientemente."}
                `;
      }

      mostrarAlertaGlobalAcceso(
        "warning",
        data.cliente || "Cliente",
        data.motivo || "Este QR ya fue escaneado recientemente.",
      );
    } else {
      if (result) {
        result.className = "global-camera-result error";
        result.innerHTML = `
                    ❌ ACCESO DENEGADO<br>
                    ${data.cliente || "Cliente"}<br>
                    ${data.motivo || data.mensaje || "Acceso denegado"}
                `;
      }

      mostrarAlertaGlobalAcceso(
        "danger",
        data.cliente || "Cliente",
        data.motivo || data.mensaje || "Acceso denegado",
      );
    }

    setTimeout(() => {
      cerrarEscanerGlobalCamara();
    }, 1200);
  } catch (error) {
    console.error(error);

    if (result) {
      result.className = "global-camera-result error";
      result.textContent = "Error al validar el QR.";
    }

    mostrarAlertaGlobalAcceso(
      "danger",
      "Error",
      "No se pudo validar el código QR.",
    );

    setTimeout(() => {
      globalCameraBloqueado = false;
    }, 2500);
  }
}

/* =========================================================
   BUSCADOR GLOBAL EN VIVO
========================================================= */

const globalSearchInput = document.getElementById("globalSearchInput");
const searchSuggestions = document.getElementById("searchSuggestions");

let searchTimer = null;

if (globalSearchInput && searchSuggestions) {
  globalSearchInput.addEventListener("input", function () {
    const query = this.value.trim();

    if (searchTimer) {
      clearTimeout(searchTimer);
    }

    if (query.length < 2) {
      searchSuggestions.classList.remove("show");
      searchSuggestions.innerHTML = "";
      return;
    }

    searchTimer = setTimeout(() => {
      buscarSugerenciasGlobales(query);
    }, 300);
  });

  document.addEventListener("click", function (event) {
    if (!event.target.closest(".navbar-search-wrapper")) {
      searchSuggestions.classList.remove("show");
    }
  });
}
async function buscarSugerenciasGlobales(query) {
  try {
    const response = await fetch(
      `/buscar/sugerencias/?q=${encodeURIComponent(query)}`,
    );

    if (!response.ok) {
      throw new Error("Error HTTP: " + response.status);
    }

    const data = await response.json();

    searchSuggestions.innerHTML = "";

    if (!data.resultados || data.resultados.length === 0) {
      searchSuggestions.innerHTML = `
        <div class="search-empty">
          No se encontraron resultados.
        </div>
      `;

      searchSuggestions.classList.add("show");
      return;
    }

    data.resultados.forEach((item) => {
      const div = document.createElement("div");
      div.className = "search-suggestion-item";

      div.innerHTML = `
        <div class="search-suggestion-top">
          <span class="search-suggestion-title">${item.titulo}</span>
          <span class="search-suggestion-type">${item.tipo}</span>
        </div>
        <span class="search-suggestion-subtitle">${item.subtitulo || ""}</span>
      `;

      div.addEventListener("click", function () {
        window.location.href = item.url;
      });

      searchSuggestions.appendChild(div);
    });

    const viewAll = document.createElement("div");
    viewAll.className = "search-view-all";
    viewAll.textContent = "Ver todos los resultados";

    viewAll.addEventListener("click", function () {
      window.location.href = `/buscar/?q=${encodeURIComponent(query)}`;
    });

    searchSuggestions.appendChild(viewAll);
    searchSuggestions.classList.add("show");
  } catch (error) {
    console.error("Error en búsqueda global:", error);

    searchSuggestions.innerHTML = `
      <div class="search-empty">
        Error al buscar resultados.
      </div>
    `;

    searchSuggestions.classList.add("show");
  }
}