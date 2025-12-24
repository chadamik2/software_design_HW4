import React, { useState } from "react";
import { ToastContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";

import UserIdBar from "./components/UserIdBar.jsx";
import AccountPanel from "./components/AccountPanel.jsx";
import OrdersPanel from "./components/OrdersPanel.jsx";
import OrderDetails from "./components/OrderDetails.jsx";

export default function App() {
  const [userId, setUserId] = useState("user-1");
  const [selectedOrderId, setSelectedOrderId] = useState(null);

  return (
    <div className="container">
      <ToastContainer position="bottom-right" />
      <UserIdBar userId={userId} setUserId={setUserId} />

      <div className="row">
        <div style={{ flex: 1, minWidth: 340 }}>
          <AccountPanel userId={userId} />
          <OrdersPanel userId={userId} onSelectOrder={setSelectedOrderId} />
        </div>

        <div style={{ flex: 1, minWidth: 340 }}>
          {selectedOrderId ? (
            <OrderDetails userId={userId} orderId={selectedOrderId} />
          ) : (
            <div className="card">
              <div><b>Order details</b></div>
              <small>Выберите заказ из списка</small>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
