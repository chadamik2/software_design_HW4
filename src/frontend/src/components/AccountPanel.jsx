import React, { useState } from "react";
import { apiGet, apiPost } from "../api.js";

export default function AccountPanel({ userId }) {
  const [balance, setBalance] = useState(null);
  const [topupAmount, setTopupAmount] = useState("100.00");
  const [err, setErr] = useState("");

  async function refresh() {
    setErr("");
    try {
      const data = await apiGet("/accounts/balance", userId);
      setBalance(data.balance);
    } catch (e) {
      setErr(String(e));
    }
  }

  async function createAccount() {
    setErr("");
    try {
      const data = await apiPost("/accounts", userId, {});
      setBalance(data.balance);
    } catch (e) {
      setErr(String(e));
    }
  }

  async function topup() {
    setErr("");
    try {
      const data = await apiPost("/accounts/topup", userId, { amount: topupAmount });
      setBalance(data.balance);
    } catch (e) {
      setErr(String(e));
    }
  }

  return (
    <div className="card">
      <div className="row" style={{ alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <div><b>Payments</b></div>
          <small>Счёт: создание, пополнение, баланс</small>
        </div>
        <div className="row">
          <button onClick={createAccount} disabled={!userId}>Создать счёт</button>
          <button onClick={refresh} disabled={!userId}>Обновить баланс</button>
        </div>
      </div>

      <div style={{ marginTop: 12 }}>
        <div>Баланс: <b>{balance ?? "—"}</b></div>
      </div>

      <div className="row" style={{ marginTop: 12, alignItems: "center" }}>
        <input
          value={topupAmount}
          onChange={(e) => setTopupAmount(e.target.value)}
          placeholder="100.00"
        />
        <button onClick={topup} disabled={!userId}>Пополнить</button>
      </div>

      {err ? <div style={{ marginTop: 12, color: "#ff8080" }}>{err}</div> : null}
    </div>
  );
}
