# Source this profile after exporting PEKO_BIN and PEKO_API_KEY.
# Token Plan endpoint supplied by the owner; no credential is stored here.
export PEKO_API_FORMAT="anthropic_messages"
export PEKO_BASE_URL="https://token-plan-cn.xiaomimimo.com/anthropic"
export PEKO_MODEL_NAME="mimo-v2.6-flash"
export PEKO_MODEL_ID="mimo-v2.6-flash"
export PEKO_CONTEXT_WINDOW="1048576"
export PEKO_MAX_OUTPUT_TOKENS="8192"
export PEKO_MODEL_SPEC='{"tool_support":"function_calling","streaming":true,"thinking":"optional","pricing":{"input_per_million":0.14,"output_per_million":0.28}}'
export PEKO_COST_BASIS="payg_reference_not_subscription_charge"
export PEKO_CACHE_READ_USD_PER_MILLION="0.0028"
# Public reference pricing (2026-10-05):
# https://mimo.mi.com/models/en-US/mimo-v2.6-flash
# Cache-hit pricing is not expressible in Peko's two-rate PricingHint.
# Actual Token Plan deductions must be checked in the owner's dashboard.
