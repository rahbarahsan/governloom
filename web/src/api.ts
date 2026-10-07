let adminToken = "";
export function setAdminToken(value: string) {
  adminToken = value;
}
export async function downloadEvidence(path: string) {
  const response = await fetch(path, {
    headers: adminToken ? { Authorization: `Bearer ${adminToken}` } : {},
  });
  if (!response.ok)
    throw new Error("Evidence download failed; check collector access.");
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download =
    response.headers
      .get("Content-Disposition")
      ?.match(/filename="([^"]+)"/)?.[1] ?? "governloom-evidence.json";
  link.click();
  URL.revokeObjectURL(url);
}
export async function api<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(
    `/api${path}`,
    body === undefined
      ? { headers: adminToken ? { Authorization: `Bearer ${adminToken}` } : {} }
      : {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(adminToken ? { Authorization: `Bearer ${adminToken}` } : {}),
          },
          body: JSON.stringify(body),
        },
  );
  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: response.statusText }));
    throw new Error(
      typeof error.detail === "string"
        ? error.detail
        : JSON.stringify(error.detail),
    );
  }
  return response.json();
}

export async function readUtf8(file: File): Promise<string> {
  if (file.size > 5_000_000)
    throw new Error("File exceeds the 5 MB import limit.");
  return new TextDecoder("utf-8", { fatal: true }).decode(
    await file.arrayBuffer(),
  );
}

export const title = (text: string) => text.replaceAll("_", " ");
export const date = (text: string) => new Date(text).toLocaleString();
export const number = (value: number | null) =>
  value === null
    ? "Unavailable"
    : Number.isInteger(value)
      ? String(value)
      : value.toPrecision(4);
