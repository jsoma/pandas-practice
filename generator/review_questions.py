import pandas as pd
import json
import os

def load_questions():
    """Load the raw question bank"""
    with open('question_bank_raw.json', 'r') as f:
        return json.load(f)

def evaluate_question(question, df):
    """
    Evaluate if a question makes semantic sense and if the code produces meaningful results
    """
    evaluation = {
        'makes_sense': True,
        'reasons': [],
        'actual_result': None,
        'is_meaningful': True
    }
    
    # Check for common issues
    q_text = question['question'].lower()
    code = question['code']
    
    # Issue 1: Asking for average/sum of IDs or codes
    if any(word in question.get('column', '').lower() for word in ['id', 'code', 'number', 'zip']):
        if any(op in code for op in ['.mean()', '.sum()']):
            evaluation['makes_sense'] = False
            evaluation['reasons'].append('Calculating mean/sum of IDs or codes is not meaningful')
    
    # Issue 2: Grouping by high-cardinality columns
    if 'groupby' in code:
        groupby_col = question.get('column', '')
        if groupby_col in df.columns:
            unique_ratio = df[groupby_col].nunique() / len(df)
            if unique_ratio > 0.5:
                evaluation['makes_sense'] = False
                evaluation['reasons'].append(f'Grouping by {groupby_col} has too many unique values ({df[groupby_col].nunique()})')
    
    # Issue 3: Empty or trivial results
    try:
        result = eval(code)
        evaluation['actual_result'] = result
        
        # Check if result is empty
        if isinstance(result, pd.DataFrame) and len(result) == 0:
            evaluation['is_meaningful'] = False
            evaluation['reasons'].append('Query returns empty result')
        
        # Check if result is too large (for value_counts)
        if isinstance(result, pd.Series) and len(result) > 100:
            evaluation['is_meaningful'] = False
            evaluation['reasons'].append('Result has too many categories to be useful')
            
    except Exception as e:
        evaluation['makes_sense'] = False
        evaluation['reasons'].append(f'Code execution error: {str(e)}')
    
    # Issue 4: Semantically odd questions
    odd_patterns = [
        ('average.*name', 'Cannot average names'),
        ('sum.*category', 'Cannot sum categories'),
        ('total.*id', 'Summing IDs is not meaningful'),
    ]
    
    for pattern, reason in odd_patterns:
        if pattern.replace('.*', ' ') in q_text:
            evaluation['makes_sense'] = False
            evaluation['reasons'].append(reason)
    
    return evaluation

def create_final_question(raw_question, dataset_info):
    """
    Convert a raw question into the final format with context and preview
    """
    df = dataset_info['df']
    
    # Get relevant columns for preview
    cols_in_question = [raw_question.get('column')]
    if 'other_column' in raw_question:
        cols_in_question.append(raw_question['other_column'])
    
    # Add some context columns
    preview_cols = list(dict.fromkeys(cols_in_question + list(df.columns)[:3]))[:5]
    preview_data = df[preview_cols].head(5).values.tolist()
    
    # Create context based on dataset
    contexts = {
        'powerplants.csv': 'This dataset contains information about US power plants including their location, energy source, and production capacity.',
        'motorcycles.csv': 'This dataset contains technical specifications for motorcycles from various manufacturers.',
        'foods.csv': 'This dataset contains nutritional information for pet food products.',
        'grammys.csv': 'This dataset contains Grammy award nominations and winners from 1990-2023.',
        'race-places.csv': 'This dataset contains race results for various drivers over multiple years.',
        'tickets-tiny.csv': 'This dataset contains traffic violation records with demographic information.'
    }
    
    final_question = {
        'dataset': raw_question['dataset'],
        'dataPreview': preview_data,
        'dataColumns': preview_cols,
        'context': contexts.get(raw_question['dataset'], 'Dataset of ' + raw_question['dataset']),
        'question': raw_question['question'],
        'canonicalAnswer': {
            'code': raw_question['code'],
            'result': raw_question['result']
        },
        'difficulty': raw_question['difficulty'],
        'concepts': determine_concepts(raw_question['code']),
        'hint': generate_hint(raw_question)
    }
    
    return final_question

def determine_concepts(code):
    """Determine which pandas concepts are used in the code"""
    concepts = []
    
    concept_patterns = [
        ('value_counts()', 'value_counts'),
        ('groupby(', 'groupby'),
        ('.mean()', 'mean'),
        ('.sum()', 'sum'),
        ('.max()', 'max'),
        ('.min()', 'min'),
        ('nlargest(', 'nlargest'),
        ('nsmallest(', 'nsmallest'),
        ('.nunique()', 'nunique'),
        ('.idxmax()', 'idxmax'),
        ('len(df[', 'filtering'),
        ('df[df[', 'boolean_indexing'),
        ('.str.contains(', 'string_contains'),
        ('.sort_values(', 'sorting')
    ]
    
    for pattern, concept in concept_patterns:
        if pattern in code:
            concepts.append(concept)
    
    return concepts

def generate_hint(question):
    """Generate a helpful hint based on the question type"""
    hints = {
        'value_counts_basic': 'Count how many times each value appears',
        'groupby_mean': 'Group the data first, then calculate the average',
        'filter_equals': 'Filter the dataframe to only include matching rows',
        'nlargest': 'Find the rows with the highest values',
        'string_contains': 'Use string methods to search for partial matches'
    }
    
    return hints.get(question.get('template_id', ''), 'Think about what operation would answer this question')

def main():
    """Review and filter questions"""
    # Load raw questions
    data = load_questions()
    raw_questions = data['questions']
    
    print(f"Loaded {len(raw_questions)} raw questions")
    
    # Load datasets for evaluation
    datasets = {}
    datasets_dir = '../datasets'
    
    for dataset_name in ['powerplants.csv', 'motorcycles.csv', 'foods.csv', 'grammys.csv', 'race-places.csv', 'tickets-tiny.csv']:
        try:
            df = pd.read_csv(os.path.join(datasets_dir, dataset_name))
            # Fix column name issue in powerplants
            if dataset_name == 'powerplants.csv' and 'state' not in df.columns:
                # Try to extract state from other columns or use a default
                df['state'] = 'Unknown'  # This would need proper state mapping
            datasets[dataset_name] = {'df': df, 'name': dataset_name}
        except Exception as e:
            print(f"Error loading {dataset_name}: {e}")
    
    # Evaluate each question
    good_questions = []
    rejected_questions = []
    
    for q in raw_questions:
        if q['status'] != 'valid':
            rejected_questions.append((q, 'Invalid code'))
            continue
            
        dataset = datasets.get(q['dataset'])
        if not dataset:
            rejected_questions.append((q, 'Dataset not found'))
            continue
            
        # Evaluate the question
        evaluation = evaluate_question(q, dataset['df'])
        
        if evaluation['makes_sense'] and evaluation['is_meaningful']:
            # Convert to final format
            final_q = create_final_question(q, dataset)
            good_questions.append(final_q)
        else:
            rejected_questions.append((q, evaluation['reasons']))
    
    print(f"\nGood questions: {len(good_questions)}")
    print(f"Rejected questions: {len(rejected_questions)}")
    
    # Show some examples of rejected questions
    print("\nExamples of rejected questions:")
    for q, reasons in rejected_questions[:5]:
        print(f"- {q['question']}")
        print(f"  Reasons: {reasons}")
    
    # Save the good questions
    output = {
        'questions': good_questions,
        'metadata': {
            'generatedAt': data['generated_at'],
            'totalQuestions': len(good_questions),
            'datasets': {}
        }
    }
    
    # Count questions per dataset
    for q in good_questions:
        dataset = q['dataset']
        output['metadata']['datasets'][dataset] = output['metadata']['datasets'].get(dataset, 0) + 1
    
    with open('questions_filtered.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\nSaved {len(good_questions)} good questions to questions_filtered.json")

if __name__ == '__main__':
    main()