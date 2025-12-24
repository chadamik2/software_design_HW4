import React from "react";

export default function UserIdBar({ userId, setUserId }) {
  return (
    <div className="card">
      <div className="row" style={{ alignItems: "center" }}>
        <div>
          <div><b>User ID</b></div>
          <small>В каждом запросе используется X-User-Id</small>
        </div>
        <input
          value={userId}
          onChange={(e) => setUserId(e.target.value)}
          placeholder="например: user-1"
          style={{ minWidth: 240 }}
        />
      </div>
    </div>
  );
}
