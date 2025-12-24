import React, { useEffect, useMemo, useRef, useState } from "react";
import { apiGet } from "../api.js";
import { toast } from "react-toastify";

function notify(title, body) {
  try {
    if (!("Notification" in window)) return;
    if (Notification.permission === "granted") {
      new Notification(title, { body });
    }
  } catch (_) {}
}

export default function OrderDetails({ userId, orderId }) {
  const [order, setOrder] = useState(null);
  const [err, setErr] = useState("");
  const wsRef = useRef(null);

  async function refresh() {
    setErr("");
    try {
      const data = await apiGet(`/orders/${orderId}`, userId);
      setOrder(data);
    } catch (e) {
      setErr(String(e));
    }
  }

  const wsUrl = useMemo(() => {
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    return `${proto}://${window.location.host}/ws/orders/${orderId}?user_id=${encodeURIComponent(userId)}`;
  }, [orderId, userId]);

  useEffect(() => {
    if (!userId || !orderId) return;
    refresh();

    if ("Notification" in window && Notification.permission === "default") {
      Notification.requestPermission().catch(() => {});
    }

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      toast.info("WebSocket подключен: отслеживание статуса заказа");
    };

    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg?.type === "snapshot") {
          setOrder((prev) => prev ? { ...prev, status: msg.status } : prev);
          return;
        }
        if (msg?.type === "update") {
          setOrder((prev) => prev ? { ...prev, status: msg.status } : prev);

          const text = `Заказ ${msg.order_id}: ${msg.status}`;
          toast.success(text);
          notify("Гоzон: статус заказа", text);
        }
      } catch (_) {}
    };

    ws.onerror = () => {
      toast.error("WebSocket error");
    };

    ws.onclose = () => {
      toast.warn("WebSocket закрыт");
    };

    return () => {
      try { ws.close(); } catch (_) {}
    };
  }, [userId, orderId, wsUrl]);

  return (
    <div className="card">
      <div><b>Order details</b></div>
      <small>WebSocket: {wsUrl}</small>

      {err ? <div style={{ marginTop: 12, color: "#ff8080" }}>{err}</div> : null}

      <div style={{ marginTop: 12 }}>
        {!order ? (
          <small>Загрузка…</small>
        ) : (
          <div>
            <div><b>ID:</b> {order.id}</div>
            <div><b>Amount:</b> {order.amount}</div>
            <div><b>Description:</b> {order.description}</div>
            <div><b>Status:</b> {order.status}</div>
          </div>
        )}
      </div>

      <div className="row" style={{ marginTop: 12 }}>
        <button onClick={refresh} disabled={!userId}>Обновить</button>
      </div>
    </div>
  );
}
