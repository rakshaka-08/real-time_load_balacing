import { useEffect, useState } from "react";

import {
  createTemplate,
  deleteTemplate,
  listTemplates,
  renameTemplate,
} from "../services/templateService.js";

import "./template-panel.css";

export default function TemplatePanel({
  token,
  configuration,
  onLoad,
  onError,
}) {
  const [templates, setTemplates] = useState([]);
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");

  async function refresh() {
    setLoading(true);

    try {
      const result = await listTemplates(token);
      setTemplates(result.templates || []);
    } catch (error) {
      onError(error);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function save() {
    if (!name.trim()) {
      onError({
        response: {
          data: { error: "Enter a name before saving the template." },
        },
      });
      return;
    }

    setBusy("save");

    try {
      await createTemplate(token, {
        name: name.trim(),
        ...configuration,
      });
      setName("");
      await refresh();
    } catch (error) {
      onError(error);
    } finally {
      setBusy("");
    }
  }

  async function rename(template) {
    const nextName = window.prompt("New template name", template.name);

    if (!nextName?.trim()) return;

    setBusy(template.id);

    try {
      await renameTemplate(token, template.id, nextName.trim());
      await refresh();
    } catch (error) {
      onError(error);
    } finally {
      setBusy("");
    }
  }

  async function remove(template) {
    if (!window.confirm(`Delete "${template.name}"?`)) return;

    setBusy(template.id);

    try {
      await deleteTemplate(token, template.id);
      await refresh();
    } catch (error) {
      onError(error);
    } finally {
      setBusy("");
    }
  }

  return (
    <section className="template-panel">
      <h3>Scenario templates</h3>
      <p>Save this configuration or load a previous scenario.</p>

      <div className="template-save">
        <input
          value={name}
          placeholder="Template name"
          maxLength="80"
          onChange={(event) => setName(event.target.value)}
        />

        <button type="button" onClick={save} disabled={busy === "save"}>
          {busy === "save" ? "Saving…" : "Save current setup"}
        </button>
      </div>

      {loading ? (
        <p>Loading templates…</p>
      ) : templates.length ? (
        <div className="template-list">
          {templates.map((template) => (
            <article key={template.id}>
              <strong>{template.name}</strong>
              <span>
                {template.algorithm} · {template.task_ids.length} tasks ·{" "}
                {template.vm_ids.length} VMs
              </span>

              <div>
                <button type="button" onClick={() => onLoad(template)}>
                  Load
                </button>
                <button
                  type="button"
                  disabled={busy === template.id}
                  onClick={() => rename(template)}
                >
                  Rename
                </button>
                <button
                  type="button"
                  className="template-delete"
                  disabled={busy === template.id}
                  onClick={() => remove(template)}
                >
                  Delete
                </button>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <p>No templates saved yet.</p>
      )}
    </section>
  );
}