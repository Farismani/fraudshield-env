import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  Bell,
  CheckCircle2,
  CreditCard,
  Download,
  LogOut,
  QrCode,
  Search,
  Send,
  Shield,
  Smartphone,
  Store,
  Users,
  UserRound,
  Wallet,
  XCircle,
} from "lucide-react";
import "./styles.css";

const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

async function api(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || data.message || "Request failed");
  return data;
}

function money(value) {
  return `${Number(value || 0).toLocaleString("en-IN", { maximumFractionDigits: 2 })} FSM`;
}

function statusIcon(status) {
  if (status === "BLOCKED") return <XCircle size={18} />;
  if (status === "WARNING") return <Shield size={18} />;
  return <CheckCircle2 size={18} />;
}

function App() {
  const [profiles, setProfiles] = useState([]);
  const [users, setUsers] = useState([]);
  const [session, setSession] = useState(() => {
    const raw = localStorage.getItem("fraudshield-session");
    return raw ? JSON.parse(raw) : null;
  });
  const [selectedProfile, setSelectedProfile] = useState("faris");
  const [password, setPassword] = useState("pass001");
  const [receiver, setReceiver] = useState("");
  const [amount, setAmount] = useState("500");
  const [pin, setPin] = useState("1234");
  const [note, setNote] = useState("Demo payment");
  const [transactions, setTransactions] = useState([]);
  const [insights, setInsights] = useState({ recent_contacts: [], spending_categories: [], total_volume: 0 });
  const [rewards, setRewards] = useState({ rewards: [], total: 0 });
  const [devices, setDevices] = useState([]);
  const [riskTrend, setRiskTrend] = useState({ average_risk: 0, trend: [] });
  const [requests, setRequests] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [admin, setAdmin] = useState(null);
  const [adminToken, setAdminToken] = useState("");
  const [merchants, setMerchants] = useState([]);
  const [merchantDashboard, setMerchantDashboard] = useState(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [fraudWarning, setFraudWarning] = useState(null);
  const [activeTab, setActiveTab] = useState("pay");
  const [requestPayer, setRequestPayer] = useState("");
  const [requestAmount, setRequestAmount] = useState("300");
  const [requestNote, setRequestNote] = useState("Collect request");
  const [qrPayload, setQrPayload] = useState("FSQR:rahul");
  const [busy, setBusy] = useState(false);

  const deviceId = useMemo(() => {
    let value = localStorage.getItem("fraudshield-device");
    if (!value) {
      value = `WEB-${crypto.randomUUID()}`;
      localStorage.setItem("fraudshield-device", value);
    }
    return value;
  }, []);

  useEffect(() => {
    api("/api/demo-profiles").then((data) => {
      setProfiles(data.profiles);
      const first = data.profiles[0];
      if (first && !session) {
        setSelectedProfile(first.user_id);
        setPassword(first.password);
      }
    });
    api("/api/users").then((data) => setUsers(data.users));
    api("/api/merchants").then((data) => setMerchants(data.merchants));
    authenticateAdmin();
  }, []);

  useEffect(() => {
    const profile = profiles.find((item) => item.user_id === selectedProfile);
    if (profile) setPassword(profile.password);
  }, [selectedProfile, profiles]);

  useEffect(() => {
    if (!session?.token) return;
    refreshData(session.token);
    const socket = new WebSocket(API_URL.replace("http", "ws") + "/ws/events");
    socket.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.type === "transaction") {
        refreshData(session.token);
        if (adminToken) {
          api(`/api/admin/dashboard?token=${encodeURIComponent(adminToken)}`).then(setAdmin);
        }
      }
    };
    return () => socket.close();
  }, [session?.token, adminToken]);

  useEffect(() => {
    if (!session?.token || session.user.user_id !== "kiran" || merchants.length === 0) return;
    api(`/api/merchants/${merchants[0].merchant_id}/dashboard?token=${encodeURIComponent(session.token)}`)
      .then(setMerchantDashboard)
      .catch(() => setMerchantDashboard(null));
  }, [session?.token, session?.user?.user_id, merchants]);

  async function authenticateAdmin() {
    try {
      const data = await api("/api/admin/login", {
        method: "POST",
        body: JSON.stringify({ username: "analyst", password: "admin001" }),
      });
      setAdminToken(data.token);
      setAdmin(await api(`/api/admin/dashboard?token=${encodeURIComponent(data.token)}`));
    } catch {
      setAdmin(null);
    }
  }

  async function refreshData(token = session?.token) {
    if (!token) return;
    const [me, tx, userList, alertList, adminData, requestList, insightData, rewardData, deviceData, trendData] = await Promise.all([
      api(`/api/auth/me?token=${encodeURIComponent(token)}`),
      api(`/api/transactions?token=${encodeURIComponent(token)}`),
      api("/api/users"),
      api(`/api/alerts?token=${encodeURIComponent(token)}`),
      adminToken
        ? api(`/api/admin/dashboard?token=${encodeURIComponent(adminToken)}`)
        : Promise.resolve(null),
      api(`/api/requests?token=${encodeURIComponent(token)}`),
      api(`/api/insights?token=${encodeURIComponent(token)}`),
      api(`/api/rewards?token=${encodeURIComponent(token)}`),
      api(`/api/devices?token=${encodeURIComponent(token)}`),
      api(`/api/risk-trend?token=${encodeURIComponent(token)}`),
    ]);
    const nextSession = { token, user: me.user };
    setSession(nextSession);
    localStorage.setItem("fraudshield-session", JSON.stringify(nextSession));
    setTransactions(tx.transactions);
    setUsers(userList.users);
    setAlerts(alertList.alerts);
    setAdmin(adminData);
    setRequests(requestList.requests);
    setInsights(insightData);
    setRewards(rewardData);
    setDevices(deviceData.devices);
    setRiskTrend(trendData);
  }

  async function login(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const data = await api("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({
          identifier: selectedProfile,
          password,
          device_id: deviceId,
          device_name: navigator.userAgent.slice(0, 80),
        }),
      });
      const nextSession = { token: data.token, user: data.user };
      setSession(nextSession);
      localStorage.setItem("fraudshield-session", JSON.stringify(nextSession));
      setNotice(`Logged in as ${data.user.name}`);
      await refreshData(data.token);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  function logout() {
    localStorage.removeItem("fraudshield-session");
    setSession(null);
    setTransactions([]);
    setAlerts([]);
    setNotice("");
  }

  async function sendMoney(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const data = await api("/api/payments/send", {
        method: "POST",
        body: JSON.stringify({
          token: session.token,
          receiver,
          amount: Number(amount),
          pin,
          note,
          device_id: deviceId,
          location: session.user.location,
        }),
      });
      showFraudWarning(data.transaction);
      setNotice(`Payment ${data.transaction.status.toLowerCase()}: ${money(data.transaction.amount)} to ${data.receiver.name}`);
      setAmount("500");
      await refreshData();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function payQr(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const data = await api("/api/qr/pay", {
        method: "POST",
        body: JSON.stringify({
          token: session.token,
          receiver: qrPayload,
          amount: Number(amount),
          pin,
          note: note || "QR payment",
          device_id: deviceId,
          location: session.user.location,
        }),
      });
      showFraudWarning(data.transaction);
      setNotice(`QR payment ${data.transaction.status.toLowerCase()}: ${money(data.transaction.amount)} to ${data.receiver.name}`);
      await refreshData();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function createMoneyRequest(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const data = await api("/api/requests", {
        method: "POST",
        body: JSON.stringify({
          token: session.token,
          payer: requestPayer,
          amount: Number(requestAmount),
          note: requestNote,
        }),
      });
      setNotice(`Request created: ${money(data.request.amount)} from ${data.request.payer}`);
      await refreshData();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function decideRequest(requestId, decision) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const data = await api(`/api/requests/${requestId}/${decision}`, {
        method: "POST",
        body: JSON.stringify({
          token: session.token,
          pin,
          device_id: deviceId,
        }),
      });
      if (data.transaction) showFraudWarning(data.transaction);
      setNotice(`Request ${decision === "approve" ? "approved" : "rejected"}`);
      await refreshData();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  function showFraudWarning(transaction) {
    if (transaction.status === "WARNING" || transaction.status === "BLOCKED") {
      setFraudWarning(transaction);
    } else {
      setFraudWarning(null);
    }
  }

  async function setProfileStatus(userId, status) {
    setBusy(true);
    setError("");
    try {
      await api(`/api/admin/users/${userId}/status`, {
        method: "POST",
          body: JSON.stringify({ token: adminToken, status }),
      });
      await refreshData();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function downloadReceipt(transactionId, token = session?.token) {
    if (!token) return;
    try {
      const receipt = await api(`/api/transactions/${encodeURIComponent(transactionId)}/receipt?token=${encodeURIComponent(token)}`);
      const file = new Blob([JSON.stringify(receipt, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(file);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${transactionId}-receipt.json`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err.message);
    }
  }

  async function setDeviceTrust(deviceId, trusted) {
    try {
      await api(`/api/devices/${encodeURIComponent(deviceId)}/trust`, {
        method: "POST",
        body: JSON.stringify({ token: session.token, trusted }),
      });
      await refreshData();
    } catch (err) {
      setError(err.message);
    }
  }

  if (!session) {
    return (
      <main className="loginShell">
        <section className="loginPanel">
          <div className="brandLine">
            <Shield size={30} />
            <div>
              <h1>FraudShield Pay</h1>
              <p>Dataset profiles. Fake money. Real-time fraud decisions.</p>
            </div>
          </div>
          <form onSubmit={login} className="stack">
            <label>
              Profile
              <select value={selectedProfile} onChange={(event) => setSelectedProfile(event.target.value)}>
                {profiles.map((profile) => (
                  <option key={profile.user_id} value={profile.user_id}>
                    {profile.name} - {profile.persona}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Password
              <input value={password} onChange={(event) => setPassword(event.target.value)} />
            </label>
            {error && <div className="error">{error}</div>}
            <button className="primaryButton" disabled={busy}>
              <Smartphone size={18} />
              {busy ? "Signing in" : "Use profile"}
            </button>
          </form>
          <div className="credentialGrid">
            {profiles.slice(0, 8).map((profile) => (
              <button
                key={profile.user_id}
                type="button"
                onClick={() => {
                  setSelectedProfile(profile.user_id);
                  setPassword(profile.password);
                }}
              >
                <strong>{profile.name}</strong>
                <span>{profile.password} / PIN {profile.pin}</span>
              </button>
            ))}
          </div>
        </section>
      </main>
    );
  }

  const receiverOptions = users.filter((user) => user.user_id !== session.user.user_id);
  const latest = transactions.slice(0, 8);

  return (
    <main className="appShell">
      <aside className="sidebar">
        <div className="brandCompact">
          <Shield size={26} />
          <span>FraudShield Pay</span>
        </div>
        <nav>
          <button className={activeTab === "pay" ? "active" : ""} onClick={() => setActiveTab("pay")}>
            <Send size={18} /> Pay
          </button>
          <button className={activeTab === "activity" ? "active" : ""} onClick={() => setActiveTab("activity")}>
            <Activity size={18} /> Activity
          </button>
          <button className={activeTab === "requests" ? "active" : ""} onClick={() => setActiveTab("requests")}>
            <Bell size={18} /> Requests
          </button>
          <button className={activeTab === "analyst" ? "active" : ""} onClick={() => setActiveTab("analyst")}>
            <Shield size={18} /> Analyst
          </button>
          {session.user.user_id === "kiran" && (
            <button className={activeTab === "merchant" ? "active" : ""} onClick={() => setActiveTab("merchant")}>
              <Store size={18} /> Merchant
            </button>
          )}
        </nav>
        <button className="ghostButton" onClick={logout}>
          <LogOut size={18} /> Logout
        </button>
      </aside>

      <section className="content">
        <header className="topbar">
          <div>
            <p className="eyebrow">Signed in as</p>
            <h2>{session.user.name}</h2>
            <span>{session.user.upi_id}</span>
          </div>
          <div className={`riskPill ${session.user.risk_level.toLowerCase()}`}>{session.user.risk_level} risk</div>
        </header>

        <section className="summaryGrid">
          <div className="balanceBand">
            <Wallet size={26} />
            <div>
              <p>FraudShield balance</p>
              <strong>{money(session.user.balance)}</strong>
            </div>
          </div>
          <div className="metricBand">
            <CreditCard size={24} />
            <div>
              <p>Transactions</p>
              <strong>{transactions.length}</strong>
            </div>
          </div>
          <div className="metricBand">
            <Bell size={24} />
            <div>
              <p>Alerts</p>
              <strong>{alerts.length}</strong>
            </div>
          </div>
        </section>

        {notice && <div className="notice">{notice}</div>}
        {error && <div className="error">{error}</div>}

        {activeTab === "pay" && (
          <section className="twoColumn">
            <form className="toolPanel" onSubmit={sendMoney}>
              <div className="panelTitle">
                <Send size={20} />
                <h3>Send FraudShield Money</h3>
              </div>
              <label>
                Receiver
                <select value={receiver} onChange={(event) => setReceiver(event.target.value)} required>
                  <option value="">Choose a profile</option>
                  {receiverOptions.map((user) => (
                    <option key={user.user_id} value={user.user_id}>
                      {user.name} - {user.upi_id}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Amount
                <input type="number" min="1" value={amount} onChange={(event) => setAmount(event.target.value)} />
              </label>
              <label>
                Note
                <input value={note} onChange={(event) => setNote(event.target.value)} />
              </label>
              <label>
                Payment PIN
                <input value={pin} onChange={(event) => setPin(event.target.value)} maxLength={6} />
              </label>
              <button className="primaryButton" disabled={busy}>
                <Send size={18} />
                {busy ? "Analyzing" : "Pay now"}
              </button>
            </form>

            <section className="toolPanel">
              <div className="panelTitle">
                <QrCode size={20} />
                <h3>QR Pay</h3>
              </div>
              <div className="qrBox">
                <QrCode size={130} />
                <strong>{session.user.upi_id}</strong>
                <span>Scan simulation payload: FSQR:{session.user.user_id}</span>
              </div>
              <form className="stack" onSubmit={payQr}>
                <label>
                  QR payload
                  <input value={qrPayload} onChange={(event) => setQrPayload(event.target.value)} />
                </label>
                <button className="primaryButton" disabled={busy}>
                  <QrCode size={18} />
                  Pay QR
                </button>
              </form>
            </section>
          </section>
        )}

        {activeTab === "requests" && (
          <section className="twoColumn">
            <form className="toolPanel" onSubmit={createMoneyRequest}>
              <div className="panelTitle">
                <Bell size={20} />
                <h3>Request money</h3>
              </div>
              <label>
                Payer
                <select value={requestPayer} onChange={(event) => setRequestPayer(event.target.value)} required>
                  <option value="">Choose a profile</option>
                  {receiverOptions.map((user) => (
                    <option key={user.user_id} value={user.user_id}>
                      {user.name} - {user.upi_id}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Amount
                <input type="number" min="1" value={requestAmount} onChange={(event) => setRequestAmount(event.target.value)} />
              </label>
              <label>
                Note
                <input value={requestNote} onChange={(event) => setRequestNote(event.target.value)} />
              </label>
              <button className="primaryButton" disabled={busy}>
                <Bell size={18} />
                Create request
              </button>
            </form>
            <RequestList requests={requests} onDecision={decideRequest} busy={busy} />
          </section>
        )}

        {activeTab === "activity" && (
          <section className="twoColumn">
            <TransactionList transactions={latest} onReceipt={downloadReceipt} />
            <section className="toolPanel">
              <div className="panelTitle">
                <Bell size={20} />
                <h3>Security alerts</h3>
              </div>
              <div className="list">
                {alerts.length === 0 && <p className="empty">No alerts for this profile.</p>}
                {alerts.map((alert) => (
                  <article key={alert.id} className="alertItem">
                    <strong>{alert.severity}</strong>
                    <span>{alert.message}</span>
                  </article>
                ))}
              </div>
              <div className="insightBlock">
                <div className="panelTitle"><Users size={18} /><h3>Recent contacts</h3></div>
                {insights.recent_contacts.length === 0 && <p className="empty">No contacts yet.</p>}
                {insights.recent_contacts.map((contact) => (
                  <div className="insightRow" key={contact.user_id}>
                    <span>{contact.name}</span><b>{contact.count} payments</b>
                  </div>
                ))}
              </div>
              <div className="insightBlock">
                <div className="panelTitle"><Wallet size={18} /><h3>Spending categories</h3></div>
                {insights.spending_categories.map((category) => (
                  <div className="insightRow" key={category.category}>
                    <span>{category.category}</span><b>{money(category.amount)}</b>
                  </div>
                ))}
              </div>
              <div className="insightBlock">
                <div className="panelTitle"><CreditCard size={18} /><h3>Cashback earned</h3></div>
                <div className="insightRow"><span>Total cashback</span><b>{money(rewards.total)}</b></div>
                {rewards.rewards.slice(0, 3).map((reward) => (
                  <div className="insightRow" key={`${reward.transaction_id}-${reward.created_at}`}>
                    <span>{reward.description}</span><b>+{money(reward.amount)}</b>
                  </div>
                ))}
              </div>
              <div className="insightBlock">
                <div className="panelTitle"><Shield size={18} /><h3>Risk trend</h3></div>
                <div className="insightRow"><span>Average recent risk</span><b>{riskTrend.average_risk}%</b></div>
                <span className="mutedText">{riskTrend.trend.length} scored payments tracked</span>
              </div>
              <div className="insightBlock">
                <div className="panelTitle"><Smartphone size={18} /><h3>Trusted devices</h3></div>
                {devices.map((device) => (
                  <div className="deviceRow" key={device.device_id}>
                    <span>{device.name || device.device_id}</span>
                    <button type="button" onClick={() => setDeviceTrust(device.device_id, !device.trusted)}>
                      {device.trusted ? "Revoke" : "Trust"}
                    </button>
                  </div>
                ))}
              </div>
            </section>
          </section>
        )}

        {activeTab === "analyst" && <AnalystView admin={admin} onStatus={setProfileStatus} busy={busy} onReceipt={(id) => downloadReceipt(id, adminToken)} />}
        {activeTab === "merchant" && <MerchantView dashboard={merchantDashboard} onReceipt={downloadReceipt} />}
      </section>
      {fraudWarning && (
        <div className="fraudModalBackdrop" role="alertdialog" aria-modal="true" aria-labelledby="fraud-warning-title">
          <section className="fraudModal">
            <div className="fraudModalIcon"><Shield size={28} /></div>
            <p className="eyebrow">FraudShield protection alert</p>
            <h2 id="fraud-warning-title">
              {fraudWarning.status === "BLOCKED" ? "Payment blocked" : "Suspicious payment detected"}
            </h2>
            <p>
              {fraudWarning.status === "BLOCKED"
                ? "This payment was stopped because it looks highly suspicious. Your wallet was not debited."
                : "This payment was flagged as suspicious. Review the details before continuing."
              }
            </p>
            <div className="fraudModalScore">Risk score: <strong>{fraudWarning.risk_score}%</strong></div>
            <ul>
              {(fraudWarning.reasons || ["Unusual payment pattern detected."]).map((reason) => <li key={reason}>{reason}</li>)}
            </ul>
            <button className="primaryButton" type="button" onClick={() => setFraudWarning(null)}>Close warning</button>
          </section>
        </div>
      )}
    </main>
  );
}

function TransactionList({ transactions, onReceipt }) {
  return (
    <section className="toolPanel">
      <div className="panelTitle">
        <Activity size={20} />
        <h3>Recent transactions</h3>
      </div>
      <div className="list">
        {transactions.length === 0 && <p className="empty">No transactions yet.</p>}
        {transactions.map((tx) => (
          <article className={`txItem ${tx.status.toLowerCase()}`} key={tx.transaction_id}>
            <div className="txIcon">{statusIcon(tx.status)}</div>
            <div>
              <strong>{tx.sender} to {tx.receiver}</strong>
              <span>{tx.note || tx.transaction_id}</span>
            </div>
            <div className="txAmount">
              <strong>{money(tx.amount)}</strong>
              <span>{tx.risk_score}% risk</span>
            </div>
            {onReceipt && <button className="iconButton" type="button" title="Download receipt" onClick={() => onReceipt(tx.transaction_id)}><Download size={16} /></button>}
          </article>
        ))}
      </div>
    </section>
  );
}

function RequestList({ requests, onDecision, busy }) {
  return (
    <section className="toolPanel">
      <div className="panelTitle">
        <Activity size={20} />
        <h3>Collect requests</h3>
      </div>
      <div className="list">
        {requests.length === 0 && <p className="empty">No collect requests yet.</p>}
        {requests.map((request) => (
          <article className="requestItem" key={request.request_id}>
            <div>
              <strong>{request.requester} requests {money(request.amount)} from {request.payer}</strong>
              <span>{request.note || request.request_id}</span>
            </div>
            <b>{request.status}</b>
            {request.direction === "incoming" && request.status === "PENDING" && (
              <div className="inlineActions">
                <button type="button" onClick={() => onDecision(request.request_id, "approve")} disabled={busy}>
                  <CheckCircle2 size={16} /> Approve
                </button>
                <button type="button" onClick={() => onDecision(request.request_id, "reject")} disabled={busy}>
                  <XCircle size={16} /> Reject
                </button>
              </div>
            )}
          </article>
        ))}
      </div>
    </section>
  );
}

function AnalystView({ admin, onStatus, busy, onReceipt }) {
  if (!admin) return null;
  return (
    <section className="analystGrid">
      <div className="metricWall">
        <Metric icon={<UserRound size={22} />} label="Profiles" value={admin.metrics.users} />
        <Metric icon={<Activity size={22} />} label="Transactions" value={admin.metrics.transactions} />
        <Metric icon={<Wallet size={22} />} label="Volume" value={money(admin.metrics.volume)} />
        <Metric icon={<Shield size={22} />} label="Flagged" value={admin.metrics.flagged} />
      </div>
      <section className="toolPanel">
        <div className="panelTitle">
          <Search size={20} />
          <h3>Profile risk map</h3>
        </div>
        <div className="profileGrid">
          {admin.risk_profiles.map((profile) => (
            <article key={profile.user_id} className="profileItem">
              <strong>{profile.name}</strong>
              <span>{profile.persona}</span>
              <b className={`riskPill ${profile.risk_level.toLowerCase()}`}>{profile.risk_level}</b>
              <div className="inlineActions">
                <button type="button" onClick={() => onStatus(profile.user_id, "BLOCKED")} disabled={busy}>
                  Freeze
                </button>
                <button type="button" onClick={() => onStatus(profile.user_id, "ACTIVE")} disabled={busy}>
                  Reactivate
                </button>
              </div>
            </article>
          ))}
        </div>
      </section>
      <TransactionList transactions={admin.live_feed} onReceipt={onReceipt} />
    </section>
  );
}

function MerchantView({ dashboard, onReceipt }) {
  if (!dashboard) return <section className="toolPanel"><p className="empty">Merchant dashboard unavailable.</p></section>;
  return (
    <section className="analystGrid">
      <div className="metricWall">
        <Metric icon={<Store size={22} />} label="Merchant" value={dashboard.merchant.name} />
        <Metric icon={<Wallet size={22} />} label="Today" value={money(dashboard.summary.daily_sales)} />
        <Metric icon={<Activity size={22} />} label="This week" value={money(dashboard.summary.weekly_sales)} />
      </div>
      <section className="toolPanel">
        <div className="panelTitle"><Store size={20} /><h3>Static merchant QR</h3></div>
        <div className="qrBox"><QrCode size={130} /><strong>{dashboard.merchant.qr_code}</strong></div>
      </section>
      <TransactionList transactions={dashboard.sales} onReceipt={onReceipt} />
    </section>
  );
}

function Metric({ icon, label, value }) {
  return (
    <div className="metricBand">
      {icon}
      <div>
        <p>{label}</p>
        <strong>{value}</strong>
      </div>
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);
