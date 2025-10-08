import re
import numpy as np 
import pandas as pd
import ast
import os
from gensim.models import Word2Vec
from nltk.corpus import stopwords
from rank_bm25 import BM25Plus

stop_words = set(stopwords.words('indonesian'))

def preprocess_text(text, use_str=True):
    text = text.lower()
    tokens = re.findall(r'\b\w+\b', text)
    if use_str:
        tokens = [t for t in tokens if t not in stop_words]
    return tokens

def expand_query(model, query_tokens, topn=5):
    valid_tokens = [w for w in query_tokens if w in model.wv]
    if not valid_tokens:
        return query_tokens

    if len(valid_tokens) == 1:
        similar = model.wv.most_similar(valid_tokens[0], topn=topn*3)
    else:
        vectors = [model.wv[w] for w in valid_tokens]
        avg_vector = np.mean(vectors, axis=0)
        similar = model.wv.similar_by_vector(avg_vector, topn=topn*3)

    added = []
    for w, _ in similar:
        if w not in valid_tokens and w not in added:
            added.append(w)
        if len(added) >= topn:
            break

    return valid_tokens + added

def load_model_and_search(query, model_name, mode):
    print(f"\n=== LOG: Sedang load model: {model_name} ===")
    print(f">>> Mode pencarian: {mode}")
    
    use_qe = mode in ["QE_STR", "QE_NOSTR"]
    use_str = mode == "QE_STR" or mode == "NO_QE"

    # Load corpus
    if use_str:
        df = pd.read_csv('data/preprocessing.csv')
        df['berita_preprocessed'] = df['berita_preprocessed'].apply(ast.literal_eval)
        corpus_tokenized = df['berita_preprocessed'].tolist()
    else:
        df = pd.read_csv('data/preprocessingnostr.csv')
        df['preprocesing-nostopremov'] = df['preprocesing-nostopremov'].apply(ast.literal_eval)
        corpus_tokenized = df['preprocesing-nostopremov'].tolist()

    bm25 = BM25Plus(corpus_tokenized, k1=1.2, b=0.75, delta=1.0)
    query_tokens = preprocess_text(query, use_str)
    print(f">>> Query awal: {query_tokens}")

    # Aman: load model hanya jika mode QE dan model_name valid
    if use_qe and model_name and model_name.strip() != "":
        model_path = f'models/{model_name}.model'
        if os.path.exists(model_path):
            print(f">>> Load model dari: {model_path}")
            model = Word2Vec.load(model_path)
            expanded_query = expand_query(model, query_tokens)
            print(f">>> Query diperluas: {expanded_query}")
        else:
            print(f">>> Model {model_name} tidak ditemukan, menggunakan query asli")
            expanded_query = query_tokens
    else:
        expanded_query = query_tokens
        print(">>> Tanpa query expansion (NO_QE).")

    # Hitung skor BM25+
    scores = bm25.get_scores(expanded_query)
    top_n = 10
    top_indices = np.argsort(scores)[::-1][:top_n]

    results = []
    for idx in top_indices:
        row = df.iloc[idx]
        results.append({
            'No': row['No'],
            'Judul': row['judul'],
            'Berita': row['berita'],
            'Tanggal': row['tanggal'],
            'Kategori': row['kategori'],
            'Link': row['link'],
            'Skor': round(scores[idx], 4)
        })

    return {
        "expanded_query": expanded_query,
        "results": results,
    }
