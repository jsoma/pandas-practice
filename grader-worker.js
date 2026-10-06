const base = 'https://cdn.jsdelivr.net/pyodide/v0.29.2/full/';
let ready;
function initialize() {
    if (!ready) {
        ready = (async () => {
            importScripts(base + 'pyodide.js');
            const runtime = await loadPyodide({ indexURL: base });
            await runtime.loadPackage('pandas');
            const response = await fetch('./grading.py');
            if (!response.ok) throw new Error('Could not load the answer checker.');
            runtime.runPython(await response.text());
            return runtime;
        })().catch(error => {
            ready = undefined;
            throw error;
        });
    }
    return ready;
}
const datasets = new Map();
onmessage = async ({ data }) => {
    try {
        const runtime = await initialize();
        if (!datasets.has(data.dataset)) {
            const response = await fetch('./datasets/' + encodeURIComponent(data.dataset));
            if (!response.ok) throw new Error('Could not load the dataset.');
            datasets.set(data.dataset, await response.text());
        }
        runtime.globals.set('csv_input', datasets.get(data.dataset));
        runtime.globals.set('canonical_input', data.canonical);
        runtime.globals.set('answer_input', data.answer);
        runtime.globals.set('preserve_order_input', data.preserveOrder ?? true);
        postMessage(JSON.parse(runtime.runPython('grade(csv_input, canonical_input, answer_input, preserve_order_input)')));
    } catch (error) {
        postMessage({ error: 'Answer checker unavailable: ' + error.message });
    }
};
