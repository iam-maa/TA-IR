from flask import Flask, render_template, request, redirect, url_for, send_file
from model_loader import load_model_and_search
from model_labels import MODEL_LABELS
import json
import os
import io
import csv

app = Flask(__name__)

RELEVANSI_FILE = 'data/relevansi.json'

@app.route("/", methods=["GET", "POST"])
def index():
    results = []
    expanded_query = []
    query = ""
    mode = ""
    selected_model_label = ""

    if request.method == "POST":
        query = request.form["query"]
        model_name = request.form["model"]
        mode = request.form["mode"]

        search_result = load_model_and_search(query, model_name, mode)
        expanded_query = search_result["expanded_query"]
        results = search_result["results"]

        selected_model_label = MODEL_LABELS.get(model_name, model_name)

    return render_template("index.html",
                           results=results,
                           expanded_query=expanded_query,
                           query=query,
                           mode=mode,
                           selected_model_label=selected_model_label)

@app.route("/simpan_relevansi", methods=["POST"])
def simpan_relevansi():
    query = request.form.get("query")
    model = request.form.get("model")
    validator = request.form.get("validator", "Tidak diketahui")
    data = request.form.to_dict()

    relevan = []
    tidak_relevan = []

    for k, v in data.items():
        if k.startswith("relevansi_"):
            doc_id = k.split("_")[1]
            if v == "relevan":
                relevan.append(doc_id)
            elif v == "tidak":
                tidak_relevan.append(doc_id)

    simpanan = {
        "query": query,
        "model": model,
        "validator": validator,
        "dokumen_relevan": relevan,
        "dokumen_tidak_relevan": tidak_relevan,
        "total_relevan": len(relevan),
        "total_tidak_relevan": len(tidak_relevan)
    }

    if os.path.exists(RELEVANSI_FILE):
        with open(RELEVANSI_FILE, "r") as f:
            all_data = json.load(f)
    else:
        all_data = []

    all_data.append(simpanan)

    with open(RELEVANSI_FILE, "w") as f:
        json.dump(all_data, f, indent=2)

    return redirect(url_for("lihat_relevansi"))

@app.route("/lihat_relevansi")
def lihat_relevansi():
    if os.path.exists(RELEVANSI_FILE):
        with open(RELEVANSI_FILE, "r") as f:
            data = json.load(f)
    else:
        data = []

    # Pagination
    page = request.args.get("page", 1, type=int)
    per_page = 10
    total_pages = (len(data) + per_page - 1) // per_page
    start = (page - 1) * per_page
    end = start + per_page
    page_data = data[start:end]

    return render_template("relevansi.html",
                           data=page_data,
                           page=page,
                            per_page=per_page,
                           total_pages=total_pages)

@app.route("/download_csv")
def download_csv():
    if not os.path.exists(RELEVANSI_FILE):
        return "Data relevansi tidak ditemukan", 404

    with open(RELEVANSI_FILE, "r") as f:
        data = json.load(f)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Query", "Model", "Validator", "Dokumen Relevan", "Dokumen Tidak Relevan", "Total Relevan", "Total Tidak Relevan"])

    for row in data:
        writer.writerow([
            row["query"],
            row["model"],
            row.get("validator", ""),
            ", ".join(row["dokumen_relevan"]),
            ", ".join(row["dokumen_tidak_relevan"]),
            row["total_relevan"],
            row["total_tidak_relevan"]
        ])

    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode("utf-8")),
        mimetype="text/csv",
        as_attachment=True,
        download_name="data_relevansi.csv"
    )

@app.route("/relevansi/hapus/<int:index>")
def hapus_relevansi(index):
    with open(RELEVANSI_FILE, "r") as f:
        data = json.load(f)

    if 0 <= index < len(data):
        data.pop(index)

        with open(RELEVANSI_FILE, "w") as f:
            json.dump(data, f, indent=4)

    return redirect(url_for("lihat_relevansi"))

@app.route("/relevansi/edit/<int:index>", methods=["GET"])
def edit_relevansi(index):
    with open(RELEVANSI_FILE, "r") as f:
        data = json.load(f)

    if 0 <= index < len(data):
        item = data[index]
        return render_template("edit_relevansi.html", item=item, index=index)
    else:
        return redirect(url_for("lihat_relevansi"))

@app.route("/relevansi/update/<int:index>", methods=["POST"])
def update_relevansi(index):
    if os.path.exists(RELEVANSI_FILE):
        with open(RELEVANSI_FILE, "r") as f:
            data = json.load(f)
    else:
        return redirect(url_for("lihat_relevansi"))

    if 0 <= index < len(data):
        relevan_str = request.form.get("dokumen_relevan", "")
        tidak_relevan_str = request.form.get("dokumen_tidak_relevan", "")

        relevan = [s.strip() for s in relevan_str.split(",") if s.strip()]
        tidak_relevan = [s.strip() for s in tidak_relevan_str.split(",") if s.strip()]

        data[index]["dokumen_relevan"] = relevan
        data[index]["dokumen_tidak_relevan"] = tidak_relevan
        data[index]["total_relevan"] = len(relevan)
        data[index]["total_tidak_relevan"] = len(tidak_relevan)

        with open(RELEVANSI_FILE, "w") as f:
            json.dump(data, f, indent=2)

    return redirect(url_for("lihat_relevansi"))

if __name__ == "__main__":
    app.run(debug=True)
