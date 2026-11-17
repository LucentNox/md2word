import os
import random
import shutil
import subprocess
import tempfile

import streamlit as st
import sympy as sp

x = sp.symbols("x")


def generate_questions(n):
    """先隨機選兩個根，再展開成題目，答案在出題時就已知。"""
    items = []
    for _ in range(n):
        r1, r2 = random.randint(-9, 9), random.randint(-9, 9)
        expr = sp.expand((x - r1) * (x - r2))
        items.append((sp.latex(expr), sp.latex(sp.factor(expr))))
    return items


def build_markdown(items):
    q = "\n".join(f"{i}. 因式分解 ${e}$" for i, (e, _) in enumerate(items, 1))
    a = "\n".join(f"{i}. ${f}$" for i, (_, f) in enumerate(items, 1))
    return f"# 因式分解練習\n\n{q}\n\n# 參考答案\n\n{a}\n"


def markdown_to_docx(md_text):
    """寫入暫存檔 → 呼叫 Pandoc → 讀回 docx 位元組。"""
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "exam.md")
        out = os.path.join(tmp, "exam.docx")
        with open(src, "w", encoding="utf-8") as f:
            f.write(md_text)
        subprocess.run(["pandoc", src, "-o", out], check=True)
        with open(out, "rb") as f:
            return f.read()


st.title("因式分解出題機（線上版）")

if shutil.which("pandoc") is None:
    st.error("伺服器找不到 Pandoc，請確認 packages.txt 已設定。")
    st.stop()

n = st.slider("題數", 5, 50, 10)

if st.button("產生題目"):
    st.session_state.md = build_markdown(generate_questions(n))

if "md" in st.session_state:
    md = st.session_state.md
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Markdown 原始碼")
        st.code(md, language="markdown")
    with col2:
        st.subheader("預覽")
        st.markdown(md)

    st.download_button(
        "下載 Word 試卷（公式可編輯）",
        data=markdown_to_docx(md),
        file_name="exam.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
