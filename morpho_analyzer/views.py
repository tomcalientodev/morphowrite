import json
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import IntegrityError
from django.conf import settings
import string
from typing import List
from google import genai
from google.genai import types
from pydantic import BaseModel
from .models import CachedMorphoAnalysis

def morpho_analyzer(request):
    """Renders the main workspace HTML page."""
    return render(request, 'morpho_analyzer/morpho_analyzer.html')


@csrf_exempt
def analyze_word_api(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST requests allowed'}, status=405)
        
    try:
        data = json.loads(request.body)
        raw_word = data.get('word', '').strip().lower().strip(string.punctuation)
        
        if not raw_word:
            return JsonResponse({'error': 'No word provided'}, status=400)
        
        # 🎯 CACHE CHECK: Do we already have this word analyzed in our database?
        cached_entry = CachedMorphoAnalysis.objects.filter(word=raw_word).first()
        
        if cached_entry:
            # DATABASE HIT! Serve the saved JSON instantly. No AI cost, no 503 risk!
            return JsonResponse(cached_entry.analysis_data)
            
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        
        # 1. Update our strict JSON data blueprint to match your entire framework!
        class MorphemeItem(BaseModel):
            type: str     # e.g., "Prefix", "Root", "Suffix"
            text: str     # e.g., "schol-", "-ic"
            meaning: str  # e.g., "school/leisure", "having the nature of"
            part_of_speech: str
        
        class TimelinePeriod(BaseModel):
            time_period: str # e.g., "12th Century (Origin)", "16th Century (Evolution)"
            description: str # The historical context of what happened to the word.
            
        class AnalysisResult(BaseModel):
            word: str              # The properly corrected spelling of the word
            input_word: str        # The raw text the student typed originally
            spelling_corrected: bool # True if the app fixed a typo like "schoolastic"
            is_valid_word: bool
            definition: str
            morphemes: List[MorphemeItem]
            did_you_know: str      # Your "Velcro Effect" Historical Story section
            history_timeline: List[TimelinePeriod]
            real_world_power: str  # Your Modern/Scientific connection section

        # 2. Craft the prompt combining your pedagogical rules and the typo protection
        prompt = f"""
        You are 'Word Weaver', an enthusiastic historical linguist and morphology expert for students.
        
        Analyze the student's input text: "{raw_word}"
        
        Follow these critical instructions:
        1. VALIDATION GUARD: Evaluate if the input text is a real, recognizable English word 
           (including short foundational words like 'cat', 'dog', 'run', or 'tree', even if they cannot be broken down further). 
           - If it is total gibberish, letters mashed together, numbers, or not a real word, set 'is_valid_word' to false.
           - If it is a real, legitimate English word or a fixable typo, you MUST set 'is_valid_word' to true.
        
        2. SPELLING GUARD: If 'is_valid_word' is true but the text is misspelled, determine the correct 
           intended word, set spelling_corrected to true, and perform the analysis on the corrected word.
        
        3. THE BREAKUP: If valid, isolate the true classical morphemes down to their absolute smallest, individual atomic parts. Do not combine adjacent prefixes or suffixes into a single large chunk (for example, do not bundle suffixes into '-astic'; instead, separate them cleanly into '-ast' and '-ic'). Do not hallucinate or duplicate overlapping letters. For 'scholastic', the core root is 'schol/schole' (Greek for leisure/school), followed by the suffix '-ast', and the final adjectival suffix '-ic'. For every single morpheme in the list, you MUST specify its exact grammatical function in the 'part_of_speech' field:
                - If it is a suffix like '-ment', label it 'Noun Maker'.
                - If it is a suffix like '-al' or '-ic', label it 'Adjective Maker'.
                - If it is an internal structural element like '-ast', label it 'Suffix Variant' or 'Suffix Extension'.
                - If it is a root, identify its base role (e.g., 'Noun Root', 'Verb Root').
                - If it is a prefix, label it 'Prefix (Modifies Meaning)'.
        
        5. DID YOU KNOW?: Provide one fascinating, concise storytelling hook or historical origin narrative about the word. 
           (e.g., explain how 'schole' originally meant free time or leisure for learning).
        
        6. CHRONOLOGICAL TIMELINE: Break down the historical evolution of the word into 2 to 3 chronological steps in the 'history_timeline' list. 
           - Step 1 MUST focus on its earliest known origin (e.g., Proto-Indo-European, Greek, Latin, or Old English roots).
           - Steps 2 and 3 should capture major shifts in spelling, meaning, or usage over time (e.g., how it entered Middle English, or exploded into common use in the 16th century).
           - Keep descriptions brief and highly engaging for students.
        
        7. REAL-WORLD POWER: Connect the morphemes to modern life, science, or other related words so students see the pattern.
            CRITICAL SAFETY RULE: You must verify that the related words share an actual historical, linguistic root with the target word. Do NOT just match strings based on accidental visual spelling similarities. If no related classical vocabulary words share a true etymological root, focus entirely on genuine idioms, historical compound words, or figurative phrases built directly around this specific word.
        """

        response = client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=AnalysisResult,
                temperature=0.0, # Complete mathematical consistency, no creative guessing
            ),
        )
        
        # 🛡️ SAFETY SHIELD 1: Strict Outage Handling
        # If Gemini crashes, drops the connection, or sends an unreadable payload,
        # we completely HALT. No database save happens, and we warn the student.
        if not response or not response.text:
            return JsonResponse({
                'error': 'Our linguistic engine is experiencing a temporary system outage. Please try your search again in a moment!'
            }, status=503)
            
        try:
            result_data = json.loads(response.text)
        except json.JSONDecodeError:
            return JsonResponse({
                'error': 'Our system experienced a momentary glitch processing that structure. Please try again!'
            }, status=502)

        # 🛡️ SAFETY SHIELD 2: Reject Unrecognized Words & Gibberish
        # We look closely at the boolean flag returned by Gemini.
        if not result_data.get('is_valid_word', False):
            return JsonResponse({
                'error': f'"{raw_word}" does not appear to be a recognized word. Check your spelling or try another linguistic structure!'
            }, status=400)
       
        # 🎯 SAVE TO CACHE: Save this fresh result to the database so we never look it up again
        final_verified_word = result_data.get('word', '').lower().strip()
        if not final_verified_word:
            return JsonResponse({'error': 'Linguistic structural error. Please try again.'}, status=500)

        try:
            CachedMorphoAnalysis.objects.get_or_create(
                word=final_verified_word,
                defaults={'analysis_data': result_data}
            )
        except IntegrityError:
            # If a parallel request saved this exact word a millisecond before us, 
            # pass cleanly instead of breaking the user's experience.
            pass

        return JsonResponse(result_data)
        
    except Exception as e:
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)
    


#     OLD CODE THAT WORKED for aboout 30 requests
#     @csrf_exempt
# def analyze_word_api(request):
#     if request.method != 'POST':
#         return JsonResponse({'error': 'Only POST requests allowed'}, status=405)
        
#     try:
#         data = json.loads(request.body)
#         raw_word = data.get('word', '').strip().lower().strip(string.punctuation)
        
#         if not raw_word:
#             return JsonResponse({'error': 'No word provided'}, status=400)
        
#         # 🎯 CACHE CHECK: Do we already have this word analyzed in our database?
#         cached_entry = CachedMorphoAnalysis.objects.filter(word=raw_word).first()
        
#         if cached_entry:
#             # DATABASE HIT! Serve the saved JSON instantly. No AI cost, no 503 risk!
#             return JsonResponse(cached_entry.analysis_data)
            
#         client = genai.Client(api_key=settings.GEMINI_API_KEY)
        
#         # 1. Update our strict JSON data blueprint to match your entire framework!
#         class MorphemeItem(BaseModel):
#             type: str     # e.g., "Prefix", "Root", "Suffix"
#             text: str     # e.g., "schol-", "-ic"
#             meaning: str  # e.g., "school/leisure", "having the nature of"
#             part_of_speech: str
        
#         class TimelinePeriod(BaseModel):
#             time_period: str # e.g., "12th Century (Origin)", "16th Century (Evolution)"
#             description: str # The historical context of what happened to the word.
            
#         class AnalysisResult(BaseModel):
#             word: str              # The properly corrected spelling of the word
#             input_word: str        # The raw text the student typed originally
#             spelling_corrected: bool # True if the app fixed a typo like "schoolastic"
#             is_valid_word: bool
#             definition: str
#             morphemes: List[MorphemeItem]
#             did_you_know: str      # Your "Velcro Effect" Historical Story section
#             history_timeline: List[TimelinePeriod]
#             real_world_power: str  # Your Modern/Scientific connection section

#         # 2. Craft the prompt combining your pedagogical rules and the typo protection
#         prompt = f"""
#         You are 'Word Weaver', an enthusiastic historical linguist and morphology expert for students.
        
#         Analyze the student's input text: "{raw_word}"
        
#         Follow these critical instructions:
#         1. VALIDATION GUARD: Evaluate if the input text is a real, recognizable English word 
#            (including short foundational words like 'cat', 'dog', 'run', or 'tree', even if they cannot be broken down further). 
#            - If it is total gibberish, letters mashed together, numbers, or not a real word, set 'is_valid_word' to false.
#            - If it is a real, legitimate English word or a fixable typo, you MUST set 'is_valid_word' to true.
        
#         2. SPELLING GUARD: If 'is_valid_word' is true but the text is misspelled, determine the correct 
#            intended word, set spelling_corrected to true, and perform the analysis on the corrected word.
        
#         3. THE BREAKUP: If valid, isolate the true classical morphemes down to their absolute smallest, individual atomic parts. Do not combine adjacent prefixes or suffixes into a single large chunk (for example, do not bundle suffixes into '-astic'; instead, separate them cleanly into '-ast' and '-ic'). Do not hallucinate or duplicate overlapping letters. For 'scholastic', the core root is 'schol/schole' (Greek for leisure/school), followed by the suffix '-ast', and the final adjectival suffix '-ic'. For every single morpheme in the list, you MUST specify its exact grammatical function in the 'part_of_speech' field:
#                 - If it is a suffix like '-ment', label it 'Noun Maker'.
#                 - If it is a suffix like '-al' or '-ic', label it 'Adjective Maker'.
#                 - If it is an internal structural element like '-ast', label it 'Suffix Variant' or 'Suffix Extension'.
#                 - If it is a root, identify its base role (e.g., 'Noun Root', 'Verb Root').
#                 - If it is a prefix, label it 'Prefix (Modifies Meaning)'.
        
#         5. DID YOU KNOW?: Provide one fascinating, concise storytelling hook or historical origin narrative about the word. 
#            (e.g., explain how 'schole' originally meant free time or leisure for learning).
        
#         6. CHRONOLOGICAL TIMELINE: Break down the historical evolution of the word into 2 to 3 chronological steps in the 'history_timeline' list. 
#            - Step 1 MUST focus on its earliest known origin (e.g., Proto-Indo-European, Greek, Latin, or Old English roots).
#            - Steps 2 and 3 should capture major shifts in spelling, meaning, or usage over time (e.g., how it entered Middle English, or exploded into common use in the 16th century).
#            - Keep descriptions brief and highly engaging for students.
        
#         7. REAL-WORLD POWER: Connect the morphemes to modern life, science, or other related words so students see the pattern.
#             CRITICAL SAFETY RULE: You must verify that the related words share an actual historical, linguistic root with the target word. Do NOT just match strings based on accidental visual spelling similarities. If no related classical vocabulary words share a true etymological root, focus entirely on genuine idioms, historical compound words, or figurative phrases built directly around this specific word.
#         """

#         response = client.models.generate_content(
#             model='gemini-2.5-flash-lite',
#             contents=prompt,
#             config=types.GenerateContentConfig(
#                 response_mime_type="application/json",
#                 response_schema=AnalysisResult,
#                 temperature=0.0, # Complete mathematical consistency, no creative guessing
#             ),
#         )
        
#         # 🛡️ SAFETY SHIELD 1: Strict Outage Handling
#         # If Gemini crashes, drops the connection, or sends an unreadable payload,
#         # we completely HALT. No database save happens, and we warn the student.
#         if not response or not response.text:
#             return JsonResponse({
#                 'error': 'Our linguistic engine is experiencing a temporary system outage. Please try your search again in a moment!'
#             }, status=503)
            
#         try:
#             result_data = json.loads(response.text)
#         except json.JSONDecodeError:
#             return JsonResponse({
#                 'error': 'Our system experienced a momentary glitch processing that structure. Please try again!'
#             }, status=502)

#         # 🛡️ SAFETY SHIELD 2: Reject Unrecognized Words & Gibberish
#         # We look closely at the boolean flag returned by Gemini.
#         if not result_data.get('is_valid_word', False):
#             return JsonResponse({
#                 'error': f'"{raw_word}" does not appear to be a recognized word. Check your spelling or try another linguistic structure!'
#             }, status=400)
       
#         # 🎯 SAVE TO CACHE: Save this fresh result to the database so we never look it up again
#         final_verified_word = result_data.get('word', '').lower().strip()
#         if not final_verified_word:
#             return JsonResponse({'error': 'Linguistic structural error. Please try again.'}, status=500)

#         try:
#             CachedMorphoAnalysis.objects.get_or_create(
#                 word=final_verified_word,
#                 defaults={'analysis_data': result_data}
#             )
#         except IntegrityError:
#             # If a parallel request saved this exact word a millisecond before us, 
#             # pass cleanly instead of breaking the user's experience.
#             pass

#         return JsonResponse(result_data)
        
#     except Exception as e:
#         return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)