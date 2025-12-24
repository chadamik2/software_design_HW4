import React, { useEffect, useState } from "react";
import { apiGet, apiPost } from "../api.js";

export default function OrdersPanel({ userId, onSelectOrder }) {
  const [orders, setOrders] = useState([]);
  const [amount, setAmount] = useState("50.00");
  const [description, setDescription] = useState("Заказ");
  const [err, setErr] = useState("");

  async function refresh() {
    setErr("");
    try {
      const data = await apiGet("/orders", userId);
      setOrders(data.orders ?? []);
    } catch (e) {
      setErr(String(e));
    }
  }

  async function createOrder() {
    setErr("");
    try {
      const data = await apiPost("/orders", userId, { amount, description });
      await refresh();
      onSelectOrder?.(data.id);
    } catch (e) {
      setErr(String(e));
    }
  }

  useEffect(() => {
    if (userId) refresh();
  }, [userId]);

  return (
    <div className="card">
      <div className="row" style={{ alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <div><b>Orders</b></div>
          <small>Создание заказа, введите стоимость и описание</small>
        </div>
        <div className="row">
          <button onClick={refresh} disabled={!userId}>Обновить</button>
        </div>
      </div>

      <div className="row" style={{ marginTop: 12, alignItems: "center" }}>
        <input value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="Стоимость" style={{ flex: 1 }}/>
        <input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Описание" style={{ flex: 1 }} />
        <button onClick={createOrder} disabled={!userId}>Создать заказ</button>
      </div>

      {err ? <div style={{ marginTop: 12, color: "#ff8080" }}>{err}</div> : null}

      <div style={{ marginTop: 12 }}>
        {orders.length === 0 ? (
          <small>Заказов нет</small>
        ) : (
          <div>
            {orders.map((o) => (
              <div
                key={o.id}
                className="card"
                style={{ marginTop: 10, cursor: "pointer" }}
                onClick={() => onSelectOrder?.(o.id)}
              >
                <div><b>{o.id}</b></div>
                <small>amount: {o.amount} • description: {o.description} • status: {o.status}</small>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
