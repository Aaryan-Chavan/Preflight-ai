import ollama, xgboost, sklearn
from tree_sitter_language_pack import get_parser

print("xgboost", xgboost.__version__, "| sklearn", sklearn.__version__)

parser = get_parser("python")
tree = parser.parse(b"def f():\n    return 1\n")
print("tree-sitter ok, root node:", tree.root_node.type)

reply = ollama.chat(
    model="preflight-primary",
    messages=[{"role": "user", "content": 'Return JSON: {"ok": true}'}],
    format="json",
)
print("ollama replied:", reply["message"]["content"])# Triggering AI code analysis
