import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { PageLoading } from "../components/Loading";
import { getPublicBusinessInfo, submitPublicEnquiry } from "../services/public";

const UTM_KEYS = ["utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"];
const CLICK_ID_KEYS = ["gclid", "fbclid"];

// Captured once at mount — this is the URL the visitor actually landed on
// (e.g. straight from a Google/Facebook ad), the standard way marketing
// forms attribute a lead back to the campaign that drove it.
function captureTrackingData() {
  const params = new URLSearchParams(window.location.search);
  const tracking = {};
  for (const key of [...UTM_KEYS, ...CLICK_ID_KEYS]) {
    const value = params.get(key);
    if (value) tracking[key] = value;
  }
  if (document.referrer) tracking.referrer = document.referrer;
  tracking.landing_page = window.location.href;
  return tracking;
}

export default function PublicEnquiry() {
  const { slug } = useParams();
  const [business, setBusiness] = useState(null);
  const [notFound, setNotFound] = useState(false);
  const [message, setMessage] = useState("");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState("");
  const [tracking] = useState(captureTrackingData);

  useEffect(() => {
    getPublicBusinessInfo(slug)
      .then(setBusiness)
      .catch(() => setNotFound(true));
  }, [slug]);

  async function handleSubmit(e) {
    e.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      await submitPublicEnquiry(slug, {
        message,
        name: name || null,
        email: email || null,
        phone: phone || null,
        tracking,
      });
      setSubmitted(true);
    } catch (err) {
      if (err.response?.status === 429) {
        setError("Too many submissions from you recently — please try again a bit later.");
      } else {
        setError(err.response?.data?.detail || "Could not submit your enquiry. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  if (notFound) {
    return (
      <div className="public-enquiry-page">
        <div className="public-enquiry-card">
          <h1>Page not found</h1>
          <p className="muted">This enquiry link doesn't match a business we know about.</p>
        </div>
      </div>
    );
  }

  if (!business) {
    return (
      <div className="public-enquiry-page">
        <PageLoading />
      </div>
    );
  }

  return (
    <div className="public-enquiry-page">
      <div className="public-enquiry-card">
        <h1>{business.name}</h1>
        {business.description && <p className="public-enquiry-desc">{business.description}</p>}

        <dl className="public-enquiry-meta">
          {business.services && (
            <>
              <dt>Services</dt>
              <dd>{business.services}</dd>
            </>
          )}
          {business.hours && (
            <>
              <dt>Hours</dt>
              <dd>{business.hours}</dd>
            </>
          )}
          {(business.contact_email || business.contact_phone) && (
            <>
              <dt>Contact</dt>
              <dd>{[business.contact_email, business.contact_phone].filter(Boolean).join(" · ")}</dd>
            </>
          )}
        </dl>

        <hr className="public-enquiry-divider" />

        {submitted ? (
          <div className="public-enquiry-success">
            <h2>Thanks — we've got it.</h2>
            <p className="muted">Someone from {business.name} will get back to you shortly.</p>
          </div>
        ) : (
          <form onSubmit={handleSubmit}>
            <h2>Send us an enquiry</h2>
            {error && <p className="form-error">{error}</p>}
            <label>
              What can we help with?
              <textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                rows={4}
                required
                placeholder="Tell us what you need..."
              />
            </label>
            <div className="form-row">
              <label>
                Your name (optional)
                <input value={name} onChange={(e) => setName(e.target.value)} />
              </label>
              <label>
                Email (optional)
                <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
              </label>
            </div>
            <label>
              Phone (optional)
              <input value={phone} onChange={(e) => setPhone(e.target.value)} />
            </label>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? "Sending..." : "Send enquiry"}
            </button>
          </form>
        )}

        <p className="public-enquiry-footer">Powered by TechFix Automation</p>
      </div>
    </div>
  );
}
