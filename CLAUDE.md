# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This repository contains educational materials and a React-based Spaced Repetition System (SRS) app to help a struggling student master pandas data analysis. The student has failed their test 6 times, showing they don't understand how to translate English questions into pandas operations.

### Project Goals
- Analyze student's common mistakes from their test attempts
- Build a React SRS app that drills problematic concepts
- Implement performance tracking with a completion code system
- Focus on Unix/system fundamentals where the student struggles most

## Key Information

### Primary Files
- **`index.html`** - Main React SRS app with spaced repetition learning
  - CDN-based (no build system required)
  - Tracks performance, hints, time spent
  - Exports results as .results files
- **`import.html`** - Results viewer for instructors
  - Imports and visualizes .results files
  - Shows performance charts and challenging questions
- **`Su 2025-07-22.md`** - Original exercise file with student's failing test
- **`pandas-equivalencies.md`** - Documents equivalent pandas operations

## Common Development Tasks

### React SRS App Development
- `npm install` - Install dependencies
- `npm start` - Run the development server
- `npm test` - Run the test suite
- `npm run build` - Build for production

### Key Components
- Question bank focusing on Unix/system concepts
- Spaced repetition algorithm for optimal learning
- Performance tracking and analytics
- Completion code generation when mastery achieved

## Student's Weak Areas (from analysis)
1. **Pandas Operations**: Doesn't know when to use sort_values(), value_counts(), groupby()
2. **Question Translation**: Can't map "most/least" → sorting, "how many" → counting
3. **Method Chaining**: Doesn't understand how to combine operations
4. **Context Awareness**: Doesn't realize same question words require different methods based on data

## Dynamic Question System
- Uses real CSV files from `datasets/` folder
- Generates contextually appropriate questions
- Progresses from multiple choice → guided code → free code entry
- Accepts multiple valid solutions

## Question Generation Process

### Primary Generator
- **`generator/generate_question_bank.py`** - Main question generator that works with any CSV dataset
  - Analyzes column types to generate appropriate questions
  - Creates value_counts, groupby, sorting, and filtering questions
  - Follows all pandas method guidelines listed above
  - Usage: `python generator/generate_question_bank.py datasets/[filename].csv`

### Supporting Files
- **`generator/analyze_csvs.py`** - Utility to analyze CSV structure before generating questions
- **`generator/review_questions.py`** - Evaluates question quality and removes nonsensical questions
- **`questions.json`** - Output file containing all generated questions with answers and hints
- **`update_questions.py`** - Script to filter and enhance existing questions

### Current Datasets Used
- powerplants.csv - US power plant data
- motorcycles.csv - Motorcycle specifications  
- tickets-tiny.csv - Traffic ticket data
- foods.csv - Pet food nutritional data
- grammys.csv - Grammy award data
- race-places.csv - Racing results data

## Pandas Method Guidelines for Question Generation
- **`.sort_values()`**: Use for "highest/lowest/most/least" questions - prefer over `.nlargest()`/`.nsmallest()`
- **`.value_counts(normalize=True)`**: Use for "What percentage of X are Y?" questions with categorical data (returns 0.0-1.0, no need for * 100)
- **`.mean()`**: Use for "What is the average/typical X?" questions with numeric data  
- **`.sum()`**: Use for "How many X?" questions with boolean conditions - it counts True values (True=1, False=0)
- **Prefer fundamentals**: Use `.sort_values()` + `.head()` instead of `.nlargest()` - teaches sorting concepts
- Some questions are just fine as filters, don't need to get fancy: "Show all of the nuclear power plants"
- **Avoid** Math or complicated ideas like floor division.
- **Avoid** Long, multi-step processes. `((df['Nationality'] == df['Country']) & (df['Race_Result'] == 1)).sum() / (df['Race_Result'] == 1).sum().head()` is no good, especially on a small screen. A "hard" question is best thought of as filter + groupby + aggregate, not just by being long.
- **Avoid** `df.assign`
- **Avoid** `.sort_index()`
- **Avoid**: Using `.mean()` on boolean conditions for percentage questions - use value_counts instead
- **Avoid**: Chaining `.head()` after single value results like `.mean()` or `.sum()`
- **Avoid**: Multiplying by 100 after `.value_counts(normalize=True)` - the decimal form (0.65 = 65%) is standard
- **Note**: For percentage questions about categorical data, always prefer `.value_counts(normalize=True)` over boolean masking with `.mean()`
- **Counting Tip**: When counting rows that meet a condition, use `(condition).sum()` not `.count()` - count() returns all non-null values
- When answering a question that only involves a subset of the columns, don't only look at those columns. It makes it extra complicated for no reason. Err on the side of simplicity.
  - BAD: `df.sort_values(by='price')[['price', 'make']]`
  - GOOD: `df.sort_values(by='price')`
  - BAD: `df.sort_values('total_mw', ascending=True).head(1)['plant_name']`
  - GOOD: `df.sort_values('total_mw', ascending=True).head(1)`
- Prefer `.value_counts()` to **
`df.groupby(XX).size()`

## Answer Explanations
When a student submits an answer, provide a brief explanation that includes:
- **Why the correct answer works**: Explain the pandas logic in plain English
- **Common mistakes**: For multiple choice, explain why wrong answers are tempting but incorrect
- **Method confusion**: Point out similar methods that don't apply here (e.g., using .count() instead of .sum())
- **Free text tips**: For code entry, list 2-3 common errors students make

Keep explanations concise (2-4 sentences) but complete enough to prevent the same mistake next time.

**Implementation Status**: ✅ Implemented in index.html. Explanations display after submitting answers in both multiple choice and code entry modes.

## Development Guidance
- When creating a new file, add a mention of what it is and what it does to CLAUDE.md
- When possible, update existing files instead of creating new versions of files

## Coding Guidelines
- Don't use any questions with lambdas
