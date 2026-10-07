export async function api<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(
    `/api${path}`,
    body === undefined
      ? undefined
      : {
          method: "POST",
          headers: { "Content-Type": "application/json" },
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
