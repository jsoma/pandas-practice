import pandas as pd
import json
import os
from datetime import datetime

def analyze_column(df, col):
    """Analyze a column to determine what questions make sense"""
    analysis = {
        'name': col,
        'dtype': str(df[col].dtype),
        'unique_count': df[col].nunique(),
        'null_count': df[col].isnull().sum(),
        'sample_values': df[col].dropna().head(5).tolist()
    }
    
    # Determine column characteristics
    total_rows = len(df)
    unique_ratio = analysis['unique_count'] / total_rows
    
    # Categorize the column
    if pd.api.types.is_numeric_dtype(df[col]):
        analysis['is_numeric'] = True
        analysis['can_sum'] = True
        analysis['can_mean'] = True
        analysis['can_rank'] = True
        # Check if it's likely an ID (high cardinality, sequential)
        if unique_ratio > 0.9 or 'id' in col.lower() or 'number' in col.lower():
            analysis['is_identifier'] = True
            analysis['can_sum'] = False
            analysis['can_mean'] = False
    else:
        analysis['is_numeric'] = False
        analysis['is_categorical'] = True
        analysis['can_group_by'] = unique_ratio < 0.5  # Good for groupby if not too unique
        analysis['can_value_count'] = True
        
    return analysis

def generate_question_templates():
    """Return all possible question templates"""
    return [
        # Value counts questions
        {
            'id': 'value_counts_basic',
            'requires': ['can_value_count'],
            'template': 'How many {entity}s are there for each {column}?',
            'code_template': "df['{column}'].value_counts()",
            'difficulty': 1
        },
        {
            'id': 'value_counts_top',
            'requires': ['can_value_count'],
            'template': 'What are the top 5 most common {column}s?',
            'code_template': "df['{column}'].value_counts().head(5)",
            'difficulty': 1
        },
        {
            'id': 'unique_count',
            'requires': ['is_categorical'],
            'template': 'How many unique {column}s are there?',
            'code_template': "df['{column}'].nunique()",
            'difficulty': 1
        },
        # Numeric aggregations
        {
            'id': 'mean_simple',
            'requires': ['can_mean'],
            'template': 'What is the average {column}?',
            'code_template': "df['{column}'].mean()",
            'difficulty': 1
        },
        {
            'id': 'sum_simple',
            'requires': ['can_sum'],
            'template': 'What is the total {column} across all {entity}s?',
            'code_template': "df['{column}'].sum()",
            'difficulty': 1
        },
        {
            'id': 'max_value',
            'requires': ['can_rank'],
            'template': 'What is the maximum {column}?',
            'code_template': "df['{column}'].max()",
            'difficulty': 1
        },
        {
            'id': 'nlargest',
            'requires': ['can_rank'],
            'template': 'Find the top 5 {entity}s by {column}',
            'code_template': "df.nlargest(5, '{column}')",
            'difficulty': 1
        },
        # Groupby questions (need two columns)
        {
            'id': 'groupby_count',
            'requires': ['can_group_by'],
            'requires_other': ['any'],
            'template': 'How many {entity}s does each {column} have?',
            'code_template': "df.groupby('{column}').size()",
            'difficulty': 2
        },
        {
            'id': 'groupby_mean',
            'requires': ['can_group_by'],
            'requires_other': ['can_mean'],
            'template': 'What is the average {other_column} for each {column}?',
            'code_template': "df.groupby('{column}')['{other_column}'].mean()",
            'difficulty': 2
        },
        {
            'id': 'groupby_sum',
            'requires': ['can_group_by'],
            'requires_other': ['can_sum'],
            'template': 'What is the total {other_column} for each {column}?',
            'code_template': "df.groupby('{column}')['{other_column}'].sum()",
            'difficulty': 2
        },
        {
            'id': 'groupby_max_category',
            'requires': ['can_group_by'],
            'requires_other': ['can_sum'],
            'template': 'Which {column} has the highest total {other_column}?',
            'code_template': "df.groupby('{column}')['{other_column}'].sum().idxmax()",
            'difficulty': 2
        },
        # Filtering questions
        {
            'id': 'filter_equals',
            'requires': ['is_categorical'],
            'template': 'How many {entity}s have {column} equal to "{value}"?',
            'code_template': "len(df[df['{column}'] == '{value}'])",
            'difficulty': 1,
            'needs_value': True
        },
        {
            'id': 'filter_greater',
            'requires': ['is_numeric'],
            'template': 'How many {entity}s have {column} greater than {value}?',
            'code_template': "len(df[df['{column}'] > {value}])",
            'difficulty': 1,
            'needs_value': True
        },
        # String operations
        {
            'id': 'string_contains',
            'requires': ['is_categorical'],
            'template': 'Find all {entity}s where {column} contains "{substring}"',
            'code_template': "df[df['{column}'].str.contains('{substring}', na=False)]",
            'difficulty': 2,
            'needs_substring': True
        }
    ]

def generate_questions_for_dataset(csv_path, dataset_name):
    """Generate all possible questions for a dataset"""
    df = pd.read_csv(csv_path)
    
    # Analyze all columns
    column_analysis = {}
    for col in df.columns:
        column_analysis[col] = analyze_column(df, col)
    
    # Determine what each row represents (entity type)
    entity_type = dataset_name.replace('.csv', '').rstrip('s')  # Simple singularization
    if dataset_name == 'powerplants.csv':
        entity_type = 'power plant'
    elif dataset_name == 'motorcycles.csv':
        entity_type = 'motorcycle'
    elif dataset_name == 'foods.csv':
        entity_type = 'pet food product'
    elif dataset_name == 'grammys.csv':
        entity_type = 'Grammy nomination'
    elif dataset_name == 'race-places.csv':
        entity_type = 'race result'
    elif dataset_name == 'tickets-tiny.csv':
        entity_type = 'traffic stop'
    
    questions = []
    templates = generate_question_templates()
    
    # Generate questions for each column
    for col, analysis in column_analysis.items():
        for template in templates:
            # Check if column meets requirements
            if 'requires' in template:
                if not all(analysis.get(req, False) for req in template['requires']):
                    continue
            
            # Single column questions
            if 'requires_other' not in template:
                q = {
                    'dataset': dataset_name,
                    'template_id': template['id'],
                    'column': col,
                    'difficulty': template['difficulty']
                }
                
                # Handle different template types
                if template.get('needs_value'):
                    if analysis['sample_values']:
                        value = analysis['sample_values'][0]
                        q['question'] = template['template'].format(
                            entity=entity_type,
                            column=col,
                            value=value
                        )
                        q['code'] = template['code_template'].format(
                            column=col,
                            value=value if analysis['is_numeric'] else f"'{value}'"
                        )
                    else:
                        continue  # Skip if no sample values
                
                elif template.get('needs_substring'):
                    if analysis['sample_values'] and isinstance(analysis['sample_values'][0], str):
                        # Take first 3 characters of a sample value
                        substring = str(analysis['sample_values'][0])[:3]
                        q['question'] = template['template'].format(
                            entity=entity_type,
                            column=col,
                            substring=substring
                        )
                        q['code'] = template['code_template'].format(
                            column=col,
                            substring=substring
                        )
                    else:
                        continue  # Skip if no string values
                else:
                    # Standard template without special requirements
                    q['question'] = template['template'].format(
                        entity=entity_type,
                        column=col
                    )
                    q['code'] = template['code_template'].format(column=col)
                
                # Execute the code to get the answer
                try:
                    result = eval(q['code'])
                    q['result'] = str(result)[:200]  # Truncate long results
                    q['status'] = 'valid'
                except Exception as e:
                    q['result'] = f"Error: {str(e)}"
                    q['status'] = 'error'
                
                questions.append(q)
            
            # Two column questions (groupby)
            else:
                # Find other suitable columns
                for other_col, other_analysis in column_analysis.items():
                    if other_col == col:
                        continue
                    
                    # Check if other column meets requirements
                    if not any(other_analysis.get(req, False) for req in template['requires_other']):
                        continue
                    
                    q = {
                        'dataset': dataset_name,
                        'template_id': template['id'],
                        'column': col,
                        'other_column': other_col,
                        'question': template['template'].format(
                            entity=entity_type,
                            column=col,
                            other_column=other_col
                        ),
                        'code': template['code_template'].format(
                            column=col,
                            other_column=other_col
                        ),
                        'difficulty': template['difficulty']
                    }
                    
                    # Execute the code
                    try:
                        result = eval(q['code'])
                        q['result'] = str(result)[:200]
                        q['status'] = 'valid'
                    except Exception as e:
                        q['result'] = f"Error: {str(e)}"
                        q['status'] = 'error'
                    
                    questions.append(q)
    
    return questions

def main():
    """Generate questions for all datasets"""
    datasets_dir = '../datasets'
    all_questions = []
    
    # Process each dataset
    datasets = [
        'powerplants.csv',
        'motorcycles.csv', 
        'foods.csv',
        'grammys.csv',
        'race-places.csv',
        'tickets-tiny.csv'
    ]
    
    for dataset in datasets:
        csv_path = os.path.join(datasets_dir, dataset)
        if os.path.exists(csv_path):
            print(f"\nProcessing {dataset}...")
            questions = generate_questions_for_dataset(csv_path, dataset)
            all_questions.extend(questions)
            print(f"Generated {len(questions)} questions")
            
            # Show some examples
            valid_questions = [q for q in questions if q['status'] == 'valid']
            print(f"Valid questions: {len(valid_questions)}")
            if valid_questions:
                print("\nExample questions:")
                for q in valid_questions[:3]:
                    print(f"- {q['question']}")
                    print(f"  Code: {q['code']}")
                    print(f"  Result: {q['result'][:50]}...")
    
    # Save all questions
    output = {
        'generated_at': datetime.now().isoformat(),
        'total_questions': len(all_questions),
        'valid_questions': len([q for q in all_questions if q['status'] == 'valid']),
        'questions': all_questions
    }
    
    with open('question_bank_raw.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n\nTotal questions generated: {len(all_questions)}")
    print(f"Valid questions: {output['valid_questions']}")
    print("Saved to question_bank_raw.json")

if __name__ == '__main__':
    main()