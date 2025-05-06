# Metric Parameters Guide

This guide explains how to use customizable parameters with metrics in the LLM Evaluation Platform.

## Metrics with Parameters

The evaluation platform supports customizing metric behavior through parameters. Parameters allow you to fine-tune how metrics evaluate model outputs.

### Using Metric Parameters

Parameters can be specified in two ways:

1. **Via the Frontend UI**: When creating or editing a metric through the Metrics UI, you can specify parameters as a JSON object.

2. **In Dataset JSON Files**: When defining a dataset, you can specify metrics with parameters in the JSON file.

## Available Metrics and Parameters

Here are some of the built-in metrics with their supported parameters:

### ExactMatch

Evaluates if the model output exactly matches the reference output, with options to control the match criteria.

```json
{
  "name": "exact_match",
  "parameters": {
    "ignore_case": true,        // Ignore case when comparing strings
    "ignore_whitespace": false  // Consider whitespace in comparison
  }
}
```

### ExactMatchFigure

Specially designed for evaluating tables, figures and structured content with additional options.

```json
{
  "name": "exact_match_figure",
  "parameters": {
    "ignore_case": true,               // Ignore case when comparing 
    "ignore_whitespace": true,         // Ignore whitespace differences
    "ignore_table_separators": true,   // Ignore differences in table separators (|, +, etc.)
    "ignore_newlines": false,          // Ignore differences in newline placement
    "normalize_numbers": true          // Normalize number formats (1,000 → 1000, 1.0 → 1)
  }
}
```

### BLEU

The BLEU score metric with customizable n-gram weights.

```json
{
  "name": "bleu",
  "parameters": {
    "weights": [0.25, 0.25, 0.25, 0.25]  // Weights for 1-gram, 2-gram, 3-gram, 4-gram
  }
}
```

### Character F1 (char_f1)

Character-level F1 score with customizable beta parameter.

```json
{
  "name": "char_f1",
  "parameters": {
    "beta": 1.0  // Beta parameter for F1 calculation
  }
}
```

### LLM Judge (llm_judge)

Uses a powerful LLM like GPT-4 to judge the quality of model outputs. Returns a score on a scale from 0 to 1.

```json
{
  "name": "llm_judge",
  "parameters": {
    "judge_model": "gpt-4-turbo",       // The LLM model to use as the judge
    "judge_provider": "openai",         // The provider of the judge model
    "system_prompt": "Custom prompt...", // System prompt for the judge
    "prompt_template": "Custom template...", // Template for evaluation without reference
    "reference_prompt_template": "Custom template...", // Template for evaluation with reference
    "use_reference": false,             // Whether to include reference in evaluation
    "scale_to_range": true,             // Whether to scale score from 0-10 to 0-1
    "max_tokens": 1024,                 // Maximum tokens for LLM response
    "temperature": 0.1,                 // Temperature for LLM response
    "api_key": ""                       // Optional API key (defaults to env variables)
  }
}
```

## Dataset Format with Metric Parameters

When creating a dataset JSON file, you can specify metrics with parameters:

```json
{
  "name": "My Dataset",
  "description": "Example dataset with parameterized metrics",
  "instruction": "Translate the following text from English to Japanese",
  "output_length": 200,
  "metrics": [
    {"name": "bleu", "parameters": {"weights": [0.5, 0.5, 0, 0]}},
    {"name": "exact_match", "parameters": {"ignore_case": true, "ignore_whitespace": true}},
    {"name": "char_f1"}
  ],
  "samples": [
    {
      "input": "Hello, world!",
      "output": "こんにちは、世界！"
    },
    // more samples...
  ]
}
```

The platform supports both formats for backward compatibility:
- Simple format: `"metrics": ["bleu", "exact_match"]`
- Parameterized format: `"metrics": [{"name": "bleu", "parameters": {...}}]`

### Example: LLM Judge in a Dataset

Here's an example of using the LLM Judge metric in a dataset:

```json
{
  "name": "LLM Judge Example",
  "description": "Dataset with LLM judge evaluation",
  "metrics": [
    {
      "name": "llm_judge",
      "parameters": {
        "judge_model": "gpt-4",
        "judge_provider": "openai",
        "system_prompt": "Please act as an impartial judge and evaluate the quality of the response provided by an AI assistant to the user question displayed below. Your evaluation should consider factors such as the helpfulness, relevance, accuracy, depth, creativity, and level of detail of the response. Begin your evaluation by providing a short explanation. Be as objective as possible. After providing your explanation, you must rate the response on a scale of 1 to 10 by strictly following this format: \"[[rating]]\", for example: \"Rating: [[5]]\".",
        "scale_to_range": true
      }
    },
    "exact_match",
    "char_f1"
  ],
  "instruction": "以下の質問に対して適切な回答を作成してください。",
  "samples": [
    {
      "input": "日本の首都はどこですか？",
      "output": "日本の首都は東京です。"
    }
  ]
}
```

## Creating Custom Metrics

You can also create custom metrics with parameters through the Metrics UI in the frontend, or by implementing a new metric class in the backend.

### Custom Metric via UI

1. Navigate to the Metrics page
2. Click "Add Metric"
3. Fill in the form, including any parameters as a JSON object
4. Click "Add" to create the metric

### Example: Custom Metric in Backend

If you want to implement a custom metric in the backend code:

```python
@register_metric
class MyCustomMetric(BaseMetric):
    """
    My custom metric description
    """

    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        super().__init__(name="my_custom_metric", parameters=parameters)
        self.is_higher_better = True

    @classmethod
    def get_parameter_definitions(cls) -> ParamDef:
        return {
            "threshold": {
                "type": "number",
                "description": "Threshold value for scoring",
                "default": 0.5,
                "required": False
            }
        }

    def calculate(self, hypothesis: str, reference: str) -> float:
        threshold = self.parameters.get("threshold", 0.5)
        # Your metric calculation logic here
        return score
```

## Best Practices

1. **Set Default Values**: Always provide sensible defaults for parameters
2. **Document Parameters**: Include clear descriptions of what each parameter does
3. **Validate Parameters**: Handle invalid parameters gracefully
4. **Test with Various Inputs**: Ensure your metric works with different parameter values