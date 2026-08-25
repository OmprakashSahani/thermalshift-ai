"use strict";

const schedulerLabels = {
  first_available: "First Available",
  capacity_only: "Capacity Only",
  thermalshift: "ThermalShift",
};

const state = { evidence: null, window: null, scheduler: "thermalshift", labWindow: null,
  gpu: 16, duration: 2, scenario: null, eligibleSiteIds: new Set() };

const byId = (id) => document.getElementById(id);
const percent = (value) => `${(Number(value) * 100).toFixed(1)}%`;
const exposure = (value) => Number(value).toFixed(3);
const timestamp = (value) => value.replace("T", " ").replace(":00Z", "Z");

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function button(label, active, onClick) {
  const node = element("button", `switch-button${active ? " active" : ""}`, label);
  node.type = "button";
  node.setAttribute("aria-pressed", String(active));
  node.addEventListener("click", onClick);
  return node;
}

function comparisonFor(baseline) {
  return state.window.comparisons.find((item) => item.baseline_scheduler === baseline);
}

function schedulerRun(name) {
  return state.window.schedulers.find((item) => item.scheduler_name === name);
}

function renderWindowSwitcher() {
  const host = byId("window-switcher");
  host.replaceChildren();
  state.evidence.windows.forEach((window) => {
    const label = window.is_primary ? `${window.label} · Primary` : `${window.label} · Robustness`;
    host.append(button(label, window.window_id === state.window.window_id, () => {
      state.window = window;
      render();
    }));
  });
}

function statCard(value, label, detail, primary = false) {
  const card = element("article", `stat-card${primary ? " primary" : ""}`);
  card.append(element("span", "stat-value", value));
  card.append(element("span", "stat-label", label));
  card.append(element("span", "stat-detail", detail));
  return card;
}

function renderHero() {
  byId("evidence-label").textContent = state.evidence.evidence_label;
  byId("hero-context").textContent = state.window.scenario_description;
  const provenance = state.window.provenance;
  byId("window-detail").textContent = `${provenance.replay_start_utc} · ${provenance.replay_slot_count} hourly slots`;

  const host = byId("hero-stats");
  host.replaceChildren();
  const thermalshift = schedulerRun("thermalshift");
  if (state.window.is_primary) {
    const first = comparisonFor("first_available");
    const capacity = comparisonFor("capacity_only");
    host.append(statCard(
      `${Number(first.thermal_exposure_reduction_pct).toFixed(1)}% lower`,
      "modeled ambient thermal exposure",
      "vs First Available",
      true,
    ));
    host.append(statCard(
      `${Number(capacity.thermal_exposure_reduction_pct).toFixed(1)}% lower`,
      "modeled exposure",
      "vs Capacity Only",
    ));
  } else {
    host.append(statCard(
      `${exposure(thermalshift.total_thermal_exposure_stress_hours)} stress-hours`,
      "modeled stress floor reached",
      "Winter robustness evidence",
      true,
    ));
    host.append(statCard(
      "Small positive baselines",
      "floor-sensitive comparison",
      "See interpretation below",
    ));
  }
  host.append(statCard(
    `${thermalshift.scheduled_count}/${thermalshift.total_workloads}`,
    "workloads scheduled",
    "same set across schedulers",
  ));
  host.append(statCard(
    percent(thermalshift.deadline_satisfaction_rate),
    "deadline satisfaction",
    "completion preserved",
  ));
}

function renderComparison() {
  const floor = byId("zero-floor-note");
  floor.hidden = !state.window.zero_floor.applies;
  floor.textContent = state.window.zero_floor.message || "";

  const maxExposure = Math.max(
    ...state.window.schedulers.map((run) => Number(run.total_thermal_exposure_stress_hours)),
  );
  const host = byId("comparison-list");
  host.replaceChildren();
  state.window.schedulers.forEach((run) => {
    const row = element("article", `scheduler-row ${run.scheduler_name}`);
    const name = element("div", "scheduler-name", schedulerLabels[run.scheduler_name]);
    if (run.scheduler_name === "thermalshift") name.append(element("small", "", "Thermal-aware optimizer"));
    const chart = element("div", "exposure-chart");
    const track = element("div", "bar-track");
    const bar = element("div", "bar");
    const ratio = maxExposure === 0 ? 0 : Number(run.total_thermal_exposure_stress_hours) / maxExposure;
    bar.style.width = `${Math.max(0, ratio * 100)}%`;
    track.append(bar);
    chart.append(track, element("div", "exposure-value", `${exposure(run.total_thermal_exposure_stress_hours)} stress-hours`));

    const metrics = element("div", "metric-grid");
    [
      ["Completion", percent(run.completion_rate)],
      ["Deadlines", percent(run.deadline_satisfaction_rate)],
      ["Mean stress", Number(run.mean_occupied_thermal_stress).toFixed(3)],
      ["Peak stress", Number(run.peak_occupied_thermal_stress).toFixed(3)],
    ].forEach(([label, value]) => {
      const metric = element("div", "");
      metric.append(element("span", "", label), element("strong", "", value));
      metrics.append(metric);
    });
    row.append(name, chart, metrics);
    host.append(row);
  });

  const valid = state.window.comparisons.every((item) =>
    item.direct_thermal_comparison_valid && item.same_scheduled_workload_set
      && item.completion_preserved && item.deadline_satisfaction_preserved
  );
  byId("fairness-note").textContent = valid
    ? `Fairness gate passed: every scheduler placed the same ${state.window.workload_count} workloads and preserved completion and deadlines.`
    : "Direct comparison is unavailable because the fairness gate did not pass.";
}

function renderSchedulerSwitcher() {
  const host = byId("scheduler-switcher");
  host.replaceChildren();
  state.window.schedulers.forEach((run) => {
    host.append(button(schedulerLabels[run.scheduler_name], run.scheduler_name === state.scheduler, () => {
      state.scheduler = run.scheduler_name;
      renderSchedulerSwitcher();
      renderDecisions();
    }));
  });
}

function renderDecisions() {
  const run = schedulerRun(state.scheduler);
  const groups = new Map(state.window.sites.map((site) => [site.site_id, []]));
  run.decisions.forEach((decision) => groups.get(decision.site_id).push(decision));
  const host = byId("decision-groups");
  host.replaceChildren();
  state.window.sites.forEach((site) => {
    const decisions = groups.get(site.site_id);
    if (!decisions.length) return;
    const group = element("article", "decision-group");
    const heading = element("h3", "");
    heading.append(document.createTextNode(site.location), element("span", "", `${decisions.length} placement${decisions.length === 1 ? "" : "s"}`));
    const table = element("table", "decision-table");
    table.innerHTML = "<thead><tr><th scope=\"col\">Workload</th><th scope=\"col\">UTC start</th><th scope=\"col\">UTC end</th><th scope=\"col\">Exposure</th></tr></thead>";
    const body = document.createElement("tbody");
    decisions.forEach((decision) => {
      const row = document.createElement("tr");
      [decision.workload_id, timestamp(decision.start_time), timestamp(decision.end_time)].forEach((value) => {
        row.append(element("td", "", value));
      });
      const value = element("td", "");
      value.append(element("span", "exposure-pill", exposure(decision.thermal_exposure)));
      row.append(value);
      body.append(row);
    });
    table.append(body);
    group.append(heading, table);
    host.append(group);
  });
}

function renderSites() {
  const host = byId("site-grid");
  host.replaceChildren();
  const capacities = [...new Set(state.window.sites.map((site) => site.modeled_gpu_capacity))];
  const capacityLabel = capacities.length === 1 ? `${capacities[0]}-GPU capacities` : "GPU capacities";
  byId("modeled-classification").textContent = `Sites, ${capacityLabel}, workloads, thermal-stress metric`;
  state.window.sites.forEach((site) => {
    const card = element("article", "site-card");
    card.append(element("span", "site-class", site.classification));
    card.append(element("h3", "", site.location));
    const data = element("div", "site-data");
    const capacity = element("span", "");
    capacity.append(document.createTextNode("Capacity · "), element("strong", "", `${site.modeled_gpu_capacity} modeled GPUs`));
    const timezone = element("span", "");
    timezone.append(document.createTextNode("Timezone · "), element("strong", "", site.timezone));
    const coordinates = element("span", "");
    coordinates.append(document.createTextNode("Coordinates · "), element("strong", "", `${site.latitude}, ${site.longitude}`));
    data.append(capacity, timezone, coordinates);
    card.append(data);
    host.append(card);
  });
}

function renderMethodAndBoundary() {
  const provenance = state.window.provenance;
  const host = byId("provenance");
  host.replaceChildren();
  [
    `${provenance.calibration_observation_count} calibration observations`,
    `${provenance.calibration_rule.replaceAll("_", " ").toUpperCase()}`,
    `${provenance.calibration_lower_reference_c}°C lower reference`,
    `${provenance.calibration_upper_reference_c}°C upper reference`,
    `${provenance.replay_slot_count} replay slots`,
  ].forEach((value) => host.append(element("span", "", value)));

  const boundaries = state.window.scientific_boundaries;
  byId("modeled-metric").textContent = boundaries.modeled_metric;
  const list = byId("boundary-list");
  list.replaceChildren();
  boundaries.not_measured_or_proven.forEach((item) => list.append(element("li", "", item)));
  if (!boundaries.not_measured_or_proven.includes("facility savings")) {
    list.append(element("li", "", "facility savings"));
  }
}

function render() {
  renderWindowSwitcher();
  renderHero();
  renderComparison();
  renderSchedulerSwitcher();
  renderDecisions();
  renderSites();
  renderMethodAndBoundary();
  if (!state.labWindow) state.labWindow = state.evidence.windows[0];
  if (!state.eligibleSiteIds.size) {
    state.eligibleSiteIds = new Set(state.labWindow.sites.map((site) => site.site_id));
  }
  renderScenarioControls();
}

function preset(hostId, values, selected, labeler, choose) {
  const host = byId(hostId); host.replaceChildren();
  values.forEach((value) => host.append(button(labeler(value), value === selected, () => {
    choose(value); renderScenarioControls();
  })));
}

function renderScenarioControls() {
  preset("lab-window", state.evidence.windows, state.labWindow, (item) => item.label, (item) => {
    state.labWindow = item; state.scenario = null; byId("scenario-result").hidden = true;
  });
  preset("gpu-presets", [8, 16, 24, 32, 48, 64], state.gpu, (v) => `${v}`, (v) => { state.gpu = v; });
  preset("duration-presets", [1, 2, 3], state.duration, (v) => `${v}h`, (v) => { state.duration = v; });
  const sites = byId("site-controls"); sites.replaceChildren();
  state.labWindow.sites.forEach((site) => {
    const label = element("label", "site-toggle");
    const input = document.createElement("input"); input.type = "checkbox"; input.value = site.site_id;
    input.checked = state.eligibleSiteIds.has(site.site_id);
    input.addEventListener("change", () => {
      if (input.checked) state.eligibleSiteIds.add(site.site_id);
      else state.eligibleSiteIds.delete(site.site_id);
    });
    label.append(input, document.createTextNode(site.location.split(",")[0])); sites.append(label);
  });
  updateOffsets();
  renderLandscape(state.scenario ? state.scenario.thermal_landscape : null);
}

function offsetTime(offset) {
  const start = new Date(state.labWindow.provenance.replay_start_utc);
  start.setUTCHours(start.getUTCHours() + Number(offset));
  return `${String(start.getUTCHours()).padStart(2, "0")}:00 UTC`;
}

function updateOffsets() {
  byId("release-time").textContent = offsetTime(byId("release-offset").value);
  byId("deadline-time").textContent = offsetTime(byId("deadline-offset").value);
}

function renderLandscape(entries) {
  const host = byId("thermal-landscape"); host.replaceChildren();
  if (!entries) { host.append(element("p", "", "Run ThermalShift to load the sanitized historical grid.")); return; }
  const table = element("table", "landscape-table");
  const times = [...new Set(entries.map((item) => item.timestamp_utc))];
  const head = document.createElement("thead"); const hr = document.createElement("tr");
  const corner = element("th", "", "Modeled site"); corner.scope = "col"; hr.append(corner);
  times.forEach((time) => { const heading = element("th", "", timestamp(time).slice(11)); heading.scope = "col"; hr.append(heading); }); head.append(hr);
  const body = document.createElement("tbody");
  state.labWindow.sites.forEach((site) => {
    const row = document.createElement("tr"); const heading = element("th", "", site.location.split(",")[0]); heading.scope = "row"; row.append(heading);
    times.forEach((time) => {
      const item = entries.find((entry) => entry.site_id === site.site_id && entry.timestamp_utc === time);
      const cell = element("td", "stress-cell", `${Number(item.thermal_stress_score).toFixed(2)} · ${Number(item.temperature_c).toFixed(1)}°C`);
      cell.style.setProperty("--stress", Number(item.thermal_stress_score)); row.append(cell);
    }); body.append(row);
  }); table.append(head, body); host.append(table);
}

function renderScenarioResult(result) {
  const host = byId("scenario-cards"); host.replaceChildren();
  result.schedulers.forEach((run) => {
    const custom = run.whatif; const card = element("article", `result-card ${run.scheduler_name}`);
    card.append(element("h3", "", schedulerLabels[run.scheduler_name]));
    card.append(element("strong", `placement-status ${custom.status}`, custom.status.toUpperCase()));
    if (custom.status === "scheduled") {
      card.append(element("p", "result-location", state.labWindow.sites.find((s) => s.site_id === custom.site_id).location));
      card.append(element("p", "", `${timestamp(custom.start_utc)} → ${timestamp(custom.end_utc)}`));
      card.append(element("p", "", `${exposure(custom.thermal_exposure)} custom stress-hours · ${exposure(custom.mean_modeled_stress)} mean stress`));
    } else card.append(element("p", "", custom.reason));
    card.append(element("p", "whole-metrics", `${run.scheduled_count}/${run.total_workload_count} workloads · ${percent(run.deadline_satisfaction_rate)} deadlines · ${exposure(run.total_thermal_exposure_stress_hours)} total stress-hours`));
    host.append(card);
  });
  const valid = result.comparisons.every((item) => item.direct_thermal_comparison_valid);
  byId("scenario-fairness").textContent = valid
    ? "Fairness comparison valid: all schedulers placed the same workload set."
    : "Direct percentage unavailable: scheduled workload sets differ.";
  byId("scenario-statement").textContent = `${result.statement} ${result.comparison_boundary}`;
  byId("scenario-result").hidden = false; renderLandscape(result.thermal_landscape);
}

byId("release-offset").addEventListener("input", updateOffsets);
byId("deadline-offset").addEventListener("input", updateOffsets);
byId("scenario-form").addEventListener("submit", async (event) => {
  event.preventDefault(); const submit = byId("run-scenario"); const error = byId("scenario-error");
  submit.disabled = true; submit.textContent = "RUNNING SCHEDULERS…"; error.textContent = "";
  state.scenario = null; byId("scenario-result").hidden = true;
  const eligible = [...document.querySelectorAll("#site-controls input:checked")].map((item) => item.value);
  try {
    const response = await fetch("/api/scenario", { method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" }, body: JSON.stringify({ window_id: state.labWindow.window_id, gpu_demand: state.gpu, duration_hours: state.duration, release_offset_hours: Number(byId("release-offset").value), deadline_offset_hours: Number(byId("deadline-offset").value), eligible_site_ids: eligible }) });
    const data = await response.json();
    if (!response.ok) {
      const detail = Array.isArray(data.detail) ? data.detail[0]?.msg : data.detail;
      throw new Error(typeof detail === "string" ? detail : `Request failed (${response.status})`);
    }
    state.scenario = data; renderScenarioResult(data);
  } catch (problem) { error.textContent = problem instanceof Error ? problem.message : "Scenario request failed."; }
  finally { submit.disabled = false; submit.textContent = "RUN THERMALSHIFT"; }
});

async function initialize() {
  try {
    const response = await fetch("/api/evidence", { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error(`Evidence endpoint returned ${response.status}`);
    state.evidence = await response.json();
    state.window = state.evidence.windows.find(
      (window) => window.window_id === state.evidence.default_window_id,
    );
    if (!state.window) throw new Error("Primary evidence window is unavailable");
    render();
  } catch (error) {
    byId("error-screen").hidden = false;
    const detail = error instanceof Error ? error.message : "Unexpected evidence loading error";
    byId("error-message").textContent = `${detail}. No synthetic substitute was used.`;
  }
}

initialize();
