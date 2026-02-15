from langsmith.evaluation import evaluate
from langsmith.schemas import Run, Example
from src.agent import generate_reply_json, traige_email
from evaluators.groq_judge import groq_judge
import json

def triage_target(inputs: dict) -> dict:
    """Wraps the triage agent to accept a dict and return a dict."""
    result = traige_email(inputs["email"])
    return {"category": result}

def draft_target(inputs: dict) -> dict:
    """Wraps the draft agent."""
    reply = generate_reply_json(
        sender=inputs["sender"],
        subject=inputs["subject"],
        body=inputs["body"],
        calendar_context=inputs["calendar_context"],
        preferences={}
    )
    return {"draft": str(reply)}

def triage_evaluator(run: Run, example: Example) -> dict:
    """
    Custom evaluator using your specific Groq Judge prompt for Triage.
    """
    model_output = run.outputs["category"]
    expected = example.outputs["expected"]
    email_text = example.inputs["email"]

    judge_prompt = f"""
    Email:
    {email_text}

    Expected Category: {expected}
    Model Output: {model_output}

    Decide STRICTLY if the model output matches the expected category.
    
    Return JSON ONLY:
    {{
        "score": 0 or 1,
        "reason": "short explanation"
    }}
    """
    
    try:
        verdict = groq_judge(judge_prompt)
        return {
            "key": "triage_accuracy",
            "score": verdict.get("score", 0),
            "comment": verdict.get("reason", "No reason provided")
        }
    except Exception as e:
        return {"key": "triage_accuracy", "score": 0, "comment": str(e)}

def draft_evaluator(run: Run, example: Example) -> dict:
    draft_reply = run.outputs["draft"]
    expected = example.outputs
    inputs = example.inputs

    judge_prompt = f"""
    You are an expert email quality evaluator.

    TARGET EMAIL TO EVALUATE:
    Subject: {inputs.get('subject', 'N/A')}
    Body: {inputs.get('body', 'N/A')}

    DRAFT REPLY GENERATED:
    {draft_reply}

    EXPECTED INTENT:
    {expected.get('intent', 'Professional response')}

    REQUIRED ELEMENTS:
    {expected.get('must_include', [])}

    Task:
    Score from 1-5 for each category:
    1. Intent Satisfaction
    2. Professional Tone
    3. Completeness
    4. Clarity

    Return JSON ONLY:
    {{
        "intent_score": <1-5>,
        "tone_score": <1-5>,
        "completeness_score": <1-5>,
        "clarity_score": <1-5>,
        "overall_score": <average of above>,
        "reason": "<brief explanation>"
    }}
    """

    try:
        # 2. Call the Judge
        verdict = groq_judge(judge_prompt)
        
        # 3. Format the detailed scores into the TEXT comment
        # This allows you to see the breakdown in LangSmith without breaking the validator
        detailed_comment = f"""{verdict.get('reason', 'No reason provided.')}

        --- Score Breakdown ---
        🎯 Intent: {verdict.get('intent_score')}/5
        👔 Tone: {verdict.get('tone_score')}/5
        ✅ Completeness: {verdict.get('completeness_score')}/5
        🔍 Clarity: {verdict.get('clarity_score')}/5
        """

        # 4. Return STRICTLY supported keys
        return {
            "key": "draft_quality",
            # Normalize to 0-1 if you prefer (score / 5), or keep as 1-5
            "score": verdict.get("overall_score", 0), 
            "comment": detailed_comment
        }

    except Exception as e:
        return {
            "key": "draft_quality",
            "score": 0,
            "comment": f"Evaluator Error: {str(e)}"
        }


def run_all_evals():
    # print("🚀 Starting Triage Evaluation...")
    # evaluate(
    #     triage_target,
    #     data="Email Triage Dataset",
    #     evaluators=[triage_evaluator],
    #     experiment_prefix="triage-groq-test",
    #     metadata={"version": "1.0", "model": "llama-3-70b"}
    # )

    print("\n🚀 Starting Draft Evaluation...")
    evaluate(
        draft_target,
        data="Email Draft Dataset",
        evaluators=[draft_evaluator],
        experiment_prefix="draft-groq-test",
        metadata={"version": "1.0", "model": "llama-3-70b"}
    )

if __name__ == "__main__":
    run_all_evals()