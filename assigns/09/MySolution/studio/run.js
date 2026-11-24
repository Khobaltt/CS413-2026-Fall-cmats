import { requestJson } from "./storage.js";

async function interpret(source) {
    const { payload } = await requestJson("/studio/interpret", { method: "POST", body: { source } });
    if (payload?.jsonrpc !== "2.0" || payload.id !== 1
        || Object.hasOwn(payload, "result") === Object.hasOwn(payload, "error")) {
        throw new Error("Invalid reply from LAMBDA3");
    }
    if (typeof payload.result?.value === "string") {
        return { kind: "value", value: payload.result.value };
    }
    const code = payload.error?.code;
    const category = payload.error?.data?.kind;
    if ((code === -32010 && category === "syntax") || (code === -32011 && category === "type")) {
        return { kind: "error", category };
    }
    throw new Error(payload.error?.message ?? "Invalid reply from LAMBDA3");
}

function matches(expected, actual) {
    return expected.kind === actual.kind && (expected.kind === "value"
        ? expected.value === actual.value : expected.category === actual.category);
}

export function describe(outcome) {
    return outcome.kind === "value" ? JSON.stringify(outcome.value) : `${outcome.category} error`;
}

export async function runCases(snapshot, onResult) {
    for (const testCase of snapshot.cases) {
        let result;
        try {
            const actual = await interpret(testCase.source);
            result = { pass: matches(testCase.expected, actual), observed: describe(actual) };
        } catch (error) {
            result = { pass: false, observed: error.message };
        }
        onResult({ ...testCase, ...result });
    }
}
