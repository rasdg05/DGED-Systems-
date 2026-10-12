const state = {
  corridor: "",
  sites: [],
  selected: null,
  scoring: false,
};

const list = document.querySelector("#site-list");
const detail = document.querySelector("#detail");
const scoreButton = document.querySelector("#score-all");
const sourcesEl = document.querySelector("#sources");

const map = new maplibregl.Map({
  container: "map",
  style: {
    version: 8,
    glyphs: "https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf",
    sources: {
      carto: {
        type: "raster",
        tiles: ["https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png"],
        tileSize: 256,
        attribution: "© OpenStreetMap © CARTO",
      },
    },
    layers: [{ id: "carto", type: "raster", source: "carto" }],
  },
  center: [-101.1, 23.4],
  zoom: 5.1,
});

map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-right");

const toggles = document.createElement("div");
toggles.className = "map-toggle";
toggles.innerHTML = `
  <label><input type="checkbox" data-layer="municipios" /> Municipios INEGI</label>
  <label><input type="checkbox" data-layer="uso_suelo" checked /> Uso de suelo</label>
  <label><input type="checkbox" data-layer="inundacion" /> Inundación</label>
`;
map.getContainer().appendChild(toggles);

function scoreClass(value) {
  if (value == null) return "";
  if (value >= 75) return "good";
  if (value >= 55) return "mid";
  return "bad";
}

function markerColor(value) {
  if (value == null) return "#e2a85a";
  if (value >= 75) return "#9cbf86";
  if (value >= 55) return "#e0c36a";
  return "#e07a68";
}

const markers = new Map();

function drawMarkers() {
  for (const site of state.sites) {
    const value = site.score ? site.score.composite : null;
    let marker = markers.get(site.id);
    if (!marker) {
      const el = document.createElement("button");
      el.className = "map-pin";
      el.style.cssText = "width:14px;height:14px;border-radius:99px;border:2px solid #101210;padding:0";
      el.addEventListener("click", () => select(site.id));
      marker = new maplibregl.Marker({ element: el }).setLngLat([site.lon, site.lat]).addTo(map);
      markers.set(site.id, marker);
    }
    marker.getElement().style.background = markerColor(value);
    marker.getElement().setAttribute("aria-label", site.name);
  }
}

function renderList() {
  const rows = state.sites.filter((site) => !state.corridor || site.corridor === state.corridor);
  list.innerHTML = "";
  for (const site of rows) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "site" + (state.selected === site.id ? " on" : "");
    const value = site.score && site.score.composite != null ? site.score.composite.toFixed(1) : null;
    const klass = scoreClass(site.score ? site.score.composite : null);
    button.innerHTML = `
      <div class="row">
        <strong>${site.name}</strong>
        ${value == null ? '<span class="pending">sin calificar</span>' : `<span class="score ${klass}">${value}</span>`}
      </div>
      <small>${site.corridorName}${site.observation && site.observation.municipality ? " · " + site.observation.municipality : ""}</small>
    `;
    button.addEventListener("click", () => select(site.id, true));
    list.appendChild(button);
  }
}

function factorLine(factor) {
  const raw = factor.raw || {};
  const windowText = Array.isArray(raw.window) && raw.window.length
    ? raw.window.map((row) => [row.name, row.activity, row.staff].filter(Boolean).join(" · ")).join(" / ")
    : null;
  const score = factor.score == null ? "—" : factor.score.toFixed(1);
  return `
    <div class="factor">
      <div class="row"><strong>${factor.label}</strong><span class="score ${scoreClass(factor.score)}">${score}</span></div>
      <p class="raw">${windowText || JSON.stringify(raw)}</p>
      <p>${(factor.caveats || []).join(" ")}</p>
    </div>
  `;
}

function km(value) {
  return value == null ? null : `${Number(value).toLocaleString("es-MX", { maximumFractionDigits: 2 })} km`;
}

function layerRow(label, known, text, source) {
  return `
    <div class="layer">
      <div class="row"><strong>${label}</strong><span class="${known ? "ok" : "bad"}">${known ? source : "sin respuesta"}</span></div>
      <p>${text}</p>
    </div>
  `;
}

// Las cuatro capas sin clave (D-009). Sismicidad y vía férrea también están en los factores;
// clima y subestación solo se muestran: no puntúan.
function layersBlock(obs) {
  if (obs.seismicKnown === undefined) return "";
  const strongest = obs.seismicStrongest;
  const seismic = obs.seismicKnown
    ? (obs.seismicCount
      ? `${obs.seismicCount} sismos M4+ en 100 km desde hace 50 años. Máximo M${obs.seismicMaxMagnitude}${strongest ? ` (${strongest.date}, ${strongest.place})` : ""}.`
      : "Ningún sismo M4+ registrado en 100 km en 50 años.")
    : "USGS no respondió; no entra al número.";
  const climate = obs.climateKnown
    ? `Lluvia media ${Number(obs.climatePrecipMm).toLocaleString("es-MX")} mm/año y ${obs.climateHotDays} días/año arriba de 35 °C (${obs.climatePeriod}). Celda de reanálisis, no una estación. No puntúa.`
    : "NASA POWER no respondió.";
  let substation = "Overpass no respondió.";
  if (obs.osmKnown) {
    substation = obs.substationDistanceKm == null
      ? "OSM no tiene subestación pública mapeada en 25 km."
      : `${obs.substationName || "Sin nombre en OSM"} a ${km(obs.substationDistanceKm)} en línea recta · ${obs.substationVoltageKv == null ? "voltaje desconocido" : obs.substationVoltageKv + " kV (tag OSM)"}${obs.substationOperator ? " · " + obs.substationOperator : ""}.`;
    substation += " OSM puede estar incompleto. No dice cuánta carga se puede conectar; eso es un estudio de CFE/CENACE. No puntúa.";
  }
  let rail = "Overpass no respondió; no entra al número.";
  if (obs.osmKnown) {
    rail = obs.railDistanceKm == null
      ? `Sin vía mapeada en ${obs.railRadiusKm || 10} km.`
      : `Vía a ${km(obs.railDistanceKm)} en línea recta${obs.railName ? " · " + obs.railName : ""}${obs.railOperator ? " · " + obs.railOperator : ""}.`;
    rail += " OSM puede estar incompleto; no es un ramal al predio.";
  }
  return `
    <h3 class="layers-title">Capas sin clave</h3>
    ${layerRow("Sismicidad", obs.seismicKnown, seismic, "USGS")}
    ${layerRow("Clima", obs.climateKnown, climate, "NASA POWER")}
    ${layerRow("Subestación aprox.", obs.osmKnown, substation, "OSM")}
    ${layerRow("Vía férrea", obs.osmKnown, rail, "OSM")}
  `;
}

function renderDetail(payload) {
  if (!payload) {
    detail.innerHTML = `<p class="empty">Elige un sitio.</p>`;
    return;
  }
  const score = payload.score;
  const obs = payload.observation || {};
  const objects = payload.graph ? payload.graph.objects : [];
  detail.innerHTML = `
    <p class="kicker">${payload.corridorName}</p>
    <h2>${payload.name}</h2>
    <p class="meta">${obs.municipality ? obs.municipality + (obs.state ? ", " + obs.state : "") : "Municipio todavía no consultado"}${obs.population ? " · " + Number(obs.population).toLocaleString("es-MX") + " hab. (2020)" : ""} · ${payload.lat.toFixed(4)}, ${payload.lon.toFixed(4)}</p>
    ${score ? `
      <p class="composite ${scoreClass(score.composite)}">${score.composite == null ? "—" : score.composite.toFixed(1)}</p>
      <p class="risk">Viabilidad ${score.modelVersion}. Riesgo complementario ${score.risk == null ? "—" : score.risk.toFixed(1)}. ${score.publishable ? "Publicable." : "Borrador: falta una de las tres fuentes."}</p>
      ${score.publishable ? "" : '<p class="unpublished">No se entrega a un cliente mientras falte sequía, inundación o uso de suelo.</p>'}
      ${score.factors.map(factorLine).join("")}
      ${layersBlock(obs)}
    ` : `<p class="empty">${payload.note}</p>`}
    ${objects.length ? `<ul class="objects">${objects.map((object) => `<li><b>${object.type}</b> ${object.name || object.category || object.landClass || (object.maxMagnitude != null ? "M" + object.maxMagnitude : null) || object.reason || object.id}</li>`).join("")}</ul>` : ""}
  `;
}

async function select(id, fly = false) {
  state.selected = id;
  renderList();
  const response = await fetch(`/api/sites/${id}`);
  const payload = await response.json();
  const known = state.sites.find((site) => site.id === id);
  if (known && known.score && !payload.score) payload.score = known.score;
  if (known && known.observation) payload.observation = { ...known.observation, ...payload.observation };
  renderDetail(payload);
  if (fly) map.flyTo({ center: [payload.lon, payload.lat], zoom: 10 });
}

async function loadSites() {
  const response = await fetch("/api/sites");
  const payload = await response.json();
  state.sites = payload.sites;
  renderList();
  drawMarkers();
}

async function scoreAll() {
  if (state.scoring) return;
  state.scoring = true;
  scoreButton.disabled = true;
  const droughtYear = document.querySelector("#drought-year").checked;
  const targets = state.sites.filter((site) => !state.corridor || site.corridor === state.corridor);
  for (const site of targets) {
    scoreButton.textContent = `Calificando ${site.name}`;
    const response = await fetch(`/api/sites/${site.id}/score?drought_year=${droughtYear ? "true" : "false"}`, { method: "POST" });
    if (!response.ok) continue;
    const payload = await response.json();
    const index = state.sites.findIndex((item) => item.id === site.id);
    state.sites[index] = payload;
    renderList();
    drawMarkers();
    if (state.selected === site.id) renderDetail(payload);
  }
  state.scoring = false;
  scoreButton.disabled = false;
  scoreButton.textContent = "Calificar sitios";
}

async function showSources() {
  if (!sourcesEl.hidden) {
    sourcesEl.hidden = true;
    return;
  }
  const response = await fetch("/api/sources");
  const sources = await response.json();
  const examples = await fetch("/api/examples").then((result) => result.json());
  const blocks = Object.entries(sources).map(([key, value]) => {
    const ok = value.ok === true;
    return `<div class="source"><strong>${key}</strong> <span class="${ok ? "ok" : "bad"}">${ok ? "responde" : "sin dato útil"}</span><br />${value.note || value.reason || value.error || ""}<br /><a href="${value.url || "#"}" target="_blank" rel="noreferrer">${value.url || ""}</a></div>`;
  }).join("");
  const calls = (examples.calls || []).slice(0, 4).map((call) => `<div class="source">${call.label}<br /><a href="${call.url}" target="_blank" rel="noreferrer">${call.url}</a></div>`).join("");
  sourcesEl.innerHTML = `<h2>Fuentes de esta sesión</h2>${blocks}<h2>Consultas reales</h2>${calls || "<p class='empty'>Aparecen al calificar un sitio.</p>"}`;
  sourcesEl.hidden = false;
}

document.querySelectorAll(".chip").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".chip").forEach((chip) => chip.classList.remove("on"));
    button.classList.add("on");
    state.corridor = button.dataset.corridor;
    renderList();
  });
});

scoreButton.addEventListener("click", scoreAll);
document.querySelector("#toggle-sources").addEventListener("click", showSources);
document.querySelector("#drought-year").addEventListener("change", () => {
  for (const site of state.sites) site.score = null;
  renderList();
  drawMarkers();
  if (state.selected) renderDetail(state.sites.find((site) => site.id === state.selected));
});

map.on("load", () => {
  for (const key of ["municipios", "uso_suelo", "inundacion"]) {
    map.addSource(key, {
      type: "raster",
      tiles: [`${location.origin}/api/wms/${key}/{z}/{x}/{y}.png`],
      tileSize: 256,
    });
    map.addLayer({
      id: key,
      type: "raster",
      source: key,
      layout: { visibility: key === "uso_suelo" ? "visible" : "none" },
      paint: { "raster-opacity": key === "municipios" ? 0.55 : 0.72 },
    });
  }
  toggles.querySelectorAll("input").forEach((input) => {
    input.addEventListener("change", () => {
      map.setLayoutProperty(input.dataset.layer, "visibility", input.checked ? "visible" : "none");
    });
  });
});

loadSites();
