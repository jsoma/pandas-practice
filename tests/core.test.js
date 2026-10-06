const assert = require('node:assert/strict');
const { test } = require('node:test');
const core = require('../practice-core.js');
const record = { question_id: '001', question_text: 'Question, with "quotes"\nand lines',
    answer_selected: 'answer = df["column"].mean()\nanswer', correct_answer: 'df["column"].mean()',
    is_correct: false, hint_shown: false, times_seen: 1, times_correct: 0,
    timestamp: 1700000000000, difficulty: 1, time_spent: 7, question_type: 'free_code',
    skipped: false, performance_streak: 0, session_id: 'test', dataset: 'test.csv' };

test('CSV round trip preserves code, multiline text, quotes and typed fields', () => {
    const records = [record, { ...record, is_correct: true, hint_shown: true }, { ...record, skipped: true }];
    const parsed = core.parseCSV(core.exportCSV(records));
    assert.deepEqual(parsed, records.map(row => ({ ...row, timestamp: new Date(row.timestamp).toISOString() })));
    assert.equal(parsed.filter(row => row.is_correct).length, 1);
    assert.equal(parsed.filter(row => row.skipped).length, 1);
});
test('legacy uppercase booleans and unquoted code quotes are preserved', () => {
    const csv = core.exportCSV([{ ...record, question_text: 'simple', answer_selected: 'df["column"].mean()' }])
        .replaceAll('"false"', 'FALSE').replace('"df[""column""].mean()"', 'df["column"].mean()');
    const row = core.parseCSV(csv)[0];
    assert.equal(row.is_correct, false);
    assert.equal(row.skipped, false);
    assert.equal(row.answer_selected, 'df["column"].mean()');
    assert.equal(row.question_id, '001');
});
test('malformed CSV fails instead of silently corrupting results', () => {
    assert.throws(() => core.parseCSV('id\n1'), /missing columns/);
    assert.throws(() => core.parseCSV(core.exportCSV([record]).slice(0, -1)), /unterminated/);
    assert.throws(() => core.parseCSV(core.exportCSV([record]).replace('"false"', '"maybe"')), /boolean/);
});
test('scheduler never serves future or ineligible questions', () => {
    const future = { difficulty: 1, srs: { nextReview: 101 } };
    const due = { difficulty: 2, srs: { nextReview: 100 } };
    assert.equal(core.selectQuestion([future], 3, 100), null);
    assert.equal(core.selectQuestion([future, due], 1, 100), null);
    assert.equal(core.selectQuestion([future, due], 2, 100), due);
    assert.equal(core.selectQuestion([future], 1, 101), future);
});

test('empty and contradictory imports fail with actionable errors', () => {
    assert.throws(() => core.parseCSV(core.exportCSV([])), /no attempts/);
    assert.throws(() => core.parseCSV(core.exportCSV([{ ...record, skipped: true, is_correct: true }])), /skipped attempt/);
});
test('every accuracy measure excludes skips consistently', () => {
    const data = [{...record, is_correct:true}, {...record, skipped:true}, {...record, is_correct:true}];
    const stats = core.calculateStats(data);
    assert.equal(stats.accuracy, 100);
    assert.equal(stats.difficultyStats[0].accuracy, 100);
    assert.equal(stats.sessionData[0].accuracy, 100);
    assert.equal(stats.difficultQuestions[0].accuracy, 100);
    assert.equal(stats.difficultyStats[0].total, 3);
    assert.equal(stats.difficultyStats[0].answered, 2);
});
test('all skipped and contradictory in-memory records cannot inflate accuracy', () => {
    const skipped = {...record, skipped:true};
    const stats = core.calculateStats([skipped, {...skipped, is_correct:true}]);
    assert.equal(stats.accuracy, 0);
    assert.equal(stats.avgTimeSpent, 0);
    assert.equal(stats.sessionData[0].accuracy, 0);
    assert.equal(stats.difficultyStats[0].accuracy, 0);
    assert.deepEqual(stats.difficultQuestions, []);
    assert.equal(core.calculateStats([{...record,is_correct:true}, {...skipped,is_correct:true}]).accuracy, 100);
});
