import ast

def clean_model_id(model_id):
    if not model_id.startswith("openrouter/"):
        return f"openrouter/{model_id.replace('-lite', '-flash').replace('kimi-k2-6', 'kimi/moonshot-v1-8k').replace('deepseek-r1t2-chimera', 'deepseek/deepseek-coder').replace('qwen3-max', 'qwen/qwen-max').replace('qwen3.6-plus', 'qwen/qwen-plus').replace('glm-4-air', 'glm/glm-4').replace('glm-5.1', 'glm/glm-4').replace('claude-sonnet', 'anthropic/claude-3-sonnet').replace('sonar-pro', 'perplexity/sonar-medium-online').replace('mimo-v2-flash', 'google/gemini-flash-1.5').replace('mimo-v2-pro', 'google/gemini-pro-1.5').replace('gpt-4o-mini', 'openai/gpt-4o-mini').replace('mistral-large-3', 'mistralai/mistral-large-2402').replace('deepseek-v3', 'deepseek/deepseek-coder').replace('gemma-4-26b', 'google/gemma-2-27b-it').replace('gpt-5', 'openai/gpt-4o').replace('grok-4.20', 'xai/grok-1').replace('MODEL_FLUX_2_FLEX', 'openrouter/image-gen').replace('MODEL_GEMINI_PRO_IMAGE', 'openrouter/image-gen')}"
    return model_id

def process_presets(raw_presets_string):
    # Extract the list part from the string
    start_marker = "_PRESET_CONFIGS: list[dict] = ["
    end_marker = "]"
    list_start = raw_presets_string.find(start_marker) + len(start_marker) -1
    list_end = raw_presets_string.rfind(end_marker) + 1
    presets_list_str = raw_presets_string[list_start:list_end]

    # Safely evaluate the string to a Python list
    presets_list = ast.literal_eval(presets_list_str)

    cleaned_presets = []
    for preset in presets_list:
        # Skip NVIDIA NIM and old image generation presets
        if "nvidia-nemotron-test" in preset["id"] or "IMAGE_GEN_" in preset["id"]:
            continue

        # Update primary_id
        if "primary_id" in preset:
            preset["primary_id"] = clean_model_id(preset["primary_id"])

        # Update routing
        if "routing" in preset:
            new_routing = {}
            for phase, model_id in preset["routing"].items():
                cleaned_id = clean_model_id(model_id)
                new_routing[phase] = cleaned_id
            preset["routing"] = new_routing

        # Update fallback_routing
        if "fallback_routing" in preset:
            new_fallback_routing = {}
            for phase, model_id in preset["fallback_routing"].items():
                cleaned_id = clean_model_id(model_id)
                new_fallback_routing[phase] = cleaned_id
            preset["fallback_routing"] = new_fallback_routing

        # Update required_env_vars
        if "required_env_vars" in preset:
            if preset["id"].startswith("cross-language"):
                preset["required_env_vars"] = ["OPENROUTER_API_KEY", "DEEPL_API_KEY"]
            else:
                preset["required_env_vars"] = ["OPENROUTER_API_KEY"]
        else: # Add it if it's missing
             if preset["id"].startswith("cross-language"):
                preset["required_env_vars"] = ["OPENROUTER_API_KEY", "DEEPL_API_KEY"]
             else:
                preset["required_env_vars"] = ["OPENROUTER_API_KEY"]

        # Update notes to reflect OpenRouter exclusivity and remove references to specific non-OpenRouter models
        if "notes" in preset:
            new_notes = []
            for note in preset["notes"]:
                # Specific replacements for model names in notes
                note = note.replace("DeepSeek + Qwen + GLM", "OpenRouter models").replace("DeepSeek", "OpenRouter").replace("Qwen", "OpenRouter").replace("GLM", "OpenRouter").replace("Gemma", "OpenRouter")
                note = note.replace("MiMo V2 Pro", "OpenRouter/Gemini Pro").replace("MiMo V2 Flash", "OpenRouter/GPT-4o").replace("Claude Sonnet", "OpenRouter/Claude 3 Sonnet")
                note = note.replace("Kimi K2.6", "OpenRouter/Kimi")
                note = note.replace("Perplexity Sonar Pro", "OpenRouter/Perplexity Sonar")
                note = note.replace("GPT-5", "OpenRouter/GPT-4o")
                note = note.replace("Grok 4.20", "OpenRouter/Grok")
                note = note.replace("NVIDIA NIM free tier", "OpenRouter via NVIDIA NIM")
                note = note.replace("NVIDIA_API_KEY", "OPENROUTER_API_KEY")
                note = note.replace("Flux 2 Flex", "OpenRouter image model").replace("Riverflow v2 Fast Preview", "OpenRouter image model").replace("Seedream 4.5", "OpenRouter image model").replace("Flux 2 Pro", "OpenRouter image model").replace("Riverflow v2 Standard Preview", "OpenRouter image model").replace("Flux 2 Max", "OpenRouter image model").replace("Riverflow v2 Max Preview", "OpenRouter image model")
                note = note.replace("Gemini 3 Pro Image Preview", "OpenRouter image model").replace("Gemini 3.1 Flash Image Preview", "OpenRouter image model")
                note = note.replace("best text-in-image, 2K/4K support", "premium features").replace("OpenAI flagship", "OpenRouter")

                # Remove any remaining mentions of specific providers or non-OpenRouter details
                if "training lineages" in note: # Specific case for diversity note
                    note = note.replace("Phase 2: Moonshot + DeepSeek + Anthropic + Mistral — 4 different training lineages", "Phase 2: Diverse top-tier OpenRouter models for maximum epistemic diversity.")
                if "different labs" in note and "genuine diversity" in note: # Specific case for diversity note
                     note = note.replace("6 different labs = genuine epistemic diversity", "Diverse OpenRouter models for genuine epistemic diversity.")

                if "top of Artificial Analysis Intelligence Index" in note or "constitutional AI training" in note or "agentic reasoning" in note or "adversarial RL environments" in note or "SWE-Bench" in note or "DeepSearchQA" in note or "low-hallucination" in note:
                    note = note # Keep it if it describes a general model capability now covered by OpenRouter models

                # More generic replacements if needed
                note = note.replace("cross-lab", "OpenRouter").replace("cross-ecosystem", "OpenRouter")
                note = note.replace("cheap models", "cost-effective OpenRouter models").replace("top-tier models", "top-tier OpenRouter models")

                # Remove notes that specify prices or non-OpenRouter details not relevant anymore
                if "~$" in note or "$2/M" in note or "$12/M" in note or "$2.10/M" in note or "cents per run" in note or "RPM limit" in note or "free tier" in note or "paid tier" in note or "1.6T MoE" in note or "200K context" in note or "256K context" in note or "1M context" in note or "1T MoE" in note or "4 different training lineages" in note or "3 different training paradigms" in note or "4 different labs" in note or "6 ecosystems" in note or "500K chars/month" in note or "50M chars/month" in note or "34% hallucination" in note or "85K+" in note or "40 RPM" in note or "Parallel mode" in note or "Sequential mode" in note or "NVIDIA-developed model" in note or "new lab diversity" in note or "Fallback chain uses OpenRouter models if NVIDIA API fails" in note:
                    continue # Skip this note if it contains specific pricing or model-specific details no longer relevant.

                new_notes.append(note)
            preset["notes"] = list(set([n.strip() for n in new_notes if n.strip()])) # Remove duplicates and empty strings
        
        # Add image generation presets back, but OpenRouter-exclusive
        if "image-generation" in preset["id"]:
            preset["primary_id"] = "openrouter/image-gen"
            preset["routing"] = {}
            preset["fallback_routing"] = {}
            preset["required_env_vars"] = ["OPENROUTER_API_KEY"]
            preset["notes"] = ["Uses OpenRouter's routing for image generation."]

        cleaned_presets.append(preset)

    return cleaned_presets

def format_presets_as_string(presets):
    import json
    formatted_string = "_PRESET_CONFIGS: list[dict] = [
"
    for i, preset in enumerate(presets):
        formatted_string += "    {
"
        for key, value in preset.items():
            if key == "notes":
                notes_str = json.dumps(value, indent=12)
                formatted_string += f"        "notes": {notes_str},
"
            elif key == "routing" or key == "fallback_routing":
                routing_str = json.dumps(value, indent=12)
                formatted_string += f"        "{key}": {routing_str},
"
            else:
                formatted_string += f"        "{key}": {json.dumps(value)},
"
        formatted_string = formatted_string.rstrip(",
") + "
    }"
        if i < len(presets) - 1:
            formatted_string += ",
"
            if "Multi-Perspective" in preset["name"] or "Debate" in preset["name"] or "Jury" in preset["name"] or "Research" in preset["name"] or "Scientific" in preset["name"] or "Socratic" in preset["name"] or "Pre-Mortem" in preset["name"] or "Bayesian" in preset["name"] or "Dialectical" in preset["name"] or "Analogical" in preset["name"] or "Delphi" in preset["name"] or "CoVe" in preset["name"] or "SoT" in preset["name"] or "ToT" in preset["name"] or "PoT" in preset["name"] or "Self-Discover" in preset["name"] or "SubAgent" in preset["name"] or "Writing" in preset["name"] or "Cross-Language" in preset["name"] or "Image Generation" in preset["name"]:
                formatted_string += "
    # ── " + preset["name"].split(" (")[0].replace("Multi-Perspective", "Multi-Perspective").replace("Jury / Orchestrated", "Jury").replace("Writing / Article", "Writing") + " ───────────────────────────────────────────
"


    formatted_string += "
]
"
    return formatted_string

# Read the original file content
with open('src/reasoner/domain/preset_registry.py', 'r') as f:
    full_content = f.read()

# Get the existing PRESETS dictionary definition for re-appending later
start_presets = full_content.find("PRESETS: dict[str, PipelinePreset] = {")
existing_presets_dict_definition = full_content[start_presets:]

# Process the presets
cleaned_presets_list = process_presets(full_content)
formatted_new_presets = format_presets_as_string(cleaned_presets_list)

# Combine the new _PRESET_CONFIGS with the existing PRESETS definition
final_output = formatted_new_presets + "
" + existing_presets_dict_definition

# Print the final output (this will be captured by run_shell_command)
print(final_output)
