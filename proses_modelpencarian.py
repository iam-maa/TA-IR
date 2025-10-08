import re #untuk tokenisasi (memecah teks ke kata)
import numpy as np 
import pandas as pd
import ast
import time
import nltk
from gensim.models import Word2Vec
from nltk.corpus import stopwords
from rank_bm25 import BM25Plus
nltk.download('stopwords')
stop_words = set(stopwords.words('indonesian'))

#preprocessing
def preprocess_text(text, use_str=True):
    text = text.lower()
    tokens = re.findall(r'\b\w+\b', text)
    if use_str:
        tokens = [t for t in tokens if t not in stop_words]  # hanya hapus stopword jika STR
    return tokens

#Fungsi Expanded Query
#model = model Word2Vec yang sudah dilatih
def expand_query(model, query_tokens, topn=5): 
    valid_tokens = [w for w in query_tokens if w in model.wv]
    if not valid_tokens:
        return query_tokens

    # Ambil kandidat lebih banyak untuk bisa dipilih top 'topn'
    if len(valid_tokens) == 1:
        similar = model.wv.most_similar(valid_tokens[0], topn=topn*2)
    else:
        vectors = [model.wv[w] for w in valid_tokens]
        avg_vector = np.mean(vectors, axis=0)
        similar = model.wv.most_similar(avg_vector, topn=topn*2)

    added_words, added_scores = [], []
    for w, score in similar:
        if w not in valid_tokens and w not in added_words:
            added_words.append(w)
            added_scores.append(score)
        if len(added_words) >= topn:
            break

    print("Top expansion words:")
    for w, score in zip(added_words, added_scores):
        print(f"  {w}: {score:.4f}")

    expanded = valid_tokens + added_words
    return expanded

#PENCARIAN DOKUMEN BM25+
#model_name: nama model Word2Vec yang akan diload
#mode = mode pencarian (QE tanpa Stopword Removal, QE dengan Stopword Removal, Tanpa QE)
def load_model_and_search(query, model_name, mode):
    start_time = time.time()
    print(f"\n=== LOG: Sedang load model: {model_name} ===")
    print(f">>> Mode pencarian: {mode}")
    
    use_qe = mode in ["QE_STR", "QE_NOSTR"]
    use_str = mode == "QE_STR" or mode == "NO_QE"

    # Load corpus yang telah dipreprocessing dengan menggunakan Stopword Removal atau tidak
    if use_str:
        print(">>> Memakai CORPUS STR")
        df = pd.read_csv('data/preprocessing.csv')
        df['berita_preprocessed'] = df['berita_preprocessed'].apply(ast.literal_eval)
        corpus_tokenized = df['berita_preprocessed'].tolist()
    else:
        print(">>> Memakai CORPUS NON STR")
        df = pd.read_csv('data/preprocessingnostr.csv')
        df['preprocesing-nostopremov'] = df['preprocesing-nostopremov'].apply(ast.literal_eval)
        corpus_tokenized = df['preprocesing-nostopremov'].tolist()


    #corpus_tokenized = [preprocess_text(doc, use_str) for doc in corpus]
#Inisialisasi BM25+
    bm25 = BM25Plus(corpus_tokenized, k1=1.2, b=0.75, delta=1.0)
    #preprocessing query
    query_tokens = preprocess_text(query, use_str)
    print(f">>> Query awal: {query_tokens}")

    
    if use_qe: #jika menggunakan stopwordremoval (use_str)
        model_path = f'models/{model_name}.model'
        print(f">>> Load model dari: {model_path}")
        model = Word2Vec.load(model_path)
        expanded_query = expand_query(model, query_tokens)
        print(f">>> Query diperluas: {expanded_query}")
    else:
        expanded_query = query_tokens
        print(">>> Tanpa query expansion.")
    #Hitung skor BM25+
    scores = bm25.get_scores(expanded_query) #Menghitung skor BM25+ untuk semua dokumen terhadap query (atau query yang diperluas).
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

    end_time = time.time()  # selesai
    elapsed_time = end_time - start_time
    print(f">>> Waktu komputasi: {elapsed_time:.4f} detik")

    return {
        "expanded_query": expanded_query,
        "results": results,
        #"elapsed_time": elapsed_time,

    }
