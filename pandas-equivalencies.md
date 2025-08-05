# Pandas Code Equivalency System

## Overview
Instead of pre-generating all variations, the JavaScript app will parse pandas code and understand equivalent operations.

## Architecture

### 1. Pandas AST Parser (Simplified)

```javascript
// Parse pandas method chains into an AST-like structure
function parsePandasCode(code) {
  // df['state'].value_counts().head(1)
  // becomes:
  return {
    base: 'df',
    operations: [
      { type: 'index', column: 'state' },
      { type: 'method', name: 'value_counts', args: [] },
      { type: 'method', name: 'head', args: [1] }
    ]
  };
}
```

### 2. Equivalency Rules

```javascript
const equivalencyRules = [
  {
    // nlargest === sort_values + head
    pattern: [
      { type: 'method', name: 'nlargest', args: ['{n}', '{col}'] }
    ],
    equivalent: [
      { type: 'method', name: 'sort_values', args: ['{col}', { ascending: false }] },
      { type: 'method', name: 'head', args: ['{n}'] }
    ]
  },
  {
    // nsmallest === sort_values + head
    pattern: [
      { type: 'method', name: 'nsmallest', args: ['{n}', '{col}'] }
    ],
    equivalent: [
      { type: 'method', name: 'sort_values', args: ['{col}'] },
      { type: 'method', name: 'head', args: ['{n}'] }
    ]
  },
  {
    // idxmax === sort_values + index[0]
    pattern: [
      { type: 'method', name: 'idxmax' }
    ],
    equivalent: [
      { type: 'method', name: 'sort_values', args: [{ ascending: false }] },
      { type: 'index', attr: 'index' },
      { type: 'index', position: 0 }
    ]
  },
  {
    // head(1) === iloc[0:1] === iloc[:1]
    pattern: [
      { type: 'method', name: 'head', args: [1] }
    ],
    equivalent: [
      { type: 'method', name: 'iloc', slice: [0, 1] }
    ]
  },
  {
    // Boolean indexing variations
    pattern: [
      { type: 'index', condition: '{condition}' }
    ],
    equivalent: [
      { type: 'method', name: 'loc', args: ['{condition}'] },
      { type: 'method', name: 'query', args: ['{condition_string}'] }
    ]
  }
];
```

### 3. Question Generation Output

```json
{
  "questions": [
    {
      "id": "powerplants_001",
      "question": "Which state has the most power plants?",
      "canonicalAnswer": {
        "code": "df['state'].value_counts().head(1)",
        "operations": [
          { "type": "index", "column": "state" },
          { "type": "method", "name": "value_counts" },
          { "type": "method", "name": "head", "args": [1] }
        ],
        "result": "California    1344"
      },
      "concepts": ["counting", "value_counts", "head"]
    }
  ]
}
```

### 4. Answer Checker Implementation

```javascript
class PandasEquivalencyChecker {
  constructor(equivalencyRules) {
    this.rules = equivalencyRules;
  }
  
  checkAnswer(studentCode, canonicalAnswer) {
    // 1. Parse student code
    const studentOps = parsePandasCode(studentCode);
    
    // 2. Normalize both to canonical form
    const studentCanonical = this.toCanonical(studentOps);
    const expectedCanonical = canonicalAnswer.operations;
    
    // 3. Check if they're equivalent
    if (this.areEquivalent(studentCanonical, expectedCanonical)) {
      return { correct: true };
    }
    
    // 4. Check known equivalencies
    const equivalents = this.generateEquivalents(expectedCanonical);
    for (const equiv of equivalents) {
      if (this.areEquivalent(studentCanonical, equiv)) {
        return { 
          correct: true, 
          note: "Correct! (Alternative approach)" 
        };
      }
    }
    
    return { correct: false };
  }
  
  generateEquivalents(operations) {
    const equivalents = [operations]; // Original is always valid
    
    // Apply each rule to generate alternatives
    for (const rule of this.rules) {
      if (this.matchesPattern(operations, rule.pattern)) {
        const equivalent = this.applyRule(operations, rule);
        equivalents.push(equivalent);
      }
    }
    
    return equivalents;
  }
  
  // Convert common patterns to canonical form
  toCanonical(operations) {
    // df.column === df['column']
    // .loc[condition] === [condition]
    // etc.
  }
}
```

### 5. Common Equivalencies to Support

#### Indexing
- `df['col']` === `df.col` (for valid identifiers)
- `df[condition]` === `df.loc[condition]`
- `df.iloc[0]` === `df.iloc[0:1]` (for single row, but different output format)

#### Sorting & Selection
- `.nlargest(n, col)` === `.sort_values(col, ascending=False).head(n)`
- `.nsmallest(n, col)` === `.sort_values(col).head(n)`
- `.idxmax()` === `.sort_values(ascending=False).index[0]`
- `.idxmin()` === `.sort_values().index[0]`

#### Counting & Grouping
- `.value_counts()` === `.groupby(col).size().sort_values(ascending=False)`
- `.nunique()` === `.unique().size` === `len(df[col].unique())`

#### Filtering
- `df[df.col > 5]` === `df.loc[df.col > 5]` === `df.query('col > 5')`

#### Aggregations
- `.mean()` === `.sum() / .count()` (conceptually)
- Multiple aggregations can be reordered

### 6. Benefits of This Approach

1. **Flexible**: Can handle variations we didn't anticipate
2. **Maintainable**: Add new rules without regenerating questions
3. **Educational**: Can show students equivalent approaches
4. **Lightweight**: Rules are just data, easy to update

### 7. Implementation Strategy

```javascript
// In the React app
const checker = new PandasEquivalencyChecker(equivalencyRules);

function handleSubmit(studentCode) {
  const result = checker.checkAnswer(studentCode, currentQuestion.canonicalAnswer);
  
  if (result.correct) {
    if (result.note) {
      showFeedback("Correct! Your approach works too!");
      showAlternative(currentQuestion.canonicalAnswer.code);
    }
  } else {
    // Maybe check for common mistakes
    const mistake = detectCommonMistake(studentCode);
    if (mistake) {
      showHint(mistake.hint);
    }
  }
}
```

### 8. Progressive Complexity

Start with basic equivalencies:
- Quote normalization
- Whitespace handling
- Simple method equivalents

Later add:
- Complex chain equivalencies
- Semantic understanding (sum/count → mean)
- Performance considerations feedback