#!/usr/bin/env python3
"""
Script de teste para extração de keywords.
Demonstra como a busca agora funciona.
"""

import re

# Stop words em português
STOP_WORDS = {
    'a', 'o', 'as', 'os', 'de', 'da', 'do', 'das', 'dos', 'em', 'no', 'na', 'nos', 'nas',
    'um', 'uma', 'uns', 'umas', 'por', 'para', 'com', 'sem', 'sob', 'sobre',
    'que', 'qual', 'quais', 'quando', 'onde', 'como', 'é', 'são', 'era', 'eram',
    'foi', 'foram', 'ser', 'estar', 'ter', 'haver', 'fazer', 'ir', 'vir', 'ver',
    'e', 'ou', 'mas', 'se', 'não', 'também', 'só', 'já', 'mais', 'muito', 'esse',
    'essa', 'este', 'esta', 'isso', 'isto', 'aquele', 'aquela', 'aquilo', 'me', 'te',
    'lhe', 'nos', 'vos', 'lhes', 'meu', 'teu', 'seu', 'nosso', 'vosso', 'minha',
    'tua', 'sua', 'nossa', 'vossa', 'dele', 'dela', 'deles', 'delas'
}

def extract_keywords(query: str):
    """Extract keywords from query."""
    # Convert to lowercase and remove punctuation
    clean_query = re.sub(r'[^\w\s]', ' ', query.lower())
    
    # Split into words
    words = clean_query.split()
    
    # Remove stop words and short words (< 3 chars)
    keywords = [w for w in words if w not in STOP_WORDS and len(w) >= 3]
    
    return keywords


# Testes
test_queries = [
    "qual era a cor da tela?",
    "qual era a cor do barco?",
    "onde fica o arquivo de configuração?",
    "como funciona o agente?",
    "quantos usuários estão cadastrados?"
]

print("🔍 Teste de Extração de Keywords\n")
print("=" * 60)

for query in test_queries:
    keywords = extract_keywords(query)
    print(f"\nQuery: '{query}'")
    print(f"Keywords: {keywords}")
    print(f"SQL: WHERE (content ILIKE '%{keywords[0]}%'", end="")
    for kw in keywords[1:]:
        print(f" OR content ILIKE '%{kw}%'", end="")
    print(")")

print("\n" + "=" * 60)
print("\n✅ Agora a busca procura por QUALQUER palavra-chave")
print("   em vez da frase completa!")
print("\nExemplo:")
print("  Query: 'qual era a cor da tela?'")
print("  Keywords: ['cor', 'tela']")
print("  Chunk: 'A tela era azul' ✅ MATCH (contém 'tela')")
print("  Chunk: 'A cor do barco' ✅ MATCH (contém 'cor')")
print("  Chunk: 'O céu estava bonito' ❌ NO MATCH")
