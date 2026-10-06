(function (root) {
    const headers = ['question_id', 'question_text', 'answer_selected', 'correct_answer',
        'is_correct', 'hint_shown', 'times_seen', 'times_correct', 'timestamp', 'difficulty',
        'time_spent', 'question_type', 'skipped', 'performance_streak', 'session_id', 'dataset'];
    const booleans = new Set(['is_correct', 'hint_shown', 'skipped']);
    const numbers = new Set(['times_seen', 'times_correct', 'difficulty', 'time_spent', 'performance_streak']);
    function exportCSV(data) {
        const escape = value => '"' + String(value ?? '').replace(/"/g, '""') + '"';
        return [headers.join(','), ...data.map(row => headers.map(key =>
            escape(key === 'timestamp' ? new Date(row[key]).toISOString() : row[key])
        ).join(','))].join('\r\n');
    }
    function parseCSV(text) {
        const rows = []; let row = [], value = '', quoted = false;
        for (let i = 0; i < text.length; i++) {
            const char = text[i];
            if (char === '"') {
                if (quoted && text[i + 1] === '"') { value += '"'; i++; }
                else if (quoted || value === '') quoted = !quoted;
                else value += char; // Preserve quotes in legacy unquoted code fields.
            } else if (char === ',' && !quoted) { row.push(value); value = ''; }
            else if ((char === '\n' || char === '\r') && !quoted) {
                if (char === '\r' && text[i + 1] === '\n') i++;
                row.push(value); if (row.some(v => v !== '')) rows.push(row);
                row = []; value = '';
            } else value += char;
        }
        if (quoted) throw new Error('Invalid CSV: unterminated quoted field.');
        row.push(value); if (row.some(v => v !== '')) rows.push(row);
        const columns = rows.shift();
        if (!columns || headers.some(h => !columns.includes(h))) throw new Error('Invalid results file: missing columns.');
        if (!rows.length) throw new Error('This results file contains no attempts.');
        return rows.map(values => {
            if (values.length !== columns.length) throw new Error('Invalid CSV row length.');
            const record = Object.fromEntries(columns.map((key, i) => {
                let value = values[i];
                if (booleans.has(key)) {
                    if (!/^(true|false)$/i.test(value)) throw new Error('Invalid boolean: ' + key);
                    value = value.toLowerCase() === 'true';
                } else if (numbers.has(key)) {
                    if (value.trim() === '' || !Number.isFinite(Number(value))) throw new Error('Invalid number: ' + key);
                    value = Number(value);
                }
                return [key, value];
            }));
            if (record.skipped && record.is_correct) throw new Error('A skipped attempt cannot be marked correct.');
            return record;
        });
    }
    function calculateStats(data) {
        if (!data?.length) return null;
        const answered = data.filter(row => !row.skipped);
        const correct = answered.filter(row => row.is_correct).length;
        const percentage = (correct, total) => total ? correct / total * 100 : 0;
        const difficultyStats = [1, 2, 3].map(level => {
            const all = data.filter(row => row.difficulty === level);
            const attempts = all.filter(row => !row.skipped);
            const correct = attempts.filter(row => row.is_correct).length;
            return { level, total: all.length, answered: attempts.length, correct,
                accuracy: percentage(correct, attempts.length) };
        });
        const sessions = new Map();
        const questions = new Map();
        for (const row of data) {
            if (!sessions.has(row.session_id)) sessions.set(row.session_id,
                { total: 0, answered: 0, correct: 0, timestamp: row.timestamp });
            const session = sessions.get(row.session_id);
            session.total++;
            if (!row.skipped) { session.answered++; if (row.is_correct) session.correct++; }
            if (!questions.has(row.question_id)) questions.set(row.question_id,
                { text: row.question_text, attempts: 0, answered: 0, correct: 0, hints: 0, totalTime: 0 });
            const question = questions.get(row.question_id);
            question.attempts++;
            if (row.hint_shown) question.hints++;
            if (!row.skipped) {
                question.answered++;
                question.totalTime += row.time_spent;
                if (row.is_correct) question.correct++;
            }
        }
        return {
            totalQuestions: data.length,
            uniqueQuestions: new Set(data.map(row => row.question_id)).size,
            correctAnswers: correct,
            skippedQuestions: data.length - answered.length,
            hintsUsed: data.filter(row => row.hint_shown).length,
            accuracy: percentage(correct, answered.length),
            avgTimeSpent: answered.length ? answered.reduce((sum, row) => sum + row.time_spent, 0) / answered.length : 0,
            difficultyStats,
            sessionData: [...sessions].map(([id, stats]) => ({ id, ...stats,
                accuracy: percentage(stats.correct, stats.answered) }))
                .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp)),
            difficultQuestions: [...questions].map(([id, stats]) => ({ id, ...stats,
                accuracy: percentage(stats.correct, stats.answered),
                avgTime: stats.answered ? stats.totalTime / stats.answered : 0 }))
                .filter(question => question.answered >= 2)
                .sort((a, b) => a.accuracy - b.accuracy).slice(0, 5)
        };
    }
    function selectQuestion(questions, maxDifficulty, now = Date.now(), random = Math.random) {
        const due = questions.filter(q => q.difficulty <= maxDifficulty && q.srs.nextReview <= now);
        return due.length ? due[Math.floor(random() * due.length)] : null;
    }
    function shuffle(values) {
        const copy = [...values];
        for (let i = copy.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [copy[i], copy[j]] = [copy[j], copy[i]];
        }
        return copy;
    }
    root.PracticeCore = { exportCSV, parseCSV, calculateStats, selectQuestion, shuffle };
    if (typeof module !== 'undefined') module.exports = root.PracticeCore;
})(globalThis);
