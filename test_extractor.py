from src.preflight.risk.ml_model import MLRiskAnalyzer

try:
    analyzer = MLRiskAnalyzer()
    print("Scoring your last commit...\n")
    
    result = analyzer.analyze("HEAD~1", "HEAD")
    
    print(f"Risk Level: {result['risk_level']}")
    print(f"Bug Probability: {result['confidence_percent']}%")
    print(f"\nTriggering metrics (for the LLM):")
    print(f"- Lines Added: {result['raw_features']['la']}")
    print(f"- Files Changed: {result['raw_features']['nf']}")
    
except Exception as e:
    print(f"Inference failed: {e}")