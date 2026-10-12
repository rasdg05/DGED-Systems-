/**
 * Atlas Screen 0.1
 *
 * Cribado de un sitio industrial. No es un estudio de interconexión,
 * un balance hídrico ni una evaluación de la caseta.
 *
 * Los caveats se enseñan tal cual. No se parafrasean en la interfaz.
 */

export const MODEL_VERSION = "atlas-screen-0.1.0";

export const DEFAULT_WEIGHTS = {
  power: 0.28,
  logistics: 0.20,
  water: 0.18,
  labor: 0.12,
  climate: 0.12,
  security: 0.10,
};

const HEADROOM = {
  constrained: 0.55,
  tight: 0.75,
  moderate: 0.9,
  open: 1,
};

function round1(n) {
  return Math.round(n * 10) / 10;
}

function clamp(n, lo = 0, hi = 100) {
  return Math.min(hi, Math.max(lo, n));
}

function band(value, rows, fallback) {
  for (const [max, score] of rows) {
    if (value <= max) return score;
  }
  return fallback;
}

export function scorePower(features, scenario = {}) {
  if (features.distSubstationKm == null || features.headroom == null) {
    return {
      key: "power",
      score: null,
      missing: true,
      raw: null,
      caveats: ["Sin distancia a subestación o sin holgura regional firmada."],
    };
  }
  const mult = HEADROOM[features.headroom];
  if (mult == null) {
    return {
      key: "power",
      score: null,
      missing: true,
      raw: { headroom: features.headroom },
      caveats: ["Holgura regional fuera del catálogo."],
    };
  }
  let score = band(features.distSubstationKm, [[2, 100], [5, 80], [10, 55], [20, 30]], 10);
  const highVoltage =
    features.voltageKnown === true &&
    features.voltageKv != null &&
    features.voltageKv >= 115;
  if (!highVoltage) score = Math.min(score, 70);
  score *= mult;
  const loadMw = Number(scenario.loadMw ?? 0);
  const tight = features.headroom === "constrained" || features.headroom === "tight";
  if (loadMw > 30 && tight) score *= 0.5;
  else if (loadMw > 10 && tight) score *= 0.8;
  else if (loadMw > 30 && features.headroom === "moderate") score *= 0.85;
  return {
    key: "power",
    score: round1(clamp(score)),
    missing: false,
    raw: {
      distSubstationKm: features.distSubstationKm,
      voltageKnown: features.voltageKnown === true,
      voltageKv: features.voltageKv ?? null,
      headroom: features.headroom,
      loadMw,
    },
    caveats: [
      "Cribado. No estima megawatts disponibles en el predio ni sustituye un estudio de interconexión ante CENACE o CFE.",
    ],
  };
}

export function scoreWater(features, scenario = {}) {
  const table = { surplus: 92, equilibrium: 70, unknown: 45, deficit: 28 };
  if (features.aquiferStatus == null || table[features.aquiferStatus] == null) {
    return {
      key: "water",
      score: null,
      missing: true,
      raw: null,
      caveats: ["Sin acuífero publicado bajo el punto."],
    };
  }
  let drought = features.droughtD2PlusPct;
  if (scenario.droughtYear === true) drought = Math.max(drought ?? 0, 60);
  if (drought == null) {
    return {
      key: "water",
      score: null,
      missing: true,
      raw: { aquiferStatus: features.aquiferStatus },
      caveats: ["Sin corte del monitor de sequía."],
    };
  }
  const droughtMultiplier = band(drought, [[10, 1], [30, 0.9], [50, 0.75], [75, 0.6]], 0.45);
  return {
    key: "water",
    score: round1(clamp(table[features.aquiferStatus] * droughtMultiplier)),
    missing: false,
    raw: { aquiferStatus: features.aquiferStatus, droughtD2PlusPct: drought },
    caveats: [
      "Disponibilidad publicada del acuífero y sequía municipal. No es un balance del predio ni un título de concesión.",
    ],
  };
}

export function scoreLogistics(features, scenario = {}) {
  if (features.minutesToBorder == null || features.minutesToPort == null) {
    return {
      key: "logistics",
      score: null,
      missing: true,
      raw: null,
      caveats: ["Sin tiempo de ruta a la frontera de referencia o al puerto."],
    };
  }
  const extra = Number(scenario.extraMinutes ?? 0);
  const border = band(
    features.minutesToBorder + extra,
    [[90, 100], [150, 82], [210, 64], [300, 40]],
    22,
  );
  const port = band(
    features.minutesToPort + extra,
    [[180, 100], [270, 78], [360, 58], [480, 36]],
    18,
  );
  let score = border * 0.62 + port * 0.38;
  if (features.railWithin5Km === true) score = Math.min(100, score + 6);
  return {
    key: "logistics",
    score: round1(clamp(score)),
    missing: false,
    raw: {
      minutesToBorder: features.minutesToBorder + extra,
      minutesToPort: features.minutesToPort + extra,
      railWithin5Km: features.railWithin5Km === true,
    },
    caveats: [
      "Tiempo de manejo en ruta libre al cruce de referencia del corredor y al puerto de referencia. No incluye espera aduanal ni dwell de patio.",
    ],
  };
}

export function scoreLabor(features) {
  if (features.laborMarketPercentile == null) {
    return {
      key: "labor",
      score: null,
      missing: true,
      raw: null,
      caveats: ["Sin masa laboral municipal."],
    };
  }
  return {
    key: "labor",
    score: round1(clamp(features.laborMarketPercentile)),
    missing: false,
    raw: { laborMarketPercentile: features.laborMarketPercentile },
    caveats: [
      "Percentil municipal de masa laboral (IMSS/DENUE). No mide salario, rotación ni oficio disponible.",
    ],
  };
}

export function scoreClimate(features) {
  const floodTable = { none: 100, low: 82, medium: 55, high: 30, very_high: 12 };
  const seismicTable = { A: 94, B: 78, C: 48, D: 22 };
  if (
    features.floodClass == null ||
    floodTable[features.floodClass] == null ||
    features.seismicZone == null ||
    seismicTable[features.seismicZone] == null
  ) {
    return {
      key: "climate",
      score: null,
      missing: true,
      raw: null,
      caveats: ["Sin clase de inundación o sin zona sísmica."],
    };
  }
  const landslide = features.landslideHigh === true ? 35 : 90;
  const score =
    floodTable[features.floodClass] * 0.7 +
    seismicTable[features.seismicZone] * 0.2 +
    landslide * 0.1;
  return {
    key: "climate",
    score: round1(clamp(score)),
    missing: false,
    raw: {
      floodClass: features.floodClass,
      seismicZone: features.seismicZone,
      landslideHigh: features.landslideHigh === true,
    },
    caveats: [
      "Peligro del entorno del punto. No es pérdida anual esperada ni una prima de seguro. La zona sísmica A es la de menor peligro.",
    ],
  };
}

export function scoreSecurity(features) {
  if (features.safetyPercentile == null) {
    return {
      key: "security",
      score: null,
      missing: true,
      raw: null,
      caveats: ["Sin incidencia municipal."],
    };
  }
  return {
    key: "security",
    score: round1(clamp(features.safetyPercentile)),
    missing: false,
    raw: { safetyPercentile: features.safetyPercentile },
    caveats: [
      "Contexto municipal de incidencia. No describe la caseta, el patio ni el tramo del turno de noche.",
    ],
  };
}

export function scoreSite(features, options = {}) {
  const weights = { ...DEFAULT_WEIGHTS, ...(options.weights ?? {}) };
  const scenario = options.scenario ?? {};
  const factors = [
    scorePower(features, scenario),
    scoreLogistics(features, scenario),
    scoreWater(features, scenario),
    scoreLabor(features),
    scoreClimate(features),
    scoreSecurity(features),
  ];
  const totalWeight = Object.values(weights).reduce((sum, weight) => sum + weight, 0);
  let presentWeight = 0;
  let weighted = 0;
  for (const factor of factors) {
    const weight = weights[factor.key] ?? 0;
    if (factor.score == null) continue;
    presentWeight += weight;
    weighted += weight * factor.score;
  }
  const composite = presentWeight > 0 ? round1(weighted / presentWeight) : null;
  const coverage = totalWeight > 0 ? round1(presentWeight / totalWeight) : 0;
  const power = factors.find((factor) => factor.key === "power");
  const publishable = composite != null && coverage >= 0.75 && power?.score != null;
  return {
    modelVersion: MODEL_VERSION,
    composite,
    coverage,
    publishable,
    factors,
    weights,
    scenario,
  };
}

export function rankSites(items) {
  return [...items].sort((a, b) => {
    if (a.publishable !== b.publishable) return a.publishable ? -1 : 1;
    return (b.composite ?? -1) - (a.composite ?? -1);
  });
}
