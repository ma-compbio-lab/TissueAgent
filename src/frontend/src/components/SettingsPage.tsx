/**
 * Settings page — single column of configuration sections.
 *
 *   1. Mode         – autopilot vs copilot
 *   2. Models       – orchestration + worker model selection + API keys
 *   3. Agent        – R kernel environment
 *   4. Display      – frontend appearance settings
 *
 * Layout: outer `.doc-page` matches Tutorial/Contact for typography and
 * width; each block is a `.settings-section` card with rows inside.
 */

import ModelPicker from "./ModelPicker";
import type {
  KeyStatusMap,
  ModelOption,
  ModelSelection,
  Provider,
} from "../hooks/useModels";
import type { SessionMode } from "../types/messages";
import { useSettings } from "../hooks/useSettings";

interface Props {
  mode: SessionMode;
  onChangeMode: (mode: SessionMode) => void;
  isRunning: boolean;
  models: ModelOption[];
  modelSelection: ModelSelection | null;
  workerPinned: boolean;
  onChangeOrchestrationModel: (id: string) => void;
  onChangeWorkerModel: (id: string) => void;
  onResetWorkerModel: () => void;
  modelKeys: KeyStatusMap;
  onSaveApiKey: (provider: Provider, key: string) => Promise<boolean>;
}

export default function SettingsPage({
  mode,
  onChangeMode,
  isRunning,
  models,
  modelSelection,
  workerPinned,
  onChangeOrchestrationModel,
  onChangeWorkerModel,
  onResetWorkerModel,
  modelKeys,
  onSaveApiKey,
}: Props) {
  const { settings, saving, error, setSandboxEnabled } = useSettings();
  const sandboxEnabled = settings?.sandbox_enabled ?? true;

  return (
    <article className="doc-page settings-page">
      <header className="doc-header">
        <p className="doc-eyebrow">Configuration</p>
        <h1 className="doc-title">Settings</h1>
      </header>

      {error && <p className="settings-error">{error}</p>}

      {/* ── Mode ───────────────────────────────────────────────────── */}
      <section className="settings-section">
        <h2 className="settings-section-title">Execution mode</h2>
        <p className="settings-section-desc">
          How the agent pipeline runs from prompt to final report.
        </p>
        <div className="settings-rows">
          <div className="settings-row">
            <div
              className="settings-mode-choices"
              role="radiogroup"
              aria-label="Execution mode"
            >
              <label
                className={`settings-mode-choice ${mode === "autopilot" ? "active" : ""}`}
              >
                <input
                  type="radio"
                  name="execution-mode"
                  value="autopilot"
                  checked={mode === "autopilot"}
                  onChange={() => onChangeMode("autopilot")}
                />
                <span className="settings-mode-choice-title">Autopilot</span>
                <span className="settings-mode-choice-body">
                  The agent runs end-to-end without pauses. Planner →
                  Recruiter → Manager → Evaluator → Reporter, all
                  automatic. Use when you trust the plan or just want
                  results.
                </span>
              </label>

              <label
                className={`settings-mode-choice ${mode === "copilot" ? "active" : ""}`}
              >
                <input
                  type="radio"
                  name="execution-mode"
                  value="copilot"
                  checked={mode === "copilot"}
                  onChange={() => onChangeMode("copilot")}
                />
                <span className="settings-mode-choice-title">Copilot</span>
                <span className="settings-mode-choice-body">
                  The agent pauses twice for your review — once after
                  the planner drafts the plan, and again after the
                  recruiter assigns agents. At each pause you can
                  approve, edit, send feedback, or cancel.
                </span>
              </label>
            </div>
            {isRunning && (
              <p className="settings-row-desc">
                A run is in progress. The change takes effect on the next prompt.
              </p>
            )}
          </div>
        </div>
      </section>

      {/* ── Models + API keys ──────────────────────────────────────── */}
      <section className="settings-section">
        <h2 className="settings-section-title">Models &amp; API keys</h2>
        <p className="settings-section-desc">
          Pick the orchestration and worker models, and supply API keys
          for the providers you'd like to use. Keys are stored on the
          server and never sent back to the browser.
        </p>
        <div className="settings-models-host">
          <ModelPicker
            models={models}
            selection={modelSelection}
            workerPinned={workerPinned}
            onChangeOrchestration={onChangeOrchestrationModel}
            onChangeWorker={onChangeWorkerModel}
            onResetWorker={onResetWorkerModel}
            keys={modelKeys}
            onSaveKey={onSaveApiKey}
            disabled={isRunning}
          />
        </div>
      </section>

      {/* ── Agent ──────────────────────────────────────────────────── */}
      <section className="settings-section">
        <h2 className="settings-section-title">Agent</h2>
        <p className="settings-section-desc">
          Configure agent behaviour and execution environment.
        </p>
        <div className="settings-rows">

          <div className="settings-row">
            <div className="settings-row-header">
              <label className="settings-row-label" htmlFor="sandbox-toggle">
                Docker for R steps
              </label>
              <button
                id="sandbox-toggle"
                type="button"
                role="switch"
                aria-checked={sandboxEnabled}
                disabled={saving || settings === null}
                className={`settings-toggle ${sandboxEnabled ? "on" : "off"}`}
                onClick={() => setSandboxEnabled(!sandboxEnabled)}
              >
                <span className="settings-toggle-thumb" />
                <span className="settings-toggle-label">
                  {sandboxEnabled ? "Enabled" : "Disabled"}
                </span>
              </button>
            </div>
            <p className="settings-row-desc">
              Run R skill steps through a Docker Jupyter Kernel Gateway.
              When disabled, R uses a local gateway. The gateway starts only
              when an R step runs. DeepAgent shell commands run locally.
            </p>

            {!sandboxEnabled && (
              <div className="settings-help-box warning" role="alert">
                <span className="settings-help-box-icon">⚠</span>
                <div className="settings-help-box-body">
                  <strong>Local R execution</strong>
                  <p>
                    R code runs with the server process's host permissions.
                    DeepAgent shell commands also run locally regardless of
                    this setting.
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* ── Display ────────────────────────────────────────────────── */}
      <section className="settings-section">
        <h2 className="settings-section-title">Display</h2>
        <p className="settings-section-desc">
          Adjust the appearance and layout of the frontend interface.
        </p>
        <div className="settings-rows">
          <p className="settings-empty">No display settings configured yet.</p>
        </div>
      </section>
    </article>
  );
}
