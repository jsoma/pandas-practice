const assert = require('node:assert/strict');
const { test } = require('node:test');
const fs = require('node:fs');
const vm = require('node:vm');

test('worker retries initialization after a transient download failure', async () => {
    const messages = []; let loads = 0; const globals = new Map();
    const context = vm.createContext({
        importScripts() {},
        async loadPyodide() {
            if (++loads === 1) throw new Error('offline');
            return { async loadPackage() {}, globals,
                runPython(code) { return code.startsWith('grade(') ? '{"correct":true,"message":"Correct!"}' : undefined; } };
        },
        async fetch(url) { return {ok:true, async text() { return url.includes('grading.py') ? '# grader' : 'value\n1'; }}; },
        postMessage(message) { messages.push(message); }
    });
    vm.runInContext(fs.readFileSync(require.resolve('../grader-worker.js'), 'utf8'), context);
    const data = { dataset:'test.csv', canonical:'df["value"].sum()', answer:'df["value"].sum()', preserveOrder:false };
    await context.onmessage({data});
    assert.match(messages[0].error, /offline/);
    await context.onmessage({data});
    assert.equal(loads, 2);
    assert.equal(messages[1].correct, true);
    assert.equal(globals.get('preserve_order_input'), false);
    await context.onmessage({data});
    assert.equal(loads, 2);
});
