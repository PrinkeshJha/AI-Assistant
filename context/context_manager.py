import re

def resolve_pronouns(query: str, ctx: dict) -> str:
    """
    Replaces pronouns in the query with the most recent entity of matching type from ctx.
    - he/him/his/she/her/hers -> last_person
    - it/its -> last_city, last_topic, last_organization, last_article (in order of recency/presence)
    - there -> in last_city
    """
    resolved = query
    
    # Backward compatibility with Phase 1 tests using last_subject
    if 'last_subject' in ctx and ctx['last_subject']:
        subject = ctx['last_subject']
        # If there's a pronoun, we replace it
        resolved = re.sub(r"\b(he|him|his|she|her|hers|it|its)\b", subject, resolved, flags=re.IGNORECASE)
        # Also replace "there" with "in {subject}" if subject is likely a city
        if 'last_city' in ctx and ctx['last_city'] == subject:
            resolved = re.sub(r"\bthere\b", f"in {subject}", resolved, flags=re.IGNORECASE)
        return resolved

    # Type-specific pronoun resolution:
    # he/him/his/she/her/hers -> last_person
    if 'last_person' in ctx and ctx['last_person']:
        person = ctx['last_person']
        resolved = re.sub(r"\b(he|him|his|she|her|hers)\b", person, resolved, flags=re.IGNORECASE)

    # there -> in last_city
    if 'last_city' in ctx and ctx['last_city']:
        city = ctx['last_city']
        resolved = re.sub(r"\bthere\b", f"in {city}", resolved, flags=re.IGNORECASE)

    # it/its -> last_city, last_topic, last_organization, last_article
    it_replacement = None
    for key in ['last_city', 'last_topic', 'last_organization', 'last_article']:
        if key in ctx and ctx[key]:
            it_replacement = ctx[key]
            break
            
    if it_replacement:
        resolved = re.sub(r"\b(it|its)\b", it_replacement, resolved, flags=re.IGNORECASE)
        
    return resolved

def is_ellipsis_or_fragment(query: str, nlp) -> bool:
    """
    Checks if the query is an ellipsis or fragment that needs merging with the previous turn.
    """
    clean = query.strip().lower()
    
    # Common ellipsis and query fragment prefixes
    prefixes = ["what about", "how about", "and ", "or ", "in ", "for ", "about ", "what of"]
    if any(clean.startswith(p) for p in prefixes):
        return True
        
    # If the query is short and has no verb/auxiliary verb, it is likely a fragment
    doc = nlp(query)
    has_verb = any(token.pos_ in ["VERB", "AUX"] for token in doc)
    if len(doc) <= 3 and not has_verb:
        return True
        
    return False

def merge_context(prev_query: str, current_query: str, nlp) -> str:
    """
    Merges the current query fragment/ellipsis with the previous query.
    """
    prev_doc = nlp(prev_query)
    curr_doc = nlp(current_query)
    
    # Extract entities by label
    curr_ents = {ent.label_: ent.text for ent in curr_doc.ents}
    prev_ents = {ent.label_: ent.text for ent in prev_doc.ents}
    
    merged = prev_query
    replaced = False
    
    # Replace overlapping entities (e.g. city with city, person with person)
    for label, curr_text in curr_ents.items():
        if label in prev_ents:
            prev_text = prev_ents[label]
            pattern = re.compile(re.escape(prev_text), re.IGNORECASE)
            merged = pattern.sub(curr_text, merged)
            replaced = True
            
    if replaced:
        return merged

    # Handle prefix-based fragments
    clean_curr = current_query.strip().lower()
    for prefix in ["what about ", "how about ", "and ", "or ", "in ", "for ", "about "]:
        if clean_curr.startswith(prefix):
            suffix = current_query.strip()[len(prefix):].strip()
            prev_clean = prev_query.rstrip("?. ")
            return f"{prev_clean} {suffix}"
            
    # Default fallback: append
    prev_clean = prev_query.rstrip("?. ")
    return f"{prev_clean} {current_query.strip()}"

def update_entities_from_doc(doc, ctx: dict):
    """
    Extracts entities from the spacy doc and updates the session context.
    Also tracks last_subject for compatibility.
    """
    for ent in doc.ents:
        text = ent.text
        if ent.label_ == "GPE":
            ctx['last_city'] = text
            ctx['last_entity'] = text
            ctx['last_subject'] = text
        elif ent.label_ == "PERSON":
            ctx['last_person'] = text
            ctx['last_entity'] = text
            ctx['last_subject'] = text
        elif ent.label_ == "ORG":
            ctx['last_organization'] = text
            ctx['last_entity'] = text
            ctx['last_subject'] = text
        elif ent.label_ in ["PRODUCT", "WORK_OF_ART", "EVENT"]:
            ctx['last_topic'] = text
            ctx['last_entity'] = text
            ctx['last_subject'] = text

def add_to_history(query: str, intent: str, entities: list, ctx: dict, response: str = None):
    """
    Appends a turn to the history list in the context, capped at 10 items.
    """
    history = ctx.get('history', [])
    history.append({
        'query': query,
        'intent': intent,
        'entities': entities,
        'response': response
    })
    if len(history) > 10:
        history = history[-10:]
    ctx['history'] = history
