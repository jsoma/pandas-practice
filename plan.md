# React SRS App: Pandas Mastery Through Dynamic Question Generation

## Core Problem
The student doesn't understand how to translate data questions into pandas operations. They need practice with real datasets to develop intuition about when to use different methods.

## Smart Question Generation System

### 1. Dataset Analysis Phase

When loading a CSV, the system will:

```typescript
interface DatasetAnalysis {
  entityType: string;  // "power plant", "motorcycle", "house"
  entityName: string;  // Column that identifies each entity
  
  columns: {
    [colName: string]: {
      dtype: 'numeric' | 'categorical' | 'datetime';
      cardinality: number;  // Number of unique values
      nullCount: number;
      
      // Analytical capabilities
      canGroupBy: boolean;      // Low cardinality categorical
      canCount: boolean;         // Any categorical
      canSum: boolean;           // Numeric, makes semantic sense
      canAverage: boolean;       // Numeric, makes semantic sense
      canRank: boolean;          // Numeric
      canFilter: boolean;        // Any column
      
      // Semantic understanding
      represents: 'identifier' | 'category' | 'measurement' | 'count' | 'location' | 'date';
      examples: any[];           // Sample values
    }
  }
}
```

### 2. Column Categorization Rules

```javascript
function categorizeColumn(colName, dtype, uniqueCount, totalRows, sampleValues) {
  const categories = {
    // Good for groupby (low cardinality categorical)
    groupable: dtype === 'categorical' && uniqueCount < totalRows * 0.5,
    
    // Good for counting
    countable: dtype === 'categorical',
    
    // Good for numerical operations
    summable: dtype === 'numeric' && colName.match(/total|amount|sum|count/i),
    averageable: dtype === 'numeric' && !colName.match(/id|code|zip/i),
    
    // Good for ranking
    rankable: dtype === 'numeric' && colName.match(/score|rating|price|speed|power/i),
    
    // Identifiers (high cardinality)
    identifier: (dtype === 'categorical' && uniqueCount > totalRows * 0.9) || 
                colName.match(/id|code|name/i)
  };
  
  return categories;
}
```

### 3. Question Generation Templates

Based on column capabilities, generate contextually appropriate questions:

```javascript
const questionTemplates = [
  {
    // "Which state has the most power plants?"
    requirements: ['groupable', 'entityType'],
    template: "Which {groupable} has the most {entityType}s?",
    code: "df['{groupable}'].value_counts().head(1)",
    difficulty: 1
  },
  {
    // "What's the average price by manufacturer?"
    requirements: ['groupable', 'averageable'],
    template: "What's the average {averageable} by {groupable}?",
    code: "df.groupby('{groupable}')['{averageable}'].mean()",
    difficulty: 2
  },
  {
    // "Find the top 5 motorcycles by power output"
    requirements: ['entityType', 'rankable'],
    template: "Find the top 5 {entityType}s by {rankable}",
    code: "df.nlargest(5, '{rankable}')",
    difficulty: 1
  },
  {
    // "Which manufacturer has the highest total production?"
    requirements: ['groupable', 'summable'],
    template: "Which {groupable} has the highest total {summable}?",
    code: "df.groupby('{groupable}')['{summable}'].sum().idxmax()",
    difficulty: 3
  }
];
```

### 4. Question Generation Algorithm

```javascript
function generateQuestion(dataset, analysis) {
  // 1. Find all applicable templates based on column capabilities
  const applicableTemplates = questionTemplates.filter(template => 
    template.requirements.every(req => 
      req === 'entityType' || 
      Object.values(analysis.columns).some(col => col[req])
    )
  );
  
  // 2. Select a template based on student's level
  const template = selectByDifficulty(applicableTemplates, studentLevel);
  
  // 3. Fill in the template with actual column names
  const question = fillTemplate(template, analysis);
  
  // 4. Generate the correct code
  const correctCode = fillCodeTemplate(template.code, analysis);
  
  // 5. Execute the code to get the actual answer
  const actualAnswer = executeCode(dataset, correctCode);
  
  // 6. Generate plausible wrong answers for multiple choice
  const wrongAnswers = generateWrongAnswers(template, analysis);
  
  return {
    question,
    correctCode,
    actualAnswer,
    wrongAnswers,
    explanation: `This question requires ${template.requirements.join(' and ')}`
  };
}
```

### 5. Example Question Generation

**Dataset: powerplants.csv**
```
Analysis:
- Entity type: "power plant"
- Columns:
  - state: groupable (50 unique values)
  - total_mw: summable, averageable, rankable
  - primary_source: groupable (10 unique values)
  - plant_name: identifier
```

**Generated Questions:**
1. "Which state has the most power plants?"
   - Code: `df['state'].value_counts().head(1)`
   - Answer: California (1,234 plants)

2. "What's the average total_mw by primary_source?"
   - Code: `df.groupby('primary_source')['total_mw'].mean()`
   - Answer: Shows actual computed values

3. "Find the top 5 power plants by total_mw"
   - Code: `df.nlargest(5, 'total_mw')`
   - Answer: Shows actual top 5 plants

### 6. Answer Verification System

```javascript
async function verifyAnswer(dataset, studentCode, correctCode) {
  try {
    // Execute both codes
    const studentResult = await executePandas(dataset, studentCode);
    const correctResult = await executePandas(dataset, correctCode);
    
    // Compare results
    if (resultsMatch(studentResult, correctResult)) {
      return { correct: true };
    }
    
    // Check for common variations
    const variations = [
      correctCode.replace('.head(1)', '.iloc[0]'),
      correctCode.replace('.idxmax()', '.sort_values(ascending=False).head(1)'),
      correctCode.replace('nlargest(5,', 'sort_values(').replace(')', ', ascending=False).head(5)')
    ];
    
    for (const variation of variations) {
      const varResult = await executePandas(dataset, variation);
      if (resultsMatch(studentResult, varResult)) {
        return { 
          correct: true, 
          note: "Correct! (Alternative approach accepted)" 
        };
      }
    }
    
    return { 
      correct: false, 
      expected: correctResult,
      actual: studentResult 
    };
  } catch (error) {
    return { 
      correct: false, 
      error: error.message 
    };
  }
}
```

### 7. Implementation Architecture

```
src/
├── analyzers/
│   ├── DatasetAnalyzer.ts      # Analyzes CSV structure
│   ├── ColumnCategorizer.ts    # Categorizes columns by use
│   └── EntityDetector.ts       # Detects what each row represents
├── generators/
│   ├── QuestionGenerator.ts    # Main generation logic
│   ├── TemplateEngine.ts       # Fills templates with data
│   └── WrongAnswerGen.ts       # Creates plausible distractors
├── executors/
│   ├── PandasExecutor.ts       # Runs pandas code safely
│   ├── ResultComparator.ts     # Compares outputs
│   └── CodeNormalizer.ts       # Handles syntax variations
└── components/
    ├── DataPreview.tsx         # Shows first N rows
    ├── QuestionDisplay.tsx     # Shows generated question
    ├── CodeEditor.tsx          # Student code input
    └── ResultFeedback.tsx      # Shows correct/incorrect
```

### 8. Benefits of This Approach

1. **Infinite Questions**: Can generate new questions from any CSV
2. **Always Valid**: Questions make semantic sense for the data
3. **Verified Answers**: Code is executed to ensure correctness
4. **Adaptive Difficulty**: Adjusts based on student performance
5. **Real-World Skills**: Students work with actual data

### 9. Example Flow

1. **Load Dataset**: motorcycles.csv
2. **Analyze**: 
   - Entity: "motorcycle"
   - make: groupable
   - power: rankable, averageable
   - weight: rankable, averageable
3. **Generate Question**: "Which make has the highest average power?"
4. **Student Types**: `df.groupby('make')['power'].mean().idxmax()`
5. **System Executes**: Both student and correct code
6. **Verifies**: Results match → Correct!
7. **Track Progress**: Student improving on groupby questions

### 10. Progressive Difficulty Levels

**Level 1: Single Operations**
- `df['col'].value_counts()`
- `df['col'].mean()`
- `df.sort_values('col')`

**Level 2: Two Operations**
- `df[df['col'] > X]['other'].mean()`
- `df.groupby('col')['other'].sum()`

**Level 3: Complex Chains**
- `df[df['type'] == 'coal'].groupby('state')['mw'].sum().nlargest(5)`
- `df.groupby(['state', 'type'])['mw'].mean().sort_values(ascending=False)`

The system tracks which types of operations the student struggles with and generates more questions targeting those weak areas.