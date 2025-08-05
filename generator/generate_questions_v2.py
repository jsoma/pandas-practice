import pandas as pd
import json
import os
import random
from datetime import datetime

def analyze_column(df, col):
    """Analyze a column to determine what questions make sense"""
    analysis = {
        'name': col,
        'dtype': str(df[col].dtype),
        'unique_count': df[col].nunique(),
        'null_count': df[col].isnull().sum(),
        'sample_values': df[col].dropna().head(10).tolist()
    }
    
    # Determine column characteristics
    total_rows = len(df)
    unique_ratio = analysis['unique_count'] / total_rows
    
    # Categorize the column
    if pd.api.types.is_numeric_dtype(df[col]):
        analysis['is_numeric'] = True
        analysis['can_sum'] = True
        analysis['can_mean'] = True
        analysis['can_sort'] = True
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
        analysis['can_filter'] = True
        
    return analysis

def create_column_description(col_name, sample_values):
    """Create a human-friendly column description"""
    # Common patterns
    if 'name' in col_name.lower():
        return "Name identifier"
    elif 'date' in col_name.lower() or 'year' in col_name.lower():
        return "Date/time information"
    elif 'price' in col_name.lower() or 'cost' in col_name.lower():
        return "Price in dollars"
    elif 'count' in col_name.lower() or 'number' in col_name.lower():
        return "Count or quantity"
    elif 'id' in col_name.lower():
        return "Unique identifier"
    elif 'status' in col_name.lower():
        return "Current status"
    elif 'type' in col_name.lower() or 'category' in col_name.lower():
        return "Category or type"
    else:
        return "Data field"

def generate_question_templates():
    """Return question templates that follow CLAUDE.md guidelines"""
    return [
        # Simple filtering questions
        {
            'id': 'filter_show_all',
            'requires': ['can_filter'],
            'template': 'Show all {entity}s where {column} is "{value}"',
            'code_template': "df[df['{column}'] == '{value}']",
            'difficulty': 1,
            'needs_value': True,
            'concepts': ['filtering']
        },
        {
            'id': 'filter_show_all_simple',
            'requires': ['can_filter'],
            'template': 'Show all {value} {entity}s',
            'code_template': "df[df['{column}'] == '{value}']",
            'difficulty': 1,
            'needs_value': True,
            'concepts': ['filtering'],
            'use_value_in_question': True
        },
        {
            'id': 'filter_count',
            'requires': ['can_filter'],
            'template': 'How many {entity}s have {column} equal to "{value}"?',
            'code_template': "(df['{column}'] == '{value}').sum()",
            'difficulty': 1,
            'needs_value': True,
            'concepts': ['boolean indexing', 'sum']
        },
        {
            'id': 'filter_numeric_greater',
            'requires': ['is_numeric'],
            'template': 'How many {entity}s have {column} greater than {value}?',
            'code_template': "(df['{column}'] > {value}).sum()",
            'difficulty': 1,
            'needs_numeric_value': True,
            'concepts': ['boolean indexing', 'sum']
        },
        # Sort and head questions
        {
            'id': 'sort_highest',
            'requires': ['can_sort'],
            'template': 'Which {entity} has the highest {column}?',
            'code_template': "df.sort_values('{column}', ascending=False).head(1)",
            'difficulty': 1,
            'concepts': ['sort_values', 'head']
        },
        {
            'id': 'sort_lowest',
            'requires': ['can_sort'],
            'template': 'What is the {entity} with the lowest {column}?',
            'code_template': "df.sort_values('{column}').head(1)",
            'difficulty': 1,
            'concepts': ['sort_values', 'head']
        },
        {
            'id': 'sort_top_5',
            'requires': ['can_sort'],
            'template': 'Show the 5 {entity}s with the highest {column}',
            'code_template': "df.sort_values('{column}', ascending=False).head(5)",
            'difficulty': 1,
            'concepts': ['sort_values', 'head']
        },
        # Value counts questions
        {
            'id': 'value_counts_percentage',
            'requires': ['can_value_count'],
            'template': 'What percentage of {entity}s are in each {column} category?',
            'code_template': "df['{column}'].value_counts(normalize=True)",
            'difficulty': 1,
            'concepts': ['value_counts', 'normalize']
        },
        {
            'id': 'value_counts_basic',
            'requires': ['can_value_count'],
            'template': 'How many {entity}s are there for each {column}?',
            'code_template': "df['{column}'].value_counts()",
            'difficulty': 1,
            'concepts': ['value_counts']
        },
        {
            'id': 'value_counts_most_common',
            'requires': ['can_value_count'],
            'template': 'What is the most common {column}?',
            'code_template': "df['{column}'].value_counts().head(1)",
            'difficulty': 1,
            'concepts': ['value_counts', 'head']
        },
        # Basic aggregations
        {
            'id': 'mean_simple',
            'requires': ['can_mean'],
            'template': 'What is the average {column}?',
            'code_template': "df['{column}'].mean()",
            'difficulty': 1,
            'concepts': ['mean']
        },
        {
            'id': 'sum_simple',
            'requires': ['can_sum'],
            'template': 'What is the total {column} across all {entity}s?',
            'code_template': "df['{column}'].sum()",
            'difficulty': 1,
            'concepts': ['sum']
        },
        # Count questions with conditions
        {
            'id': 'count_multiple_values',
            'requires': ['can_filter'],
            'template': 'How many {entity}s are either {value1} or {value2}?',
            'code_template': "df['{column}'].isin(['{value1}', '{value2}']).sum()",
            'difficulty': 2,
            'needs_two_values': True,
            'concepts': ['isin', 'sum']
        },
        # Groupby questions (simpler)
        {
            'id': 'groupby_count',
            'requires': ['can_group_by'],
            'template': 'How many {entity}s does each {column} have?',
            'code_template': "df.groupby('{column}').size()",
            'difficulty': 2,
            'concepts': ['groupby', 'size']
        },
        {
            'id': 'groupby_mean',
            'requires': ['can_group_by'],
            'requires_other': ['can_mean'],
            'template': 'What is the average {other_column} by {column}?',
            'code_template': "df.groupby('{column}')['{other_column}'].mean()",
            'difficulty': 2,
            'concepts': ['groupby', 'mean']
        },
        {
            'id': 'groupby_sum_sorted',
            'requires': ['can_group_by'],
            'requires_other': ['can_sum'],
            'template': 'What is the total {other_column} by {column}?',
            'code_template': "df.groupby('{column}')['{other_column}'].sum().sort_values(ascending=False)",
            'difficulty': 2,
            'concepts': ['groupby', 'sum', 'sort_values']
        }
    ]

def generate_questions_for_dataset(csv_path, dataset_name):
    """Generate questions following CLAUDE.md guidelines"""
    df = pd.read_csv(csv_path)
    
    # Sample the dataframe for preview
    preview_df = df.head(5)
    
    # Analyze all columns
    column_analysis = {}
    for col in df.columns:
        column_analysis[col] = analyze_column(df, col)
    
    # Determine entity type
    entity_type_map = {
        'powerplants.csv': 'power plant',
        'motorcycles.csv': 'motorcycle',
        'foods.csv': 'pet food product',
        'grammys.csv': 'Grammy nomination',
        'race-places.csv': 'race result',
        'tickets-tiny.csv': 'traffic stop',
        'crops.csv': 'crop',
        'wreckers.csv': 'tow truck',
        'overflows.csv': 'overflow event',
        'forces.csv': 'force measurement',
        'injurydat-cleaned.csv': 'injury report',
        'township-154.csv': 'township record',
        'boston_house_prices.csv': 'house',
        'msft.csv': 'stock trading day'
    }
    
    entity_type = entity_type_map.get(dataset_name, 'record')
    
    questions = []
    templates = generate_question_templates()
    question_id = 1
    
    # Generate questions for each column
    for col, analysis in column_analysis.items():
        # Skip ID columns and high-cardinality columns
        if analysis.get('is_identifier', False):
            continue
            
        for template in templates:
            # Check if column meets requirements
            if 'requires' in template:
                if not all(analysis.get(req, False) for req in template['requires']):
                    continue
            
            # Single column questions
            if 'requires_other' not in template:
                # Handle different value requirements
                if template.get('needs_value'):
                    # Get appropriate sample values
                    if analysis['sample_values']:
                        # Pick a value that appears multiple times
                        value_counts = df[col].value_counts()
                        common_values = value_counts[value_counts > 1].index.tolist()[:5]
                        if common_values:
                            value = random.choice(common_values)
                        else:
                            continue
                            
                        if template.get('use_value_in_question'):
                            # Special case: use value directly in question
                            question_text = template['template'].format(
                                entity=entity_type,
                                value=value
                            )
                        else:
                            question_text = template['template'].format(
                                entity=entity_type,
                                column=col,
                                value=value
                            )
                        
                        if analysis['is_numeric']:
                            code = template['code_template'].format(column=col, value=value)
                        else:
                            code = template['code_template'].format(column=col, value=value)
                    else:
                        continue
                        
                elif template.get('needs_numeric_value'):
                    if analysis['is_numeric'] and analysis['sample_values']:
                        # Use median as threshold
                        median_val = df[col].median()
                        question_text = template['template'].format(
                            entity=entity_type,
                            column=col,
                            value=round(median_val, 2)
                        )
                        code = template['code_template'].format(
                            column=col,
                            value=round(median_val, 2)
                        )
                    else:
                        continue
                        
                elif template.get('needs_two_values'):
                    if analysis['sample_values'] and len(analysis['sample_values']) >= 2:
                        value_counts = df[col].value_counts()
                        common_values = value_counts[value_counts > 1].index.tolist()[:10]
                        if len(common_values) >= 2:
                            value1, value2 = random.sample(common_values, 2)
                            question_text = template['template'].format(
                                entity=entity_type,
                                column=col,
                                value1=value1,
                                value2=value2
                            )
                            code = template['code_template'].format(
                                column=col,
                                value1=value1,
                                value2=value2
                            )
                        else:
                            continue
                    else:
                        continue
                else:
                    # Standard template
                    question_text = template['template'].format(
                        entity=entity_type,
                        column=col
                    )
                    code = template['code_template'].format(column=col)
                
                # Create data preview
                preview_cols = [col]
                if len(df.columns) > 1:
                    # Add 1-2 more relevant columns
                    other_cols = [c for c in df.columns if c != col and not column_analysis[c].get('is_identifier', False)]
                    preview_cols.extend(other_cols[:min(2, len(other_cols))])
                
                preview_data = [preview_cols] + preview_df[preview_cols].values.tolist()
                
                # Create column descriptions
                col_descriptions = {}
                for pc in preview_cols:
                    col_descriptions[pc] = create_column_description(pc, column_analysis[pc]['sample_values'])
                
                # Create the question
                q = {
                    'id': f"{dataset_name.replace('.csv', '')}_{template['id']}_{question_id:03d}",
                    'dataset': dataset_name,
                    'dataPreview': preview_data,
                    'columnDescriptions': col_descriptions,
                    'context': f"Working with {entity_type} data.",
                    'question': question_text,
                    'canonicalAnswer': {
                        'code': code,
                        'result': 'Computed result'
                    },
                    'difficulty': template['difficulty'],
                    'concepts': template['concepts'],
                    'hint': f"Use {template['concepts'][0]} to solve this"
                }
                
                questions.append(q)
                question_id += 1
                
            # Two column questions (groupby)
            else:
                # Find suitable other columns
                for other_col, other_analysis in column_analysis.items():
                    if other_col == col or other_analysis.get('is_identifier', False):
                        continue
                    
                    # Check if other column meets requirements
                    meets_requirements = False
                    for req in template['requires_other']:
                        if req == 'any' or other_analysis.get(req, False):
                            meets_requirements = True
                            break
                    
                    if not meets_requirements:
                        continue
                    
                    question_text = template['template'].format(
                        entity=entity_type,
                        column=col,
                        other_column=other_col
                    )
                    code = template['code_template'].format(
                        column=col,
                        other_column=other_col
                    )
                    
                    # Create data preview with both columns
                    preview_cols = [col, other_col]
                    if len(df.columns) > 2:
                        # Add one more column if available
                        extra_cols = [c for c in df.columns if c not in preview_cols and not column_analysis[c].get('is_identifier', False)]
                        if extra_cols:
                            preview_cols.append(extra_cols[0])
                    
                    preview_data = [preview_cols] + preview_df[preview_cols].values.tolist()
                    
                    # Create column descriptions
                    col_descriptions = {}
                    for pc in preview_cols:
                        col_descriptions[pc] = create_column_description(pc, column_analysis[pc]['sample_values'])
                    
                    q = {
                        'id': f"{dataset_name.replace('.csv', '')}_{template['id']}_{question_id:03d}",
                        'dataset': dataset_name,
                        'dataPreview': preview_data,
                        'columnDescriptions': col_descriptions,
                        'context': f"Analyzing {entity_type} data by categories.",
                        'question': question_text,
                        'canonicalAnswer': {
                            'code': code,
                            'result': 'Computed result'
                        },
                        'difficulty': template['difficulty'],
                        'concepts': template['concepts'],
                        'hint': f"Use {' and '.join(template['concepts'])} to solve this"
                    }
                    
                    questions.append(q)
                    question_id += 1
                    
                    # Limit groupby questions per column pair
                    if question_id % 5 == 0:
                        break
    
    return questions

def add_explanations(questions):
    """Add explanations to questions based on their type"""
    explanation_templates = {
        'filtering': "Boolean filtering selects rows where a condition is True. Use df[condition] syntax.",
        'sort_values': "sort_values() orders the dataframe by a column. Use ascending=False for highest first.",
        'head': "head(n) returns the first n rows. Combine with sort_values() to find top/bottom values.",
        'value_counts': "value_counts() counts occurrences of each unique value. Add normalize=True for percentages.",
        'mean': "mean() calculates the average of numeric values. Use on a column to get its average.",
        'sum': "sum() adds up values. On boolean conditions, it counts True values (True=1, False=0).",
        'groupby': "groupby() splits data into groups. Follow with an aggregation like sum() or mean().",
        'isin': "isin() checks if values are in a list. Returns True/False for each row.",
        'boolean indexing': "Create True/False conditions to filter data. Use & for AND, | for OR."
    }
    
    for q in questions:
        # Build explanation based on concepts
        explanations = []
        for concept in q['concepts']:
            if concept in explanation_templates:
                explanations.append(explanation_templates[concept])
        
        q['explanation'] = ' '.join(explanations[:2])  # Use first 2 explanations
        
    return questions

def main():
    """Generate questions for multiple datasets"""
    # Change to parent directory to access datasets
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    datasets_dir = '../datasets'
    
    all_questions = []
    
    # Process these datasets
    datasets = [
        'powerplants.csv',
        'motorcycles.csv', 
        'foods.csv',
        'grammys.csv',
        'race-places.csv',
        'tickets-tiny.csv',
        'crops.csv',
        'wreckers.csv',
        'overflows.csv',
        'forces.csv'
    ]
    
    for dataset in datasets:
        csv_path = os.path.join(datasets_dir, dataset)
        if os.path.exists(csv_path):
            print(f"\nProcessing {dataset}...")
            try:
                questions = generate_questions_for_dataset(csv_path, dataset)
                questions = add_explanations(questions)
                all_questions.extend(questions)
                print(f"Generated {len(questions)} questions")
            except Exception as e:
                print(f"Error processing {dataset}: {str(e)}")
    
    # Shuffle questions to mix datasets
    random.shuffle(all_questions)
    
    # Format for questions.json
    output = {
        'questions': all_questions
    }
    
    # Save the generated questions
    with open('../generated_questions_pool.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n\nTotal questions generated: {len(all_questions)}")
    print("Saved to generated_questions_pool.json")
    print("\nNext steps:")
    print("1. Review generated_questions_pool.json")
    print("2. Remove any problematic questions")
    print("3. Select best ~100 questions for final questions.json")

if __name__ == '__main__':
    main()