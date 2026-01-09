import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from gruut import sentences
from google.cloud import translate_v2 as translate

app = Flask(__name__)
CORS(app)

# AUTHENTICATION
# Render Secret File path - ensure this matches your Render Dashboard filename
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/etc/secrets/serviceaccount.json'
translate_client = translate.Client()

# PHONETIC MAPPINGS
MAPS = {
    'hebrew': {
        'consonants': {
            'p': 'פּ', 'b': 'בּ', 't': 'ט', 'd': 'ד', 'k': 'כּ', 'ɡ': 'ג',
            'f': 'פ', 'v': 'ב', 's': 'ס', 'z': 'ז', 'ʃ': 'שׁ', 'ʒ': 'ז',
            'x': 'ח', 'h': 'ה', 'm': 'מ', 'n': 'נ', 'l': 'ל', 'r': 'ר',
            'j': 'י', 'w': 'ו', 'θ': 'ת', 'ð': 'ד', 't͡ʃ': 'צ׳', 'd͡ʒ': 'ג׳',
            'ŋ': 'נ', 'ɹ': 'ר', 'ɾ': 'ר'
        },
        'vowels': {
            'a': '\u05B8', 'æ': '\u05B7', 'e': '\u05B6', 'i': '\u05B4', 
            'o': '\u05B9', 'u': '\u05BB', 'ə': '\u05B0', 'ɪ': '\u05B4', 
            'ʊ': '\u05BB', 'ʌ': '\u05B8', 'ɛ': '\u05B6', 'ɑ': '\u05B8',
            'ɔ': '\u05B8', 'oʊ': '\u05B9', 'ɚ': '\u05B0ר', 'ɝ': '\u05B0ר'
        },
        'sofit': {'כּ': 'ך', 'כ': 'ך', 'מ': 'ם', 'נ': 'ן', 'פּ': 'ף', 'פ': 'ף', 'צ': 'ץ'},
        'target': 'he'
    },
    'arabic': {
        'consonants': {
            'p': 'ب', 'b': 'ب', 't': 'ت', 'd': 'د', 'k': 'ك', 'ɡ': 'ज',
            'f': 'ف', 'v': 'ف', 's': 'س', 'z': 'ز', 'ʃ': 'ش', 'ʒ': 'ج',
            'x': 'خ', 'h': 'ه', 'm': 'م', 'n': 'न', 'l': 'ल', 'r': 'ر',
            'j': 'ي', 'w': 'و', 'θ': 'ث', 'ð': 'ذ', 't͡ʃ': 'تش', 'd͡ʒ': 'ج',
            'ŋ': 'ن', 'ɹ': 'ر', 'ɾ': 'ر'
        },
        'vowels': {
            'a': '\u064E', 'æ': '\u064E', 'e': '\u0650', 'i': '\u0650', 
            'o': '\u064F', 'u': '\u064F', 'ə': '\u0652', 'ɪ': '\u0650', 
            'ʊ': '\u064F', 'ʌ': '\u064E', 'ɛ': '\u0650', 'ɑ': '\u064E',
            'ɔ': '\u064E', 'oʊ': '\u064F', 'ɚ': '\u064Eر', 'ɝ': '\u064Eر'
        },
        'sofit': {},
        'target': 'ar'
    },
    'indian': {
        'consonants': {
            'p': 'प', 'b': 'ब', 't': 'त', 'd': 'द', 'क': 'क', 'ɡ': 'ग',
            'f': 'फ़', 'v': 'व', 's': 'स', 'z': 'ज़', 'ʃ': 'श', 'ʒ': 'झ',
            'x': 'ख', 'h': 'ह', 'm': 'म', 'n': 'न', 'l': 'ल', 'r': 'र',
            'j': 'य', 'w': 'व', 'θ': 'थ', 'ð': 'द', 't͡ʃ': 'च', 'd͡ʒ': 'ज',
            'ŋ': 'ङ', 'ɹ': 'र', 'ɾ': 'र'
        },
        'vowels': {
            'a': 'ा', 'æ': 'ा', 'e': 'े', 'i': 'ि', 
            'o': 'ो', 'u': 'ु', 'ə': '', 'ɪ': 'ि', 
            'ʊ': 'ु', 'ʌ': 'ा', 'ɛ': 'े', 'ɑ': 'ा',
            'ɔ': 'ो', 'oʊ': 'ो', 'ɚ': 'र', 'ɝ': 'र'
        },
        'sofit': {},
        'target': 'hi'
    }
}

def get_phonetic_sig(name, mode):
    cfg = MAPS.get(mode, MAPS['hebrew'])
    try:
        ipa_list = []
        for sentence in sentences(name, lang="en-us"):
            for word in sentence:
                if word.phonemes: ipa_list.extend(word.phonemes)
        
        sig = ""
        last_was_con = False
        for p in ipa_list:
            if p in cfg['consonants']:
                sig += cfg['consonants'][p]
                last_was_con = True
            elif p in cfg['vowels']:
                if mode == 'hebrew':
                    anchor = 'א' if not last_was_con else ''
                    sig += anchor + cfg['vowels'][p]
                elif mode == 'arabic':
                    anchor = 'ا' if not last_was_con else ''
                    sig += anchor + cfg['vowels'][p]
                else: # Indian
                    sig += cfg['vowels'][p]
                last_was_con = 'ר' in cfg['vowels'][p] or mode == 'indian'

        if mode == 'hebrew':
            chars = list(sig)
            for j in range(len(chars)-1, -1, -1):
                if chars[j] in cfg['sofit']:
                    chars[j] = cfg['sofit'][chars[j]]
                    break
            sig = "".join(chars)
        return sig
    except: return "???"

# --- HEARTBEAT ENDPOINT ---
@app.route('/awake', methods=['GET'])
def awake():
    """Endpoint for cron-job.org to keep the server from sleeping."""
    return "The Oracle is conscious.", 200

@app.route('/oracle', methods=['POST'])
def oracle():
    data = request.json
    text = data.get('name', '')
    mode = data.get('mode', 'hebrew')
    
    words = text.split()
    parts = [get_phonetic_sig(w, mode) for w in words]
    full_sig = " ".join(parts)
    
    target = MAPS.get(mode, MAPS['hebrew'])['target']
    result = translate_client.translate(full_sig, target_language='en', source_language=target)
    
    return jsonify({
        "signature": full_sig,
        "interpretation": result['translatedText']
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)