import test from "node:test";import assert from "node:assert/strict";
import {cycleMarker,shouldRunMonthly} from "../monthly.mjs";
test("día 3 corre si falta corte",()=>assert.equal(shouldRunMonthly({event:"schedule",month:"2026-11",comments:[]}),true));
test("día 4 omite ciclo si ya fue informado",()=>assert.equal(shouldRunMonthly({event:"schedule",month:"2026-11",comments:[{body:"OK "+cycleMarker("2026-11")}]}),false));
test("mes siguiente tiene ciclo independiente",()=>assert.equal(shouldRunMonthly({event:"schedule",month:"2026-12",comments:[cycleMarker("2026-11")]}),true));
test("prueba manual permitida sin bloquear por calendario",()=>assert.equal(shouldRunMonthly({event:"workflow_dispatch",month:"2026-11",comments:[cycleMarker("2026-11")]}),true));
