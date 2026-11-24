export class ClientError extends Error {
    constructor(message, code, details = {}) {
        super(message);
        this.code = code;
        this.details = details;
    }
}

export async function requestJson(path, { method = "GET", body, tag } = {}) {
    const headers = { Accept: "application/json" };
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (tag !== undefined) headers["If-Match"] = tag;
    let response;
    try {
        response = await fetch(path, {
            method, headers, body: body === undefined ? undefined : JSON.stringify(body),
            cache: "no-store", signal: AbortSignal.timeout(6000),
        });
    } catch {
        throw new ClientError("The request failed or timed out. Check the service and try again.", "network");
    }
    if (response.status === 204) return {};
    let payload;
    try {
        payload = await response.json();
    } catch {
        throw new ClientError("The server response was incomplete or invalid.", "invalid_response");
    }
    if (!response.ok) {
        const error = payload?.error;
        throw new ClientError(error?.message ?? `HTTP ${response.status}`, error?.code, error);
    }
    return { payload, tag: response.headers.get("ETag") };
}

export class StorageAdapter {
    constructor(resource) {
        this.path = `/api/v1/${resource}s`;
        this.resource = resource;
    }

    async list() {
        const items = [];
        let cursor;
        do {
            const query = new URLSearchParams({ limit: 100 });
            if (cursor) query.set("cursor", cursor);
            const { payload } = await requestJson(`${this.path}?${query}`);
            items.push(...payload.items);
            cursor = payload.next_cursor;
        } while (cursor);
        return items;
    }

    async item(path, options) {
        const { payload, tag } = await requestJson(path, options);
        return { record: payload[this.resource], tag };
    }

    get(id) {
        return this.item(`${this.path}/${encodeURIComponent(id)}`);
    }

    save(body, current) {
        if (!current) return this.item(this.path, { method: "POST", body });
        const { record: { id }, tag } = current;
        return this.item(`${this.path}/${encodeURIComponent(id)}`, { method: "PUT", tag, body });
    }

    remove({ record: { id }, tag }) {
        return requestJson(`${this.path}/${encodeURIComponent(id)}`, { method: "DELETE", tag });
    }

    saveCase(collection, caseId, body) {
        const path = `${this.path}/${encodeURIComponent(collection.record.id)}/cases`;
        if (!caseId) return this.item(path, { method: "POST", tag: collection.tag, body });
        return this.item(`${path}/${encodeURIComponent(caseId)}`, {
            method: "PUT", tag: collection.tag, body,
        });
    }

    removeCase(collection, caseId) {
        const path = `${this.path}/${encodeURIComponent(collection.record.id)}/cases/${encodeURIComponent(caseId)}`;
        return this.item(path, { method: "DELETE", tag: collection.tag });
    }
}
