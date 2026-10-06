# Pandas Mastery

A static pandas practice app with spaced reviews and a results viewer.

## Run locally

Serve this directory over HTTP (opening `index.html` directly does not support dataset fetching or workers):

```sh
python3 -m http.server 8000
```

Open http://localhost:8000 to practice, or http://localhost:8000/import.html to inspect exported `.results` archives.

Code answers are compared with the canonical pandas result on the full CSV, using Pyodide in a worker. The first check downloads Python and pandas from the pinned Pyodide CDN and needs internet access. The page stays responsive; loading failures and timeouts allow a retry without recording an incorrect answer. Answers may use supported pandas methods, expressions, and assignments, ending in the desired result. Imports, loops, and private Python attributes are not supported. Result shape and labels must match; numeric values allow small floating-point differences. Row order is checked for ranking or explicitly ordered questions. Unordered aggregations are compared by their labels, so equivalent group counts can appear in a different display order.

Successful answers advance only when you click **Next Question**. When no eligible reviews are due, the app shows a caught-up message and waits for the next review rather than advancing mastery through early repetitions.

## Verify changes

Python checks require pandas and numpy:

```sh
python3 -m unittest discover -s tests
node --test tests/*.test.js
```

After changing questions or datasets, rebuild validated multiple-choice distractors:

```sh
python3 generator/validate_choices.py
```

Each question has exactly one correct choice. Distractors are generated from the canonical expression by changing pandas operations, reversing chained operations, or changing the filter/sort logic. They may raise runtime errors when the selected operation or order is wrong. Missing delimiters, spelling mistakes, and `.size` versus `.size()` trivia are not generated. Any distractor that produces an equivalent result on the full dataset is excluded, using the same ordering policy as code grading. Run the tests afterward to verify the bank.

The practice app and results viewer share a CSV codec. New exports preserve commas, quotes, newlines, booleans, and text identifiers. Existing uppercase boolean exports are accepted. Empty files and contradictory records (a skipped attempt marked correct) show an import error with the upload controls still available. All accuracy summaries and charts exclude skips. Already-corrupted legacy CSV files cannot always be recovered automatically.
