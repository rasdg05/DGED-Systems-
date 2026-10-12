import assert from "node:assert/strict";
import test from "node:test";
import { rankSites, scoreSite } from "./score.mjs";

const ready = {
  distSubstationKm: 1.4,
  voltageKnown: true,
  voltageKv: 115,
  headroom: "open",
  aquiferStatus: "equilibrium",
  droughtD2PlusPct: 8,
  minutesToBorder: 130,
  minutesToPort: 300,
  railWithin5Km: true,
  laborMarketPercentile: 70,
  floodClass: "low",
  seismicZone: "A",
  landslideHigh: false,
  safetyPercentile: 55,
};

test("un sitio completo es publicable y no esconde caveats", () => {
  const result = scoreSite(ready);
  assert.equal(result.publishable, true);
  assert.equal(result.coverage, 1);
  assert.ok(result.composite > 70);
  const power = result.factors.find((factor) => factor.key === "power");
  assert.match(power.caveats[0], /No estima megawatts/);
});

test("sin voltaje confirmado el factor eléctrico no pasa de 70", () => {
  const high = scoreSite(ready);
  const unknown = scoreSite({ ...ready, voltageKnown: false, voltageKv: null });
  const powerHigh = high.factors.find((factor) => factor.key === "power").score;
  const powerUnknown = unknown.factors.find((factor) => factor.key === "power").score;
  assert.equal(powerHigh, 100);
  assert.equal(powerUnknown, 70);
  assert.ok(unknown.composite < high.composite);
});

test("40 MW sobre holgura apretada cambia el ranking", () => {
  const northFeatures = {
    ...ready,
    headroom: "tight",
    minutesToBorder: 80,
    minutesToPort: 240,
    railWithin5Km: true,
  };
  const southFeatures = {
    ...ready,
    headroom: "open",
    minutesToBorder: 280,
    minutesToPort: 450,
    railWithin5Km: false,
  };
  const north = scoreSite(northFeatures);
  const south = scoreSite(southFeatures);
  const northLoaded = scoreSite(northFeatures, { scenario: { loadMw: 40 } });
  const baseOrder = rankSites([
    { name: "north", ...north },
    { name: "south", ...south },
  ]).map((item) => item.name);
  const loadedOrder = rankSites([
    { name: "north", ...northLoaded },
    { name: "south", ...south },
  ]).map((item) => item.name);
  assert.deepEqual(baseOrder, ["north", "south"]);
  assert.deepEqual(loadedOrder, ["south", "north"]);
  const loadedPower = northLoaded.factors.find((factor) => factor.key === "power").score;
  assert.equal(loadedPower, 37.5);
});

test("un año seco baja el agua y no toca la energía", () => {
  const base = scoreSite(ready);
  const dry = scoreSite(ready, { scenario: { droughtYear: true } });
  const water = (result) => result.factors.find((factor) => factor.key === "water").score;
  const power = (result) => result.factors.find((factor) => factor.key === "power").score;
  assert.ok(water(dry) < water(base));
  assert.equal(power(dry), power(base));
  assert.equal(dry.factors.find((factor) => factor.key === "water").raw.droughtD2PlusPct, 60);
});

test("sin energía no se publica aunque el resto esté lleno", () => {
  const result = scoreSite({ ...ready, distSubstationKm: null, headroom: null });
  assert.equal(result.publishable, false);
  assert.ok(result.coverage < 0.75);
  assert.equal(result.composite == null, false);
});

test("los pesos del cliente se guardan y mueven el compuesto", () => {
  const normal = scoreSite({ ...ready, safetyPercentile: 10, laborMarketPercentile: 10 });
  const securityHeavy = scoreSite(
    { ...ready, safetyPercentile: 10, laborMarketPercentile: 10 },
    { weights: { power: 0.05, logistics: 0.05, water: 0.05, labor: 0.05, climate: 0.05, security: 0.75 } },
  );
  assert.ok(securityHeavy.composite < normal.composite);
  assert.equal(securityHeavy.weights.security, 0.75);
});
