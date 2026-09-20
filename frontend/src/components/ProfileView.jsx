import { useEffect, useState } from "react";
import { fetchProfile, updateProfile } from "../lib/api.js";

export default function ProfileView({ onToast }) {
  const [profile, setProfile] = useState({
    preferred_languages: [],
    preferred_frameworks: [],
    current_projects: [],
    interests: [],
    skills: [],
    technologies: [],
    writing_style: "Concise, technical, direct",
    learning_goals: [],
  });
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  const [langDraft, setLangDraft] = useState("");
  const [fwDraft, setFwDraft] = useState("");
  const [projDraft, setProjDraft] = useState("");
  const [skillDraft, setSkillDraft] = useState("");

  const fetchProfile = async () => {
    setLoading(true);
    try {
      const data = await fetchProfile();
      setProfile((prev) => ({ ...prev, ...data }));
    } catch {
      // Keep defaults
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProfile();
  }, []);

  const saveProfile = async () => {
    setSaving(true);
    try {
      await updateProfile(profile);
      if (onToast) onToast("User profile updated successfully!");
    } catch (e) {
      if (onToast) onToast("Error saving profile: " + (e.message || e));
    } finally {
      setSaving(false);
    }
  };

  const addTag = (field, val, clearFn) => {
    const v = val.trim();
    if (!v) return;
    if (!profile[field].includes(v)) {
      setProfile((p) => ({ ...p, [field]: [...p[field], v] }));
    }
    clearFn("");
  };

  const removeTag = (field, tag) => {
    setProfile((p) => ({ ...p, [field]: p[field].filter((t) => t !== tag) }));
  };

  return (
    <div className="view-panel" id="viewProfile">
      <div className="panel-head">
        <div>
          <h2>User Profile &amp; Continuous Preferences</h2>
          <p className="panel-sub">Deterministically extracted user traits automatically injected into prompt context</p>
        </div>
        <div className="panel-actions">
          <button className="btn outline" onClick={fetchProfile} disabled={loading}>
            {loading ? "Loading…" : "↻ Reload"}
          </button>
          <button className="btn primary" onClick={saveProfile} disabled={saving}>
            {saving ? "Saving…" : "Save Profile"}
          </button>
        </div>
      </div>

      <div className="profile-grid">
        <div className="profile-section">
          <label>Preferred Programming Languages</label>
          <div className="chip-box">
            {profile.preferred_languages.map((l) => (
              <span key={l} className="chip">
                {l}
                <button type="button" onClick={() => removeTag("preferred_languages", l)}>×</button>
              </span>
            ))}
          </div>
          <div className="tag-input-row">
            <input
              type="text"
              placeholder="Add language (e.g. Python, TypeScript)…"
              value={langDraft}
              onChange={(e) => setLangDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") addTag("preferred_languages", langDraft, setLangDraft);
              }}
            />
            <button className="btn small" onClick={() => addTag("preferred_languages", langDraft, setLangDraft)}>
              + Add
            </button>
          </div>
        </div>

        <div className="profile-section">
          <label>Preferred Frameworks &amp; Libraries</label>
          <div className="chip-box">
            {profile.preferred_frameworks.map((f) => (
              <span key={f} className="chip accent">
                {f}
                <button type="button" onClick={() => removeTag("preferred_frameworks", f)}>×</button>
              </span>
            ))}
          </div>
          <div className="tag-input-row">
            <input
              type="text"
              placeholder="Add framework (e.g. FastAPI, React, PyTorch)…"
              value={fwDraft}
              onChange={(e) => setFwDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") addTag("preferred_frameworks", fwDraft, setFwDraft);
              }}
            />
            <button className="btn small" onClick={() => addTag("preferred_frameworks", fwDraft, setFwDraft)}>
              + Add
            </button>
          </div>
        </div>

        <div className="profile-section">
          <label>Current Projects</label>
          <div className="chip-box">
            {profile.current_projects.map((p) => (
              <span key={p} className="chip green">
                {p}
                <button type="button" onClick={() => removeTag("current_projects", p)}>×</button>
              </span>
            ))}
          </div>
          <div className="tag-input-row">
            <input
              type="text"
              placeholder="Add project (e.g. MemOS, Apollo)…"
              value={projDraft}
              onChange={(e) => setProjDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") addTag("current_projects", projDraft, setProjDraft);
              }}
            />
            <button className="btn small" onClick={() => addTag("current_projects", projDraft, setProjDraft)}>
              + Add
            </button>
          </div>
        </div>

        <div className="profile-section">
          <label>Technical Skills &amp; Domain Expertise</label>
          <div className="chip-box">
            {profile.skills.map((s) => (
              <span key={s} className="chip">
                {s}
                <button type="button" onClick={() => removeTag("skills", s)}>×</button>
              </span>
            ))}
          </div>
          <div className="tag-input-row">
            <input
              type="text"
              placeholder="Add skill (e.g. LLM Agents, Vector Search)…"
              value={skillDraft}
              onChange={(e) => setSkillDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") addTag("skills", skillDraft, setSkillDraft);
              }}
            />
            <button className="btn small" onClick={() => addTag("skills", skillDraft, setSkillDraft)}>
              + Add
            </button>
          </div>
        </div>

        <div className="profile-section full">
          <label>Writing &amp; Response Style Preference</label>
          <input
            type="text"
            className="full-input"
            value={profile.writing_style}
            onChange={(e) => setProfile((p) => ({ ...p, writing_style: e.target.value }))}
            placeholder="e.g. Concise, technical, direct, code-first"
          />
          <span className="helper">Injected into system instructions for LLM responses.</span>
        </div>
      </div>
    </div>
  );
}
