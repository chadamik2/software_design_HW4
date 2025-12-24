export async function apiGet(path, userId) {
  const res = await fetch(path, {
    method: "GET",
    headers: {
      "X-User-Id": userId
    }
  });
  if (!res.ok) throw new Error(await res.text());
  return await res.json();
}

export async function apiPost(path, userId, body) {
  const res = await fetch(path, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-User-Id": userId
    },
    body: JSON.stringify(body ?? {})
  });
  if (!res.ok) throw new Error(await res.text());
  return await res.json();
}
