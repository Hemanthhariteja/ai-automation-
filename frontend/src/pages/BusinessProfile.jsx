import { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { PageLoading } from "../components/Loading";
import { getBusinessProfile, updateBusinessProfile } from "../services/business";
import { createStaff, listStaff, updateStaff } from "../services/staff";

function StaffPanel() {
  const [staff, setStaff] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    setStaff(await listStaff());
  }

  useEffect(() => {
    load();
  }, []);

  async function handleAdd(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await createStaff({ email, full_name: fullName, password });
      setEmail("");
      setFullName("");
      setPassword("");
      setShowForm(false);
      await load();
    } catch (err) {
      setError(err.response?.data?.detail || "Could not add staff account");
    } finally {
      setBusy(false);
    }
  }

  async function toggleActive(member) {
    setBusy(true);
    try {
      await updateStaff(member.id, { is_active: !member.is_active });
      await load();
    } finally {
      setBusy(false);
    }
  }

  if (!staff) return <section className="panel"><PageLoading label="Loading team..." /></section>;

  return (
    <section className="panel">
      <div className="panel-header">
        <h2>Team</h2>
        <button type="button" className="btn btn-secondary btn-sm" onClick={() => setShowForm((s) => !s)}>
          {showForm ? "Cancel" : "Add staff"}
        </button>
      </div>
      <p className="section-intro">
        Staff can work leads, workflows, and the dashboard, but can't change AI provider settings, the business
        profile, or manage other staff — those stay owner-only.
      </p>

      {error && <p className="form-error">{error}</p>}
      {showForm && (
        <form onSubmit={handleAdd} className="mb-form">
          <div className="form-row">
            <label>
              Name
              <input value={fullName} onChange={(e) => setFullName(e.target.value)} required />
            </label>
            <label>
              Email
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
            </label>
          </div>
          <label>
            Temporary password
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} minLength={8} required />
          </label>
          <button type="submit" className="btn btn-primary btn-sm" disabled={busy}>
            {busy ? "Adding..." : "Add staff account"}
          </button>
        </form>
      )}

      <table className="data-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Email</th>
            <th>Role</th>
            <th>Status</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {staff.map((member) => (
            <tr key={member.id}>
              <td>{member.full_name}</td>
              <td>{member.email}</td>
              <td>{member.role}</td>
              <td>{member.is_active ? "Active" : "Disabled"}</td>
              <td>
                {member.role === "staff" && (
                  <button className="btn btn-sm btn-secondary" disabled={busy} onClick={() => toggleActive(member)}>
                    {member.is_active ? "Disable" : "Re-enable"}
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

export default function BusinessProfile() {
  const { user } = useAuth();
  const isOwner = user?.role === "owner";
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    getBusinessProfile().then(setForm);
  }, []);

  function update(field) {
    return (e) => {
      setForm((f) => ({ ...f, [field]: e.target.value }));
      setSaved(false);
    };
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      const data = await updateBusinessProfile(form);
      setForm(data);
      setSaved(true);
    } catch (err) {
      setError(err.response?.data?.detail || "Could not save profile");
    } finally {
      setSaving(false);
    }
  }

  async function handleCopyLink() {
    await navigator.clipboard.writeText(enquiryUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  if (!form) return <PageLoading label="Loading business profile..." />;

  const enquiryUrl = `${window.location.origin}/enquiry/${form.slug}`;

  return (
    <div>
      <h1>Business Profile</h1>
      <p className="muted">
        This is the only information the AI is allowed to use when drafting replies — it never invents prices,
        policies, or promises beyond what&apos;s here.
      </p>
      {error && <p className="form-error">{error}</p>}
      {saved && <p className="form-success">Saved.</p>}

      <section className="panel">
        <h2>Your public enquiry link</h2>
        <p className="section-intro">
          Share this link, or link it from your own website — anyone can submit an enquiry here without an
          account. It's how real customer enquiries reach this dashboard.
        </p>
        <div className="share-link-row">
          <input readOnly value={enquiryUrl} onFocus={(e) => e.target.select()} />
          <button type="button" className="btn btn-secondary btn-sm" onClick={handleCopyLink}>
            {copied ? "Copied!" : "Copy link"}
          </button>
          <a href={enquiryUrl} target="_blank" rel="noreferrer" className="btn btn-secondary btn-sm">
            Open
          </a>
        </div>
      </section>

      <form className="panel" onSubmit={handleSubmit}>
        {!isOwner && <p className="section-intro">Only the business owner can edit this profile.</p>}
        <fieldset disabled={!isOwner} className="fieldset-reset">
          <label>
            Business name
            <input value={form.name || ""} onChange={update("name")} required />
          </label>
          <label>
            Description
            <textarea rows={2} value={form.description || ""} onChange={update("description")} />
          </label>
          <label>
            Services
            <textarea
              rows={2}
              value={form.services || ""}
              onChange={update("services")}
              placeholder="e.g. Website development, digital marketing, mobile apps, AI automation"
            />
          </label>
          <label>
            Hours
            <input value={form.hours || ""} onChange={update("hours")} placeholder="e.g. Mon-Fri 9am-6pm" />
          </label>
          <div className="form-row">
            <label>
              Contact email
              <input type="email" value={form.contact_email || ""} onChange={update("contact_email")} />
            </label>
            <label>
              Contact phone
              <input value={form.contact_phone || ""} onChange={update("contact_phone")} />
            </label>
          </div>
          <label>
            Tone
            <select value={form.tone || "professional"} onChange={update("tone")}>
              <option value="professional">Professional</option>
              <option value="friendly">Friendly</option>
              <option value="casual">Casual</option>
              <option value="formal">Formal</option>
            </select>
          </label>
          {isOwner && (
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? "Saving..." : "Save profile"}
            </button>
          )}
        </fieldset>
      </form>

      {isOwner && <StaffPanel />}
    </div>
  );
}
