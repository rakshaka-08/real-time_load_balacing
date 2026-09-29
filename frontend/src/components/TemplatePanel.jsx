import { useEffect, useState } from "react";

import {
  createTemplate,
  deleteTemplate,
  listSharedTemplates,
  listTemplates,
  renameTemplate,
  revokeTemplateAccess,
  shareTemplate,
} from "../services/templateService.js";

import "./template-panel.css";

export default function TemplatePanel({
  token,
  configuration,
  onLoad,
  onError,
}) {
  const [templates, setTemplates] = useState([]);
  const [sharedTemplates, setSharedTemplates] = useState([]);
  const [name, setName] = useState("");
  const [shareEmail, setShareEmail] = useState({});
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");

  async function refresh() {
    setLoading(true);

    try {
      const [ownedResult, sharedResult] = await Promise.all([
        listTemplates(token),
        listSharedTemplates(token),
      ]);

      setTemplates(ownedResult.templates || []);
      setSharedTemplates(sharedResult.templates || []);
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

  async function share(template) {
    const email = shareEmail[template.id]?.trim();

    if (!email) {
      onError({
        response: {
          data: { error: "Enter a collaborator email address." },
        },
      });
      return;
    }

    setBusy(template.id);

    try {
      await shareTemplate(token, template.id, email);
      setShareEmail((current) => ({
        ...current,
        [template.id]: "",
      }));
      await refresh();
    } catch (error) {
      onError(error);
    } finally {
      setBusy("");
    }
  }

  async function revoke(template, collaborator) {
    if (!window.confirm(`Remove ${collaborator.email}?`)) return;

    setBusy(template.id);

    try {
      await revokeTemplateAccess(
        token,
        template.id,
        collaborator.user_id
      );
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
      <p>Save a setup, share it, or load a template shared with you.</p>

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
      ) : (
        <>
          <h4>My templates</h4>

          {templates.length ? (
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

                  <div className="template-sharing">
                    <input
                      type="email"
                      placeholder="Collaborator email"
                      value={shareEmail[template.id] || ""}
                      onChange={(event) =>
                        setShareEmail((current) => ({
                          ...current,
                          [template.id]: event.target.value,
                        }))
                      }
                    />
                    <button
                      type="button"
                      disabled={busy === template.id}
                      onClick={() => share(template)}
                    >
                      Share
                    </button>
                  </div>

                  {template.collaborators?.length > 0 && (
                    <ul className="template-collaborators">
                      {template.collaborators.map((collaborator) => (
                        <li key={collaborator.user_id}>
                          {collaborator.email}
                          <button
                            type="button"
                            disabled={busy === template.id}
                            onClick={() => revoke(template, collaborator)}
                          >
                            Remove
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </article>
              ))}
            </div>
          ) : (
            <p>No templates saved yet.</p>
          )}

          <h4>Shared with me</h4>

          {sharedTemplates.length ? (
            <div className="template-list">
              {sharedTemplates.map((template) => (
                <article key={template.id}>
                  <strong>{template.name}</strong>
                  <span>
                    {template.algorithm} · {template.task_ids.length} tasks ·{" "}
                    {template.vm_ids.length} VMs
                  </span>
                  <button type="button" onClick={() => onLoad(template)}>
                    Load shared template
                  </button>
                </article>
              ))}
            </div>
          ) : (
            <p>No templates have been shared with you.</p>
          )}
        </>
      )}
    </section>
  );
}