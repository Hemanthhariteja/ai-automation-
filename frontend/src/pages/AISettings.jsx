import { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { PageLoading } from "../components/Loading";
import { getAIStatus, updateAISettings, testAIPipeline } from "../services/ai";

export default function AISettings() {
  const { user } = useAuth();
  const isOwner = user?.role === "owner";
  const [status, setStatus] = useState(null);
  const [testText, setTestText] = useState("");
  const [testResult, setTestResult] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    const data = await getAIStatus();
    setStatus(data);
  }

  useEffect(() => {
    load();
  }, []);

  async function handleSelect(name, kind) {
    setBusy(true);
    setError("");
    try {
      const payload = kind === "primary" ? { ai_provider: name } : { ai_fallback_provider: name };
      const data = await updateAISettings(payload);
      setStatus(data);
    } catch (err) {
      setError(err.response?.data?.detail || "Could not update settings");
    } finally {
      setBusy(false);
    }
  }

  async function handleTest(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const result = await testAIPipeline({ text: testText });
      setTestResult(result);
    } catch (err) {
      setError(err.response?.data?.detail || "Test failed");
    } finally {
      setBusy(false);
    }
  }

  if (!status) return <PageLoading label="Loading AI provider status..." />;

  return (
    <div>
      <h1>AI Provider Settings</h1>
      <p className="muted">
        Active provider: <strong>{status.active_provider}</strong> &middot; Fallback:{" "}
        <strong>{status.active_fallback}</strong>. The app always works even with none of these configured —
        Demo Mode is the guaranteed fallback.
      </p>
      {error && <p className="form-error">{error}</p>}

      <table className="data-table">
        <thead>
          <tr>
            <th>Provider</th>
            <th>Label</th>
            <th>Status</th>
            <th>Message</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {status.providers.map((p) => (
            <tr key={p.name}>
              <td>
                {p.name}{" "}
                {p.is_active_primary && <span className="badge badge-high">primary</span>}{" "}
                {p.is_active_fallback && <span className="badge badge-normal">fallback</span>}
              </td>
              <td>{p.label}</td>
              <td>{p.connection_ok ? "Connected" : "Unavailable"}</td>
              <td className="muted">{p.message}</td>
              <td>
                {isOwner ? (
                  <>
                    <button className="btn btn-sm" disabled={busy} onClick={() => handleSelect(p.name, "primary")}>
                      Set primary
                    </button>{" "}
                    <button className="btn btn-sm btn-secondary" disabled={busy} onClick={() => handleSelect(p.name, "fallback")}>
                      Set fallback
                    </button>
                  </>
                ) : (
                  <span className="muted">Owner only</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <section className="panel mt-section">
        <h2>Test the pipeline</h2>
        <form onSubmit={handleTest}>
          <label>
            Sample enquiry
            <textarea
              value={testText}
              onChange={(e) => setTestText(e.target.value)}
              rows={3}
              placeholder="Type a sample enquiry..."
              required
            />
          </label>
          <button type="submit" className="btn btn-primary" disabled={busy}>
            Run test
          </button>
        </form>
        {testResult && (
          <div className="test-result">
            <p>
              Provider used: <strong>{testResult.provider_used}</strong>{" "}
              {testResult.fallback_used && <span className="badge badge-high">fallback</span>}
            </p>
            {testResult.fallback_reason && <p className="muted">{testResult.fallback_reason}</p>}
            <p>
              Intent: {testResult.intent} ({testResult.category || "no category"}) &middot; Score:{" "}
              {testResult.score}
            </p>
            <p className="summary-box">{testResult.response_text}</p>
          </div>
        )}
      </section>
    </div>
  );
}
