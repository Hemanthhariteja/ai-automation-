import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { getBusinessProfile, updateBusinessProfile } from "../services/business";
import { getChannelsStatus, simulateMessengerMessage } from "../services/channels";
import { PageLoading } from "../components/Loading";

export default function Channels() {
  const { user } = useAuth();
  const isOwner = user?.role === "owner";
  const [status, setStatus] = useState(null);
  const [pageId, setPageId] = useState("");
  const [savingPageId, setSavingPageId] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  const [senderName, setSenderName] = useState("");
  const [messageText, setMessageText] = useState("");
  const [simulating, setSimulating] = useState(false);
  const [result, setResult] = useState(null);
  const [simError, setSimError] = useState("");

  async function load() {
    const [statusData, profile] = await Promise.all([getChannelsStatus(), getBusinessProfile()]);
    setStatus(statusData);
    setPageId(profile.messenger_page_id || "");
  }

  useEffect(() => {
    load();
  }, []);

  async function handleSavePageId(e) {
    e.preventDefault();
    setSavingPageId(true);
    setError("");
    try {
      await updateBusinessProfile({ messenger_page_id: pageId || null });
      setSaved(true);
      await load();
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      setError(err.response?.data?.detail || "Could not save");
    } finally {
      setSavingPageId(false);
    }
  }

  async function handleSimulate(e) {
    e.preventDefault();
    setSimulating(true);
    setSimError("");
    setResult(null);
    try {
      const lead = await simulateMessengerMessage({
        sender_id: `demo-${Date.now()}`,
        sender_name: senderName || null,
        text: messageText,
      });
      setResult(lead);
      setMessageText("");
    } catch (err) {
      setSimError(err.response?.data?.detail || "Could not simulate message");
    } finally {
      setSimulating(false);
    }
  }

  if (!status) return <PageLoading label="Loading channels..." />;

  const messenger = status.channels.find((c) => c.name === "messenger");

  return (
    <div>
      <h1>Channels</h1>
      <p className="page-intro">
        Where customer messages actually come from. The web enquiry form is always on; Messenger/Instagram is
        optional — receiving works the same whether or not it's connected to a real Meta Page.
      </p>
      {error && <p className="form-error">{error}</p>}

      <section className="panel">
        <h2>Messenger / Instagram</h2>
        <p className="section-intro">
          Status: <strong>{messenger.configured ? "Configured" : "Not configured"}</strong> — {messenger.message}
          {messenger.business_connected && " · This business has a Page connected."}
        </p>

        {isOwner ? (
          <form onSubmit={handleSavePageId}>
            <label>
              Connected Meta Page ID
              <input
                value={pageId}
                onChange={(e) => setPageId(e.target.value)}
                placeholder="e.g. 1234567890 — found in your Meta Page settings"
              />
            </label>
            <button type="submit" className="btn btn-secondary btn-sm" disabled={savingPageId}>
              {savingPageId ? "Saving..." : saved ? "Saved!" : "Save"}
            </button>
          </form>
        ) : (
          <p className="muted">Only the business owner can connect a Page.</p>
        )}
      </section>

      <section className="panel">
        <h2>Try it without any real setup</h2>
        <p className="section-intro">
          Simulates an inbound Messenger message through the exact same pipeline a real one would use — same AI
          classification, same workflow triggers — with zero Meta account required.
        </p>
        {simError && <p className="form-error">{simError}</p>}
        <form onSubmit={handleSimulate}>
          <label>
            Sender name (optional)
            <input value={senderName} onChange={(e) => setSenderName(e.target.value)} placeholder="Jane" />
          </label>
          <label>
            Message
            <textarea
              value={messageText}
              onChange={(e) => setMessageText(e.target.value)}
              rows={3}
              required
              placeholder="Can I book a table for 4 this Saturday at 7pm?"
            />
          </label>
          <button type="submit" className="btn btn-primary" disabled={simulating}>
            {simulating ? "Sending..." : "Simulate inbound message"}
          </button>
        </form>

        {result && (
          <div className="test-result">
            <p>
              Created as a lead — intent <strong>{result.intent || "unclassified"}</strong>, score{" "}
              <strong>{result.score ?? "-"}</strong>, priority{" "}
              <span className={`badge badge-${result.priority}`}>{result.priority}</span>
            </p>
            <p>
              <Link to={`/leads/${result.id}`}>View this lead &rarr;</Link>
            </p>
          </div>
        )}
      </section>
    </div>
  );
}
